"""Only after whole-episode bitwise parity: independent batch-1 stream evaluation."""
import sys,gc,json,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent
while not (OUT/'stream_episode_parity_v5.json').exists():time.sleep(2)
import batch_rollout
for seed in (1,2,3):
    arms=[('replanning',2,10),('replanning',1,10),('replanning',4,10),('ddim',2,10),('ddim',2,5),('ddim',2,50)]
    for group,h,steps in arms:
        name=f'diffusion_seed{seed}_h{h}_ddim{steps}'+('_ddimstudy' if group=='ddim' else '')
        print('START',name,flush=True)
        sys.argv=['batch_rollout.py',str(seed),'--horizon',str(h),'--steps',str(steps),'--starts','40','--group',group,'--workers','1']
        with (OUT/f'{name}_streams.log').open('a',encoding='utf-8') as log:
            previous_out,previous_err=sys.stdout,sys.stderr
            try:sys.stdout=log;sys.stderr=log;batch_rollout.main()
            finally:sys.stdout=previous_out;sys.stderr=previous_err
        gc.collect();batch_rollout.torch.cuda.empty_cache();print('DONE',name,flush=True)
(OUT/'all_closed_complete.json').write_text(json.dumps(dict(training_seeds=[1,2,3],ddim_steps_closed=[5,10,50],execution_horizons=[1,2,4],starts_each=40,no_training=True)))
