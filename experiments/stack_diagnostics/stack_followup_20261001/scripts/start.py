import json, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
EXP=ROOT/'experiments/stack_diagnostics/stack_followup_20261001'
assert json.loads((EXP/'preflight.json').read_text())['validated']
assert not (EXP/'launch.json').exists()
previous_pid=json.loads((EXP/'status.json').read_text())['pid'] if (EXP/'status.json').exists() else None
logs=EXP/'logs'; logs.mkdir(exist_ok=True)
with (logs/'pipeline.log').open('ab',buffering=0) as out,(logs/'pipeline.stderr.log').open('ab',buffering=0) as err:
    child=subprocess.Popen([sys.executable,'-u',str(EXP/'scripts/pipeline.py')],cwd=str(ROOT),
        stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB)
(EXP/'launch.json').write_text(json.dumps({'pid':child.pid},indent=2))
for _ in range(20):
    if child.poll() is not None: raise RuntimeError('Queued follow-up exited during launch')
    if (EXP/'status.json').exists():
        state=json.loads((EXP/'status.json').read_text())
        if state['pid']!=previous_pid:
            print(json.dumps(state),flush=True); break
    time.sleep(.2)
