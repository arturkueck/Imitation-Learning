"""Deterministic session deadline, no LLM/API calls, registered processes only."""
from pathlib import Path
import os,sys,json,time,argparse
from datetime import datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import site
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
sys.path.insert(0,str(ROOT/'experiments/visual_overnight_20261101'))
import psutil
from night import save,independence


def register(pid,role,run):
    run=Path(run).resolve()
    if not run.is_relative_to(HERE) or run==HERE:raise ValueError('Register only V3 run directories')
    process=psutil.Process(pid);command=process.cmdline()
    if not any(str(HERE).lower() in arg.lower().replace('/',os.sep) for arg in command):
        raise ValueError('Process command must reference this V3 experiment')
    record=dict(pid=pid,create_time=process.create_time(),role=role,run_directory=run.relative_to(HERE).as_posix())
    lock=HERE/'registered_processes.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        path=HERE/'registered_processes.json';rows=json.loads(path.read_text()) if path.exists() else []
        if not any(x['pid']==pid and x['create_time']==record['create_time'] for x in rows):rows.append(record)
        save(path,rows)
    finally:os.close(fd);lock.unlink()
    return record


def matching(row):
    try:
        process=psutil.Process(row['pid'])
        return process if abs(process.create_time()-row['create_time'])<.01 and process.is_running() else None
    except psutil.NoSuchProcess:return None


def guard():
    import ctypes
    proof=independence();save(HERE/'deadline_guard_independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Deadline guard must be independent')
    # An exclusive lock prevents multiple independent watchdogs.
    lock=HERE/'deadline_guard.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState(0x80000001)
    try:
        session=json.loads((HERE/'session.json').read_text());deadline=datetime.fromisoformat(session['deadline']).timestamp()
        requested=False;last=0
        while True:
            t=time.time();path=HERE/'registered_processes.json';rows=json.loads(path.read_text()) if path.exists() else []
            handoff=HERE/'monitor_state.json'
            finished=handoff.exists() and json.loads(handoff.read_text()).get('phase')=='finished'
            if finished and not any(matching(row) is not None for row in rows):
                save(HERE/'deadline_guard_status.json',dict(stage='workflow_finished',time_unix=t,deadline_unix=deadline))
                break
            if t>=deadline-180 and not requested:
                for row in rows:
                    run=(HERE/row['run_directory']).resolve()
                    if not run.is_relative_to(HERE):raise ValueError('Invalid registered run path')
                    (run/'STOP_REQUESTED').touch(exist_ok=True)
                requested=True
            if t>=deadline:
                outcomes=[]
                for row in reversed(rows):
                    process=matching(row)
                    if process is None:continue
                    try:process.terminate();process.wait(timeout=10);outcomes.append(dict(pid=row['pid'],action='terminated_at_deadline'))
                    except psutil.TimeoutExpired:process.kill();outcomes.append(dict(pid=row['pid'],action='killed_at_deadline'))
                save(HERE/'deadline_guard_status.json',dict(stage='deadline_reached',deadline_unix=deadline,time_unix=time.time(),actions=outcomes))
                break
            if t-last>=60:
                save(HERE/'deadline_guard_status.json',dict(stage='watching',pid=os.getpid(),time_unix=t,deadline_unix=deadline,registered_processes=len(rows)))
                last=t
            time.sleep(min(5,max(.05,deadline-t)))
    finally:kernel.SetThreadExecutionState(0x80000000);os.close(fd);lock.unlink()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['guard','register']);p.add_argument('--pid',type=int);p.add_argument('--role');p.add_argument('--run',type=Path);a=p.parse_args()
    if a.mode=='guard':guard()
    else:
        if not a.pid or not a.role or not a.run:p.error('register requires --pid --role --run')
        print(json.dumps(register(a.pid,a.role,a.run)))
