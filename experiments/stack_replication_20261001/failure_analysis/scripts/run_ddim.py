"""Meaningful offline-selected DDIM endpoints and a fresh matched baseline."""
import sys,time,json,gc
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent
last=OUT/'rollouts/diffusion_seed3_h4_ddim10/complete.json'
while not last.exists():time.sleep(2)
import rollout
for seed in (1,2,3):
    for steps in (10,5,50):
        name=f'diffusion_seed{seed}_h2_ddim{steps}_ddimstudy'
        print('START',name,flush=True)
        sys.argv=['rollout.py','diffusion',str(seed),'--horizon','2','--steps',str(steps),'--starts','40','--group','ddim']
        if steps==10:sys.argv+=['--parity']
        with (OUT/f'{name}.log').open('a',encoding='utf-8') as log:
            previous_out,previous_err=sys.stdout,sys.stderr
            try:sys.stdout=log;sys.stderr=log;rollout.main()
            finally:sys.stdout=previous_out;sys.stderr=previous_err
        print('DONE',name,flush=True)
        gc.collect()
(OUT/'ddim_closed_complete.json').write_text(json.dumps(dict(seeds=[1,2,3],steps=[5,10,50],starts=40)))
