"""Replay representative saved states; no policy rerun or interventions."""
import json,random
import numpy as np
import torch
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from balance_common import EXP,SOURCE
from robomimic.utils.file_utils import load_dict_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(cfg)
env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True)
for v in ('uniform','balanced'):
    results=json.loads((EXP/v/'rollouts/results.json').read_text());success=[r['seed'] for r in results if r['stack']]
    progress=[r for r in results if r['lift']];best=max(progress,key=lambda r:(r['position'],r['near'],r['full_lift_end'] is not None,-r['xy_action_reversals']))['seed'] if progress else 46000
    for seed in sorted(set([46002,success[0] if success else best])):
        path=EXP/v/'rollouts'/f'{seed}.npz';data=np.load(path);t=data['trace'];states=data['states'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);env.reset();video_views.setup_cameras(env)
        with imageio.get_writer(str(path.with_suffix('.mp4')),fps=4) as writer:
            for i in range(0,len(t),5):
                env.reset_to({'states':states[i]});frame=Image.fromarray(video_views.frame(env,size=256));draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black');delta=t[i,4:7]-t[i,1:4]
                draw.text((4,480),f'{v} seed {seed} t={i*.05:.2f}s XY={np.linalg.norm(delta[:2])*100:.1f}cm',fill='white');draw.text((4,496),f'B-z={t[i,6]:.3f} grip={t[i,26]:+.2f} held={int(t[i,34])}',fill='white');writer.append_data(np.array(frame))
        print(path.with_suffix('.mp4'),flush=True)
env.base_env.close()
