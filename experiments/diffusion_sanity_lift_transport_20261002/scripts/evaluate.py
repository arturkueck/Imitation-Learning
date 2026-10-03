"""Identical 40 starts/phase criteria; verify each action in controller units."""
import argparse,time,random,traceback
from collections import deque
import numpy as np,torch
from common import *
from dynamics_common import extra_metrics
from sanity_metrics import metrics
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
from robustness import Intervention,refresh_observation
import video_views

class DirectPolicy:
    def __init__(self,path,n):
        ck=torch.load(path,map_location='cpu',weights_only=False)
        assert ck['normalization_stats']==read(OUT/'normalization_stats.json')
        self.model=DirectChunk().cuda().eval();self.model.load_state_dict(ck['ema']);self.queue=deque();self.n=n;self.inverse_error=0.
    def start_episode(self):self.queue.clear()
    def __call__(self,ob):
        if not self.queue:
            x=torch.tensor(flatten(self.n.observations(ob)),device='cuda')
            normalized=self.model(x)[0].detach().cpu().numpy();raw=self.n.inverse_actions(normalized)
            self.n.check_actions(raw)
            self.inverse_error=max(self.inverse_error,float(abs(self.n.actions(raw)-normalized).max()))
            assert self.inverse_error<1e-6,'Wrong direct denormalization'
            self.queue.extend(raw[1:3])
        return self.queue.popleft()

def run(v,kind,seed):
    dest=folder(v,kind,seed);rd=dest/'rollouts';rd.mkdir(exist_ok=True);assert not (rd/'results.json').exists()
    protocol=read(OUT/'protocol.json')['baseline_protocol'];n=Normalizer(v);torch.set_num_threads(4)
    ck=load_dict_from_checkpoint(ckpt_path=str(checkpoint(v,kind,seed)) if kind=='diffusion' else SOURCE['checkpoint'])
    cfg=json.loads(ck['config']);cfg['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(cfg)
    if kind=='direct':
        c,_=config_from_checkpoint(ckpt_dict=ck);obs_utils.initialize_obs_utils_with_config(c);policy=DirectPolicy(checkpoint(v,kind,seed),n)
    else:
        policy,_=policy_from_checkpoint(ckpt_dict=ck)
        if n.obs_enabled:
            for k in KEYS:
                for s in ('scale','offset'):assert np.array_equal(policy.obs_normalization_stats[k][s],n.obs[k][s])
        for s in ('scale','offset'):
            expected=n.action[s] if n.action_enabled else np.ones((1,7),np.float32) if s=='scale' else np.zeros((1,7),np.float32)
            assert np.array_equal(policy.action_normalization_stats['actions'][s],expected)
        captured=[];old_get=policy.policy.get_action
        def capture(*a,**kw):
            result=old_get(*a,**kw);captured[:]=[result.detach().cpu().numpy()[0]];return result
        policy.policy.get_action=capture
    env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=True);torch.backends.cuda.matmul.allow_tf32=False
    results=[];inverse_error=0.;action_count=0;obs_error=0.;start=time.monotonic()
    try:
        for startseed in protocol['fixed_start_seeds']:
            random.seed(startseed);np.random.seed(startseed);torch.manual_seed(startseed);policy.start_episode()
            obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',startseed);intervention.apply();obs=refresh_observation(env)
            assert intervention.initial_state_hash==protocol['fixed_start_hashes'][str(startseed)]
            video_views.setup_cameras(env);raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS};measured=None;tail=0;success=False
            for step in range(500):
                po={k:np.asarray(obs[k]) for k in KEYS}
                for k in KEYS:observations[k].append(po[k].copy())
                with torch.no_grad():
                    if kind=='diffusion' and step==0:
                        actual=policy._prepare_observation(po)
                        expected=n.observations(po)
                        for k in KEYS:obs_error=max(obs_error,float(abs(actual[k][0].cpu().numpy()-expected[k]).max()))
                        assert obs_error<1e-6,'Wrong rollout observation normalization'
                    action=np.asarray(policy(ob=po)).copy()
                n.check_actions(action);action_count+=1
                if kind=='diffusion':
                    expected=n.inverse_actions(captured[0]).reshape(7)
                    inverse_error=max(inverse_error,float(abs(action-expected).max()))
                    assert inverse_error<1e-6,'Wrong native rollout denormalization'
                obs,_,done,_=env.step(action)
                pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids])
                held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task'])
                trace.append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
                early=metrics(np.array(trace))
                if early['simplified_success'] or done or step==499:
                    measured=step+1;success=early['simplified_success'];break
            t=np.array(trace);assert np.isfinite(t).all()
            np.savez_compressed(rd/f'{startseed}.npz',trace=t,states=np.array(states),measured=measured,**{k:np.array(z) for k,z in observations.items()})
            r=dict(variant=v,model_class=kind,training_seed=seed,seed=startseed,initial_state_sha256=intervention.initial_state_hash,measured_steps=measured,**extra_metrics(t,measured),sustained_success=False,**metrics(t))
            results.append(r);write(rd/'results.json',results)
            print(json.dumps(dict(start=startseed,completed=len(results),simplified_successes=sum(x['simplified_success'] for x in results))),flush=True)
        write(dest/'rollout_verification.json',dict(start_hashes_verified=40,finite_actions_verified=action_count,denormalization_max_error=inverse_error if kind=='diffusion' else policy.inverse_error,observation_normalization_max_error=obs_error,controller_range_checked_each_step=True,elapsed_seconds=time.monotonic()-start))
    finally:env.base_env.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=VARIANTS);p.add_argument('kind');p.add_argument('seed',type=int);a=p.parse_args()
    try:run(a.variant,a.kind,a.seed)
    except Exception:
        write(folder(a.variant,a.kind,a.seed)/'aborted.json',dict(stage='rollout',cause=traceback.format_exc()));raise
