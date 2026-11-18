"""Train standard BC A, reuse exposure-matched B/C, and compare corrected policies."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


registry = module('abc_model_registry', HERE.parent/'registry.py')
validation = module('abc_clock_validation', HERE.with_name('axis_bc_clock_validation_20261112')/'pipeline.py')
runtime = validation.monitor
read, write = runtime.read, runtime.write


def full_schedule(data, updates, batch, seed):
    _, _, np = runtime.libraries()
    rng = np.random.default_rng(seed)
    phases = rng.integers(7, size=(updates, batch))
    samples = np.empty((updates, batch), np.int32)
    for phase in range(7):
        candidates = np.flatnonzero(data[2] == phase)
        if not len(candidates):
            raise ValueError('Missing phase')
        mask = phases == phase
        samples[mask] = rng.choice(candidates, size=int(mask.sum()))
    return samples


def validate(plan, cfg):
    if plan['updates'] != cfg['updates'] or plan['batch_size'] != cfg['batch_size'] or plan['seeds'] != cfg['seeds']:
        raise ValueError('A must match reused B/C budgets')
    if plan['train_new'] != ['A'] or plan['clock_correction'] != dict(phase=6,placement_stage=2,maximum_input_steps=17,same_for_all_arms=True):
        raise ValueError('Comparison scope changed')
    if not 0 < plan['shutdown_reserve_seconds'] < plan['wall_clock_cap_seconds'] <= 36000:
        raise ValueError('Invalid total time budget')
    ranges = [plan['confirmation_seeds'], plan['two_cube_seeds']]
    new = [set(range(r[0],r[1]+1)) for r in ranges]
    used = set(range(2026113000,2026113020)) | set(range(2026114000,2026114100)) | set(range(2026115000,2026115100)) | set(range(2026117000,2026117100)) | set(range(2026119000,2026119100)) | set(range(2026119200,2026119220))
    if not all(new) or new[0]&new[1] or (new[0]|new[1])&used or plan['technical_seed'] in new[0]|new[1]:
        raise ValueError('Confirmation namespaces overlap')


def prepare(out):
    base, torch, np = runtime.libraries()
    if out.exists():
        raise FileExistsError('Use a new run directory')
    original = HERE.with_name('axis_bc_20261110')/'ready_001'
    runtime.verify(HERE.with_name('axis_bc_extension_20261110')/'ready_001')
    cfg = read(original/'config.json')
    plan = read(HERE/'config.json')
    validate(plan, cfg)
    inventory = read(HERE.parent/'models.json')
    parents, inputs = {}, {}
    for seed in plan['seeds']:
        audit = inventory['initialization_audit'][str(seed)]
        if not audit['initialization_equal']:
            raise ValueError('B/C initial weights differ')
        for arm, model_id in (('A',f'initial_s{seed}_u0'),('B',f'mixed_s{seed}_u30000'),('C',f'curriculum_s{seed}_u30000')):
            entry = inventory['models'][model_id]
            if base.sha(ROOT/entry['checkpoint']) != entry['sha256']:
                raise ValueError('Registered model changed')
            checkpoint = torch.load(ROOT/entry['checkpoint'], map_location='cpu', weights_only=False)
            if checkpoint['config'] != cfg or checkpoint['technical_only'] or checkpoint['update'] != (0 if arm=='A' else 30000):
                raise ValueError('B/C cannot be reused under these settings')
            parents[f'{arm}_seed{seed}'] = entry
            inputs[entry['checkpoint']] = entry['sha256']
    # Archived B/C used one complete batch multiset in two orders.
    exposure = {}
    for seed in plan['seeds']:
        with np.load(original/f'schedule_seed{seed}.npz', allow_pickle=False) as source:
            batches, permutation = source['batches'], source['permutation']
            if sorted(permutation.tolist()) != list(range(30000)):
                raise ValueError('B/C ordering is not a permutation')
            if not np.array_equal(np.bincount(batches.ravel()),np.bincount(batches[permutation].ravel())):
                raise ValueError('B/C exposure differs')
        exposure[seed] = dict(batch_multiset_equal=True, initialization_equal=True)
    proof = read(original/'provenance.json')
    inputs.update(proof['input_hashes'])
    own = list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+[HERE/'config.json', HERE.parent/'registry.py',HERE.parent/'models.json',
          HERE.with_name('axis_bc_clock_validation_20261112')/'pipeline.py', HERE.with_name('axis_bc_clock_validation_20261112')/'policy.py',
          HERE.with_name('axis_bc_extension_20261110')/'night.py']
    inputs.update({str(p.relative_to(ROOT)):base.sha(p) for p in own})
    out.mkdir(parents=True)
    for name,value in (('plan.json',plan),('base_config.json',cfg),('parents.json',parents),('reuse_audit.json',exposure)):
        write(out/name,value)
        inputs[str((out/name).relative_to(ROOT))]=base.sha(out/name)
    data = base.load_data()['train']
    (out/'sampling').mkdir()
    for seed in plan['seeds']:
        samples = full_schedule(data,plan['updates'],plan['batch_size'],seed)
        path = out/'sampling'/f'A_seed{seed}.npz'
        np.savez_compressed(path,batches=samples)
        inputs[str(path.relative_to(ROOT))]=base.sha(path)
    for path in own:
        target = out/'source_snapshot'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
    write(out/'provenance.json',dict(input_hashes=inputs,library_source_hashes=proof['library_source_hashes'],versions=proof['versions'],prepared_unix=time.time()))
    write(out/'status.json',dict(state='READY',completed_round=0,updated_unix=time.time(),new_models=3,reused_models=6))
    print(json.dumps(dict(state='READY',new_A_models=3,reused_BC_models=6,output=str(out))))


def restore_training_checkpoint(path,device):
    base,torch,_=runtime.libraries()
    ck=torch.load(path,map_location='cpu',weights_only=False)
    cfg=ck['config']
    model=base.backend().native.historical.PhaseNet(cfg['width']).to(device)
    model.load_state_dict(ck['model'])
    opt=torch.optim.AdamW(model.parameters(),lr=cfg['lr'],weight_decay=cfg['weight_decay'])
    opt.load_state_dict(ck['optimizer'])
    return model,opt,ck


def save(path,model,opt,update,seed,cfg,plan,sampler,technical):
    _,torch,np=runtime.libraries()
    checkpoint=dict(model=model.state_dict(),optimizer=opt.state_dict(),update=update,seed=seed,arm='A',config=cfg,
        abc_plan=plan,sampler_file=str(sampler.relative_to(ROOT)),sampler_sha256=registry.libraries()[0].sha(sampler),next_batch=update,
        technical_only=technical,torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        numpy_rng=np.random.get_state(),python_rng=random.getstate(),initial_bundle=f'initial_s{seed}_u0')
    tmp=path.with_suffix('.tmp')
    torch.save(checkpoint,tmp)
    tmp.replace(path)


def evaluate(model,cfg,count,seeds,out,deadline):
    base,_,_=runtime.libraries()
    env=base.backend().native.historical.make_env(count)
    rows=[]
    try:
        for seed in seeds:
            result=validation.episode(env,model,cfg,seed,17,out,deadline)
            rows.append(validation.public(result))
    finally:
        env.close()
    return dict(n=len(rows),successes=sum(r['success'] for r in rows),rows=rows)


def run(out,device,deadline=None,prepared=None):
    base,torch,np=runtime.libraries()
    technical=prepared is not None
    source=prepared or out
    runtime.verify(source)
    plan,cfg,parents=read(source/'plan.json'),read(source/'base_config.json'),read(source/'parents.json')
    if technical:
        out.mkdir(parents=True,exist_ok=False)
        plan=copy.deepcopy(plan)
        plan.update(seeds=[1],updates=3,evaluation_updates=[3])
    elif read(out/'status.json')['state']!='READY':
        raise ValueError('Use a fresh READY run')
    if (out/'STOP').exists():raise InterruptedError('STOP requested')
    with (out/'launch.json').open('x') as stream:json.dump(dict(pid=os.getpid(),started_unix=time.time(),technical_only=technical),stream)
    started=time.time();deadline=deadline or started+(600 if technical else plan['wall_clock_cap_seconds']-plan['shutdown_reserve_seconds'])
    state=dict(state='INITIALIZING',pid=os.getpid(),started_unix=started,deadline=deadline,completed_round=0,technical_only=technical)
    members={};histories=[]
    def status(**extra):
        state.update(extra,updated_unix=time.time());write(out/'status.json',state)
    status()
    try:
        base.configure(1)
        data=base.load_data();weights=base.positive_weights(data['train'],device)
        for seed in plan['seeds']:
            model,opt,_=registry.restore(f'initial_s{seed}_u0',device)
            folder=out/f'A_seed{seed}';folder.mkdir()
            sampler=source/'sampling'/f'A_seed{seed}.npz'
            with np.load(sampler,allow_pickle=False) as archive:samples=archive['batches'].copy()
            members[seed]=dict(model=model,opt=opt,samples=samples,sampler=sampler,update=0,folder=folder)
            save(folder/'initial.pth',model,opt,0,seed,cfg,plan,sampler,technical)
        for update in range(1,plan['updates']+1):
            base.check_stop(out,deadline)
            for seed,m in members.items():
                m['model'].train()
                metrics=base.step(m['model'],m['opt'],data['train'],m['samples'][update-1],weights,cfg,update,device)
                m['update']=update
                if update%100==0 or update in plan['evaluation_updates']:
                    with (out/'metrics.jsonl').open('a') as stream:stream.write(json.dumps(dict(model=f'A_seed{seed}',update=update,**metrics))+'\n')
            if update%100==0 or update in plan['evaluation_updates']:
                status(state='TRAINING',completed_round=update,last_metrics=metrics,updates={s:m['update'] for s,m in members.items()})
            if update%1000==0 or update in plan['evaluation_updates']:
                for seed,m in members.items():save(m['folder']/'latest.pth',m['model'],m['opt'],update,seed,cfg,plan,m['sampler'],technical)
            if update in plan['evaluation_updates']:
                for seed,m in members.items():
                    metric=runtime.offline(m['model'],data['valid'],cfg,device,weights)
                    seeds=[plan['technical_seed']] if technical else range(plan['development_seeds'][0],plan['development_seeds'][1]+1)
                    for count in (2,3):
                        status(state='EVALUATING',evaluating=f'A_seed{seed}',count=count)
                        result=evaluate(m['model'],cfg,count,seeds,out,deadline)
                        write(m['folder']/f'dev{count}_u{update}.json',result)
                        metric[f'dev{count}']={k:v for k,v in result.items() if k!='rows'}
                    histories.append(dict(seed=seed,arm='A',update=update,**metric))
                    write(out/'learning_curve.json',histories)
        status(state='FREEZING_CONFIRMATION',completed_round=plan['updates'])
        frozen={};folder=out/'confirmation';folder.mkdir()
        # Every A/B/C model is frozen before the first new confirmation scene.
        for seed in plan['seeds']:
            for arm in ('A','B','C'):
                name=f'{arm}_seed{seed}';target=folder/f'{name}.pth'
                source_ck=members[seed]['folder']/'latest.pth' if arm=='A' else ROOT/parents[name]['checkpoint']
                shutil.copy2(source_ck,target)
                frozen[name]=dict(path=str(target),sha256=base.sha(target))
        write(folder/'frozen.json',frozen)
        results,hashes={},{}
        for name,entry in frozen.items():
            if base.sha(entry['path'])!=entry['sha256']:raise ValueError('Frozen checkpoint changed')
            model,_,_=restore_training_checkpoint(entry['path'],device)
            results[name]={}
            for count in (3,2):
                status(state='FINAL_TEST',evaluating=name,count=count)
                interval=plan['confirmation_seeds'] if count==3 else plan['two_cube_seeds']
                seeds=[plan['technical_seed']] if technical else range(interval[0],interval[1]+1)
                result=evaluate(model,cfg,count,seeds,out,deadline)
                runtime.check_pairing(hashes,count,result)
                write(folder/f'{name}_count{count}.json',result)
                results[name][str(count)]={k:v for k,v in result.items() if k!='rows'}
        write(out/'result_summary.json',dict(technical_only=technical,models=results,selection='fixed 30k',clock_corrected=True,
              interpretation='B vs C isolates batch ordering; A vs B tests exposure weighting; A vs C tests the whole curriculum. Report each seed, not pooled scenes as independent training replicas.'))
        status(state='SMOKE_COMPLETE' if technical else 'COMPLETE')
    except (TimeoutError,InterruptedError) as exc:
        status(state='PARTIAL_TIME_CAP' if isinstance(exc,TimeoutError) else 'STOPPED',reason=str(exc))
    except BaseException as exc:
        status(state='FAILED',reason=repr(exc),traceback=traceback.format_exc());raise
    finally:
        for seed,m in members.items():save(m['folder']/'latest.pth',m['model'],m['opt'],m['update'],seed,cfg,plan,m['sampler'],technical)
    print(json.dumps(dict(state=state['state'],updates={s:m['update'] for s,m in members.items()})))


def supervise(out,device):
    started=time.time();runtime.verify(out)
    if read(out/'status.json')['state']!='READY' or (out/'STOP').exists():raise ValueError('Not READY')
    with (out/'supervisor_launch.json').open('x') as stream:json.dump(dict(pid=os.getpid(),started_unix=started),stream)
    plan=read(out/'plan.json');hard=started+plan['wall_clock_cap_seconds'];deadline=hard-plan['shutdown_reserve_seconds']
    state=dict(state='STARTING',pid=os.getpid(),started_unix=started,deadline=deadline,hard_deadline=hard)
    worker=None;awake=False
    try:
        if os.name=='nt':awake=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        worker=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'run','--output',str(out),'--device',device,'--deadline',str(deadline)],cwd=ROOT)
        state.update(state='RUNNING',worker_pid=worker.pid,sleep_prevention_active=awake,updated_unix=time.time());write(out/'supervisor_status.json',state)
        try:code=worker.wait(timeout=max(.001,hard-time.time()))
        except subprocess.TimeoutExpired:
            worker.kill();worker.wait();raise TimeoutError('Hard ten-hour maximum reached')
        if code:raise RuntimeError('Worker failed with exit code '+str(code))
        state['state']=read(out/'status.json')['state']
    except BaseException as exc:
        state.update(state='FAILED',reason=repr(exc),traceback=traceback.format_exc());raise
    finally:
        if worker is not None and worker.poll() is None:worker.kill();worker.wait()
        if awake:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(),sleep_prevention_active=False);write(out/'supervisor_status.json',state)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','preflight','smoke','run','supervise','status'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--prepared',type=Path);p.add_argument('--device',choices=('cpu','cuda'),default='cuda');p.add_argument('--deadline',type=float)
    args=p.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT):p.error('Output must stay inside workspace')
    if args.command=='prepare':prepare(out)
    elif args.command=='preflight':
        runtime.verify(out)
        if read(out/'status.json')['state']!='READY' or any((out/n).exists() for n in ('launch.json','supervisor_launch.json','STOP')):raise ValueError('Not startable')
        print(json.dumps(dict(state='READY',input_hashes_verified=True)))
    elif args.command=='smoke':
        if args.prepared is None:p.error('--prepared required')
        run(out,args.device,prepared=args.prepared.resolve())
    elif args.command=='run':run(out,args.device,args.deadline)
    elif args.command=='supervise':supervise(out,args.device)
    else:runtime.status(out)


if __name__=='__main__':main()
