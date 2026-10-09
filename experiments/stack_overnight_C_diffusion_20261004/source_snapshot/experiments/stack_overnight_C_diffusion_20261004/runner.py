"""Exactly one fresh C run, supervised in a Windows kill-on-close Job Object."""
import argparse, copy, csv, ctypes, hashlib, json, os, shutil, subprocess, sys, time, traceback
from ctypes import wintypes
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
DEST = OUT/'C/diffusion/seed_2'
PYTHON = ROOT/'praxis/.venv/Scripts/python.exe'
BASE = ROOT/'experiments/stack_normalization_20261001'
MAX_SECONDS = 15*60*60
SEED = 2

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p, value):
    p = Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp = p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8'); tmp.replace(p)
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def seal():
    assert not (OUT/'launch.json').exists(), 'Source seal must precede launch'
    paths={ROOT/p for p in read(OUT/'source_hashes.json')}
    paths.update((OUT/'RESEARCH_REVIEW.md',OUT/'supervision_self_test.json'))
    paths.update((ROOT/'praxis/upstream/robosuite/robosuite').rglob('*.py'))
    source={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    for p in sorted(paths):
        target=OUT/'source_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    write(OUT/'source_hashes.json',source)
    write(OUT/'research_frozen.json',dict(sha256=sha(OUT/'RESEARCH_REVIEW.md'),frozen_unix=time.time(),source_files=len(source)))
    print('Sealed source and pre-launch research:',len(source),'files')

def prepare():
    assert not (OUT/'prepared.json').exists() and not DEST.exists(), 'Fresh folder required'
    assert read(OUT/'existing_evidence_verification.json')['passed']
    DEST.mkdir(parents=True); (OUT/'scripts').mkdir()
    for name in ('common.py','train.py','evaluate.py'):
        shutil.copy2(BASE/'scripts'/name,OUT/'scripts'/name)
    shutil.copy2(BASE/'normalization_stats.json',OUT/'normalization_stats.json')
    shutil.copy2(BASE/'protocol.json',OUT/'protocol.json')
    cfg = read(BASE/'C/diffusion/seed_1/config.json'); original=copy.deepcopy(cfg)
    cfg['experiment']['name']='stack_overnight_C_diffusion_20261004_seed_2'
    cfg['train']['output_dir']=str(DEST/'runs'); cfg['train']['seed']=SEED
    assert cfg['train']['num_epochs']*cfg['experiment']['epoch_every_n_steps']==30000
    assert cfg['experiment']['ckpt_path'] is None and not cfg['experiment']['rollout']['enabled']
    write(DEST/'config.json',cfg)
    delta={}
    def compare(a,b,path=''):
        if isinstance(a,dict):
            for k in a: compare(a[k],b[k],path+'.'+k if path else k)
        elif a!=b:delta[path]=dict(original=a,effective=b)
    compare(original,cfg)
    assert set(delta)=={'experiment.name','train.output_dir','train.seed'}
    import h5py, torch
    assert torch.cuda.is_available(), 'CUDA unavailable: no CPU training fallback'
    dataset=Path(cfg['train']['data'][0]['path'])
    assert sha(dataset)==read(BASE/'protocol.json')['baseline_protocol']['data_sha256']
    with h5py.File(dataset,'r') as f:
        split={k:[x.decode() for x in f['mask/'+k][:]] for k in ('train','valid')}
        assert len(split['train'])==180 and len(split['valid'])==20
        assert not set(split['train']) & set(split['valid'])
    write(OUT/'dataset_manifest.json',dict(path=str(dataset),sha256=sha(dataset),split=split,
          split_sha256=hashlib.sha256(json.dumps(split,sort_keys=True).encode()).hexdigest()))
    paths=set()
    for directory in (ROOT/'praxis/src',ROOT/'praxis/upstream/robomimic/robomimic',
                      ROOT/'experiments/stack_followup_20261001/scripts',ROOT/'experiments/square/scripts',OUT/'scripts'):
        paths.update(directory.rglob('*.py'))
    paths.update((OUT/'runner.py',OUT/'audit_existing.py',BASE/'C/diffusion/seed_1/config.json',
                  OUT/'normalization_stats.json',OUT/'protocol.json',DEST/'config.json'))
    source={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    write(OUT/'source_hashes.json',source)
    # Freeze source content as well as hashes; training uses the existing imports.
    for p in sorted(paths):
        target=OUT/'source_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    (OUT/'environment_frozen.txt').write_bytes(subprocess.check_output([str(PYTHON),'-m','pip','freeze']))
    write(OUT/'prepared.json',dict(seed=SEED,optimizer_updates=30000,config_changes=delta,
          source_files=len(source),python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,
          gpu=torch.cuda.get_device_name(0),maximum_wall_clock_seconds=MAX_SECONDS,
          evaluation=dict(fixed_start_seeds=list(range(46000,46040)),ddim_steps=10,execute_actions=2,
                          checkpoint_config_action_horizon=8,main_steps=500,stability_tail_steps=40),
          final_checkpoint_selection='Final trained weights only; no evaluation-based selection',
          interpretation='One fresh training seed, no method change; research conclusion frozen before launch'))
    print(json.dumps(read(OUT/'prepared.json'),indent=2))

class Job:
    def __init__(self):
        k=ctypes.WinDLL('kernel32',use_last_error=True);self.k=k
        class BASIC(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
                      ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),
                      ('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
        class IO(ctypes.Structure): _fields_=[(x,ctypes.c_ulonglong) for x in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class EXT(ctypes.Structure): _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];k.CreateJobObjectW.restype=wintypes.HANDLE
        k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        k.CloseHandle.argtypes=[wintypes.HANDLE]
        k.TerminateJobObject.argtypes=[wintypes.HANDLE,wintypes.UINT]
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        info=EXT();info.BasicLimitInformation.LimitFlags=0x2000 # KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):raise ctypes.WinError(ctypes.get_last_error())
    def assign(self,p):
        if not self.k.AssignProcessToJobObject(self.handle,wintypes.HANDLE(int(p._handle))):
            p.kill();p.wait();raise ctypes.WinError(ctypes.get_last_error())
    def terminate(self): self.k.TerminateJobObject(self.handle,124)
    def close(self): self.k.CloseHandle(self.handle)

def supervise(mode, deadline, job, log_path, test_seconds=None):
    # System execution requirement is owned by this watchdog thread and cleared after each child.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.SetThreadExecutionState.argtypes=[wintypes.DWORD];kernel.SetThreadExecutionState.restype=wintypes.DWORD
    if not kernel.SetThreadExecutionState(0x80000001):raise ctypes.WinError(ctypes.get_last_error())
    p=None
    try:
        args=[str(PYTHON),'-u',str(OUT/'runner.py'),mode]
        if test_seconds is not None:args+=['--test-seconds',str(test_seconds)]
        with Path(log_path).open('ab',buffering=0) as log:
            p=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
            job.assign(p)
            if mode in ('train','evaluate'):
                write(OUT/'status.json',dict(state='TRAINING' if mode=='train' else 'EVALUATING',worker_pid=p.pid,
                      watchdog_pid=os.getpid(),deadline_unix=deadline,seed=SEED))
            while p.poll() is None:
                now=time.time()
                if now>=deadline:
                    job.terminate();p.wait(timeout=5);return dict(returncode=p.returncode,timed_out=True,worker_pid=p.pid)
                if mode=='train' and now>=deadline-120 and not (OUT/'STOP_REQUESTED').exists():
                    (OUT/'STOP_REQUESTED').write_text('Wall-clock deadline approaching: checkpoint and stop at next safe batch boundary.',encoding='utf-8')
                time.sleep(min(.5,max(.01,deadline-now)))
            return dict(returncode=p.returncode,timed_out=False,worker_pid=p.pid)
    finally:
        if p is not None and p.poll() is None:job.terminate();p.wait(timeout=5)
        kernel.SetThreadExecutionState(0x80000000)

def modules():
    import importlib.util
    sys.path.insert(0,str(OUT/'scripts'))
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
        return module
    common=load('common',OUT/'scripts/common.py')
    common.OUT=OUT
    train=load('overnight_historical_train',OUT/'scripts/train.py')
    evaluate=load('overnight_historical_evaluate',OUT/'scripts/evaluate.py')
    train.OUT=OUT;evaluate.OUT=OUT
    return common,train,evaluate

def train_worker():
    import numpy as np, torch
    assert not (DEST/'initialization.json').exists(), 'Never resume or rerun'
    common,historical,_=modules();n=common.Normalizer('C')
    from robomimic.algo.diffusion_policy import DiffusionPolicyUNet
    import robomimic.utils.train_utils as TU
    from robomimic.config import config_factory
    from robomimic.utils import file_utils as FU
    model_ref=[];save_args=[];old_batch=DiffusionPolicyUNet.train_on_batch;old_save=TU.save_model
    started=time.monotonic();original_stdout=sys.stdout;original_stderr=sys.stderr
    losses_file=(DEST/'losses.csv').open('x',newline='',encoding='utf-8')
    csvwriter=csv.writer(losses_file);csvwriter.writerow(['optimizer_update','epoch','split','epsilon_mse','elapsed_seconds'])
    counter=[0]
    def audited_batch(model,batch,epoch,validate=False):
        if not model_ref:model_ref.append(model)
        if (OUT/'STOP_REQUESTED').exists():raise InterruptedError('Safe stop requested by 15-hour watchdog')
        info=old_batch(model,batch,epoch,validate=validate)
        if not validate:counter[0]+=1
        csvwriter.writerow([counter[0],epoch,'valid' if validate else 'train',float(info['losses']['l2_loss']),time.monotonic()-started])
        if counter[0]%100==0:losses_file.flush()
        return info
    DiffusionPolicyUNet.train_on_batch=audited_batch
    def atomic_save(*a,**kw):
        assert not a
        save_args[:]=[dict(kw)]
        destination=Path(kw['ckpt_path']);temp=destination.with_suffix('.pth.tmp')
        old_save(**{**kw,'ckpt_path':str(temp)});temp.replace(destination)
        manifest=read(DEST/'checkpoint_hashes.json') if (DEST/'checkpoint_hashes.json').exists() else {}
        manifest[str(destination.relative_to(OUT))]=dict(sha256=sha(destination),bytes=destination.stat().st_size,
                                                        optimizer_updates=counter[0])
        write(DEST/'checkpoint_hashes.json',manifest)
    TU.save_model=atomic_save
    error=None;result=None
    try:
        result=historical.train_diffusion(DEST,n,SEED)
    except BaseException:
        error=traceback.format_exc()
    finally:
        sys.stdout=original_stdout;sys.stderr=original_stderr;losses_file.flush();losses_file.close()
        if historical.LIVE_AUDIT:
            np.savez_compressed(DEST/('training_audit.npz' if result else 'training_audit_partial.npz'),
                                **{k:np.asarray(v) for k,v in historical.LIVE_AUDIT.items()})
        checkpoint_error=None
        if model_ref:
            try:
                model=model_ref[0];updates={int(v['step']) for v in model.optimizers['policy'].state.values()}
                assert updates=={counter[0]} and model.ema.optimization_step==counter[0]
                assert model.lr_schedulers['policy'].last_epoch==counter[0]
                if save_args:kw=save_args[0].copy()
                else:
                    cfg=config_factory('diffusion_policy',dic=read(DEST/'config.json'));cfg.lock()
                    ds=cfg.train.data[0];env=FU.get_env_metadata_from_dataset(dataset_path=ds['path']);env['lang']=None
                    shape=FU.get_shape_metadata_from_dataset(dataset_config=ds,action_keys=cfg.train.action_keys,all_obs_keys=cfg.all_obs_keys)
                    kw=dict(config=cfg,env_meta=env,shape_meta=shape,obs_normalization_stats=n.obs,
                            action_normalization_stats={'actions':dict(offset=np.zeros((1,7),np.float32),scale=np.ones((1,7),np.float32))})
                kw.update(model=model,ckpt_path=str(DEST/'model_final.pth'),
                          variable_state=dict(epoch=counter[0]//100,optimizer_updates=counter[0],interrupted=error is not None))
                atomic_save(**kw)
                manifest=read(DEST/'checkpoint_hashes.json')
                for path in DEST.rglob('*.pth'):
                    key=str(path.relative_to(OUT))
                    if key not in manifest:
                        h=sha(path);matching=[r for r in manifest.values() if r['sha256']==h]
                        manifest[key]=dict(sha256=h,bytes=path.stat().st_size,
                                           optimizer_updates=matching[0]['optimizer_updates'] if matching else None)
                write(DEST/'checkpoint_hashes.json',manifest)
            except BaseException:checkpoint_error=traceback.format_exc()
        summary=dict(state='COMPLETED' if result and not checkpoint_error else 'INTERRUPTED' if error and 'InterruptedError' in error else 'FAILED',
                     seed=SEED,optimizer_updates=counter[0],configured_optimizer_updates=30000,
                     elapsed_seconds=time.monotonic()-started,result=result,error=error,checkpoint_error=checkpoint_error,
                     final_checkpoint=str(DEST/'model_final.pth') if (DEST/'model_final.pth').exists() else None)
        losses=historical.LIVE_AUDIT.get('loss',[])
        summary['loss_last']=float(losses[-1]) if losses else None
        summary['loss_last500']=float(np.mean(losses[-500:])) if losses else None
        write(DEST/'training_result.json',summary)
        print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['state']=='COMPLETED' else 2

def evaluate_worker():
    _,_,evaluation=modules()
    evaluation.checkpoint=lambda v,kind,seed:DEST/'model_final.pth'
    start=time.monotonic()
    try:
        evaluation.run('C','diffusion',SEED)
        import numpy as np
        rows=read(DEST/'rollouts/results.json');assert len(rows)==40
        for r in rows:
            z=np.load(DEST/'rollouts'/f"{r['seed']}.npz");t=z['trace'];m=int(z['measured'])
            assert len(t[m:])==40
            stable=bool(t[m-1,36]>0 and (t[m:,36]>0).all() and not t[m:,34].any() and (t[m:,35]>0).all())
            assert stable==r['sustained_success']
        result=dict(state='COMPLETED',n=40,checkpoint_sha256=sha(DEST/'model_final.pth'),
                    stable_stacks=sum(r['sustained_success'] for r in rows),
                    partial_phase_counts={k:sum(bool(r[k]) for r in rows) for k in ('grasp','lift','transport_started','position','lower','release')},
                    elapsed_seconds=time.monotonic()-start,selected_intermediate_checkpoint=False)
        write(DEST/'evaluation_result.json',result);print(json.dumps(result,indent=2),flush=True);return 0
    except BaseException:
        write(DEST/'evaluation_result.json',dict(state='FAILED',error=traceback.format_exc(),elapsed_seconds=time.monotonic()-start))
        raise

def watchdog():
    launch=read(OUT/'launch.json');deadline=launch['deadline_unix'];start=time.time()
    job=Job();state='FAILED';detail={}
    try:
        detail['training_process']=supervise('train',deadline,job,OUT/'train_worker.log')
        if detail['training_process']['timed_out']:state='TIMED_OUT_TRAINING'
        elif detail['training_process']['returncode']!=0:
            result=read(DEST/'training_result.json') if (DEST/'training_result.json').exists() else {}
            state='INTERRUPTED_TRAINING' if result.get('state')=='INTERRUPTED' else 'FAILED_TRAINING'
        elif time.time()>=deadline-120:state='TRAINED_EVALUATION_SKIPPED_DEADLINE'
        else:
            detail['evaluation_process']=supervise('evaluate',deadline,job,OUT/'evaluate_worker.log')
            state='TIMED_OUT_EVALUATION' if detail['evaluation_process']['timed_out'] else 'COMPLETED' if detail['evaluation_process']['returncode']==0 else 'FAILED_EVALUATION'
    except BaseException:detail['error']=traceback.format_exc()
    finally:
        job.close()
        result=dict(state=state,seed=SEED,launch_unix=launch['launch_unix'],deadline_unix=deadline,
                    finished_unix=time.time(),elapsed_since_launch_seconds=time.time()-launch['launch_unix'],
                    awake_request_released=True,worker_job_closed=True,watchdog_exiting=True,automatic_retry=False,**detail)
        write(OUT/'status.json',result);write(OUT/'run_result.json',result)
        training=read(DEST/'training_result.json') if (DEST/'training_result.json').exists() else {}
        ev=read(DEST/'evaluation_result.json') if (DEST/'evaluation_result.json').exists() else {}
        lines=['# Single fresh C diffusion training result','',f"Status: **{state}**.",'',
               f"Training seed: {SEED}. Budget: 30,000 optimizer updates. Recorded updates: {training.get('optimizer_updates','see last atomic status/checkpoint manifest')}.",
               f"Elapsed since launch: {result['elapsed_since_launch_seconds']:.1f} seconds. Maximum: {MAX_SECONDS} seconds.",'',
               f"Stable stacks: {ev.get('stable_stacks','unavailable')} / {ev.get('n','evaluation incomplete or not started')}.",
               f"Partial phase counts (separate): {json.dumps(ev.get('partial_phase_counts',{}))}.",'',
               'This is one fresh training seed with unchanged learning settings. It neither establishes a robust training improvement nor explains the Direct–diffusion gap. The research conclusion in RESEARCH_REVIEW.md is unchanged.',
               '', 'Exact process status: run_result.json. Losses: C/diffusion/seed_2/losses.csv. Configuration: C/diffusion/seed_2/config.json. Dataset/source manifests and checkpoint hashes are preserved. No automatic retry.']
        (OUT/'TRAINING_RESULT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2),flush=True)

def launch():
    assert (OUT/'prepared.json').exists() and (OUT/'supervision_self_test.json').exists()
    assert not (OUT/'launch.json').exists(), 'Exactly one launch; never retry automatically'
    assert (OUT/'research_frozen.json').exists()
    assert all(sha(ROOT/p)==h for p,h in read(OUT/'source_hashes.json').items()), 'Source changed after sealing'
    now=time.time();write(OUT/'launch.json',dict(launch_unix=now,deadline_unix=now+MAX_SECONDS,
                    executable=str(PYTHON),seed=SEED,budget_updates=30000,max_seconds=MAX_SECONDS))
    flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW
    with (OUT/'watchdog.log').open('ab',buffering=0) as log:
        p=subprocess.Popen([str(PYTHON),'-u',str(OUT/'runner.py'),'watchdog'],cwd=ROOT,
                           stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,close_fds=True)
    write(OUT/'watchdog_pid.json',dict(pid=p.pid,launch_unix=now))
    print(json.dumps(dict(watchdog_pid=p.pid,deadline_unix=now+MAX_SECONDS,folder=str(OUT)),indent=2))

def self_test():
    records=[]
    for child_seconds,limit in ((.2,5),(10,1)):
        job=Job();start=time.time()
        try:r=supervise('test-child',start+limit,job,OUT/'supervision_self_test.log',child_seconds)
        finally:job.close()
        records.append(dict(child_seconds=child_seconds,limit=limit,elapsed=time.time()-start,**r))
    assert records[0]['returncode']==0 and not records[0]['timed_out']
    assert records[1]['timed_out'] and records[1]['elapsed']<7
    write(OUT/'supervision_self_test.json',dict(passed=True,training_launched=False,records=records))
    print(json.dumps(records,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','seal','self-test','launch','watchdog','train','evaluate','test-child']);p.add_argument('--test-seconds',type=float,default=.2);a=p.parse_args()
    if a.mode=='prepare':prepare()
    elif a.mode=='seal':seal()
    elif a.mode=='self-test':self_test()
    elif a.mode=='launch':launch()
    elif a.mode=='watchdog':watchdog()
    elif a.mode=='train':sys.exit(train_worker())
    elif a.mode=='evaluate':sys.exit(evaluate_worker())
    else:time.sleep(a.test_seconds);print('Synthetic worker finished',flush=True)
