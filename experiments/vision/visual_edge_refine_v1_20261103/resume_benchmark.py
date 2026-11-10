"""Single technical retry of an unscored failed benchmark, preserving its exact plan."""
from pathlib import Path
import os,sys,time,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from benchmark import worker,HERE
from pipeline.common import read,save,sha,now
from pipeline.locking import exclusive

def main():
    run=(HERE/sys.argv[1]).resolve()
    if not run.is_relative_to(HERE) or run==HERE:raise ValueError('Invalid run')
    with exclusive(run):
        if read(run/'status.json')['stage']!='error':raise RuntimeError('Retry requires recorded failed process')
        if (run/'attempt_002_runtime.json').exists():raise RuntimeError('Only one technical retry permitted')
        config=read(run/'config.json');evaluation=read(run/'evaluation_config.json');active=read(run/'active_config.json')
        if sha(run/'evaluation_config.json')!=read(run/'evaluation_seal.json')['sha256']:raise RuntimeError('Evaluation plan changed')
        if any(sha(HERE/n)!=h for n,h in config['source_hashes'].items()):raise RuntimeError('Frozen evaluation implementation changed')
        folders=list((run/'development').glob('scene_*'))
        if any(any(p.name!='sample.npz' for p in folder.iterdir()) for folder in folders):raise RuntimeError('Scored/acquired partial scene requires separate recovery review')
        # Four initial samples survived the memory error. Keep them in the archive;
        # the shared content claim rejects any different regenerated RGB/geometry.
        import numpy as np
        from pipeline.claims import claim
        preserved={}
        for folder in folders:
            sample=folder/'sample.npz'
            if sample.exists():
                with np.load(sample,allow_pickle=False) as z:claim({k:z[k] for k in z.files},'development',sha(run/'config.json'),verify_only=True)
                preserved[folder.name]=sha(sample)
        archive=run/'attempt_001_failed';archive.mkdir();(archive/'development').mkdir()
        for folder in folders:folder.rename(archive/'development'/folder.name)
        for path in list(run.glob('worker_*'))+[run/'status.json',run/'STOP_REQUESTED']:
            if path.exists():path.rename(archive/path.name)
        save(run/'attempt_002_runtime.json',dict(created=now(),reason='4 workers exhausted Windows commit/pagefile and CUDA memory; 2-worker preflight passed',
            original_workers=evaluation['workers'],workers=2,scientific_plan_sha256=sha(run/'evaluation_config.json'),families_unchanged=True,models_and_rules_unchanged=True,
            previous_process_confirmed_ended=True,previous_completed_scenes=0,preserved_initial_samples=preserved,
            unchanged_initial_content_enforced_by_shared_claim=True,retry_limit=1,orchestrator_sha256=sha(Path(__file__))))
        import shutil
        shutil.copy2(__file__,run/'resume_benchmark_source.py')
        for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[name]='1'
        started=time.perf_counter();pool=ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn'))
        pending={pool.submit(worker,str(run),evaluation['count'],config['frames'],active['table_height_m'],2,i) for i in range(2)}
        try:
            while pending:
                done,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
                for future in done:future.result()
                count=len(list((run/'development').glob('scene_*/result.json')))
                save(run/'status.json',dict(stage='evaluation',completed=count,total=evaluation['count'],workers=2,attempt=2,time=now(),heartbeat_unix=time.time(),training_started=False))
            rows=[]
            for index,family in enumerate(evaluation['families']):
                row=read(run/'development'/f'scene_{index:04d}/result.json')
                if row['family']!=family:raise RuntimeError('Frozen family assignment changed')
                rows.append(row)
            save(run/'results.json',dict(development_only=True,policy_trained=False,optimizer_updates=0,scenes=rows))
            from benchmark_report import report
            report(run)
            from active_reporting import annotate
            annotate(run,indices=evaluation['media_scene_indices'])
            save(run/'artifacts.json',dict(files={p.relative_to(run).as_posix():sha(p) for p in (run/'development').rglob('*') if p.is_file()},evaluation_config_sha256=sha(run/'evaluation_config.json')))
            save(run/'status.json',dict(stage='complete',completed=len(rows),total=evaluation['count'],attempt=2,workers=2,time=now(),wall_seconds=time.perf_counter()-started,training_started=False,optimizer_updates=0))
        except BaseException as error:
            (run/'STOP_REQUESTED').touch();save(run/'status.json',dict(stage='error',error=repr(error),attempt=2,time=now(),training_started=False))
            for future in pending:future.cancel()
            raise
        finally:pool.shutdown(wait=True,cancel_futures=True)

if __name__=='__main__':main()
