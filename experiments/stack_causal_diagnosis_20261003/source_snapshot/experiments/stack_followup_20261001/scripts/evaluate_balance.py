"""Fixed paired rollout evaluation; no action intervention."""
import argparse,json,random
import numpy as np
import torch
from balance_common import EXP,SOURCE,ROOT,KEYS,rollout_metrics
from robomimic.utils.file_utils import policy_from_checkpoint,env_from_checkpoint,load_dict_from_checkpoint
from robustness import Intervention,refresh_observation
import video_views
p=argparse.ArgumentParser();p.add_argument('variant');args=p.parse_args()
folder=EXP/args.variant;out=folder/'rollouts';out.mkdir(exist_ok=True)
ckpt=load_dict_from_checkpoint(ckpt_path=str(folder/'model_final.pth'))
cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4);policy,ckpt=policy_from_checkpoint(ckpt_dict=ckpt)
env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True);results=[]
for episode in range(20):
    seed=46000+episode;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state())
    intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env)
    assert intervention.initial_state_hash==SOURCE['rollouts'][episode]['intervention']['initial_state_sha256']
    video_views.setup_cameras(env);raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS};measured=None;success=False;tail=0
    for step in range(540):
        for k in KEYS:observations[k].append(np.asarray(obs[k]).copy())
        with torch.no_grad():action=np.asarray(policy(ob=obs)).copy()
        obs,_,done,_=env.step(action)
        pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids])
        held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1]
        ok=bool(env.is_success()['task']);trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
        if measured is None and (ok or done or step==499):measured=step+1;success=ok
        elif measured is not None:
            tail+=1
            if tail==40:break
    t=np.array(trace);np.savez_compressed(out/f'{seed}.npz',trace=t,states=np.array(states),measured=measured,**{k:np.array(v) for k,v in observations.items()})
    r=dict(seed=seed,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**rollout_metrics(t,measured),sustained_success=bool(success and np.all(t[measured:,36]>0)))
    results.append(r);(out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(r),flush=True)
env.base_env.close()
