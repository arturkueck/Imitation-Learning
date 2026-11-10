"""Bounded Windows-spawn simulation workers; coordinator alone seals the split."""
import multiprocessing as mp
import os,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from .common import read,save,sha,event,check_stop
from .protocol import verify_protocol,verify_imports

def shard_indices(count,workers,worker):return range(worker,count,workers)

def worker(run,split,smoke_count,workers,worker_id):
    os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
    import torch
    torch.set_num_threads(1)
    from .generate import collect
    return collect(Path(run),split,smoke_count,workers,worker_id)

def collect_parallel(run,split,smoke_count,workers):
    if not 2<=workers<=4:raise ValueError('Use 1..4 simulation workers')
    run=Path(run);cfg=verify_protocol(run,full_sources=True);folder=run/'data'/split
    count=smoke_count or cfg['splits'][split]['count']
    seed=cfg['development_seed'] if smoke_count else cfg['splits'][split]['seed']
    if (folder/'seal.json').exists():
        seal=read(folder/'seal.json')
        if seal['count']!=count:raise RuntimeError('Sealed split size cannot be changed')
        return seal
    if smoke_count is None:verify_imports(cfg)
    cancelled=run/'PARALLEL_CANCELLED';cancelled.unlink(missing_ok=True)
    save(run/'parallel_runtime.json',dict(workers=workers,start_method='spawn',assignment='index modulo workers',threads_per_worker=1))
    started=time.perf_counter();pool=ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn'))
    pending={pool.submit(worker,str(run),split,smoke_count,workers,i) for i in range(workers)}
    try:
        while pending:
            done,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
            check_stop(run,60)
            for future in done:future.result()
            completed=len(list(folder.glob('[0-9]*.json')))
            event(run,'render',split=split,rendered=completed,render_total=count,workers=workers,training_started=False)
        records=[]
        for index in range(count):
            check_stop(run,15);path=folder/f'{index:06d}.npz';r=read(path.with_suffix('.json'))
            if r['family']!=[seed,index] or r['split']!=split or sha(path)!=r['sha256']:raise RuntimeError('Worker family/hash mismatch')
            records.append(r)
        save(folder/'index.json',dict(split=split,seed=seed,count=count,records=records,purpose='development_only' if smoke_count else 'frozen_main_protocol'))
        seal=dict(split=split,count=count,seed=seed,index_sha256=sha(folder/'index.json'),history_sha256=cfg['historical_registry_sha256'],smoke_only=bool(smoke_count))
        save(folder/'seal.json',seal)
        save(run/f'parallel_{split}_timing.json',dict(workers=workers,families=count,wall_seconds=time.perf_counter()-started,included_worker_startup=True))
        return seal
    except BaseException:
        cancelled.write_text('Stop other workers; preserve partial families.',encoding='utf-8')
        for future in pending:future.cancel()
        raise
    finally:pool.shutdown(wait=True,cancel_futures=True)
