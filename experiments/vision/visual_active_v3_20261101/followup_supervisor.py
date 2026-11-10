"""Independent, deadline-registered supervisor for exactly one bounded worker."""
from pathlib import Path
import sys,site,os,time,json,subprocess,ctypes
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3];RUN=HERE/'run_001';OUT=RUN/'followup_001'
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import save,independence
from deadline_guard import register
proof=independence();save(OUT/'supervisor_independence.json',proof)
if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Job-bound supervisor refused')
register(os.getpid(),'followup_phase_supervisor',RUN)
phase=json.loads((OUT/'phase.json').read_text());end=min(phase['shared_deadline_unix'],phase['head_phase_deadline_unix'])
if time.time()>=end-300:raise RuntimeError('No bounded phase time remains')
ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
worker=None;reason=None
try:
    with (OUT/'bootstrap.log').open('x',encoding='utf-8') as log:
        worker=subprocess.Popen([sys.executable,str(HERE/'followup_bootstrap.py'),'production'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    save(OUT/'supervisor.json',dict(pid=os.getpid(),worker_pid=worker.pid,phase_deadline_unix=end,shared_deadline_unix=phase['shared_deadline_unix']))
    # Child bootstrap immediately registers itself before importing ML packages.
    while worker.poll() is None:
        t=time.time()
        if t>=end-180:(OUT/'STOP_REQUESTED').touch(exist_ok=True)
        if t>=end:
            reason='six_hour_phase_deadline';worker.terminate()
            try:worker.wait(timeout=15)
            except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=10)
            break
        time.sleep(min(5,max(.05,end-t)))
    save(OUT/'supervisor_exit.json',dict(returncode=worker.returncode,reason=reason,finished_unix=time.time()))
finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
