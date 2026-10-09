"""Replay selected saved simulator states. No fresh policy rollout."""
import json,random
import numpy as np,torch
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from dynamics_common import OUT,SOURCE
from robomimic.utils.file_utils import load_dict_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(cfg);env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True)
for v in ('baseline','dynamics'):
    for seed in json.loads((OUT/'representative_seeds.json').read_text()):
        path=OUT/v/'rollouts'/f'{seed}.npz';data=np.load(path);t=data['trace'];states=data['states'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);env.reset();video_views.setup_cameras(env)
        with imageio.get_writer(str(path.with_suffix('.mp4')),fps=4) as writer:
            for i in range(0,len(t),5):
                env.reset_to({'states':states[i]});frame=Image.fromarray(video_views.frame(env,size=256));draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black');dist=np.linalg.norm(t[i,4:6]-t[i,1:3])
                draw.text((4,480),f'{v} seed {seed} t={(i+1)*.05:.2f}s XY={dist*100:.1f}cm',fill='white');draw.text((4,496),f'B-z={t[i,6]:.3f} grip={t[i,26]:+.2f} held={int(t[i,34])}',fill='white');writer.append_data(np.array(frame))
        print(path.with_suffix('.mp4'),flush=True)
env.base_env.close()
