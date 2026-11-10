"""Independent Windows supervisor with immutable noon deadline; no automatic retry."""
from pathlib import Path
import os,sys,site,json,time,subprocess,ctypes,traceback,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import independence
from pipeline.common import read,save,event

def main():
    mode=sys.argv[1];run=Path(sys.argv[2]).resolve()
    if not run.is_relative_to(HERE) or mode not in ['supervise','worker']:raise ValueError('Invalid run/mode')
    proof=independence();save(run/f'{mode}_independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Refuse job-bound background process')
    if mode=='worker':
        spec=importlib.util.spec_from_file_location('vision_pipeline_cli',HERE/'pipeline.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        sys.argv=[str(HERE/'pipeline.py'),'start','--run',run.name,'--start-training','--workers','4']
        try:cli.main()
        except BaseException as e:
            if isinstance(e,(TimeoutError,InterruptedError)):event(run,'budget_exhausted',reason=str(e),training_started=(run/'checkpoints/latest.pth').exists())
            else:event(run,'error',error=repr(e),training_started=(run/'checkpoints/latest.pth').exists())
            raise
        return
    import psutil
    deadline=read(run/'budget.json')['deadline_unix'];kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState(0x80000001)
    process=None;known={};requested=False
    try:
        with (run/'worker.log').open('x',encoding='utf-8',buffering=1) as log:
            env=os.environ.copy();env['PYTHONUNBUFFERED']='1'
            process=subprocess.Popen([sys.executable,str(HERE/'runtime_entry.py'),'worker',str(run)],cwd=str(ROOT),stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
            parent=psutil.Process(process.pid)
            save(run/'launch.json',dict(supervisor_pid=os.getpid(),worker_pid=process.pid,worker_created=parent.create_time(),deadline_unix=deadline))
            while process.poll() is None:
                now=time.time()
                try:
                    for child in [parent]+parent.children(recursive=True):known[(child.pid,child.create_time())]=child
                except psutil.NoSuchProcess:pass
                if now>=deadline-180 and not requested:
                    (run/'STOP_REQUESTED').touch();requested=True
                if now>=deadline:
                    for (pid,created),child in reversed(list(known.items())):
                        try:
                            if abs(child.create_time()-created)<.01:child.terminate()
                        except psutil.NoSuchProcess:pass
                    _,alive=psutil.wait_procs(list(known.values()),timeout=5)
                    for child in alive:
                        try:child.kill()
                        except psutil.NoSuchProcess:pass
                    process.wait(timeout=10);break
                save(run/'supervisor_status.json',dict(pid=os.getpid(),worker_pid=process.pid,heartbeat_unix=now,deadline_unix=deadline,stop_requested=requested,known_processes=len(known)))
                time.sleep(5)
        save(run/'supervisor_exit.json',dict(returncode=process.returncode,time_unix=time.time(),deadline_unix=deadline,status=read(run/'status.json')))
    finally:kernel.SetThreadExecutionState(0x80000000)

if __name__=='__main__':main()
