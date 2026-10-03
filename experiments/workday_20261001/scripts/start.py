"""Detach the validated pipeline and confirm that its first training started."""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/workday_20261001'
assert len(json.loads((EXP/'smoke/validation.json').read_text())['completed'])==4
assert not (EXP/'launch.json').exists(), 'Already launched; inspect existing process'
logs=EXP/'logs'; logs.mkdir(exist_ok=True)
with (logs/'pipeline.log').open('ab',buffering=0) as out, (logs/'pipeline.stderr.log').open('ab',buffering=0) as err:
    process=subprocess.Popen([sys.executable,'-u',str(EXP/'scripts/pipeline.py')],
        cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|
            subprocess.CREATE_BREAKAWAY_FROM_JOB)
info=dict(pid=process.pid,launcher_pid=os.getpid(),pipeline=str(EXP/'scripts/pipeline.py'))
(EXP/'launch.json').write_text(json.dumps(info,indent=2))
for _ in range(55):
    if process.poll() is not None:
        raise RuntimeError('Pipeline exited during launch; inspect status and stderr')
    path=logs/'train_stack_two_vision_short.log'
    if path.exists() and 'Train Epoch 1' in path.read_text(errors='replace'):
        status=json.loads((EXP/'status.json').read_text())
        assert status['sleep_prevention_active']
        print(json.dumps(dict(launch=info,confirmed_training_epoch=1,status=status['state'],
            child_pid=status.get('child_pid'),results=str(EXP/'RESULTS.md'))),flush=True)
        break
    time.sleep(1)
else:
    print(json.dumps(dict(launch=info,confirmation='PROCESS_ALIVE; first epoch not yet logged; inspect status.json')))
