"""Frozen paired development evaluation with bounded, independent scene workers."""
from pathlib import Path
import os,sys,time,copy,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import numpy as np
from run import HERE,ROOT,prepare
from pipeline.common import read,save,sha,now
from pipeline.locking import exclusive

CRITICAL=['active_policy.py','active_analysis.py','centered_sweep.py','geometry.py','tracking.py','refine.py']

def worker(path,count,frames,table_height,workers,index):
    os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
    import run_active
    with (Path(path)/f'worker_{index}.log').open('x',encoding='utf-8',buffering=1) as log:
        sys.stdout=log;sys.stderr=log
        sys.argv=[str(HERE/'run_active.py'),'--run',Path(path).name,'--scenes',str(count),'--frames',str(frames),'--table-height',str(table_height),'--benchmark','--workers',str(workers),'--evaluation-worker',str(index)]
        run_active.main()
    return index

def launch(args):
    if not 1<=args.scenes<=100 or args.frames!=28 or args.table_height!=.8:raise ValueError('Evaluation keeps 28 frames and known0.8m table;1..100 development scenes')
    run=(HERE/args.run).resolve()
    if not run.is_relative_to(HERE) or run==HERE:raise ValueError('Invalid evaluation directory')
    baseline=read(HERE/'active_smoke_002/config.json')
    if any(sha(HERE/name)!=baseline['source_hashes'][name] for name in CRITICAL):raise RuntimeError('Frozen geometry/policy changed; do not silently benchmark another algorithm')
    with exclusive(ROOT/'monitor/vision-namespace'):cfg,protocol=prepare(run,args.scenes,args.frames)
    active=copy.deepcopy(read(HERE/'active_smoke_002/active_config.json'));active.update(created=now(),parent_protocol_sha256=sha(run/'config.json'),evaluation_mode='shadow both sides; adaptive decision sees acquired prefix only')
    save(run/'active_config.json',active);save(run/'active_seal.json',dict(active_config_sha256=sha(run/'active_config.json'),parent_protocol_sha256=sha(run/'config.json')))
    evaluation=dict(created=now(),purpose='fixed development evaluation; not final heldout test',count=args.scenes,workers=args.workers,families=[[protocol['family_seed'],i] for i in range(args.scenes)],
        variants=['initial','one_side','two_sides','adaptive'],fallback='unavailable side uses last available prefix; report availability separately; paired subset requires both sides',
        acquisition='record both feasible sides even if policy would stop; shadow-only images never enter earlier policy decisions',
        harm_threshold_mm_equivalent=1.,any_harm_epsilon=1e-6,update_labels='GT only after acquisition; raw candidate and gate assessed on fixed initial GT association',
        media_scene_indices=list(range(min(6,args.scenes))),critical_source_hashes={name:sha(HERE/name) for name in CRITICAL},
        config_sha256=sha(run/'config.json'),active_config_sha256=sha(run/'active_config.json'),heldout_endtests_used_for_scoring_or_selection=False,
        history_fingerprints_read_for_leakage_protection_only=True,optimizer_updates=0)
    save(run/'evaluation_config.json',evaluation);save(run/'evaluation_seal.json',dict(sha256=sha(run/'evaluation_config.json')))
    development=run/'development';development.mkdir();np.save(development/'family.npy',np.array(evaluation['families']))
    started=time.perf_counter()
    with exclusive(run):
        for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[name]='1'
        pool=ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn'))
        pending={pool.submit(worker,str(run),args.scenes,args.frames,args.table_height,args.workers,i) for i in range(args.workers)}
        try:
            while pending:
                done,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
                for future in done:future.result()
                count=len(list(development.glob('scene_*/result.json')))
                save(run/'status.json',dict(stage='evaluation',completed=count,total=args.scenes,workers=args.workers,time=now(),heartbeat_unix=time.time(),training_started=False))
            rows=[]
            for index in range(args.scenes):
                row=read(development/f'scene_{index:04d}/result.json')
                if row['family']!=evaluation['families'][index]:raise RuntimeError('Scene family assignment changed')
                rows.append(row)
            save(run/'results.json',dict(development_only=True,policy_trained=False,optimizer_updates=0,scenes=rows))
            from benchmark_report import report
            report(run)
            from active_reporting import annotate
            annotate(run,indices=evaluation['media_scene_indices'])
            files={p.relative_to(run).as_posix():sha(p) for p in development.rglob('*') if p.is_file()}
            save(run/'artifacts.json',dict(files=files,evaluation_config_sha256=sha(run/'evaluation_config.json')))
            save(run/'status.json',dict(stage='complete',completed=len(rows),total=args.scenes,time=now(),wall_seconds=time.perf_counter()-started,training_started=False,optimizer_updates=0))
        except BaseException as error:
            (run/'STOP_REQUESTED').touch();save(run/'status.json',dict(stage='error',error=repr(error),time=now(),training_started=False))
            for future in pending:future.cancel()
            raise
        finally:pool.shutdown(wait=True,cancel_futures=True)
