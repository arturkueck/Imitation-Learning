"""Controlled inference matrix after four complete native/graph episode parity checks."""
import sys,gc,json,faulthandler
from pathlib import Path
import batch_rollout

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
assert (OUT/'stream_episode_parity_v6.json').exists()
faulthandler.enable();faulthandler.dump_traceback_later(300,repeat=True)
for seed in (1,2,3):
    for group,h,steps in [('replanning',2,10),('replanning',1,10),('replanning',4,10),('ddim',2,10),('ddim',2,5),('ddim',2,50)]:
        name=f'diffusion_seed{seed}_h{h}_ddim{steps}'+('_ddimstudy' if group=='ddim' else '')
        print('START',name,flush=True)
        sys.argv=['batch_rollout.py',str(seed),'--horizon',str(h),'--steps',str(steps),'--starts','40','--group',group,'--workers','4']
        with (OUT/f'{name}_v6.log').open('a',encoding='utf-8') as log:
            previous_out,previous_err=sys.stdout,sys.stderr
            try:
                sys.stdout=log;sys.stderr=log
                batch_rollout.main()
            finally:sys.stdout=previous_out;sys.stderr=previous_err
        gc.collect();batch_rollout.torch.cuda.empty_cache()
        print('DONE',name,flush=True)
(OUT/'all_closed_complete.json').write_text(json.dumps(dict(training_seeds=[1,2,3],ddim_steps_closed=[5,10,50],execution_horizons=[1,2,4],starts_each=40,no_training=True,workers=4,native_sampling_batch_size=1)))
faulthandler.cancel_dump_traceback_later()
