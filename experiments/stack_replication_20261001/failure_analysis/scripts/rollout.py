"""Change only execution horizon or native DDIM inference step count."""
import argparse, random, time
from collections import deque
import numpy as np,torch
from common import *
from localise import localise
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
from robustness import Intervention,refresh_observation
import video_views

class Policy:
    def __init__(self,seed,horizon):
        ck=torch.load(checkpoint('direct',seed),map_location='cpu',weights_only=False);self.model=DirectChunk().cuda().eval();self.model.load_state_dict(ck['ema']);self.queue=deque();self.horizon=horizon
    def start_episode(self):self.queue.clear()
    def __call__(self,ob):
        if not self.queue:
            chunk=self.model(torch.tensor(flatten(ob),device='cuda'))[0].cpu().numpy();self.queue.extend(chunk[1:1+self.horizon])
        return self.queue.popleft()

def main():
    p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('seed',type=int);p.add_argument('--horizon',type=int,default=2);p.add_argument('--steps',type=int,default=10);p.add_argument('--starts',type=int,default=40);p.add_argument('--parity',action='store_true');p.add_argument('--group',default='replanning');p.add_argument('--native',action='store_true');args=p.parse_args()
    assert args.kind in ('direct','diffusion');assert args.horizon in (1,2,4);assert args.steps in (5,10,20,50)
    numerics();tag='' if args.group=='replanning' else ('_ddimstudy' if args.group=='ddim' else '_'+args.group);name=f'{args.kind}_seed{args.seed}_h{args.horizon}_ddim{args.steps}'+tag;dest=OUT/'rollouts'/name;dest.mkdir(parents=True,exist_ok=True)
    ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',args.seed));cfg=json.loads(ck['config']);cfg['algo']['horizon']['action_horizon']=args.horizon;cfg['algo']['ddim']['num_inference_timesteps']=args.steps;ck['config']=json.dumps(cfg)
    if args.kind=='direct':
        c,_=config_from_checkpoint(ckpt_dict=ck);obs_utils.initialize_obs_utils_with_config(c);policy=Policy(args.seed,args.horizon)
    else:
        policy,_=policy_from_checkpoint(ckpt_dict=ck)
        if not args.native:
            from graph_sampler import install
            graph=install(policy.policy,args.seed)
    env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=True)
    rows=json.loads((dest/'results.json').read_text()) if (dest/'results.json').exists() else [];events=json.loads((dest/'events.json').read_text()) if (dest/'events.json').exists() else [];completed={r['start_seed'] for r in rows};start=time.monotonic()
    for seed in PROTOCOL['fixed_start_seeds'][:args.starts]:
        if seed in completed:continue
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env);assert intervention.initial_state_hash==PROTOCOL['fixed_start_hashes'][str(seed)];video_views.setup_cameras(env);raw=env.base_env;trace=[];observations={k:[] for k in KEYS};measured=None;tail=0;success=False
        for step in range(540):
            po={k:np.asarray(obs[k]) for k in KEYS}
            for k in KEYS:observations[k].append(po[k].copy())
            with torch.no_grad():action=np.asarray(policy(ob=po)).copy()
            obs,_,done,_=env.step(action);pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task']);trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok])
            if measured is None and (ok or done or step==499):measured=step+1;success=ok
            elif measured is not None:
                tail+=1
                if tail==40:break
        t=np.array(trace);np.savez_compressed(dest/f'{seed}.npz',trace=t,measured=measured,**{k:np.array(v) for k,v in observations.items()});metrics=extra_metrics(t,measured);metrics['sustained_success']=bool(success and np.all(t[measured:,36]>0));f,e=localise(t,measured,metrics)
        r=dict(model=args.kind,training_seed=args.seed,start_seed=seed,executed_actions=args.horizon,ddim_steps=args.steps if args.kind=='diffusion' else 0,comparison_group=args.group,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**(metrics|f))
        if args.parity:
            assert args.horizon==2 and args.steps==10
            old=np.load(rollouts(args.kind,args.seed)/f'{seed}.npz')['trace'];assert old.shape[1]==t.shape[1]
            count=min(len(old),len(t));r['parity_frames']=count
            r['baseline_max_abs_error']=float(abs(t[:count]-old[:count]).max());r['baseline_action_max_abs_error']=float(abs(t[:count,20:27]-old[:count,20:27]).max());r['historical_trace_bitwise_equal']=bool(np.array_equal(t[:count],old[:count]));r['first_action_max_abs_error']=float(abs(t[0,20:27]-old[0,20:27]).max())
        rows.append(r);events.append(dict(start_seed=seed,**e));(dest/'results.json').write_text(json.dumps(rows,indent=2));(dest/'events.json').write_text(json.dumps(events,indent=2));print(f'{args.kind}/{args.seed} h={args.horizon} steps={args.steps} start={seed} stack={r["sustained_success"]} first_missing={r["first_unfulfilled_task_indicator"]} elapsed={time.monotonic()-start:.1f}s',flush=True)
    env.base_env.close();(dest/'complete.json').write_text(json.dumps(dict(starts=len(rows),elapsed_seconds=time.monotonic()-start,parity=args.parity)))
    if args.kind=='diffusion' and not args.native:(dest/'graph_live_parity.json').write_text(json.dumps(graph.live_checks,indent=2))
    return policy,ck

if __name__=='__main__':main()
