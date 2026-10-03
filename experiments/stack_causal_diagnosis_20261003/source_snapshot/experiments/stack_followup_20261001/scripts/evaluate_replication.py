"""Same 40 fixed starts for every training replicate; hold rollout RNG fixed."""
import argparse,json,random
import numpy as np,torch
from replication_common import OUT,folder,checkpoint,SOURCE
from direct_common import DirectPolicy,KEYS
from dynamics_common import extra_metrics
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
from robustness import Intervention,refresh_observation
import video_views
p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('seed',type=int);args=p.parse_args();dest=folder(args.kind,args.seed)/'rollouts';dest.mkdir(exist_ok=True);assert not (dest/'results.json').exists();protocol=json.loads((OUT/'protocol.json').read_text());torch.set_num_threads(4)
ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',args.seed) if args.kind=='diffusion' else SOURCE['checkpoint']);cfg=json.loads(ck['config']);cfg['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(cfg)
if args.kind=='direct':
    c,_=config_from_checkpoint(ckpt_dict=ck);obs_utils.initialize_obs_utils_with_config(c);policy=DirectPolicy(checkpoint('direct',args.seed))
else:policy,_=policy_from_checkpoint(ckpt_dict=ck)
env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=True);torch.backends.cuda.matmul.allow_tf32=False;results=[]
for seed in protocol['fixed_start_seeds']:
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env);assert intervention.initial_state_hash==protocol['fixed_start_hashes'][str(seed)];video_views.setup_cameras(env);raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS};measured=None;tail=0;success=False
    for step in range(540):
        po={k:np.asarray(obs[k]) for k in KEYS}
        for k in KEYS:observations[k].append(po[k].copy())
        with torch.no_grad():action=np.asarray(policy(ob=po)).copy()
        obs,_,done,_=env.step(action);pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task']);trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
        if measured is None and (ok or done or step==499):measured=step+1;success=ok
        elif measured is not None:
            tail+=1
            if tail==40:break
    t=np.array(trace);np.savez_compressed(dest/f'{seed}.npz',trace=t,states=np.array(states),measured=measured,**{k:np.array(v) for k,v in observations.items()});r=dict(seed=seed,training_seed=args.seed,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**extra_metrics(t,measured),sustained_success=bool(success and np.all(t[measured:,36]>0)));results.append(r);(dest/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(r),flush=True)
env.base_env.close()
