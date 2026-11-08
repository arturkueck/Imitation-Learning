"""Future collection adapter: measured native grasp and complete state timing.

No scripted expert or safety action is introduced. Default is dry-run. A
20-frame --smoke validates signal shapes only; it is never training data.
"""
from pathlib import Path
import argparse, json, random, sys, time
from collections import defaultdict
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/stack_five_curriculum_20261023'))
import runner as historical
from transition_pilot import sha, dump, audit_arrays, extract

def finger_contact(env, cube):
    gripper=env.robots[0].gripper
    grippers=list(gripper.values()) if isinstance(gripper,dict) else [gripper]
    return any(env.check_contact(g.contact_geoms,cube.contact_geoms) for g in grippers)

@torch.no_grad()
def collect(env,model,count,seed,max_frames,deadline,snapshot_hook=None):
    np.random.seed(seed);random.seed(seed);env.reset();env.sim.forward()
    obs=env._get_observations(force_update=True)
    initial=env.sim.get_state().flatten().copy();seq=historical.Sequencer(model,count)
    records=defaultdict(list);tail=0
    for frame in range(max_frames):
        if time.time()>=deadline:raise TimeoutError('technical collector deadline')
        if snapshot_hook is not None:snapshot_hook(frame,env,seq,obs)
        policy=seq.policy;stage=seq.stage;phase=policy.phase;steps=policy.steps
        positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        anchor=positions[stage if phase<4 else stage-1].copy() if policy.anchor is None else policy.anchor.copy()
        pre=historical.observation(env,obs);pre_state=env.sim.get_state().flatten().copy()
        action,actual,prob=policy.action(obs,positions[stage-1],positions[stage]);assert actual==phase
        env.step(action);env.sim.forward()
        next_obs=env._get_observations(force_update=True)
        fingers=np.array([finger_contact(env,c) for c in env.cubes])
        prefixes=np.array([historical.old.prefix_valid(env,k) and not fingers[:k].any()
                           for k in range(2,count+1)])
        row=dict(x=historical.vector(obs,anchor,steps),a=action,p=phase,
            y=int(policy.phase!=phase),phase_steps=steps,anchor=anchor,stage=stage,
            retreat=seq.retreat,pre_obs=pre,post_obs=historical.observation(env,next_obs),
            pre_state=pre_state,post_state=env.sim.get_state().flatten().copy(),
            # These are native simulator signals measured AFTER the action.
            held_post=np.array([env._check_grasp(env.robots[0].gripper,c.contact_geoms) for c in env.cubes],bool),
            held_known=True,prefix_valid=prefixes,valid2=prefixes[0],valid=prefixes[-1],
            contacts=np.array([env.check_contact(env.cubes[k],env.cubes[k+1]) for k in range(count-1)]),
            fingers=fingers,
            velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes]),prob=prob)
        row['controller_event']=seq.advance(prefixes[stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        for k,v in row.items():records[k].append(v)
        obs=next_obs;tail=tail+1 if prefixes[-1] else 0
        if tail>=50:break
    a={k:np.asarray(v) for k,v in records.items()};a['initial']=initial
    audit_arrays(a,count)
    assert np.array_equal(a['post_state'][:-1],a['pre_state'][1:]),'state timing'
    assert a['held_post'].shape==(len(a['x']),count)
    # Validate serialized state against the synchronized derived state, not just
    # equality of consecutive state vectors. No subsequent rollout is performed.
    snapshot=env.sim.get_state();max_error=0.
    for j in np.unique(np.linspace(0,len(a['x'])-1,min(10,len(a['x'])),dtype=int)):
        env.sim.set_state_from_flattened(a['post_state'][j]);env.sim.forward()
        positions=np.array([env.sim.data.body_xpos[k] for k in env.cube_ids]).flatten()
        max_error=max(max_error,float(np.abs(positions-a['post_obs'][j,:count*3]).max()))
        restored_fingers=np.array([finger_contact(env,c) for c in env.cubes])
        restored_held=np.array([env._check_grasp(env.robots[0].gripper,c.contact_geoms) for c in env.cubes])
        assert np.array_equal(restored_fingers,a['fingers'][j]),'restored finger signal'
        assert np.array_equal(restored_held,a['held_post'][j]),'restored grasp signal'
    env.sim.set_state(snapshot);env.sim.forward();assert max_error<1e-9,'restored positions'
    return a,dict(seed=seed,count=count,frames=len(a['x']),complete_success=tail>=50,
        collector_schema='native_v2_forward_synchronized',restored_position_max_error_m=max_error,
        restored_contacts_and_grasp_verified=True,
        censored=tail<50 and len(a['x'])<500*(count-1),native_grasp_measured=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--frames',type=int,default=20);p.add_argument('--seed',type=int,default=498001)
    args=p.parse_args()
    if not args.smoke:print('DRY_RUN: native collector adapter; production orchestrator not activated');return
    assert args.output;args.output.mkdir(parents=True,exist_ok=False)
    assert 1<=args.frames<=400 and args.seed in (498001,498002),'bounded technical namespace'
    torch.set_num_threads(4)
    parent=ROOT/'experiments/stack_self_imitation_20261023/final_test/C_seed1.pth'
    model=historical.load(parent);env=historical.make_env(3)
    try:
        a,report=collect(env,model,3,args.seed,args.frames,time.time()+120)
        target=args.output/'technical_episode.npz';np.savez_compressed(target,**a)
        (args.output/'model.xml').write_text(env.model.get_xml(),encoding='utf-8')
        gripper=env.robots[0].gripper
        report.update(technical_only=True,excluded_from_training_and_eval=True,parent_sha256=sha(parent),
            gripper_type=type(gripper).__name__,finger_contact_uses_explicit_geometry=True,
            any_native_grasp=bool(a['held_post'].any()),any_finger_contact=bool(a['fingers'].any()))
        row=dict(path=str(target),teacher=str(parent),teacher_sha256=sha(parent),seed=args.seed,
            split='technical',initial_sha256=sha(target),count=3,native_collector=True)
        sections=extract(a,row,grasp=dict(held_post=a['held_post'],held_known=a['held_known']))
        report['accepted_technical_sections']=len(sections)
        report['technical_sections_never_training_data']=True
        dump(args.output/'technical_sections.json',sections)
        if args.frames>=300:
            assert report['any_native_grasp'] and report['any_finger_contact'],'positive measured signals missing'
        dump(args.output/'validation.json',report)
    finally:env.close()

if __name__=='__main__':main()
