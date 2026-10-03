"""Videos of conditional transport gains and the one transient stack."""
import json
import numpy as np,imageio.v2 as imageio
from PIL import Image,ImageDraw
from balance_common import EXP,SOURCE
from robomimic.utils.file_utils import load_dict_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(cfg);env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True)
for v,name in [('uniform','demo_47'),('balanced','demo_47'),('uniform','demo_22')]:
    path=EXP/v/'expert_lift_rollouts'/(name+'.npz');data=np.load(path);t=data['trace'];states=data['states'];env.reset();video_views.setup_cameras(env)
    with imageio.get_writer(str(path.with_suffix('.mp4')),fps=4) as writer:
        for i in range(0,len(t),5):
            env.reset_to({'states':states[i]});frame=Image.fromarray(video_views.frame(env,size=256));draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black');delta=t[i,4:7]-t[i,1:4]
            draw.text((4,480),f'{v} {name} Expert-lift start t={(i+1)*.05:.2f}s XY={np.linalg.norm(delta[:2])*100:.1f}cm',fill='white');draw.text((4,496),f'dZ={delta[2]*100:.1f}cm grip={t[i,26]:+.2f} held={int(t[i,34])} stack={int(t[i,36])}',fill='white');writer.append_data(np.array(frame))
    print(path.with_suffix('.mp4'),flush=True)
env.base_env.close()
