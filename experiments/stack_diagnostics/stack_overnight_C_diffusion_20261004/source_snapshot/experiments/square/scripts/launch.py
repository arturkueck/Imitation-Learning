"""Launch an independent Windows process, outside the launching shell job."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--experiment-root', type=Path, default=ROOT / 'experiments/square')
args = parser.parse_args()
EXP = args.experiment_root.resolve()
logs = EXP / 'logs'
logs.mkdir(exist_ok=True)
if (EXP / 'launch.json').exists():
    raise RuntimeError('launch.json already exists; inspect the previous process before restarting')
with (logs / 'pipeline.log').open('ab',buffering=0) as out, (logs / 'pipeline.stderr.log').open('ab',buffering=0) as err:
    process = subprocess.Popen([sys.executable,'-u',str(EXP / 'scripts/pipeline.py')],
        cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP |
                      subprocess.CREATE_BREAKAWAY_FROM_JOB)
info = {'pid':process.pid,'launcher_pid':os.getpid(),'mechanism':
    'Windows DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP + CREATE_BREAKAWAY_FROM_JOB',
    'python':sys.executable,'pipeline':str(EXP / 'scripts/pipeline.py')}
(EXP / 'launch.json').write_text(json.dumps(info,indent=2))
print(json.dumps(info),flush=True)
