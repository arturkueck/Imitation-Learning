"""Paired horizons within one process and cached native cuDNN kernels."""
import sys,time,gc,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent
while not (OUT/'offline_audit_seed3.json').exists():time.sleep(2)
import rollout
p=argparse.ArgumentParser();p.add_argument('--direct-only',action='store_true');args=p.parse_args()
for kind in (('direct',) if args.direct_only else ('direct','diffusion')):
    for seed in (1,2,3):
        arms=[(2,10),(1,10),(4,10)]
        for horizon,steps in arms:
            name=f'{kind}_seed{seed}_h{horizon}_ddim{steps}'
            print('START',name,flush=True)
            sys.argv=['rollout.py',kind,str(seed),'--horizon',str(horizon),'--steps',str(steps),'--starts','40']
            if horizon==2 and steps==10:sys.argv+=['--parity']
            with (OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                previous_out,previous_err=sys.stdout,sys.stderr
                try:sys.stdout=log;sys.stderr=log;rollout.main()
                finally:sys.stdout=previous_out;sys.stderr=previous_err
            print('DONE',name,flush=True)
            gc.collect()
