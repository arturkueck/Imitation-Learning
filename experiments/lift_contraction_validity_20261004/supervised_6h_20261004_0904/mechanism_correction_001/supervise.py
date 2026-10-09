"""One bounded diagnostic, no training, fresh output and exit after completion."""
import ctypes
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import psutil

OUT = Path(__file__).resolve().parent
SESSION = OUT.parent
ROOT = SESSION.parents[2]

def write(path, value):
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

assert not (OUT / 'launch.json').exists(), 'No overwrite/restart in the same folder'
launch = time.time()
session = json.loads((SESSION / 'session.json').read_text(encoding='utf-8'))
deadline = min(launch + 1200, session['deadline_unix'])
assert launch < deadline
write(OUT / 'launch.json', {'launch_unix': launch, 'deadline_unix': deadline, 'supervisor_pid': __import__('os').getpid(),
                          'supervisor_create_time': psutil.Process().create_time(), 'maximum_seconds': 1200,
                          'policy_training_updates': 0, 'original_session_deadline_unix': session['deadline_unix']})
spec = importlib.util.spec_from_file_location('diagnostic_job', SESSION / 'job.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
job = module.Job()
proc = None
result = {}
try:
    with (OUT / 'worker.log').open('xb', buffering=0) as log:
        proc = subprocess.Popen([sys.executable, '-u', str(OUT / 'run.py')], cwd=ROOT,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        job.assign(proc)
        identity = {'pid': proc.pid, 'create_time': psutil.Process(proc.pid).create_time()}
        write(OUT / 'worker_process.json', identity)
        while proc.poll() is None:
            now = time.time()
            if now >= deadline:
                job.terminate(); proc.wait(timeout=5)
                result['timed_out'] = True
                break
            if now >= deadline - 30 and not (OUT / 'STOP_REQUESTED').exists():
                (OUT / 'STOP_REQUESTED').write_text('Fixed bounded diagnostic deadline', encoding='utf-8')
            write(OUT / 'supervisor_status.json', {'state': 'RUNNING', 'worker': identity,
                                                  'deadline_unix': deadline, 'checked_unix': now})
            time.sleep(min(2, max(.1, deadline - now)))
        result.update(returncode=proc.returncode, worker=identity)
except BaseException:
    result.update(error=traceback.format_exc()); traceback.print_exc()
finally:
    if proc is not None and proc.poll() is None:
        job.terminate(); proc.wait(timeout=5)
    job.close()
    result.update(elapsed_seconds=time.time() - launch, finished_unix=time.time(),
                  deadline_unix=deadline, worker_job_closed=True, supervisor_exiting=True,
                  requested_awake_state=False)
    write(OUT / 'supervisor_result.json', result)
    print(json.dumps(result, indent=2))
