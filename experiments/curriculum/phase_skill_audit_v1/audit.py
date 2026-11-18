"""Diagnose BC phase heads, transitions, and expert-prefix starts without training."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import sys
import time
import traceback
from functools import cache

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


registry=module('phase_audit_registry',HERE.parent/'registry.py')
validation=module('phase_audit_clock',HERE.parent/'axis_bc_clock_validation_20261112/pipeline.py')
runtime=validation.monitor
read,write=runtime.read,runtime.write


@cache
def libraries():
    return runtime.libraries()


def physical_ready(phase,measurement,context,plan):
    """Observable phase goals, not ground-truth expert action labels."""
    if phase==3:
        return bool(measurement['held'] and measurement['lift']>=plan['minimum_grasped_lift_m'] and
                    measurement['eef_goal_error']<=plan['lift_target_error_m'])
    if phase==4:
        return bool(measurement['held'] and measurement['xy_error']<=plan['travel_xy_error_m'] and
                    measurement['height_above_target']>=plan['travel_clearance_m'])
    if phase==5:
        return bool(measurement['xy_error']<=plan['placement_xy_error_m'] and
                    abs(measurement['height_above_target']-.04)<=plan['placement_height_error_m'] and measurement['pair_contact'])
    if phase==6:
        return bool(measurement['prefix_valid'])
    raise ValueError('Unsupported phase')


def eligible(phase,measurement,plan):
    if phase==3:return bool(measurement['held'])
    if phase==4:return bool(measurement['held'] and measurement['lift']>=plan['minimum_grasped_lift_m'])
    if phase==5:return bool(measurement['held'] and measurement['xy_error']<=.03 and measurement['height_above_target']>=.06)
    if phase==6:return physical_ready(5,measurement,{},plan)
    raise ValueError('Unsupported phase')


def measurement(env,obs,placement,source_start_z,lift_goal,controller):
    _,_,np=libraries()
    pos=[env.sim.data.body_xpos[i].copy() for i in env.cube_ids]
    source,target=pos[placement],pos[placement-1]
    valid=[controller.native.historical.old.prefix_valid(env,k) and
           not any(controller.native.finger_contact(env,c) for c in env.cubes[:k]) for k in (2,3)]
    fingers=[controller.native.finger_contact(env,c) for c in env.cubes]
    velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes])
    return dict(held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[placement].contact_geoms)),
        lift=float(source[2]-source_start_z),xy_error=float(np.linalg.norm(source[:2]-target[:2])),
        height_above_target=float(source[2]-target[2]),eef_goal_error=float(np.linalg.norm(obs['robot0_eef_pos']-lift_goal)),
        pair_contact=bool(env.check_contact(env.cubes[placement-1],env.cubes[placement])),
        prefix_valid=bool(valid[placement-1]),protected_lower_valid=bool(valid[0]) if placement==2 else None,
        fingers=fingers,valid=valid,positions=np.asarray(pos),velocities=velocities,eef=np.asarray(obs['robot0_eef_pos']).copy())


def scalar(m):return {k:v for k,v in m.items() if k not in ('positions','velocities','eef')}


def offline_audit(out,plan,device):
    base,torch,np=libraries()
    import h5py
    vector=base.backend().native.historical.vector
    from task_extensions.stack_expert import StackExpert
    data=base.load_data();manifest=read(base.MANIFEST)
    if base.sha(base.DATA)!=manifest['dataset_sha256']:raise ValueError('Expert data changed')
    durations={split:{str(p):[] for p in range(7)} for split in data}
    reconstruction_error=0.
    with h5py.File(base.DATA,'r') as f:
        for split in data:
            offset=0
            for name in sorted(manifest['split_ids'][split]):
                d=f['data'][name];actions=d['actions'][:]
                obs={k:d['obs'][k][:] for k in ('object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos')}
                raw=SimpleNamespace(cubes=[0,1],cube_ids=[0,1],sim=SimpleNamespace(data=SimpleNamespace(body_xpos=None)))
                expert=StackExpert(SimpleNamespace(base_env=raw));counts={p:0 for p in range(7)}
                anchor=None
                for t,action in enumerate(actions):
                    observation={k:v[t] for k,v in obs.items()};positions=observation['object'].reshape(2,3)
                    raw.sim.data.body_xpos=positions;phase=expert.phase
                    if expert.target is None:anchor=positions[1 if phase<4 else 0].copy()
                    x=vector(observation,anchor,expert.phase_steps)
                    label=expert(observation)
                    reconstruction_error=max(reconstruction_error,float(np.max(np.abs(label-action))))
                    if data[split][2][offset+t]!=phase or not np.array_equal(x,data[split][0][offset+t]):
                        raise ValueError('Phase/features no longer match archived arrays')
                    if data[split][3][offset+t]!=int(expert.phase!=phase):raise ValueError('Completion labels differ')
                    counts[phase]+=1
                for p,n in counts.items():durations[split][str(p)].append(n)
                offset+=len(actions)
            if offset!=len(data[split][0]):raise ValueError('Trajectory/frame mismatch')
    summary={s:{p:dict(n_trajectories=len(v),min_frames=min(v),median_frames=float(np.median(v)),max_frames=max(v)) for p,v in phases.items()} for s,phases in durations.items()}
    write(out/'segmentation_audit.json',dict(exact_phase_labels_verified=True,max_reconstructed_action_error=reconstruction_error,
        phase_durations=summary,phase_names={0:'Approach',1:'Grasp descend',2:'Close',3:'Lift',4:'Travel',5:'Descend',6:'Open'},
        source_has_full_retreat=False,source_has_full_50_frame_hold=False))
    results={}
    for model_id in plan['model_ids']:
        model,_,_=registry.restore(model_id,device)
        model.eval();predictions=[];logits=[]
        with torch.no_grad():
            for start in range(0,len(data['valid'][0]),512):
                a,z=model(torch.as_tensor(data['valid'][0][start:start+512],device=device),torch.as_tensor(data['valid'][2][start:start+512],device=device))
                predictions.append(a.cpu().numpy());logits.append(z.cpu().numpy())
        a=np.concatenate(predictions);z=np.concatenate(logits);results[model_id]={}
        for p in range(7):
            mask=data['valid'][2]==p;errors=(a[mask]-data['valid'][1][mask])**2
            truth=data['valid'][3][mask].astype(bool);done=z[mask]>=np.log(.8/.2)
            results[model_id][str(p)]=dict(n=int(mask.sum()),action_mse=float(errors.mean()),axis_mse=errors.mean(0).tolist(),
                tp=int((done&truth).sum()) if p<6 else None,fp=int((done&~truth).sum()) if p<6 else None,
                fn=int((~done&truth).sum()) if p<6 else None,
                training_clock_max=float(data['train'][0][data['train'][2]==p,9].max()),
                completion_used=p<6)
    write(out/'offline_phase_metrics.json',results)
    return data


def reset(env,seed):
    _,_,np=libraries();random.seed(seed);np.random.seed(seed);env.reset();env.sim.forward()
    return env._get_observations(force_update=True),env.sim.get_state().flatten().copy(),np.array([env.sim.data.body_xpos[i][2] for i in env.cube_ids])


def expert_prefix(env,seed,placement,phase,out,deadline,plan):
    base,_,_=libraries()
    from task_extensions.stack_expert import StackExpert
    obs,initial,z=reset(env,seed);expert=StackExpert(SimpleNamespace(base_env=env));digest=hashlib.sha256(initial.tobytes())
    for frame in range(plan['prefix_horizon']):
        base.check_stop(out,deadline)
        if expert.cube_index==placement and expert.phase==phase:
            return obs,expert,initial,z,frame,digest.hexdigest()
        if expert.cube_index>placement or expert.phase>7:raise ValueError('Expert prefix skipped requested phase')
        action=expert(obs);digest.update(action.tobytes());env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        digest.update(env.sim.get_state().flatten().tobytes())
    raise TimeoutError('Expert prefix did not reach phase within fixed horizon')


def isolated(env,model,seed,placement,phase,out,deadline,plan,teacher=False):
    base,torch,np=libraries();controller=base.backend();historical=controller.native.historical
    obs,expert,initial,z,prefix_frames,prefix_hash=expert_prefix(env,seed,placement,phase,out,deadline,plan)
    start_state=env.sim.get_state().flatten().copy();source=env.sim.data.body_xpos[env.cube_ids[placement]].copy()
    lift_goal=source+np.array([0,0,.24]);context={}
    start=measurement(env,obs,placement,z[placement],lift_goal,controller)
    start_eligible=eligible(phase,start,plan)
    policy=validation.adapter.make_policy(base,historical,model,.8,lambda:placement,17)
    policy.phase=phase;policy.steps=0;policy.anchor=None
    stable=0;ever=False;exit_predicted=False;trace=[];goal_frames=plan['phase6_stability_frames'][str(placement)]
    for frame in range(plan['phase_horizon']):
        base.check_stop(out,deadline)
        positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if teacher:
            # Extend the same phase-6 proportional hold for the final stability
            # check; this is an evaluation reference, never new training data.
            if phase==6:expert.phase=6
            action=expert(obs);exit_predicted=expert.phase!=phase
            probability=float(exit_predicted)
        else:
            with torch.no_grad():action,_,probability=policy.action(obs,positions[placement-1],positions[placement])
            exit_predicted=policy.phase!=phase
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        m=measurement(env,obs,placement,z[placement],lift_goal,controller)
        ready=physical_ready(phase,m,context,plan);ever|=ready;stable=stable+1 if ready else 0
        trace.append(np.r_[frame,placement,phase,probability,exit_predicted,ready,stable,m['eef'],m['positions'].ravel(),action,m['fingers'],m['valid'],m['velocities']])
        success=stable>=goal_frames if phase==6 else bool(exit_predicted and ready)
        if success or (phase<6 and exit_predicted):break
    final=measurement(env,obs,placement,z[placement],lift_goal,controller)
    return dict(seed=seed,placement=placement,phase=phase,teacher=teacher,eligible_start=start_eligible,
        prefix_frames=prefix_frames,prefix_sha256=prefix_hash,start_state_sha256=hashlib.sha256(start_state.tobytes()).hexdigest(),
        frames=frame+1,success=success,ever_physically_ready=ever,completion_predicted=exit_predicted if phase<6 else None,
        premature_completion=bool(phase<6 and exit_predicted and not physical_ready(phase,final,context,plan)),
        reached_without_completion=bool(phase<6 and ever and not exit_predicted),start=scalar(start),final=scalar(final)),np.asarray(trace)


def full_episode(env,model,seed,out,deadline,plan):
    base,torch,np=libraries();controller=base.backend();historical=controller.native.historical
    obs,initial,z=reset(env,seed);seq=controller.GuardedSequencer(model,3,controller.Clearance(env))
    seq.policy=validation.adapter.make_policy(base,historical,model,.8,lambda:seq.stage,17)
    segments=[];current=None;trace=[];tail=0
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline);stage,phase,retreat=seq.stage,seq.policy.phase,seq.retreat
        key=(stage,phase,retreat)
        positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if current is None or current['key']!=key:
            if current is not None:segments.append(current)
            goal=positions[stage]+np.array([0,0,.24])
            m=measurement(env,obs,stage,z[stage],goal,controller)
            current=dict(key=key,stage=stage,phase=phase,retreat=bool(retreat),start_frame=frame,frames=0,
                eligible_start=eligible(phase,m,plan) if phase in plan['phases'] and not retreat else None,
                start=scalar(m),ever_ready=False,lift_goal=goal.tolist(),clock_outside_training_frames=0)
        with torch.no_grad():action,_,probability=seq.policy.action(obs,positions[stage-1],positions[stage])
        raw,used=seq.policy.raw_steps,seq.policy.used_steps
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        m=measurement(env,obs,stage,z[stage],np.asarray(current['lift_goal']),controller)
        if phase in plan['phases'] and not retreat:
            ready=physical_ready(phase,m,{},plan);current['ever_ready']|=ready;current['ready_at_exit']=ready
        current['frames']+=1;current['end_frame']=frame;current['final']=scalar(m)
        current['clock_outside_training_frames']+=int(phase==6 and used>17)
        event=seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        current['exit_to']=[seq.stage,seq.policy.phase,bool(seq.retreat)]
        tail=tail+1 if m['valid'][-1] else 0
        trace.append(np.r_[frame,stage,phase,retreat,probability,raw,used,event,tail,m['eef'],m['positions'].ravel(),action,m['fingers'],m['valid'],m['velocities']])
        if tail>=50 or seq.timed_out:break
    if current is not None:segments.append(current)
    return dict(seed=seed,success=tail>=50,frames=frame+1,initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
        final_stage=seq.stage,final_phase=seq.policy.phase,retreat_timeout=seq.timed_out,segments=segments),np.asarray(trace)


def aggregate(isolated_rows,full_rows,teacher_rows,plan,complete):
    reference={(r['seed'],r['placement'],r['phase']):r for r in teacher_rows}
    result={}
    for model_id in plan['model_ids']:
        result[model_id]={}
        for placement in plan['placements']:
            result[model_id][placement]={}
            for phase in plan['phases']:
                rows=[r for r in isolated_rows if r['model']==model_id and r['placement']==placement and r['phase']==phase]
                valid=[r for r in rows if r['eligible_start'] and reference.get((r['seed'],placement,phase),{}).get('success')]
                segments=[s for r in full_rows if r['model']==model_id for s in r['segments'] if s['stage']==placement and s['phase']==phase and not s['retreat']]
                result[model_id][placement][phase]=dict(isolated_attempts=len(rows),valid_reference_attempts=len(valid),
                    isolated_successes=sum(r['success'] for r in valid),premature_completions=sum(r['premature_completion'] for r in valid),
                    full_visits=len(segments),full_eligible=sum(bool(s['eligible_start']) for s in segments),
                    full_physically_ready_at_last_frame=sum(bool(s.get('ready_at_exit')) for s in segments),
                    full_never_ready=sum(not s['ever_ready'] for s in segments))
    return dict(complete=complete,models=result,full_episode_successes={m:dict(n=sum(r['model']==m for r in full_rows),
        successes=sum(r['model']==m and r['success'] for r in full_rows)) for m in plan['model_ids']},
        teacher_reference=dict(n=len(teacher_rows),successes=sum(r['success'] for r in teacher_rows)),optimizer_updates=0,
        interpretation='Conditional developmental phase diagnosis, not fresh endtest success. Expert-prefix successes do not imply robust chained execution; reference-invalid or ineligible starts are excluded from conditional success counts.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',choices=('cpu','cuda'),default='cuda');p.add_argument('--smoke',action='store_true');args=p.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(ROOT):p.error('Output must stay in workspace')
    if out.exists():raise FileExistsError('Use a new diagnostic directory')
    out.mkdir(parents=True);plan=read(HERE/'config.json')
    plan['technical_only']=args.smoke
    if args.smoke:
        plan['model_ids']=plan['model_ids'][:1]
        plan['development_seeds'][1]=plan['development_seeds'][0]
        plan['isolated_seeds'][1]=plan['isolated_seeds'][0]
    write(out/'plan.json',plan)
    base,torch,np=libraries();base.configure(1);started=time.time();deadline=started+plan['maximum_seconds']
    (out/'traces').mkdir();full=[];units=[];teachers=[]
    def status(**values):write(out/'status.json',dict(pid=os.getpid(),started_unix=started,updated_unix=time.time(),deadline=deadline,**values))
    try:
        status(state='OFFLINE_AUDIT')
        offline_audit(out,plan,args.device)
        model_entries=read(HERE.parent/'models.json')['models']
        proof={str(path.relative_to(ROOT)):base.sha(path) for path in list(HERE.glob('*.py'))+[HERE/'config.json',HERE.parent/'registry.py',base.ARRAYS,base.DATA]}
        for model_id in plan['model_ids']:proof[model_entries[model_id]['checkpoint']]=model_entries[model_id]['sha256']
        write(out/'provenance.json',dict(inputs=proof,clock_adapter_sha256=base.sha(HERE.parent/'axis_bc_clock_validation_20261112/policy.py')))
        controller=base.backend();historical=controller.native.historical
        isolated_seeds=range(plan['isolated_seeds'][0],plan['isolated_seeds'][1]+1)
        # Shared expert positive controls for every paired phase context.
        env=historical.make_env(3)
        try:
            model,_,_=registry.restore(plan['model_ids'][0],args.device)
            for seed in isolated_seeds:
                for placement in plan['placements']:
                    for phase in plan['phases']:
                        status(state='EXPERT_REFERENCE',seed=seed,placement=placement,phase=phase,completed=len(teachers))
                        result,trace=isolated(env,model,seed,placement,phase,out,deadline,plan,teacher=True)
                        teachers.append(result);write(out/'expert_reference.json',teachers)
                        if seed==plan['isolated_seeds'][0]:np.savez_compressed(out/'traces'/f'expert_s{seed}_place{placement}_phase{phase}.npz',trace=trace)
        finally:env.close()
        references={(r['seed'],r['placement'],r['phase']):r for r in teachers}
        hashes={}
        for model_id in plan['model_ids']:
            model,_,_=registry.restore(model_id,args.device);model.eval();env=historical.make_env(3)
            try:
                for seed in range(plan['development_seeds'][0],plan['development_seeds'][1]+1):
                    status(state='FULL_ROLLOUTS',model=model_id,seed=seed,completed=len(full))
                    result,trace=full_episode(env,model,seed,out,deadline,plan);result['model']=model_id
                    if seed in hashes and hashes[seed]!=result['initial_sha256']:raise ValueError('Full rollout starts differ')
                    hashes[seed]=result['initial_sha256'];full.append(result);write(out/'full_rollouts.json',full)
                    np.savez_compressed(out/'traces'/f'{model_id}_full_{seed}.npz',trace=trace)
                for seed in isolated_seeds:
                    for placement in plan['placements']:
                        for phase in plan['phases']:
                            status(state='ISOLATED_PHASES',model=model_id,seed=seed,placement=placement,phase=phase,completed=len(units))
                            result,trace=isolated(env,model,seed,placement,phase,out,deadline,plan)
                            ref=references[(seed,placement,phase)]
                            if result['prefix_sha256']!=ref['prefix_sha256'] or result['start_state_sha256']!=ref['start_state_sha256']:
                                raise ValueError('Expert-prefix history/state differs between comparison branches')
                            result['model']=model_id;units.append(result);write(out/'isolated_phases.json',units)
                            if seed==plan['isolated_seeds'][0]:np.savez_compressed(out/'traces'/f'{model_id}_isolated_{seed}_place{placement}_phase{phase}.npz',trace=trace)
            finally:env.close()
            write(out/'summary.json',aggregate(units,full,teachers,plan,False))
        for path,digest in proof.items():
            if base.sha(ROOT/path)!=digest:raise ValueError('Source or model changed during diagnosis')
        summary=aggregate(units,full,teachers,plan,True);write(out/'summary.json',summary)
        status(state='COMPLETE',full_episodes=len(full),isolated_episodes=len(units),expert_references=len(teachers),elapsed_seconds=time.time()-started)
        print(json.dumps(summary))
    except BaseException as exc:
        write(out/'summary.json',aggregate(units,full,teachers,plan,False))
        status(state='PARTIAL_TIME_CAP' if isinstance(exc,TimeoutError) else 'FAILED',error=repr(exc),traceback=traceback.format_exc())
        raise


if __name__=='__main__':main()
