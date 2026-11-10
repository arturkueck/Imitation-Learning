"""Inference-only matrix with the validated single stream and one shared baseline."""
import sys,gc,json,faulthandler,shutil
from pathlib import Path
import batch_rollout

OUT=Path(__file__).resolve().parent.parent
assert (OUT/'stream_episode_parity_v5.json').exists()
faulthandler.enable()
for seed in (1,2,3):
    for group,h,steps in [('replanning',2,10),('replanning',1,10),('replanning',4,10),('ddim',2,5),('ddim',2,50)]:
        name=f'diffusion_seed{seed}_h{h}_ddim{steps}'+('_ddimstudy' if group=='ddim' else '')
        print('START',name,flush=True)
        sys.argv=['batch_rollout.py',str(seed),'--horizon',str(h),'--steps',str(steps),'--starts','40','--group',group,'--workers','1']
        with (OUT/f'{name}_final.log').open('a',encoding='utf-8') as log:
            previous_out,previous_err=sys.stdout,sys.stderr
            try:
                sys.stdout=log;sys.stderr=log
                batch_rollout.main()
            finally:sys.stdout=previous_out;sys.stderr=previous_err
        gc.collect();batch_rollout.torch.cuda.empty_cache()
        print('DONE',name,flush=True)
    # The h=2, DDIM-10 reference is the same inference condition in both studies.
    source=OUT/'rollouts'/f'diffusion_seed{seed}_h2_ddim10'
    dest=OUT/'rollouts'/f'diffusion_seed{seed}_h2_ddim10_ddimstudy'
    shutil.copytree(source,dest,dirs_exist_ok=True)
    rows=json.loads((dest/'results.json').read_text())
    for row in rows:row['comparison_group']='ddim';row['shared_replanning_baseline']=True
    (dest/'results.json').write_text(json.dumps(rows,indent=2))
    meta=json.loads((dest/'complete.json').read_text());meta['shared_replanning_baseline']=True
    (dest/'complete.json').write_text(json.dumps(meta))
(OUT/'all_closed_complete.json').write_text(json.dumps(dict(training_seeds=[1,2,3],ddim_steps_closed=[5,10,50],execution_horizons=[1,2,4],starts_each=40,no_training=True,workers=1,native_sampling_batch_size=1,shared_ddim10_replanning_baseline=True,unique_new_diffusion_rollouts=600,unique_new_direct_rollouts=360)))
faulthandler.cancel_dump_traceback_later()
