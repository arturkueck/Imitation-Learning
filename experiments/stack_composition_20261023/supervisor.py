"""Independent watchdog, finite wall-clock budget, no automatic retries."""
from pathlib import Path
import ctypes,datetime,json,os,subprocess,sys,time,traceback,hashlib
OUT=Path(__file__).resolve().parent

def write(value):
    tmp=OUT/'status.tmp';tmp.write_text(json.dumps(value,indent=2));tmp.replace(OUT/'status.json')

def main():
    start=time.time();deadline=start+8*3600
    info=dict(state='RUNNING',pid=os.getpid(),started_utc=datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat(),
        deadline_utc=datetime.datetime.fromtimestamp(deadline,datetime.timezone.utc).isoformat(),max_hours=8)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    child=None
    try:
        with (OUT/'worker.log').open('ab',buffering=0) as log:
            child=subprocess.Popen([sys.executable,'-u',str(OUT/'run.py'),'--deadline',str(deadline)],stdout=log,stderr=log,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
            info['worker_pid']=child.pid;write(info)
            while child.poll() is None:
                if time.time()>=deadline or (OUT/'STOP').exists():
                    child.terminate()
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    info['state']='TIME_BUDGET_REACHED' if time.time()>=deadline else 'STOPPED';break
                time.sleep(2)
            else: info['state']='COMPLETED' if child.returncode==0 else 'FAILED'
            info['returncode']=child.returncode
    except Exception:
        info.update(state='FAILED',error=traceback.format_exc())
        if child and child.poll() is None:child.terminate()
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        info['elapsed_seconds']=time.time()-start;write(info)
        subprocess.run([sys.executable,str(OUT/'summarize.py')],timeout=60,check=False)

if __name__=='__main__':main()
