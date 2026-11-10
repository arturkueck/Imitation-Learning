"""Bounded worker supervision, no automatic retry or method change."""
from pathlib import Path
import subprocess,sys,time,json,ctypes,os,traceback
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[1]/'experiments/stack_phased_8h_20261023'))
from method import write
def main():
    plan=json.loads((OUT/'protocol.json').read_text());deadline=plan['deadline'];process=None
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    info=dict(state='RUNNING',pid=os.getpid(),deadline=deadline)
    try:
        with (OUT/'worker.log').open('ab',buffering=0) as log:
            command=[sys.executable,'-u',str(OUT/'pipeline.py')]
            if '--resume-collection' in sys.argv:command.append('--resume-collection')
            process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            info['worker_pid']=process.pid;write(OUT/'supervisor_status.json',info)
            while process.poll() is None:
                if time.time()>=deadline or (OUT/'STOP').exists():
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True);info['state']='TIME_LIMIT' if time.time()>=deadline else 'STOPPED';break
                time.sleep(2)
            else:info['state']='COMPLETED' if process.returncode==0 else 'FAILED'
            info['returncode']=process.returncode
    except Exception:info.update(state='FAILED',error=traceback.format_exc())
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);write(OUT/'supervisor_status.json',info)
if __name__=='__main__':main()
