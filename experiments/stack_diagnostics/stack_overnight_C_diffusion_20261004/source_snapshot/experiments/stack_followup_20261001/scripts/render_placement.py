"""Render saved simulator trajectories, without rerunning policy inference."""
import sys,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
import numpy as np
import torch
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from robomimic.utils.file_utils import load_dict_from_checkpoint, env_from_checkpoint, config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
OUT=ROOT/'experiments/stack_placement_20261001'
old=json.loads((ROOT/'experiments/stack_followup_20261001/evaluation/fixed_scheduler_h2/evaluation_results.json').read_text())
ckpt=load_dict_from_checkpoint(ckpt_path=old['checkpoint'])
config,_=config_from_checkpoint(ckpt_dict=ckpt)
obs_utils.initialize_obs_utils_with_config(config)
env,_=env_from_checkpoint(ckpt_dict=ckpt, render=False,render_offscreen=True)
for variant in ('baseline','xy_feedback','release_gate'):
    for seed in (46000,46002,46006):
        p=OUT/variant/f'{seed}.npz'
        if not p.exists(): continue
        if p.with_suffix('.mp4').exists(): continue
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        env.reset(); video_views.setup_cameras(env)
        data=np.load(p); trace=data['trace']; states=data['states']
        with imageio.get_writer(str(p.with_suffix('.mp4')),fps=4) as writer:
            for i in range(0,len(states),5):
                env.reset_to({'states':states[i]})
                frame=Image.fromarray(video_views.frame(env,size=256))
                delta=trace[i,4:7]-trace[i,1:4]
                draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black')
                draw.text((4,480),f'{variant} seed {seed} step {i} XY {np.linalg.norm(delta[:2])*1000:.1f}mm',fill='white')
                draw.text((4,496),f'height {delta[2]*1000:.1f}mm grip {trace[i,26]:+.2f} held {int(trace[i,34])}',fill='white')
                writer.append_data(np.array(frame))
        print(str(p.with_suffix('.mp4')),flush=True)
env.base_env.close()
