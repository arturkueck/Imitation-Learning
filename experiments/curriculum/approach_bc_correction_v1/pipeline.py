"""Targeted BC action/completion learning from expert second-approach corrections."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('correction_bc_helpers',HERE.parent/'phase_skill_audit_v1/audit.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
read,write=h.read,h.write


def span(pair):return list(range(pair[0],pair[1]+1))


def validate(plan):
    sets=[set(span(plan[k])) for k in ('train_seeds','validation_seeds','development_seeds','confirmation_seeds')]
    if any(not s for s in sets) or any(a&b for i,a in enumerate(sets) for b in sets[i+1:]):raise ValueError('Overlapping scene families')
    if set(plan['smoke_seeds'])&set.union(*sets):raise ValueError('Technical fixtures overlap scientific families')
    if plan['batch_size']!=64 or plan['correction_fraction']!=.5:raise ValueError('Expected matched 32 replay + 32 correction batches')


def frozen_except_approach(model):
    for name,param in model.named_parameters():param.requires_grad_(name.startswith('heads.0.'))


def compose(reference,actor=None,completion=None,active=False):
    _,torch,_=h.libraries()
    class Composite(torch.nn.Module):
        def __init__(self):
            super().__init__();self.reference=reference;self.actor=actor;self.completion=completion;self.active=active
        def forward(self,x,phase):
            a,z=self.reference(x,phase);mask=(phase==0) if self.active else torch.zeros_like(phase,dtype=torch.bool)
            if mask.any():
                if self.actor is not None:a=a.clone();a[mask]=self.actor(x[mask],phase[mask])[0]
                if self.completion is not None:z=z.clone();z[mask]=self.completion(x[mask],phase[mask])[1]
            return a,z
    return Composite().eval()


def evaluate_episode(env,model,seed,out,deadline,plan):
    base,torch,np=h.libraries();c=base.backend();obs,initial,z=h.reset(env,seed)
    seq=c.GuardedSequencer(model,3,c.Clearance(env))
    seq.policy=h.validation.adapter.make_policy(base,c.native.historical,model,.8,lambda:seq.stage,17)
    tail=0;lift=None;adapted_frames=0;first_tower_seen=False
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline);stage,phase,retreat=seq.stage,seq.policy.phase,seq.retreat
        if hasattr(model,'active'):model.active=stage==2 and phase==0 and not retreat
        adapted_frames+=int(bool(getattr(model,'active',False)))
        if stage==2 and phase==3 and not retreat and lift is None:
            lift=dict(frame=frame,held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[2].contact_geoms)))
        pos=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        with torch.no_grad():action,_,_=seq.policy.action(obs,pos[stage-1],pos[stage])
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        m=h.measurement(env,obs,stage,z[stage],pos[stage],c)
        first_tower_seen|=m['valid'][0]
        seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        tail=tail+1 if m['valid'][-1] else 0
        if tail>=50 or seq.timed_out:break
    return dict(seed=seed,success=tail>=50,frames=frame+1,initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
        final_stage=seq.stage,final_phase=seq.policy.phase,retreat_timeout=seq.timed_out,
        second_lift=lift,adapted_frames=adapted_frames,first_tower_seen=first_tower_seen)


def collect_one(env,model,seed,plan,out,deadline):
    base,torch,np=h.libraries();c=base.backend()
    from task_extensions.stack_expert import StackExpert
    obs,initial,_=h.reset(env,seed);seq=c.GuardedSequencer(model,3,c.Clearance(env))
    seq.policy=h.validation.adapter.make_policy(base,c.native.historical,model,.8,lambda:seq.stage,17)
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline)
        pos=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if seq.stage==2 and not seq.retreat:break
        action,_,_=seq.policy.action(obs,pos[seq.stage-1],pos[seq.stage]);env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        valid=c.native.historical.old.prefix_valid(env,seq.stage+1) and not any(c.native.finger_contact(env,cube) for cube in env.cubes[:seq.stage+1])
        seq.advance(valid,env.sim.data.body_xpos[env.cube_ids[seq.stage]])
        if seq.timed_out:return [],dict(seed=seed,accepted=False,reason='prefix_retreat_timeout')
    else:return [],dict(seed=seed,accepted=False,reason='second_approach_not_reached')
    teacher=StackExpert(SimpleNamespace(base_env=env));teacher.cube_index=2
    anchor=env.sim.data.body_xpos[env.cube_ids[2]].copy();rows=[]
    state_hash=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest()
    for step in range(plan['approach_horizon']):
        base.check_stop(out,deadline)
        x=c.native.historical.vector(obs,anchor,step);action=teacher(obs);done=teacher.phase!=0
        rows.append((x,action[[0,1,2,6]],float(done)))
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        if done:return rows,dict(seed=seed,accepted=True,prefix_frames=frame,frames=len(rows),initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),entry_state_sha256=state_hash)
    return [],dict(seed=seed,accepted=False,reason='expert_approach_timeout')


def collect(out,plan,deadline):
    base,_,np=h.libraries();data={};attempts=[]
    for split in ('train','validation'):
        rows=[];families=[]
        for model_id in plan['models']:
            model,_,_=h.registry.restore(model_id,'cuda');model.eval();env=base.backend().native.historical.make_env(3)
            try:
                for seed in span(plan[split+'_seeds']):
                    write(out/'status.json',dict(state='COLLECTING',split=split,model=model_id,seed=seed,pid=os.getpid(),updated_unix=time.time()))
                    episode,info=collect_one(env,model,seed,plan,out,deadline);info.update(model=model_id,split=split);attempts.append(info)
                    rows.extend(episode);families.extend([seed]*len(episode));write(out/'collection_attempts.json',attempts)
            finally:env.close()
        if not rows:raise ValueError('No corrections in '+split)
        x=np.asarray([r[0] for r in rows],dtype=np.float32);a=np.asarray([r[1] for r in rows],dtype=np.float32);y=np.asarray([r[2] for r in rows],dtype=np.float32)
        if y.sum()<1 or not np.isfinite(x).all() or not np.isfinite(a).all():raise ValueError('Invalid correction labels')
        data[split]=(x,a,y)
        np.savez_compressed(out/f'corrections_{split}.npz',x=x,a=a,y=y,family=np.asarray(families,dtype=np.int64))
    write(out/'dataset_manifest.json',dict(attempts=len(attempts),accepted=sum(r['accepted'] for r in attempts),
        train_frames=len(data['train'][0]),validation_frames=len(data['validation'][0]),
        split_unit='whole initial scene family across all source controllers; no frame splitting',
        rejected=[r for r in attempts if not r['accepted']],
        hashes={s:base.sha(out/f'corrections_{s}.npz') for s in data}))
    return data


def save_checkpoint(path,model,opt,model_id,kind,source,update,out,plan):
    base,torch,np=h.libraries()
    ck=dict(schema='second-approach-branch-v1',model=model.state_dict(),optimizer=opt.state_dict(),model_id=model_id,
        kind=kind,source=source,update=update,next_batch=update,plan=plan,
        inputs={str(p.relative_to(ROOT)):base.sha(p) for p in [out/'plan.json',out/f'schedule_{model_id}.npz',out/'corrections_train.npz']},
        torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),numpy_rng=np.random.get_state(),python_rng=random.getstate())
    temp=path.with_suffix('.tmp');torch.save(ck,temp);temp.replace(path)


def restore_branch(path,device='cuda'):
    base,torch,np=h.libraries();ck=torch.load(path,map_location='cpu',weights_only=False)
    for name,digest in ck['inputs'].items():
        if base.sha(ROOT/name)!=digest:raise ValueError('Branch input changed: '+name)
    model,opt,_=h.registry.restore(ck['model_id'],device);frozen_except_approach(model)
    model.load_state_dict(ck['model']);opt.load_state_dict(ck['optimizer'])
    torch.set_rng_state(ck['torch_rng'])
    if device=='cuda':torch.cuda.set_rng_state_all(ck['cuda_rng'])
    np.random.set_state(ck['numpy_rng']);random.setstate(ck['python_rng'])
    return model,opt,ck


def fit_branch(out,plan,model_id,kind,source,data,old,deadline,resume=None):
    base,torch,np=h.libraries();folder=out/f'{model_id}_{source}_{kind}';folder.mkdir(exist_ok=True)
    if resume:
        cfg=h.registry.restore(model_id,'cpu')[2]['config'];model,opt,ck=restore_branch(resume);start=ck['next_batch']
    else:model,opt,ck=h.registry.restore(model_id,'cuda');cfg=ck['config'];start=0
    frozen_except_approach(model);model.train()
    with np.load(out/f'schedule_{model_id}.npz') as archive:old_ids=archive['old'];new_ids=archive['new']
    # Both branches see exactly the same replay/correction row indices.
    old_pos=min(50.,max(1.,float((1-old[2]).sum())/float(old[2].sum())))
    new_pos=min(50.,max(1.,float((1-data['train'][2]).sum())/float(data['train'][2].sum())))
    write(folder/'training_contract.json',dict(model_id=model_id,kind=kind,source=source,old_positive_weight=old_pos,new_positive_weight=new_pos,
        parent_config=cfg,trainable_phase=0,frozen_phases=list(range(1,7)),start_batch=start))
    def objective(batch,pos):
        x,a,y=[torch.as_tensor(v,device='cuda') for v in batch];p=torch.zeros(len(x),dtype=torch.long,device='cuda');pred,z=model(x,p)
        return (pred-a).square().mean() if kind=='actor' else cfg['completion_coefficient']*torch.nn.functional.binary_cross_entropy_with_logits(z,y,pos_weight=torch.tensor(pos,device='cuda'))
    logs=[]
    for update in range(start,plan['updates']):
        base.check_stop(out,deadline)
        ids=old_ids[update];first=ids[:32]
        old_loss=objective(tuple(v[first] for v in old),old_pos)
        extra=objective(tuple(v[new_ids[update]] for v in data['train']),new_pos) if source=='correction' else objective(tuple(v[ids[32:]] for v in old),old_pos)
        loss=.5*old_loss+.5*extra
        if not torch.isfinite(loss):raise FloatingPointError('Nonfinite BC loss')
        opt.zero_grad(set_to_none=True);loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['gradient_clip'])
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite gradient')
        opt.step()
        if (update+1)%plan['checkpoint_every']==0 or update+1==plan['updates']:
            checkpoint=folder/f'update_{update+1:06}.pth'
            save_checkpoint(checkpoint,model,opt,model_id,kind,source,update+1,out,plan)
            temp=folder/'latest.tmp';temp.write_bytes(checkpoint.read_bytes());temp.replace(folder/'latest.pth')
            logs.append(dict(update=update+1,loss=float(loss.detach()),replay_loss=float(old_loss.detach()),extra_loss=float(extra.detach())))
            write(folder/'loss.json',logs);write(out/'status.json',dict(state='TRAINING',pid=os.getpid(),model=model_id,kind=kind,source=source,update=update+1,updated_unix=time.time()))
    # Other heads must remain byte-identical to their B ancestor.
    reference=h.registry.restore(model_id,'cpu')[0].state_dict()
    if any(not torch.equal(v.cpu(),reference[k]) for k,v in model.state_dict().items() if not k.startswith('heads.0.')):raise ValueError('Untargeted phase changed')
    with torch.no_grad():
        x,a,y=[torch.as_tensor(v,device='cuda') for v in data['validation']]
        pred,z=model(x,torch.zeros(len(x),dtype=torch.long,device='cuda'))
        write(folder/'validation.json',dict(action_mse=float((pred-a).square().mean()),completion_bce=float(torch.nn.functional.binary_cross_entropy_with_logits(z,y)),
            completion_accuracy=float(((z.sigmoid()>=.8)==y.bool()).float().mean()),selection=False))
    return model.eval()


def worker(out,deadline):
    base,torch,np=h.libraries();plan=read(out/'plan.json');base.configure(1);verify(out)
    try:
        data=collect(out,plan,deadline);olddata=base.load_data()['train'];mask=olddata[2]==0
        old=(olddata[0][mask],olddata[1][mask],olddata[3][mask]);results=[]
        for index,model_id in enumerate(plan['models']):
            rng=np.random.default_rng(61001+index)
            np.savez_compressed(out/f'schedule_{model_id}.npz',old=rng.integers(len(old[0]),size=(plan['updates'],64),dtype=np.int32),new=rng.integers(len(data['train'][0]),size=(plan['updates'],32),dtype=np.int32))
            reference=h.registry.restore(model_id,'cuda')[0].eval();branches={}
            for source in ('replay','correction'):
                for kind in ('actor','completion'):branches[source,kind]=fit_branch(out,plan,model_id,kind,source,data,old,deadline)
            policies=dict(baseline=reference,replay=compose(reference,branches['replay','actor'],branches['replay','completion']),
                action=compose(reference,branches['correction','actor']),completion=compose(reference,completion=branches['correction','completion']),
                combined=compose(reference,branches['correction','actor'],branches['correction','completion']))
            write(out/f'composition_{model_id}.json',dict(reference=model_id,execution_scope='Only placement 2, phase 0, excluding retreat; use evaluate_episode context gate',policies={
                'baseline':{},'replay':{'actor':f'{model_id}_replay_actor/latest.pth','completion':f'{model_id}_replay_completion/latest.pth'},
                'action':{'actor':f'{model_id}_correction_actor/latest.pth'},'completion':{'completion':f'{model_id}_correction_completion/latest.pth'},
                'combined':{'actor':f'{model_id}_correction_actor/latest.pth','completion':f'{model_id}_correction_completion/latest.pth'}}))
            for panel in ('development','confirmation'):
                starts={};env=base.backend().native.historical.make_env(3)
                try:
                    for policy_name,policy in policies.items():
                        for seed in span(plan[panel+'_seeds']):
                            base.check_stop(out,deadline)
                            write(out/'status.json',dict(state='EVALUATING',pid=os.getpid(),panel=panel,model=model_id,policy=policy_name,seed=seed,updated_unix=time.time()))
                            row=evaluate_episode(env,policy,seed,out,deadline,plan)
                            if panel=='development' and policy_name=='baseline':
                                expected=next(r for r in read(ROOT/'praxis/results/curriculum/phase_skill_audit_v1/run_001/full_rollouts.json') if r['model']==model_id and r['seed']==seed)
                                if any(row[k]!=expected[k] for k in ('success','frames','initial_sha256','final_stage','final_phase','retreat_timeout')):raise ValueError('Baseline regression against previous evaluator')
                            if seed in starts and starts[seed]!=row['initial_sha256']:raise ValueError('Evaluation starts differ')
                            starts[seed]=row['initial_sha256'];row.update(model=model_id,policy=policy_name,panel=panel);results.append(row)
                            with (out/'rollouts.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                    write(out/'rollouts.json',results)
                finally:env.close()
        summary={panel:{m:{p:dict(n=sum(r['model']==m and r['policy']==p and r['panel']==panel for r in results),successes=sum(r['success'] for r in results if r['model']==m and r['policy']==p and r['panel']==panel)) for p in plan['policies']} for m in plan['models']} for panel in ('development','confirmation')}
        write(out/'summary.json',summary)
        pairs={}
        for panel in summary:
            pairs[panel]={}
            for m in plan['models']:
                pairs[panel][m]={}
                for comparator in ('baseline','replay'):
                    baseline={r['seed']:r['success'] for r in results if r['panel']==panel and r['model']==m and r['policy']==comparator}
                    pairs[panel][m][comparator]={p:dict(gains=sum(r['success'] and not baseline[r['seed']] for r in results if r['panel']==panel and r['model']==m and r['policy']==p),
                        losses=sum(not r['success'] and baseline[r['seed']] for r in results if r['panel']==panel and r['model']==m and r['policy']==p)) for p in plan['policies']}
        write(out/'paired_changes.json',pairs)
        lines=['# BC-Korrekturtraining: Ergebnis','',f"Technical only: {plan['technical_only']}. Fester Endpunkt: {plan['updates']} Updates je Komponente.",'',
               '| Panel | Modell | Ausführung | Erfolge | Gewinne / Verluste gegen B | Gewinne / Verluste gegen Replay |','|---|---|---|---:|---:|---:|']
        for panel,models in summary.items():
            for m,policies in models.items():
                for p,value in policies.items():
                    b=pairs[panel][m]['baseline'][p];r=pairs[panel][m]['replay'][p]
                    lines.append(f"| {panel} | {m} | {p} | {value['successes']}/{value['n']} | {b['gains']} / {b['losses']} | {r['gains']} / {r['losses']} |")
        lines+=['','Getrennte Aktions-/Abschlusskomponenten; nur Phase 0 angepasst. Kein Curriculum-Reihenfolgeexperiment. Gemeinsame Szenen je Modellseed; keine unabhängigen Szenen über Modellseeds unterstellen. Entwicklung und Bestätigung getrennt auswerten. Technische Läufe sind aus Forschungsresultaten ausgeschlossen.']
        (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');verify(out)
        write(out/'status.json',dict(state='COMPLETE',pid=os.getpid(),technical_only=plan['technical_only'],updated_unix=time.time()))
    except BaseException as exc:
        write(out/'status.json',dict(state='FAILED',error=repr(exc),traceback=traceback.format_exc(),updated_unix=time.time()));raise


def verify(out):
    base,_,_=h.libraries()
    for path,digest in read(out/'provenance.json').items():
        if base.sha(ROOT/path)!=digest:raise ValueError('Changed input: '+path)


def prepare(out,smoke):
    plan=read(HERE/'config.json');validate(plan)
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Require new workspace folder')
    plan['technical_only']=smoke
    if smoke:
        plan.update(models=plan['models'][:1],train_seeds=plan['smoke_seeds'][:3:2],validation_seeds=plan['smoke_seeds'][3::2],
            development_seeds=[2026113000]*2,confirmation_seeds=[2026113002]*2,updates=4,checkpoint_every=2)
    base,torch,np=h.libraries();base.backend();out.mkdir(parents=True);write(out/'plan.json',plan)
    entries=read(HERE.parent/'models.json')['models']
    files={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT) and (ROOT/'praxis/.venv') not in Path(m.__file__).resolve().parents}
    files.update([Path(__file__),HERE/'config.json',HERE/'README.md',HERE.parent/'phase_skill_audit_v1/audit.py',HERE.parent/'registry.py',base.ARRAYS,base.MANIFEST,HERE.parent/'axis_bc_clock_validation_20261112/policy.py',HERE.parent/'grasp_phase_ablation_v1/pipeline.py',ROOT/'praxis/results/curriculum/phase_skill_audit_v1/run_001/full_rollouts.json'])
    controller=base.backend()
    for module in (h,h.registry,h.validation,h.runtime,h.validation.adapter,controller.native,controller.native.historical,controller.native.historical.old):
        if getattr(module,'__file__',None):files.add(Path(module.__file__).resolve())
    files.add(HERE.parent/'models.json')
    files.update(ROOT/entries[m]['checkpoint'] for m in plan['models'])
    write(out/'provenance.json',{str(p.relative_to(ROOT)):base.sha(p) for p in sorted(files)})
    for path in files:
        if path.suffix in ('.py','.json','.md'):
            dest=out/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    write(out/'environment.json',dict(python=sys.version,platform=platform.platform(),torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0),packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}))
    write(out/'status.json',dict(state='READY',technical_only=smoke,updated_unix=time.time()))


def run(out):
    if read(out/'status.json')['state']!='READY':raise ValueError('Expected READY; no automatic restart')
    verify(out);plan=read(out/'plan.json');start=time.time();deadline=start+plan['maximum_seconds']-plan['exit_reserve_seconds']
    with (out/'launch.json').open('x') as f:json.dump(dict(pid=os.getpid(),started_unix=start),f)
    proc=None;awake=False;state=dict(state='STARTING',pid=os.getpid(),started_unix=start,deadline=deadline)
    # Reuse the tested own-process-tree watchdog without changing its source.
    watchdog=h.module('approach_bc_watchdog',HERE.parent/'grasp_phase_ablation_v1/pipeline.py')
    try:
        if os.name=='nt':awake=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('w',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker','--output',str(out),'--deadline',str(deadline)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            state.update(state='RUNNING',worker_pid=proc.pid,sleep_prevention_active=awake);write(out/'supervisor_status.json',state)
            try:code=proc.wait(timeout=max(1,deadline+5-time.time()))
            except subprocess.TimeoutExpired:watchdog.stop_worker(proc);raise TimeoutError('Hard training deadline')
            if code:raise RuntimeError('Worker failed; inspect status.json and worker.log')
        state['state']=read(out/'status.json')['state']
    except BaseException as exc:state.update(state='FAILED',error=repr(exc));raise
    finally:
        if proc is not None and proc.poll() is None:watchdog.stop_worker(proc)
        if awake:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(),sleep_prevention_active=False);write(out/'supervisor_status.json',state)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','run','worker','status']);p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--deadline',type=float);args=p.parse_args();out=args.output.resolve()
    if args.command=='prepare':prepare(out,args.smoke)
    elif args.command=='run':run(out)
    elif args.command=='worker':worker(out,args.deadline)
    else:print(json.dumps(read(out/'status.json')))
