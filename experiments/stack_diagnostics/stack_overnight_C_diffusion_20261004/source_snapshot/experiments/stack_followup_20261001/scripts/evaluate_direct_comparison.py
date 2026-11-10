"""Reuse original diffusion starts 0..19 and evaluate 20 more paired starts."""
import argparse,json,random,shutil
import numpy as np,torch
from direct_common import OUT,ROOT,KEYS,SOURCE,DirectPolicy
from dynamics_common import extra_metrics
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
from robustness import Intervention,refresh_observation
import video_views
p=argparse.ArgumentParser();p.add_argument('variant',choices=['diffusion','direct']);v=p.parse_args().variant;folder=OUT/v/'rollouts';folder.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
if v=='diffusion':policy,_=policy_from_checkpoint(ckpt_dict=ckpt)
else:
    c,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(c);policy=DirectPolicy(OUT/'model_final.pth')
env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True);torch.backends.cuda.matmul.allow_tf32=False;results=[]
if v=='diffusion':
    for episode in range(20):
        seed=46000+episode;source=ROOT/'experiments/stack_placement_20261001/baseline'/f'{seed}.npz';z=np.load(source);t=z['trace'];assert len(t)==500 and not t[:,36].any();shutil.copyfile(source,folder/f'{seed}.npz');r=dict(seed=seed,initial_state_sha256=SOURCE['rollouts'][episode]['intervention']['initial_state_sha256'],measured_steps=500,**extra_metrics(t,500),sustained_success=False,reused=True);results.append(r)
    (folder/'results.json').write_text(json.dumps(results,indent=2))
for episode in range(20 if v=='diffusion' else 0,40):
    seed=46000+episode;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env)
    if episode<20:assert intervention.initial_state_hash==SOURCE['rollouts'][episode]['intervention']['initial_state_sha256']
    video_views.setup_cameras(env);raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS};measured=None;tail=0;success=False
    for step in range(540):
        po={k:np.asarray(obs[k]) for k in KEYS}
        for k in KEYS:observations[k].append(po[k].copy())
        with torch.no_grad():action=np.asarray(policy(ob=po)).copy()
        obs,_,done,_=env.step(action);pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task']);trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
        if measured is None and (ok or done or step==499):measured=step+1;success=ok
        elif measured is not None:
            tail+=1
            if tail==40:break
    t=np.array(trace);np.savez_compressed(folder/f'{seed}.npz',trace=t,states=np.array(states),measured=measured,**{k:np.array(z) for k,z in observations.items()});r=dict(seed=seed,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**extra_metrics(t,measured),sustained_success=bool(success and np.all(t[measured:,36]>0)),reused=False);results.append(r);(folder/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(r),flush=True)
env.base_env.close()
