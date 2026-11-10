"""Unattended collection -> training -> evaluation -> robustness -> videos."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / 'experiments/baselines/stack_four_night'
TASK = ROOT / 'experiments/baselines/additional_tasks/stack_four'
SCRIPTS = ROOT / 'experiments/baselines/additional_tasks'
LOGS = EXP / 'logs'
LOGS.mkdir(exist_ok=True)
status = {'state':'STARTING','pid':os.getpid(),'task':'stack_four',
    'target_demos':200,'algorithms':['bc_rnn','bc_transformer'],'epochs_per_model':1000,
    'task_outputs':str(TASK),'cube_handover':'NOT_SCHEDULED: demonstrator missing'}

def save():
    status['updated_at'] = datetime.now(timezone.utc).isoformat()
    temporary = EXP / 'status.tmp'; temporary.write_text(json.dumps(status,indent=2)); temporary.replace(EXP/'status.json')

def run(script, args, log):
    with log.open('w',encoding='utf-8') as output:
        child = subprocess.Popen([sys.executable,'-u',str(SCRIPTS/script),*args],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
        status['child_pid'] = child.pid; save()
        code = child.wait()
        if code: raise RuntimeError(f'{script} failed with exit code {code}; log: {log}')

if __name__ == '__main__':
    # Keep the system awake while working; allow the display to turn off.
    awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    status['sleep_prevention_active'] = bool(awake); save()
    try:
        report_path = TASK/'collection_report.json'
        if (TASK/'data/image_demonstrations.hdf5').exists():
            report = json.loads(report_path.read_text()) if report_path.exists() else {}
            if not report.get('ready_for_baseline') or report.get('accepted',0) < 200:
                raise RuntimeError('An incomplete dataset exists; preserving it, refusing overwrite')
        else:
            status['state'] = 'COLLECTING_DEMONSTRATIONS'; save()
            run('collect_demonstrations.py',['--task','stack_four','--expert',
                'task_extensions.stack_expert:make_expert','--demos','200','--attempts','1200'],
                LOGS/'collection.log')
        status['state'] = 'TRAINING_AND_EVALUATING'; save()
        run('run_training.py',['--task','stack_four'],LOGS/'training_pipeline.log')
        status['state'] = 'COMPLETED'; save()
    except Exception:
        status['state'] = 'FAILED'; status['error'] = traceback.format_exc(); save()
        traceback.print_exc(); sys.exit(1)
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
