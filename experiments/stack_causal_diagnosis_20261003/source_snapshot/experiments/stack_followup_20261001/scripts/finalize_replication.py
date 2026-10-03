"""Finalize when both frozen evaluation pipelines have completed; never partial."""
import subprocess,sys,time,json
from pathlib import Path
base=Path(__file__).parent
out=base.parents[1]/'stack_replication_20261001'
while not all((out/k/f'seed_{s}'/'evaluation_complete.json').exists() for k in ('diffusion','direct') for s in (2,3)):
    time.sleep(2)
for script in ('analyze_replication.py','verify_replication.py','report_replication.py'):
    with (out/(script+'.log')).open('w') as log:
        subprocess.run([sys.executable,str(base/script)],stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'complete.json').write_text(json.dumps({'models':6,'fixed_starts_per_model':40,'verified':True}))
print('All six training replicates finalized and audited.',flush=True)
