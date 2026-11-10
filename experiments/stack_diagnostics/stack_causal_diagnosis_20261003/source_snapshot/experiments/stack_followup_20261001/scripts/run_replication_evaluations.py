"""Run the frozen offline and rollout protocol when each training finishes."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from replication_common import OUT,ROOT,folder
p=argparse.ArgumentParser();p.add_argument('kind');args=p.parse_args();scripts=Path(__file__).parent
for seed in (2,3):
    dest=folder(args.kind,seed)
    while not (dest/'training_complete.json').exists():time.sleep(2)
    start=time.monotonic()
    for script in ('offline_replication.py','evaluate_replication.py'):
        logfile=dest/(script.removesuffix('.py')+'.log')
        with logfile.open('w',encoding='utf-8') as log:subprocess.run([sys.executable,'-u',str(scripts/script),args.kind,str(seed)],cwd=ROOT,stdout=log,stderr=log,check=True)
    (dest/'evaluation_complete.json').write_text(json.dumps(dict(seed=seed,model_class=args.kind,fixed_starts=40,elapsed_seconds=time.monotonic()-start),indent=2))
