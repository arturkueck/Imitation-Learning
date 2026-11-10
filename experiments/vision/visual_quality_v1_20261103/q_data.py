"""Role-bound raw collection and causal feature export; GT only creates targets."""
from pathlib import Path
import os,sys,time,json,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import numpy as np
from q_protocol import ROOT,HERE,LEGACY,read,save,sha,now,verify
from q_features import extract
from pipeline.common import check_stop

def paths(run,split):return Path(run)/'features'/split

def worker(raw,role,count,index):
    for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[name]='1'
    import run_active
    with (Path(raw)/f'worker_{index}.log').open('x',encoding='utf-8',buffering=1) as log:
        sys.stdout=log;sys.stderr=log
        sys.argv=[str(LEGACY/'run_active.py'),'--prepared-path',str(raw),'--data-role',role,'--benchmark','--workers','2','--evaluation-worker',str(index),'--scenes',str(count),'--frames','28']
        run_active.main()

def collect(run,split):
    run=Path(run);cfg=verify(run);s=cfg['splits'][split];raw=run/'raw'/split
    raw_cfg=read(raw/'config.json')
    if sha(raw/'config.json')!=read(raw/'active_seal.json')['sha256'] or raw_cfg['family_seed']!=s['seed'] or raw_cfg['data_role']!=s['role'] or raw_cfg['scenes']!=s['count']:raise RuntimeError('Raw split plan changed')
    if split=='reserved_test' and (not (run/'policy_freeze.json').exists() or not (run/'audit.json').exists() or not read(run/'audit.json')['passed']):raise RuntimeError('Blind test blocked until frozen policy passes independent audit')
    if (raw/'seal.json').exists():
        seal=read(raw/'seal.json')
        if sha(raw/'config.json')!=seal['config_sha256']:raise RuntimeError('Raw protocol changed')
        return
    if list((raw/'development').glob('scene_*')):raise RuntimeError('Partial collection preserved; targeted recovery review required')
    folder=raw/'development';folder.mkdir(exist_ok=True);np.save(folder/'family.npy',np.array([[s['seed'],i] for i in range(s['count'])]))
    for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[name]='1'
    pool=ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn'));pending={pool.submit(worker,str(raw),s['role'],s['count'],i) for i in range(2)}
    try:
        while pending:
            done,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
            if split!='development':check_stop(run,300)
            for f in done:f.result()
            save(run/'status.json',dict(stage='collecting',split=split,completed=len(list(folder.glob('scene_*/result.json'))),total=s['count'],time=now(),training_started=False))
        files={p.relative_to(raw).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
        save(raw/'seal.json',dict(config_sha256=sha(raw/'config.json'),files=files,count=s['count'],seed=s['seed'],role=s['role']))
    except BaseException:
        (raw/'STOP_REQUESTED').touch()
        for f in pending:f.cancel()
        raise
    finally:pool.shutdown(wait=True,cancel_futures=True)

def export(run,split):
    from benchmark_report import fixed_matches,object_error
    from pipeline.claims import claim
    run=Path(run);cfg=verify(run);raw=run/'raw'/split;s=cfg['splits'][split];seal=read(raw/'seal.json')
    if sha(raw/'config.json')!=seal['config_sha256'] or any(sha(raw/name)!=h for name,h in seal['files'].items()):raise RuntimeError('Raw observations changed')
    output=paths(run,split);output.mkdir(parents=True,exist_ok=True)
    if (output/'manifest.json').exists():return load(run,split)
    x=[];families=[];objects=[];stages=[];eligible=[];labelled=[];classes=[];gains=[]
    for index in range(s['count']):
        if split!='development' and index%64==0:check_stop(run,300)
        folder=raw/'development'/f'scene_{index:04d}';observation=read(folder/'initial_observation_summary.json');journal=read(folder/'decisions.json');motion=read(folder/'motion.json')
        with np.load(folder/'sample.npz',allow_pickle=False) as z:truth={k:z[k] for k in z.files}
        family=[s['seed'],index]
        if truth['family'].tolist()!=family:raise RuntimeError('Raw family identity changed')
        claim(truth,s['role'],sha(raw/'config.json'),verify_only=True)
        # The feature function below receives predictions/observations only.
        matches=fixed_matches(observation['initial'],truth)
        for event in journal:
            if event['stage']!='after_sweep':continue
            snapshot=read(folder/event['analysis_snapshot'])
            if sha(folder/event['analysis_snapshot'])!=event['analysis_sha256']:raise RuntimeError('Snapshot changed')
            if max(snapshot['fitting_frames']+snapshot['heldout_frames'],default=0)>=event['seen_frames']:raise RuntimeError('Future view leaked into proposal')
            phase=int(Path(event['analysis_snapshot']).stem.split('_')[-1])
            cameras=[f['camera'] for f in motion['frames'][:event['seen_frames']]]
            for obj in snapshot['objects']:
                i=obj['object_index'];initial=observation['initial'][i];candidate=snapshot['raw'][i]
                values,ok=extract(initial,candidate,observation['groups'][i],phase,i,snapshot,obj,cameras,len(observation['initial']),observation['table_height'])
                # GT is restricted to this target branch; no target enters values.
                matched=i in matches;gain=object_error(initial,truth,matches[i])-object_error(candidate,truth,matches[i]) if matched else 0.
                cls=0 if gain< -1 else 2 if gain>1 else 1
                x.append(values);families.append(family);objects.append(i);stages.append(phase);eligible.append(ok);labelled.append(matched);classes.append(cls if matched else -1);gains.append(gain)
    arrays=dict(x=np.asarray(x,np.float32).reshape(-1,48),family=np.asarray(families,np.int64).reshape(-1,2),object_index=np.asarray(objects,np.int64),stage=np.asarray(stages,np.int64),
        eligible=np.asarray(eligible,bool),labelled=np.asarray(labelled,bool),classes=np.asarray(classes,np.int64),gains=np.asarray(gains,np.float32))
    np.savez_compressed(output/'dataset.npz',**arrays)
    save(output/'manifest.json',dict(split=split,role=s['role'],family_seed=s['seed'],families=s['count'],examples=len(x),eligible_labelled=int((arrays['eligible']&arrays['labelled']).sum()),
        dataset_sha256=sha(output/'dataset.npz'),raw_seal_sha256=sha(raw/'seal.json'),main_protocol_sha256=sha(run/'config.json')))
    return arrays

def load(run,split):
    run=Path(run);cfg=verify(run);p=paths(run,split);m=read(p/'manifest.json')
    if m['split']!=split or m['role']!=cfg['splits'][split]['role'] or m['family_seed']!=cfg['splits'][split]['seed'] or sha(p/'dataset.npz')!=m['dataset_sha256']:raise RuntimeError('Feature dataset seal/role changed')
    if sha(run/'raw'/split/'seal.json')!=m['raw_seal_sha256'] or sha(run/'config.json')!=m['main_protocol_sha256']:raise RuntimeError('Feature provenance changed')
    with np.load(p/'dataset.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
    family=arrays['family'];s=cfg['splits'][split]
    if len(family) and (not np.all(family[:,0]==s['seed']) or family[:,1].min()<0 or family[:,1].max()>=s['count']):raise RuntimeError('Foreign family in feature split')
    return arrays
