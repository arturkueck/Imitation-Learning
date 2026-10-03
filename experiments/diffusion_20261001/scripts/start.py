import json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/diffusion_20261001'
validation=json.loads((EXP/'smoke/validation.json').read_text())
assert len(validation['models'])==3 and validation['windows_sharing_retry']
assert not (EXP/'launch.json').exists(), 'Already launched'
logs=EXP/'logs'; logs.mkdir(exist_ok=True)
with (logs/'pipeline.log').open('ab',buffering=0) as out,(logs/'pipeline.stderr.log').open('ab',buffering=0) as err:
    child=subprocess.Popen([sys.executable,'-u',str(EXP/'scripts/pipeline.py')],
        cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB)
info=dict(pid=child.pid,launcher_pid=os.getpid(),pipeline=str(EXP/'scripts/pipeline.py'))
(EXP/'launch.json').write_text(json.dumps(info,indent=2))
for _ in range(55):
    if child.poll() is not None: raise RuntimeError('Pipeline exited during launch; inspect status')
    path=logs/'train_stack_two_diffusion_vision.log'
    if path.exists() and 'Train Epoch 1' in path.read_text(errors='replace'):
        state=json.loads((EXP/'status.json').read_text())
        print(json.dumps(dict(launch=info,training_epoch_confirmed=1,
            training_pid=state.get('child_pid'),repair=state['repair'],results=str(EXP/'RESULTS.md'))),flush=True)
        break
    time.sleep(1)
else: print(json.dumps(dict(launch=info,confirmation='Process alive; first epoch not yet logged')))
