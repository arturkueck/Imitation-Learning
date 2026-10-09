"""Additional evaluation from identical held-out expert lift-end states, no training."""
import json,random,argparse,hashlib
import h5py,numpy as np,torch
from balance_common import EXP,SOURCE,event,rollout_metrics
from transport_data import DATA,KEYS,demos,history
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint
from robustness import refresh_observation
p=argparse.ArgumentParser();p.add_argument('variant');args=p.parse_args();v=args.variant;out=EXP/v/'expert_lift_rollouts';out.mkdir(exist_ok=True)
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint'] if v=='source' else str(EXP/v/'model_final.pth'));cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4);policy,ckpt=policy_from_checkpoint(ckpt_dict=ckpt);env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False);rs=[]
protocol=dict(type='additional evaluation only',train_changed=False,demos='all 20 validation demos',start='stored state at frozen event(d)',initial_observation='exact expert history k-1,k',horizon=120,tail=40,seed='81000 + demo suffix',interventions=False,reset_caveat='Simulator state restored; controller internal memory is reinitialized identically for all models. After first action observations come from the environment.')
protocol_path=EXP/'expert_lift_protocol.json'
if protocol_path.exists():assert json.loads(protocol_path.read_text())==protocol
else:protocol_path.write_text(json.dumps(protocol,indent=2))
with h5py.File(DATA,'r') as f:
    for d in demos():
        if d['split']!='valid':continue
        seed=81000+int(d['name'].split('_')[-1]);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();env.reset();k=event(d);state=f['data'][d['name']]['states'][k]
        env.reset_to({'states':state});raw=env.base_env;pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);error=float(np.max(abs(pos.ravel()-d['obs']['object'][k])));assert error<.001,(d['name'],error)
        initial_grasp=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));obs=history(d,k);trace=[];states=[];observations={key:[] for key in KEYS};measured=None;tail=0
        for step in range(160):
            for key in KEYS:observations[key].append(np.asarray(obs[key]).copy())
            with torch.no_grad():action=np.asarray(policy(ob=obs)).copy()
            obs,_,done,_=env.step(action);pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task'])
            trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
            if measured is None and (ok or done or step==119):measured=step+1
            elif measured is not None:
                tail+=1
                if tail==40:break
        t=np.array(trace);np.savez_compressed(out/(d['name']+'.npz'),trace=t,states=np.array(states),initial_state=state,expert_event=k,measured=measured,**{key:np.array(value) for key,value in observations.items()})
        distances={str(s):float(np.linalg.norm(t[j,4:6]-t[j,1:3])) for s,j in ((.5,9),(1.,19),(2.,39)) if j<len(t)}
        rs.append(dict(demo=d['name'],seed=seed,expert_event=k,initial_grasp=initial_grasp,initial_state_sha256=hashlib.sha256(state.tobytes()).hexdigest(),restored_position_error_m=error,measured_steps=measured,**rollout_metrics(t,measured),distance_from_expert_lift_start_m=distances));(out/'results.json').write_text(json.dumps(rs,indent=2));print(json.dumps(rs[-1]),flush=True)
env.base_env.close()
