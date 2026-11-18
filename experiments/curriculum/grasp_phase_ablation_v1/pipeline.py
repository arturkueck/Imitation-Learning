"""Prepare/run a paired second-grasp phase ablation with frozen BC weights."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('grasp_ablation_helpers',HERE.parent/'phase_skill_audit_v1/audit.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
read,write=helpers.read,helpers.write


def selected(arm,stage,phase,retreat,arms):
    return stage==2 and not retreat and phase in arms[arm]


def summary(groups,arms):
    result={}
    for arm in arms:
        rows=[g['arms'][arm] for g in groups]
        result[arm]=dict(n=len(rows),successes=sum(r['success'] for r in rows),
            gains=sum(not g['arms']['control']['success'] and g['arms'][arm]['success'] for g in groups),
            losses=sum(g['arms']['control']['success'] and not g['arms'][arm]['success'] for g in groups),
            exposed=sum(r['expert_frames']>0 for r in rows),
            reached_lift=sum(r['second_lift'] is not None for r in rows),
            held_at_lift=sum(bool((r['second_lift'] or {}).get('held')) for r in rows))
    return result


def episode(env,model,seed,arm,plan,out,deadline):
    base,torch,np=helpers.libraries();controller=base.backend()
    from task_extensions.stack_expert import StackExpert
    obs,initial,z=helpers.reset(env,seed)
    seq=controller.GuardedSequencer(model,3,controller.Clearance(env))
    seq.policy=helpers.validation.adapter.make_policy(base,controller.native.historical,model,.8,lambda:seq.stage,17)
    digest=hashlib.sha256(initial.tobytes());entries={};teacher=None;teacher_phase=None
    expert_frames=0;lift=None;tail=0;trace=[]
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline)
        stage,phase,retreat=seq.stage,seq.policy.phase,seq.retreat
        pos=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if stage==2 and not retreat and phase<=3 and str(phase) not in entries:
            entries[str(phase)]=dict(frame=frame,history_sha256=digest.hexdigest(),
                state_sha256=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest())
        if stage==2 and not retreat and phase==3 and lift is None:
            lift=dict(frame=frame,held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[2].contact_geoms)),
                lower_valid=bool(controller.native.historical.old.prefix_valid(env,2)))
        expert_action=selected(arm,stage,phase,retreat,plan['arms'])
        if expert_action:
            if teacher is None or teacher_phase!=phase:
                teacher=StackExpert(SimpleNamespace(base_env=env));teacher.cube_index=2
                teacher.phase=phase;teacher_phase=phase
            action=teacher(obs);probability=float(teacher.phase!=phase);expert_frames+=1
            seq.policy.phase=teacher.phase;seq.policy.steps=teacher.phase_steps;seq.policy.anchor=None
            if teacher.phase!=phase:teacher=None;teacher_phase=None
        else:
            with torch.no_grad():action,_,probability=seq.policy.action(obs,pos[stage-1],pos[stage])
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        digest.update(action.tobytes());digest.update(env.sim.get_state().flatten().tobytes())
        m=helpers.measurement(env,obs,stage,z[stage],pos[stage]+np.array([0,0,.24]),controller)
        event=seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        tail=tail+1 if m['valid'][-1] else 0
        trace.append(np.r_[frame,stage,phase,retreat,expert_action,probability,event,tail,m['eef'],m['positions'].ravel(),action,m['fingers'],m['valid'],m['velocities']])
        if tail>=plan['success_frames'] or seq.timed_out:break
    return dict(seed=seed,arm=arm,success=tail>=plan['success_frames'],frames=frame+1,
        initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),entries=entries,
        second_lift=lift,expert_frames=expert_frames,final_stage=seq.stage,
        final_phase=seq.policy.phase,retreat_timeout=seq.timed_out),np.asarray(trace)


def check_group(group,plan,reference):
    rows=group['arms'];control=rows['control']
    for arm,phases in plan['arms'].items():
        row=rows[arm]
        if row['initial_sha256']!=control['initial_sha256']:raise ValueError('Initial-state mismatch')
        if phases:
            phase=str(min(phases));left=control['entries'].get(phase);right=row['entries'].get(phase)
            if left!=right:raise ValueError('Pre-intervention phase history mismatch: '+arm)
            if left is None and row['expert_frames']:raise ValueError('Intervention without eligible phase')
            if left is None and any(row[k]!=control[k] for k in ('frames','success','final_stage','final_phase')):
                raise ValueError('Unexposed arm differs')
    for arm,old in [('control',reference['control']),('full_grasp',reference['expert_grasp'])]:
        if any(rows[arm][k]!=old[k] for k in ('initial_sha256','frames','success','final_stage','final_phase','retreat_timeout','expert_frames','second_lift')):
            raise ValueError('Historical control reproduction failed: '+arm)


def verify(out):
    base,_,_=helpers.libraries()
    for path,digest in read(out/'provenance.json').items():
        if base.sha(ROOT/path)!=digest:raise ValueError('Changed input: '+path)


def prepare(out,smoke=False):
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Require new workspace folder')
    plan=read(HERE/'config.json');plan['technical_only']=smoke
    plan['seeds']= [2026113000,2026113002,2026113003] if smoke else list(range(plan['seeds'][0],plan['seeds'][1]+1))
    if smoke:plan['models']=plan['models'][:1]
    base,torch,np=helpers.libraries();base.backend()
    out.mkdir(parents=True);(out/'traces').mkdir();write(out/'plan.json',plan)
    entries=read(HERE.parent/'models.json')['models']
    files={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(ROOT) and (ROOT/'praxis/.venv') not in Path(m.__file__).resolve().parents}
    # Some libraries expose synthetic __file__ names for generated modules.
    files={path for path in files if path.is_file()}
    files.update([Path(__file__),HERE/'config.json',HERE/'README.md',HERE.parent/'phase_skill_audit_v1/audit.py',HERE.parent/'registry.py',HERE.parent/'axis_bc_clock_validation_20261112/pipeline.py',HERE.parent/'axis_bc_clock_validation_20261112/policy.py',ROOT/plan['reference_pairs']])
    files.update(ROOT/entries[m]['checkpoint'] for m in plan['models'])
    proof={str(p.relative_to(ROOT)):base.sha(p) for p in sorted(files)}
    write(out/'provenance.json',proof)
    for path in files:
        if path.suffix in ('.py','.json','.md'):
            dest=out/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    write(out/'environment.json',dict(python=sys.version,platform=platform.platform(),torch=torch.__version__,numpy=np.__version__,cuda=torch.version.cuda,
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        distributions={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}))
    write(out/'status.json',dict(state='READY',technical_only=smoke,episodes=len(plan['models'])*len(plan['seeds'])*len(plan['arms']),updated_unix=time.time()))


def worker(out,deadline):
    plan=read(out/'plan.json');base,_,np=helpers.libraries();base.configure(1);verify(out)
    refs={(r['model'],r['seed']):r for r in read(ROOT/plan['reference_pairs'])}
    groups=[];env=None
    try:
        for model_id in plan['models']:
            model,_,_=helpers.registry.restore(model_id,'cuda');model.eval()
            env=base.backend().native.historical.make_env(3)
            try:
                for seed in plan['seeds']:
                    group=dict(model=model_id,seed=seed,arms={})
                    for arm in plan['arms']:
                        write(out/'status.json',dict(state='EVALUATING',pid=os.getpid(),model=model_id,seed=seed,arm=arm,completed_groups=len(groups),updated_unix=time.time()))
                        row,trace=episode(env,model,seed,arm,plan,out,deadline);group['arms'][arm]=row
                        np.savez_compressed(out/'traces'/f'{model_id}_{seed}_{arm}.npz',trace=trace)
                        write(out/'current_group.json',group)
                    check_group(group,plan,refs[(model_id,seed)])
                    groups.append(group);write(out/'groups.json',groups);write(out/'summary.json',summary(groups,plan['arms']))
            finally:env.close();env=None
        verify(out)
        lines=['# Second-grasp phase ablation','',f"Technical only: {plan['technical_only']}. Groups: {len(groups)}. Optimizer updates: 0.",'',
               '| Arm | Successes | Gains vs BC | Losses vs BC | Exposed | Held / reached Lift |','|---|---:|---:|---:|---:|---:|']
        for arm,r in summary(groups,plan['arms']).items():lines.append(f"| {arm} | {r['successes']}/{r['n']} | {r['gains']} | {r['losses']} | {r['exposed']} | {r['held_at_lift']}/{r['reached_lift']} |")
        by_model={m:summary([g for g in groups if g['model']==m],plan['arms']) for m in plan['models']}
        write(out/'by_model.json',by_model)
        lines+=['','## Per-model results','', '| Model | Arm | Successes | Gains | Losses |','|---|---|---:|---:|---:|']
        for model_id,arms in by_model.items():
            for arm,r in arms.items():lines.append(f"| {model_id} | {arm} | {r['successes']}/{r['n']} | {r['gains']} | {r['losses']} |")
        lines+=['','Each selected intervention replaces actions AND the completion rule. Single-phase effects include changed successor states. No full factorial decomposition, training improvement or fresh-scene generalization is established. Shared development scenes are reused across models.']
        (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        write(out/'status.json',dict(state='COMPLETE',technical_only=plan['technical_only'],completed_groups=len(groups),updated_unix=time.time()))
    except BaseException as exc:
        write(out/'status.json',dict(state='FAILED',error=repr(exc),traceback=traceback.format_exc(),completed_groups=len(groups),updated_unix=time.time()));raise


def stop_worker(proc):
    # The Windows venv launcher can own the actual Python worker as a child.
    import psutil
    try:children=psutil.Process(proc.pid).children(recursive=True)
    except psutil.NoSuchProcess:children=[]
    for child in reversed(children):
        try:child.kill()
        except psutil.NoSuchProcess:pass
    if proc.poll() is None:proc.kill()
    proc.wait(timeout=3)


def run(out):
    if read(out/'status.json')['state']!='READY':raise ValueError('Require READY; no resume/restart')
    verify(out);plan=read(out/'plan.json');start=time.time();deadline=start+plan['maximum_seconds']-plan['shutdown_reserve_seconds']
    with (out/'launch.json').open('x') as f:json.dump(dict(started_unix=start,pid=os.getpid()),f)
    awake=False;proc=None;state=dict(state='STARTING',pid=os.getpid(),started_unix=start,deadline=deadline)
    try:
        if os.name=='nt':awake=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('w',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker','--output',str(out),'--deadline',str(deadline)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            state.update(state='RUNNING',worker_pid=proc.pid,sleep_prevention_active=awake);write(out/'supervisor_status.json',state)
            try:code=proc.wait(timeout=max(1,deadline+5-time.time()))
            except subprocess.TimeoutExpired:stop_worker(proc);raise TimeoutError('Hard deadline')
            if code:raise RuntimeError('Worker failed; inspect status.json and worker.log')
        state['state']=read(out/'status.json')['state']
    except BaseException as exc:state.update(state='FAILED',error=repr(exc));raise
    finally:
        if proc is not None and proc.poll() is None:stop_worker(proc)
        if awake:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(),sleep_prevention_active=False);write(out/'supervisor_status.json',state)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','run','worker','status']);p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--deadline',type=float);args=p.parse_args();out=args.output.resolve()
    if args.command=='prepare':prepare(out,args.smoke)
    elif args.command=='run':run(out)
    elif args.command=='worker':worker(out,args.deadline)
    else:print(json.dumps(read(out/'status.json')))
