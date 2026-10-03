"""Paired fixed full rollouts with identical feature computation online/offline."""
import argparse,json,random
import numpy as np,torch
from dynamics_common import OUT,augment,numerics,extra_metrics,SOURCE,KEYS
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint
from robustness import Intervention,refresh_observation
import video_views
p=argparse.ArgumentParser();p.add_argument('variant');v=p.parse_args().variant;folder=OUT/v;dest=folder/'rollouts';dest.mkdir(exist_ok=True)
ckpt=load_dict_from_checkpoint(ckpt_path=str(folder/'model_final.pth'));cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg);torch.set_num_threads(4);policy,ckpt=policy_from_checkpoint(ckpt_dict=ckpt);env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True);numerics();results=[]
for episode in range(20):
    seed=46000+episode;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env)
    assert intervention.initial_state_hash==SOURCE['rollouts'][episode]['intervention']['initial_state_sha256'];video_views.setup_cameras(env);raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS+['zz_dynamics']};measured=None;tail=0;success=False
    for step in range(540):
        policy_obs=augment({k:np.asarray(obs[k]) for k in KEYS},v)
        for k in observations:observations[k].append(policy_obs[k].copy())
        with torch.no_grad():action=np.asarray(policy(ob=policy_obs)).copy()
        obs,_,done,_=env.step(action);pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task'])
        trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
        if measured is None and (ok or done or step==499):measured=step+1;success=ok
        elif measured is not None:
            tail+=1
            if tail==40:break
    t=np.array(trace);np.savez_compressed(dest/f'{seed}.npz',trace=t,states=np.array(states),measured=measured,**{k:np.array(value) for k,value in observations.items()});r=dict(seed=seed,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**extra_metrics(t,measured),sustained_success=bool(success and np.all(t[measured:,36]>0)));results.append(r);(dest/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(r),flush=True)
env.base_env.close()
