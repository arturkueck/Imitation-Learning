"""Replay existing states only; no additional policy evaluation or heuristic."""
import json,os,random
import numpy as np,torch
from replication_common import OUT,rollouts,SOURCE
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from robomimic.utils.file_utils import load_dict_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
import video_views
dest=OUT/'representative';dest.mkdir(exist_ok=True)
for start in (46000,46003,46005):
    fig,axes=plt.subplots(3,3,figsize=(13,8),sharex=True)
    for col,seed in enumerate((1,2,3)):
        z=np.load(rollouts('direct',seed)/f'{start}.npz');t=z['trace'];times=(t[:,0]+1)*.05
        row=next(r for r in json.loads((rollouts('direct',seed)/'results.json').read_text()) if r['seed']==start)
        axes[0,col].plot(times,t[:,6],label='Cube');axes[0,col].plot(times,t[:,17],label='EEF');axes[0,col].axhline(1.045,color='k',ls='--');axes[0,col].set_title(f"Direct training seed {seed}; stable={row['sustained_success']}")
        axes[1,col].plot(times,np.linalg.norm(t[:,4:6]-t[:,1:3],axis=1)*100);axes[1,col].axhline(3,color='k',ls='--')
        axes[2,col].plot(times,np.linalg.norm(t[:,20:22],axis=1),label='XY');axes[2,col].plot(times,t[:,22],label='Z');axes[2,col].plot(times,t[:,26],label='Gripper',alpha=.5);axes[2,col].set_xlabel('Seconds after reset')
        for ax in axes[:,col]:
            if row['transport_start'] is not None:ax.axvline((row['transport_start']+1)*.05,color='tab:orange',alpha=.5)
            ax.grid(alpha=.2)
        axes[0,col].legend();axes[2,col].legend()
    for ax,label in zip(axes[:,0],('Height (m)','XY target distance (cm)','Action')):ax.set_ylabel(label)
    fig.suptitle(f'Same fixed start {start}; orange line = measured transport onset');fig.tight_layout();fig.savefig(dest/f'direct_start_{start}.png',dpi=150);plt.close(fig)
fig,axes=plt.subplots(3,2,figsize=(12,8),sharex=True,sharey='row')
for col,kind in enumerate(('diffusion','direct')):
    t=np.load(rollouts(kind,3)/'46003.npz')['trace'];times=(t[:,0]+1)*.05
    axes[0,col].plot(times,t[:,6],label='Cube');axes[0,col].plot(times,t[:,17],label='EEF');axes[0,col].axhline(1.045,color='k',ls='--');axes[0,col].set_title(kind+' training seed 3, start 46003')
    axes[1,col].plot(times,np.linalg.norm(t[:,4:6]-t[:,1:3],axis=1)*100);axes[1,col].axhline(3,color='k',ls='--')
    axes[2,col].plot(times,np.linalg.norm(t[:,20:22],axis=1),label='XY');axes[2,col].plot(times,t[:,22],label='Z');axes[2,col].plot(times,t[:,26],label='Gripper',alpha=.5);axes[2,col].set_xlabel('Seconds after reset')
    for ax in axes[:,col]:ax.grid(alpha=.2)
    axes[0,col].legend();axes[2,col].legend()
for ax,label in zip(axes[:,0],('Height (m)','XY target distance (cm)','Action')):ax.set_ylabel(label)
fig.tight_layout();fig.savefig(dest/'model_pair_seed_3_start_46003.png',dpi=150);plt.close(fig)
ck=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ck);obs_utils.initialize_obs_utils_with_config(cfg);env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=True)
records=[]
for kind,train,start in (('direct',2,46000),('direct',3,46003),('direct',3,46005),('diffusion',3,46003)):
    path=dest/f'{kind}_seed_{train}_start_{start}.mp4'
    records.append(dict(model_class=kind,training_seed=train,start_seed=start,video=str(path),saved_states_replayed=True))
    if path.exists():continue
    z=np.load(rollouts(kind,train)/f'{start}.npz');t=z['trace'];random.seed(start);np.random.seed(start);torch.manual_seed(start);env.reset();video_views.setup_cameras(env)
    with imageio.get_writer(str(path),fps=4) as writer:
        for i in range(0,len(t),5):
            env.reset_to({'states':z['states'][i]});frame=Image.fromarray(video_views.frame(env,size=256));draw=ImageDraw.Draw(frame);draw.rectangle((0,478,512,512),fill='black');draw.text((4,480),f'{kind} train {train}, start {start}, t={(i+1)*.05:.2f}s',fill='white');draw.text((4,496),f'B-z={t[i,6]:.3f}, XY={np.linalg.norm(t[i,4:6]-t[i,1:3])*100:.1f}cm, held={int(t[i,34])}',fill='white');writer.append_data(np.array(frame))
env.base_env.close();(dest/'manifest.json').write_text(json.dumps(records,indent=2));print(json.dumps(records))
