"""Independent guarded Q1 launch; invoked only after explicit training approval."""
from pathlib import Path
import os,sys,site,time,subprocess,ctypes,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'));sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import independence
from q_protocol import read,save,verify

def main():
    import psutil
    mode=sys.argv[1];run=Path(sys.argv[2]).resolve()
    if not run.is_relative_to(HERE) or mode not in ['supervise','worker']:raise ValueError('Invalid entry')
    proof=independence();save(run/f'{mode}_independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Refuse job-bound training process')
    cfg=verify(run)
    if mode=='worker':
        import quality
        sys.argv=[str(HERE/'quality.py'),'start','--run',run.name,'--start-training'];quality.main();return
    from pipeline.common import begin_budget
    hours=float(sys.argv[3])
    if not 0<hours<=cfg['planned_hours']:raise ValueError('Budget outside prepared maximum')
    if (run/'budget.json').exists():raise RuntimeError('Existing budget cannot be reset')
    budget=begin_budget(run,hours);deadline=budget['deadline_unix'];kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState(0x80000001);known={}
    try:
        with (run/'worker.log').open('x',encoding='utf-8',buffering=1) as log:
            process=subprocess.Popen([sys.executable,str(HERE/'runtime.py'),'worker',str(run)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUNBUFFERED':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
            parent=psutil.Process(process.pid);save(run/'launch.json',dict(supervisor_pid=os.getpid(),worker_pid=process.pid,worker_created=parent.create_time(),deadline_unix=deadline))
            while process.poll() is None:
                t=time.time()
                try:
                    for p in [parent]+parent.children(recursive=True):known[(p.pid,p.create_time())]=p
                except psutil.NoSuchProcess:pass
                if t>=deadline-300:
                    (run/'STOP_REQUESTED').touch()
                    for raw in (run/'raw').rglob('config.json'):(raw.parent/'STOP_REQUESTED').touch()
                if t>=deadline:
                    for (pid,created),p in reversed(list(known.items())):
                        try:
                            if abs(p.create_time()-created)<.01:p.terminate()
                        except psutil.NoSuchProcess:pass
                    _,alive=psutil.wait_procs(list(known.values()),timeout=5)
                    for p in alive:
                        try:p.kill()
                        except psutil.NoSuchProcess:pass
                    process.wait(timeout=10);break
                save(run/'supervisor_status.json',dict(time_unix=t,deadline_unix=deadline,worker_pid=process.pid,known_processes=len(known)));time.sleep(5)
        save(run/'supervisor_exit.json',dict(returncode=process.returncode,time_unix=time.time(),status=read(run/'status.json')))
    finally:kernel.SetThreadExecutionState(0x80000000)

if __name__=='__main__':main()
