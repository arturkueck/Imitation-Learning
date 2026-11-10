"""One fresh paired attempt inside a user-authorized supervised recovery session."""
import argparse
import copy
import csv
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p/'praxis/configs/lift_ph_bc_seed1.json').is_file())
PYTHON = ROOT/'praxis/.venv/Scripts/python.exe'
MAX_SECONDS = 7200
SEED = 41004


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    tmp.replace(p)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def prepare():
    assert not (OUT/'prepared.json').exists() and not (OUT/'B0').exists() and not (OUT/'B1').exists()
    # Preserve the already tested Windows Job Object implementation locally.
    old = (ROOT/'experiments/stack_overnight_C_diffusion_20261004/runner.py').read_text(encoding='utf-8')
    job_source = 'import ctypes\nfrom ctypes import wintypes\n\n'+old[old.index('class Job:'):old.index('\ndef supervise(')]
    (OUT/'job.py').write_text(job_source,encoding='utf-8')
    base = read(ROOT/'praxis/configs/lift_ph_bc_seed1.json')
    changes = {}
    for arm, algo in [('B0','bc'),('B1','bc_sensor')]:
        cfg = copy.deepcopy(base)
        cfg['algo_name'] = algo
        cfg['experiment']['name'] = f'lift_sensor_pilot_{arm}_seed{SEED}'
        cfg['experiment']['logging']['terminal_output_to_txt'] = False
        cfg['experiment']['save'].update(every_n_epochs=None, epochs=[5,10,20], on_best_validation=False,
                                          on_best_rollout_return=False, on_best_rollout_success_rate=False)
        cfg['train']['seed'] = SEED
        cfg['train']['output_dir'] = str(OUT/arm/'runs')
        cfg['train']['data'][0]['path'] = str(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5')
        assert cfg['train']['num_epochs']*cfg['experiment']['epoch_every_n_steps']==2000
        assert cfg['experiment']['ckpt_path'] is None and not cfg['experiment']['rollout']['enabled']
        assert not cfg['train']['hdf5_normalize_obs'] and cfg['train']['batch_size']==100
        if arm == 'B1':
            cfg['algo']['sensor'] = dict(mix=.5,radius=.005,seed=4100401,eef_key='robot0_eef_pos',object_key='object')
        write(OUT/arm/'config.json', cfg)
        changes[arm] = cfg
    b0, b1 = copy.deepcopy(changes['B0']), copy.deepcopy(changes['B1'])
    for cfg in [b0,b1]:
        cfg.pop('algo_name');cfg['experiment'].pop('name');cfg['train'].pop('output_dir')
        cfg['algo'].pop('sensor',None)
    assert b0 == b1, 'Only algorithm/noise and output identity may differ between arms'
    data = read(ROOT/'experiments/lift_contraction_validity_20261004/offline.json')
    assert sha(Path(changes['B0']['train']['data'][0]['path']))==data['dataset_sha256']
    write(OUT/'dataset_manifest.json',dict(path=changes['B0']['train']['data'][0]['path'],sha256=data['dataset_sha256'],
          train_demos=data['train_demos'],valid_demos=data['valid_demos'],split_sha256=hashlib.sha256(json.dumps([data['train_demos'],data['valid_demos']]).encode()).hexdigest()))
    paths = {OUT/'run.py',OUT/'job.py',OUT/'PILOT_PROTOCOL.md',OUT/'B0/config.json',OUT/'B1/config.json'}
    for directory in [ROOT/'praxis/src',ROOT/'praxis/upstream/robomimic/robomimic',ROOT/'praxis/upstream/robosuite/robosuite']:
        paths.update(directory.rglob('*.py'))
    paths.update((ROOT/'praxis/tests').glob('*.py'))
    manifest = {}
    for path in sorted(paths):
        key=str(path.relative_to(ROOT));manifest[key]=sha(path)
        dst=OUT/'source_snapshot'/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)
    write(OUT/'source_hashes.json',manifest)
    (OUT/'environment_frozen.txt').write_bytes(subprocess.check_output([str(PYTHON),'-m','pip','freeze']))
    write(OUT/'prepared.json',dict(seed=SEED,arms=['B0','B1'],updates_per_arm=2000,maximum_wall_clock_seconds=MAX_SECONDS,
          source_files=len(manifest),protocol_sha256=sha(OUT/'PILOT_PROTOCOL.md'),paired_config_audit=True,automatic_retry=False))


def bootstrap():
    snapshot=OUT/'source_snapshot'
    # A .py-only provenance snapshot is not a complete simulator installation:
    # robosuite also requires XML / meshes / Windows DLLs. Use the pinned,
    # complete dependencies with verified Python source; freeze local method code.
    manifest=read(OUT/'source_hashes.json')
    for key,value in manifest.items():
        if key.startswith('praxis/upstream/'):
            assert sha(ROOT/key)==value, f'Pinned dependency changed: {key}'
    for path in [ROOT/'praxis/upstream/robomimic',ROOT/'praxis/upstream/robosuite',snapshot/'praxis/src']:
        sys.path.insert(0,str(path))
    os.environ['MUJOCO_GL']='glfw'
    os.environ['MPLCONFIGDIR']=str(ROOT/'praxis/.cache/matplotlib')
    os.environ['HF_HOME']=str(ROOT/'praxis/.cache/huggingface')
    import types
    probe=types.ModuleType('egl_probe');probe.get_available_devices=lambda:[];sys.modules['egl_probe']=probe
    import robosuite.utils.binding_utils as binding
    binding._MUJOCO_GL='glfw'
    import robosuite.macros as macros
    macros.MUJOCO_GPU_RENDERING=False
    import robomimic_ext  # noqa: F401


def parameter_hash(model):
    h=hashlib.sha256()
    for key,value in sorted(model.nets.state_dict().items()):
        h.update(key.encode());h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def train_arm(arm):
    import numpy as np
    import torch
    from robomimic.algo.bc import BC
    from robomimic.config import config_factory
    from robomimic.scripts import train as upstream
    from robomimic.utils import train_utils as TU, file_utils as FU
    dest=OUT/arm
    assert not (dest/'losses.csv').exists() and not (dest/'training_result.json').exists(), 'No restart/resume'
    cfg=config_factory('bc' if arm=='B0' else 'bc_sensor')
    with cfg.unlocked():
        cfg.update(read(dest/'config.json'))
        cfg.algo.optim_params.policy.num_train_batches=cfg.experiment.epoch_every_n_steps
        cfg.algo.optim_params.policy.num_epochs=cfg.train.num_epochs
    cfg.lock()
    started=time.monotonic();counter=0;model_ref=[];save_kwargs=[];losses=[];batch_hash=hashlib.sha256()
    original_batch,original_save=BC.train_on_batch,TU.save_model
    initial_hash=None;checkpoint_error=None;error=None
    file=(dest/'losses.csv').open('x',encoding='utf-8',newline='')
    csv_writer=csv.writer(file);csv_writer.writerow(['optimizer_update','epoch','split','objective','clean_l2','noisy_objective','elapsed_seconds'])
    manifest={}
    def audited_batch(model,batch,epoch,validate=False):
        nonlocal counter,initial_hash
        if not model_ref:
            model_ref.append(model);initial_hash=parameter_hash(model)
            write(dest/'initialization.json',dict(seed=SEED,parameter_sha256=initial_hash))
        if (OUT/'STOP_REQUESTED').exists():raise InterruptedError('Safe stop requested')
        if not validate:
            assert counter < 2000
            for key in sorted(batch['obs']):
                batch_hash.update(key.encode());batch_hash.update(batch['obs'][key].detach().cpu().contiguous().numpy().tobytes())
            batch_hash.update(batch['actions'].detach().cpu().contiguous().numpy().tobytes())
        info=original_batch(model,batch,epoch,validate=validate)
        if not validate:counter+=1
        objective=float(info['losses']['action_loss']);clean=float(info['losses']['l2_loss'])
        noisy=float(info['losses'].get('noisy_action_loss',torch.tensor(0.)))
        csv_writer.writerow([counter,epoch,'valid' if validate else 'train',objective,clean,noisy,time.monotonic()-started])
        if not np.isfinite(objective):raise FloatingPointError('Nonfinite training objective')
        if not validate:losses.append(objective)
        if not validate and counter%100==0:
            file.flush();torch.cuda.synchronize()
            states={int(s['step']) for s in model.optimizers['policy'].state.values()}
            assert states=={counter}, f'Optimizer state mismatch: {states}, counter={counter}'
            write(dest/'progress.json',dict(state='TRAINING',optimizer_updates=counter,loss=objective,
                  elapsed_seconds=time.monotonic()-started,batch_sequence_sha256=batch_hash.hexdigest(),worker_pid=os.getpid()))
        return info
    def atomic_save(*args,**kwargs):
        assert not args
        save_kwargs[:]=[dict(kwargs)]
        target=Path(kwargs['ckpt_path']);temporary=target.with_suffix('.pth.tmp')
        original_save(**{**kwargs,'ckpt_path':str(temporary)});temporary.replace(target)
        manifest[str(target.relative_to(OUT))]=dict(sha256=sha(target),optimizer_updates=counter,bytes=target.stat().st_size)
        write(dest/'checkpoint_hashes.json',manifest)
        write(dest/'effective_config.json',json.loads(kwargs['config'].dump()))
    BC.train_on_batch=audited_batch;TU.save_model=atomic_save
    try:
        assert torch.cuda.is_available(),'No CPU fallback for training'
        upstream.train(cfg,torch.device('cuda'),resume=False)
        assert counter==2000
    except BaseException:
        error=traceback.format_exc()
    finally:
        file.flush();file.close()
        if model_ref:
            try:
                model=model_ref[0]
                if save_kwargs:kwargs=save_kwargs[0].copy()
                else:
                    ds=cfg.train.data[0];env=FU.get_env_metadata_from_dataset(dataset_path=ds['path']);env['lang']=None
                    shape=FU.get_shape_metadata_from_dataset(dataset_config=ds,action_keys=cfg.train.action_keys,all_obs_keys=cfg.all_obs_keys)
                    kwargs=dict(config=cfg,env_meta=env,shape_meta=shape,obs_normalization_stats=None,action_normalization_stats=None)
                kwargs.update(model=model,ckpt_path=str(dest/'model_final.pth'),
                              variable_state=dict(epoch=counter//100,optimizer_updates=counter,interrupted=error is not None))
                atomic_save(**kwargs)
                for path in dest.rglob('*.pth'):
                    key=str(path.relative_to(OUT))
                    if key not in manifest:manifest[key]=dict(sha256=sha(path),bytes=path.stat().st_size,optimizer_updates=counter)
                write(dest/'checkpoint_hashes.json',manifest)
            except BaseException:checkpoint_error=traceback.format_exc()
        BC.train_on_batch=original_batch;TU.save_model=original_save
        result=dict(state='COMPLETED' if error is None and checkpoint_error is None else 'INTERRUPTED' if error and 'InterruptedError' in error else 'FAILED',
                    arm=arm,seed=SEED,optimizer_updates=counter,configured_updates=2000,
                    initial_parameters_sha256=initial_hash,batch_sequence_sha256=batch_hash.hexdigest(),
                    final_parameters_sha256=parameter_hash(model_ref[0]) if model_ref else None,
                    final_checkpoint_sha256=sha(dest/'model_final.pth') if (dest/'model_final.pth').exists() else None,
                    loss_last=losses[-1] if losses else None,loss_last100=float(np.mean(losses[-100:])) if losses else None,
                    elapsed_seconds=time.monotonic()-started,error=error,checkpoint_error=checkpoint_error,
                    torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
        write(dest/'training_result.json',result)
        print(json.dumps(result,indent=2),flush=True)
    if result['state']!='COMPLETED':raise RuntimeError(f'{arm} failed; preserve artifacts and stop, no replacement run')
    return result


def evaluate(arm,update,condition,episodes):
    import numpy as np
    import torch
    from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
    dest=OUT/arm
    checkpoint=dest/'model_final.pth' if update==2000 else next((dest/'runs').glob(f'*/*/models/model_epoch_{update//100}.pth'))
    path=dest/'evaluation'/f'{update}_{condition}.json'
    assert not path.exists(), 'No overwrite of an evaluation'
    policy,ckpt=policy_from_checkpoint(ckpt_path=str(checkpoint),verbose=False)
    env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False)
    rows=[];started=time.monotonic()
    result=dict(state='RUNNING',arm=arm,optimizer_updates=update,condition=condition,episodes_planned=episodes,
                horizon=400,checkpoint=str(checkpoint),checkpoint_sha256=sha(checkpoint),rollouts=rows)
    try:
        for episode in range(episodes):
            seed=714000+episode;np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset()
            cube=env.env.sim.data.get_joint_qpos(env.env.cube.joints[0]).copy()
            eef=np.array(obs['robot0_eef_pos'],copy=True)
            success=False;steps=400;applied=False;actual_addition=0.;trace=[]
            for step in range(400):
                if (OUT/'STOP_REQUESTED').exists():raise InterruptedError('Stop during evaluation; partial episodes preserved')
                measured=dict(obs)
                bias=.005 if condition=='sensor_y_plus5mm' else -.005 if condition=='sensor_y_minus5mm' else 0.
                if bias:
                    measured['robot0_eef_pos']=np.array(obs['robot0_eef_pos'],copy=True);measured['robot0_eef_pos'][1]+=bias
                    measured['object']=np.array(obs['object'],copy=True);measured['object'][-2]-=bias
                action=np.array(policy(ob=measured),copy=True)
                if condition=='action_impulse_x_plus0.5' and step==20:
                    old=float(action[0]);action[0]=np.clip(action[0]+.5,-1,1);actual_addition=float(action[0])-old;applied=True
                next_obs,_,_,_=env.step(action)
                trace.append(dict(step=step,physical_eef_m=np.asarray(obs['robot0_eef_pos']).tolist(),
                                  cube_m=np.asarray(obs['object'][:3]).tolist(),sensor_bias_y_m=bias,action=action.tolist(),
                                  eef_step_m=(np.asarray(next_obs['robot0_eef_pos'])-obs['robot0_eef_pos']).tolist()))
                obs=next_obs
                if bool(env.is_success()['task']):success=True;steps=step+1;break
            row=dict(seed=seed,success=success,steps=steps,initial_cube_qpos=cube.tolist(),initial_eef_pos=eef.tolist(),
                     impulse_applied=applied,actual_impulse_x=actual_addition,trace=trace)
            rows.append(row)
            result.update(episodes_completed=len(rows),successes=sum(r['success'] for r in rows),elapsed_seconds=time.monotonic()-started)
            write(path,result)
            print(f'eval {arm} {update} {condition}: {len(rows)}/{episodes}, success={result["successes"]}',flush=True)
        result.update(state='COMPLETED',success_rate=result['successes']/episodes,selected_intermediate_checkpoint=False)
    except BaseException:
        result.update(state='INTERRUPTED' if (OUT/'STOP_REQUESTED').exists() else 'FAILED',error=traceback.format_exc())
        raise
    finally:
        env.env.close();result['elapsed_seconds']=time.monotonic()-started;write(path,result)
    return result


def worker():
    started=time.monotonic();result={'state':'RUNNING','seed':SEED}
    try:
        bootstrap()
        import torch
        torch.set_num_threads(2)
        training={arm:train_arm(arm) for arm in ['B0','B1']}
        assert training['B0']['initial_parameters_sha256']==training['B1']['initial_parameters_sha256']
        assert training['B0']['batch_sequence_sha256']==training['B1']['batch_sequence_sha256']
        write(OUT/'pairing_audit.json',dict(passed=True,initial_parameters_equal=True,all_2000_batch_sequence_equal=True))
        evaluations=[]
        for update,condition,n in [(500,'nominal',6),(1000,'nominal',6),(2000,'nominal',10),
                                   (2000,'sensor_y_plus5mm',10),(2000,'sensor_y_minus5mm',10),(2000,'action_impulse_x_plus0.5',10)]:
            for arm in ['B0','B1']:
                write(OUT/'worker_status.json',dict(state='EVALUATING',arm=arm,optimizer_updates=update,condition=condition))
                evaluations.append(evaluate(arm,update,condition,n))
        for i in range(0,len(evaluations),2):
            for a,b in zip(evaluations[i]['rollouts'],evaluations[i+1]['rollouts']):
                assert a['seed']==b['seed'] and a['initial_cube_qpos']==b['initial_cube_qpos'] and a['initial_eef_pos']==b['initial_eef_pos']
        result.update(state='COMPLETED',training=training,paired_initial_states=True,evaluation_elapsed_seconds=sum(e['elapsed_seconds'] for e in evaluations),
                      evaluations=[{k:v for k,v in e.items() if k!='rollouts'} for e in evaluations])
    except BaseException:
        result.update(state='INTERRUPTED' if (OUT/'STOP_REQUESTED').exists() else 'FAILED',error=traceback.format_exc())
        traceback.print_exc()
    finally:
        result['elapsed_seconds']=time.monotonic()-started;write(OUT/'worker_result.json',result)
    return 0 if result['state']=='COMPLETED' else 2


def get_job():
    spec=importlib.util.spec_from_file_location('pilot_job',OUT/'job.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Job()


def supervise(deadline,args,log_path,record_status=True):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32];kernel.SetThreadExecutionState.restype=ctypes.c_uint32
    job=get_job();p=None;awake=False
    try:
        with Path(log_path).open('ab',buffering=0) as log:
            p=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
            job.assign(p)
            if not kernel.SetThreadExecutionState(0x80000001):raise ctypes.WinError(ctypes.get_last_error())
            awake=True
            if record_status:write(OUT/'status.json',dict(state='ACTIVE',worker_pid=p.pid,watchdog_pid=os.getpid(),deadline_unix=deadline))
            timed_out=False
            while p.poll() is None:
                now=time.time()
                if now>=deadline:
                    timed_out=True;job.terminate();p.wait(timeout=5);break
                if record_status and now>=deadline-90 and not (OUT/'STOP_REQUESTED').exists():
                    (OUT/'STOP_REQUESTED').write_text('Save final partial weights and stop: approaching wall-clock limit',encoding='utf-8')
                time.sleep(.5)
            return dict(returncode=p.returncode,timed_out=timed_out,worker_pid=p.pid)
    finally:
        if p is not None and p.poll() is None:job.terminate();p.wait(timeout=5)
        job.close()
        if awake:kernel.SetThreadExecutionState(0x80000000)


def watchdog():
    launch=read(OUT/'launch.json');result={}
    try:
        process=supervise(launch['deadline_unix'],[str(PYTHON),'-u',str(OUT/'run.py'),'worker'],OUT/'worker.log')
        worker_result=read(OUT/'worker_result.json') if (OUT/'worker_result.json').exists() else {}
        result.update(state='TIMED_OUT' if process['timed_out'] else worker_result.get('state','FAILED'),process=process)
    except BaseException:result.update(state='FAILED',error=traceback.format_exc())
    finally:
        result.update(launch_unix=launch['launch_unix'],finished_unix=time.time(),deadline_unix=launch['deadline_unix'],
                      elapsed_since_launch_seconds=time.time()-launch['launch_unix'],awake_request_released=True,
                      worker_job_closed=True,watchdog_exiting=True,automatic_retry=False)
        write(OUT/'run_result.json',result);write(OUT/'status.json',result);print(json.dumps(result,indent=2),flush=True)


def self_test():
    assert not (OUT/'launch.json').exists()
    rows=[]
    for duration,limit in [(.1,5),(20,1)]:
        start=time.time()
        row=supervise(start+limit,[str(PYTHON),'-c',f'import time;time.sleep({duration})'],OUT/'supervision_test.log',record_status=False)
        row['elapsed_seconds']=time.time()-start;rows.append(row)
    assert rows[0]['returncode']==0 and not rows[0]['timed_out'] and rows[1]['timed_out'] and rows[1]['elapsed_seconds']<7
    write(OUT/'supervision_self_test.json',dict(passed=True,records=rows,policy_training_started=False))


def launch():
    assert read(OUT/'supervision_self_test.json')['passed'] and (OUT/'prepared.json').exists()
    assert not (OUT/'launch.json').exists(), 'Exactly one pilot launch'
    assert all(sha(ROOT/k)==v for k,v in read(OUT/'source_hashes.json').items())
    now=time.time();write(OUT/'launch.json',dict(launch_unix=now,deadline_unix=now+MAX_SECONDS,updates_per_arm=2000,seed=SEED,maximum_seconds=MAX_SECONDS))
    with (OUT/'watchdog.log').open('ab',buffering=0) as log:
        p=subprocess.Popen([str(PYTHON),'-u',str(OUT/'run.py'),'watchdog'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                           creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW,close_fds=True)
    write(OUT/'watchdog_pid.json',dict(pid=p.pid,launch_unix=now))
    print(json.dumps(dict(watchdog_pid=p.pid,deadline_unix=now+MAX_SECONDS,folder=str(OUT)),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','self-test','launch','watchdog','worker']);args=parser.parse_args()
    if args.mode=='worker':sys.exit(worker())
    elif args.mode=='self-test':self_test()
    else:globals()[args.mode]()
