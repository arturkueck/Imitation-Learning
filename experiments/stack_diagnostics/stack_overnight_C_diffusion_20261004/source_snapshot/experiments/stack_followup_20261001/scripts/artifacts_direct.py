"""Representative trajectories and videos from saved states, no new rollout."""
import json,random,os
import numpy as np,torch
from direct_common import OUT,SOURCE
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from robomimic.utils.file_utils import load_dict_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
rows={v:json.loads((OUT/v/'rollouts/results.json').read_text()) for v in ('diffusion','direct')};success=[r['seed'] for r in rows['direct'] if r['sustained_success']];lift=[r for r in rows['direct'] if r['lift']];best=max(lift,key=lambda r:(r['position'],r['near'],r['correct_lift']))['seed'] if lift else 46003;unstable=[r['seed'] for r in rows['direct'] if r['near'] and not r['sustained_success']];seeds=sorted(set([46003,success[0] if success else best]+unstable[:1]));(OUT/'representative_seeds.json').write_text(json.dumps(seeds))
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(cfg);env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True)
for seed in seeds:
    fig,axes=plt.subplots(3,2,figsize=(12,8),sharex=True)
    for col,v in enumerate(('diffusion','direct')):
        path=OUT/v/'rollouts'/f'{seed}.npz';z=np.load(path);t=z['trace'];times=(t[:,0]+1)*.05
        axes[0,col].plot(times,t[:,6],label='Cube B');axes[0,col].plot(times,t[:,17],label='EEF');axes[0,col].axhline(1.045,color='black',ls='--');axes[0,col].set_ylabel('Height (m)');axes[0,col].set_title(v+' seed '+str(seed))
        axes[1,col].plot(times,np.linalg.norm(t[:,4:6]-t[:,1:3],axis=1)*100);axes[1,col].axhline(3,color='black',ls='--');axes[1,col].set_ylabel('XY target distance (cm)')
        axes[2,col].plot(times,np.linalg.norm(t[:,20:22],axis=1),label='XY');axes[2,col].plot(times,t[:,22],label='Z');axes[2,col].set_ylabel('Action');axes[2,col].set_xlabel('Seconds after reset')
        for ax in axes[:,col]:ax.grid(alpha=.2)
        axes[0,col].legend();axes[2,col].legend();random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);env.reset();video_views.setup_cameras(env)
        with imageio.get_writer(str(path.with_suffix('.mp4')),fps=4) as writer:
            for i in range(0,len(t),5):
                env.reset_to({'states':z['states'][i]});frame=Image.fromarray(video_views.frame(env,size=256));draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black');dist=np.linalg.norm(t[i,4:6]-t[i,1:3]);draw.text((4,480),f'{v} seed {seed} t={(i+1)*.05:.2f}s XY={dist*100:.1f}cm',fill='white');draw.text((4,496),f'B-z={t[i,6]:.3f} grip={t[i,26]:+.2f} held={int(t[i,34])}',fill='white');writer.append_data(np.array(frame))
    fig.tight_layout();fig.savefig(OUT/f'rollout_pair_{seed}.png',dpi=150);plt.close(fig)
env.base_env.close()
