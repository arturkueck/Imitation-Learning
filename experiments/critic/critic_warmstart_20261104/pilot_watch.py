"""One bounded pilot worker, explicit start, keep-awake and incremental check."""
from pathlib import Path
import argparse
import ctypes
from datetime import datetime
import json
import os
import re
import subprocess
import sys
import time
import traceback
from night import read,write,sha,terminate

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]


def verify(out):
    proto=read(out/'protocol.json');cfg=read(out/'config.json')
    assert cfg['schema'] in ('relative-exploratory-online-v1','relative-exploratory-online-v2')
    if cfg['schema']=='relative-exploratory-online-v2':assert cfg['target_action_projection']=='actor_bounds_v1'
    assert cfg['temporary_regression_allowed'] and not cfg['performance_abort_enabled']
    assert read(out/'status.json')['state']=='READY'
    assert not (out/'STOP').exists() and not (out/'launch.json').exists(), 'No resume or retry'
    assert time.time()<datetime.fromisoformat(cfg['absolute_deadline_utc']).timestamp(), 'Deadline passed'
    for path,h in proto['input_hashes'].items():assert sha(path)==h, f'Prepared input changed: {path}'
    expected=[proto['worker_argv'][0],'-u',str(HERE/'relative_range.py'),'run','--execute','--output',str(out)]
    assert proto['worker_argv']==expected
    return proto,cfg


def supervise(out):
    worker=None
    info=dict(state='STARTING',pid=os.getpid(),started_unix=time.time())
    kernel=ctypes.windll.kernel32
    info['keepawake_enabled']=bool(kernel.SetThreadExecutionState(0x80000001))
    try:
        proto,cfg=verify(out)
        deadline=min(time.time()+cfg['wall_clock_cap_seconds'],datetime.fromisoformat(cfg['absolute_deadline_utc']).timestamp())
        info['deadline_unix']=deadline
        with (out/'worker.log').open('xb',buffering=0) as log:
            worker=subprocess.Popen(proto['worker_argv'],cwd=ROOT,stdin=subprocess.DEVNULL,
                stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            info.update(state='RUNNING',worker_pid=worker.pid)
            while worker.poll() is None:
                info['last_check_unix']=time.time();write(out/'supervisor.json',info)
                if (out/'STOP').exists() or time.time()>=deadline:
                    requested=(out/'STOP').exists()
                    terminate(worker,out)
                    info.update(state='STOPPED' if requested else 'TIME_LIMIT',returncode=worker.returncode)
                    return
                time.sleep(5)
            status=read(out/'status.json')
            info.update(state='COMPLETED' if worker.returncode==0 and status['state']=='COMPLETED' else 'ERROR',
                        returncode=worker.returncode,worker_state=status['state'])
    except Exception:
        info.update(state='ERROR',error=traceback.format_exc())
        if worker is not None and worker.poll() is None:terminate(worker,out)
    finally:
        kernel.SetThreadExecutionState(0x80000000)
        info['ended_unix']=time.time();write(out/'supervisor.json',info)


def launch(out):
    verify(out)
    with (out/'supervisor_launch.json').open('x',encoding='utf-8') as f:
        json.dump(dict(started_unix=time.time(),no_automatic_retry=True),f)
    with (out/'supervisor.log').open('xb',buffering=0) as log:
        p=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'_worker','--output',str(out)],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(supervisor_pid=p.pid,output=str(out))))


def check(out):
    if not (out/'supervisor.json').exists():
        state=read(out/'status.json')['state']
        print(f"{'READY' if state=='READY' and not (out/'supervisor_launch.json').exists() else 'ERROR'} | {state} | Kein Supervisor-Heartbeat")
        return
    now=time.time();sup=read(out/'supervisor.json');status=read(out/'status.json')
    folder=out/'monitor';folder.mkdir(exist_ok=True);path=folder/'state.json'
    prev=read(path) if path.exists() else {}
    log=out/'worker.log';offset=0;identity=None;errors=[]
    if log.exists():
        stat=log.stat();identity=[stat.st_ino,stat.st_ctime_ns]
        offset=prev.get('offset',max(0,stat.st_size-65536))
        if offset>stat.st_size or identity!=prev.get('log_identity',identity):offset=0
        with log.open('rb') as f:
            f.seek(offset)
            for line in f:
                text=line.decode('utf-8',errors='replace').strip()
                if re.search(r'Traceback|CUDA out of memory|AssertionError|RuntimeError|FloatingPointError|\b(?:NaN|Inf)\b',text,re.I):errors.append(text[:300])
            offset=f.tell()
    alive=sup['state']=='RUNNING' and now-sup.get('last_check_unix',0)<20
    progress={k:status[k] for k in ('state','seed','model','round','step','episode') if k in status}
    changed=progress!=prev.get('progress');last_progress=now if changed else prev.get('last_progress_unix',now)
    level='OK'
    if sup['state']=='STOPPED':level='WARNING'
    elif sup['state'] in ('ERROR','TIME_LIMIT') or status['state']=='ERROR' or errors or (sup['state']!='COMPLETED' and not alive):level='ERROR'
    elif alive and now-last_progress>600:level='WARNING'
    write(path,dict(last_check_unix=now,last_successful_check_unix=now if level=='OK' else prev.get('last_successful_check_unix'),
        offset=offset,log_identity=identity,progress=progress,last_progress_unix=last_progress,
        loss=status.get('loss'),process_alive=alive,worker_pid=sup.get('worker_pid'),new_errors=errors,
        handled_problems=prev.get('handled_problems',[])))
    print(f"{level} | {sup['state']} | Phase: {status['state']} | Step: {status.get('step','-')} | Neue Fehler: {len(errors)} | Aktion: keine")
    if level!='OK':print(json.dumps(dict(supervisor_error=sup.get('error'),worker_error=status.get('error'),new_errors=errors)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['launch','check','_worker'])
    p.add_argument('--output',type=Path,default=HERE/'pilot_002');args=p.parse_args();out=args.output.resolve()
    if args.command=='launch':launch(out)
    elif args.command=='check':check(out)
    else:supervise(out)
