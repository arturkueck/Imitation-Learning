"""Paired placement diagnosis. No training or checkpoint mutations."""
import sys, json, random, argparse, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'experiments/baselines/square/scripts'))
import runtime
import numpy as np
import torch
from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint, load_dict_from_checkpoint
from robustness import Intervention, refresh_observation
from task_metrics import StackProgress
import video_views

OUT = ROOT/'experiments/stack_diagnostics/stack_placement_20261001'
OUT.mkdir(exist_ok=True)
parser=argparse.ArgumentParser()
parser.add_argument('--variant', default='baseline')
parser.add_argument('--episodes', type=int, default=20)
args=parser.parse_args()
assert args.variant in ('baseline','release_gate','xy_feedback')
old=json.loads((ROOT/'experiments/stack_diagnostics/stack_followup_20261001/evaluation/fixed_scheduler_h2/evaluation_results.json').read_text())
ckpt=load_dict_from_checkpoint(ckpt_path=old['checkpoint'])
cfg=json.loads(ckpt['config']); cfg['algo']['horizon']['action_horizon']=2
ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4)
policy,ckpt=policy_from_checkpoint(ckpt_dict=ckpt)
env,_=env_from_checkpoint(ckpt_dict=ckpt, render=False, render_offscreen=True)
folder=OUT/args.variant; folder.mkdir(exist_ok=True)
results=[]
for episode in range(args.episodes):
    seed=46000+episode
    baseline_path=OUT/'baseline'/f'{seed}.npz'
    if args.variant!='baseline' and baseline_path.exists():
        bt=np.load(baseline_path)['trace']
        if not ((bt[:-1,6]>.88)&(bt[:-1,34]>0)).any():
            # Neither intervention can activate; reuse identical deterministic trajectory.
            shutil.copy2(baseline_path,folder/f'{seed}.npz')
            result=next(r for r in json.loads((OUT/'baseline/results.json').read_text()) if r['seed']==seed)
            result={**result,'modified_steps':0,'reused_unchanged_baseline':True}
            results.append(result); (folder/'results.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(result),flush=True); continue
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    policy.start_episode(); obs=env.reset(); obs=env.reset_to(env.get_state())
    intervention=Intervention(env,'nominal',seed); intervention.apply(); obs=refresh_observation(env)
    assert intervention.initial_state_hash==old['rollouts'][episode]['intervention']['initial_state_sha256']
    video_views.setup_cameras(env)
    raw=env.base_env; progress=StackProgress(raw); trace=[]; states=[]; lifted_held=False
    for step in range(500):
        with torch.no_grad(): action=np.asarray(policy(ob=obs)).copy()
        original=action.copy()
        before=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids])
        held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]))
        lifted_held |= held and before[1,2]>raw.table_offset[2]+.08
        delta=before[1]-before[0]
        if args.variant=='release_gate' and lifted_held and held:
            # Only suppress premature opening. All six arm actions remain from policy.
            if np.linalg.norm(delta[:2])>=.009 or abs(delta[2]-.04)>=.008:
                action[-1]=1.
        if args.variant=='xy_feedback' and lifted_held and held:
            # Only lateral motion; policy retains height, rotation, and gripper control.
            action[:2]=np.clip(-.6*delta[:2]/.05,-1,1)
        obs,_,done,_=env.step(action); progress.update()
        pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids])
        quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids])
        grasp=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]))
        eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1]
        qpos=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1]
        row=np.r_[step,pos.ravel(),quat.ravel(),eef,qpos,action,original,grasp,raw.check_contact(*raw.cubes),raw.is_success()['task'] if hasattr(raw,'is_success') else env.is_success()['task']]
        trace.append(row); states.append(env.get_state()['states'].copy())
        if done or env.is_success()['task']: break
    np.savez_compressed(folder/f'{seed}.npz', trace=np.array(trace), states=np.array(states))
    result=dict(seed=seed, initial_state_sha256=intervention.initial_state_hash, success=bool(env.is_success()['task']), modified_steps=int(np.any(np.array(trace)[:,20:27]!=np.array(trace)[:,27:34],axis=1).sum()), **progress.result())
    results.append(result); (folder/'results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(result),flush=True)
env.base_env.close()
