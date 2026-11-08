"""Detached bounded worker. Never retries or changes experimental parameters."""
from pathlib import Path
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent


def write(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)


def supervise(name):
    runtime=HERE/'runtime';runtime.mkdir(exist_ok=True)
    out=HERE/name;statuspath=runtime/f'{name}.supervisor.json'
    start=time.time();deadline=start+10860;worker=None
    info=dict(state='STARTING',pid=os.getpid(),started_unix=start,deadline=deadline,output=str(out))
    keepawake=ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    info['keepawake_enabled']=bool(keepawake)
    try:
        assert not out.exists(),'Never overwrite an existing run'
        with (runtime/f'{name}.worker.log').open('xb',buffering=0) as log:
            worker=subprocess.Popen([sys.executable,'-u',str(HERE/'pilot.py'),'--output',str(out)],
                cwd=str(HERE.parents[1]),stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW)
            info.update(state='RUNNING',worker_pid=worker.pid);write(statuspath,info)
            while worker.poll() is None:
                if time.time()>=deadline or (out/'STOP').exists():
                    # Cooperative episode/update boundaries first; only this worker is killed.
                    (out/'STOP').touch(exist_ok=True)
                    try:worker.wait(timeout=30)
                    except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=10)
                    info['state']='TIME_LIMIT' if time.time()>=deadline else 'STOPPED'
                    break
                info['last_check_unix']=time.time();write(statuspath,info)
                time.sleep(5)
            else:info['state']='COMPLETED' if worker.returncode==0 else 'ERROR'
            info['returncode']=worker.returncode
    except Exception:
        info.update(state='ERROR',error=traceback.format_exc())
        if worker is not None and worker.poll() is None:worker.kill();worker.wait(timeout=10)
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        info['ended_unix']=time.time();write(statuspath,info)


def launch(name):
    assert name=='run_001','Explicit separate run name required for another experiment'
    assert not (HERE/name).exists()
    runtime=HERE/'runtime';runtime.mkdir(exist_ok=True)
    lock=runtime/f'{name}.launch.json'
    with lock.open('x',encoding='utf-8') as stream:
        json.dump(dict(started_unix=time.time(),no_automatic_retry=True),stream)
    with (runtime/f'{name}.supervisor.log').open('xb',buffering=0) as log:
        proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--worker','--name',name],
            cwd=str(HERE.parents[1]),stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW,
            close_fds=True)
    print(json.dumps(dict(supervisor_pid=proc.pid,run=str(HERE/name))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--name',default='run_001');args=p.parse_args()
    if args.worker:supervise(args.name)
    else:launch(args.name)
