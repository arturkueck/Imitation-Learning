"""Frozen, bounded selective completion and factorial release diagnosis."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ENGINE_PATH = HERE.parent/'completion_placement_check_v1/pipeline.py'
spec = importlib.util.spec_from_file_location('selective_existing_engine',ENGINE_PATH)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
h, res, prior = engine.h, engine.res, engine.prior
read, write = engine.read, engine.write
ARMS = ['control','grasp_timeout','grasp_ready','release_hold','release_feedback','guarded_bc','guarded_hold','guarded_feedback']
RELEASE_ARMS = [a for a in ARMS if not a.startswith('grasp_')]
TRACE_COLUMNS = ['frame','placement','phase','retreat','raw_phase_steps','used_phase_steps','bc_probability',
    'grasp_ready','grasp_ready_streak','forced_done','guard_blocked','release_mode','release_age',
    'phase_after_decision','sequencer_event','valid_tail','pre_xy_m','pre_height_m','pre_pair_contact',
    'pre_linear_m_s','pre_angular_rad_s','pre_lower_valid','pre_placement_ready','placement_ready_streak',
    'post_xy_m','post_height_m','post_pair_contact','post_held','finger_cube_0','finger_cube_1','finger_cube_2',
    'valid_two','valid_three']
TRACE_COLUMNS += [f'eef_{a}' for a in 'xyz'] + [f'cube_{i}_{a}' for i in range(3) for a in 'xyz']
TRACE_COLUMNS += [f'cube_velocity_{i}' for i in range(18)] + [f'action_{i}' for i in range(7)]
TRACE_COLUMNS += [f'bc_action_{i}' for i in range(7)] + [f'feature_{i}' for i in range(10)]


def grasp_decision(arm, steps, bc_done, streak, cfg):
    if bc_done or steps < cfg['late_after_steps']:
        return False
    return arm=='grasp_timeout' or (arm=='grasp_ready' and streak>=cfg['consecutive_ready_frames'])


def release_profile(arm):
    if arm not in ARMS:
        raise ValueError('Unknown arm')
    guarded = arm.startswith('guarded_')
    if arm.endswith('_hold'):
        return guarded,'hold'
    if arm.endswith('_feedback'):
        return guarded,'feedback'
    return guarded,'bc'


class ReleaseController:
    """Matched gain, height, gripper and duration; different XY reference."""
    def __init__(self, mode, eef, cfg):
        self.mode, self.goal, self.cfg = mode,eef.copy(),cfg
        self.age, self.locked = 0,False

    def action(self, eef, source, target, np):
        cfg = self.cfg
        if self.mode=='feedback' and self.age>=cfg['feedback_frames'] and not self.locked:
            self.goal[:2] = eef[:2]
            self.locked = True
        error = self.goal-eef
        if self.mode=='feedback' and self.age<cfg['feedback_frames']:
            error[:2] = target[:2]-source[:2]
        action = np.zeros(7)
        action[:3] = np.clip(cfg['gain']*error/cfg['action_scale_m'],-1,1)
        action[6] = cfg['gripper']
        self.age += 1
        return action


def cases_for(plan, smoke=False):
    source = read(ROOT/plan['source_run']/'plan.json')
    cases = []
    if not smoke:
        for i,block in enumerate(source['blocks']):
            for seed in range(plan['calibration_seeds'][0],plan['calibration_seeds'][1]+1):
                cases.append(dict(id=f'cal_{seed}_s{i+1}',seed=seed,block=block['id'],model=block['heldout_model'],
                    panel='calibration',stratum='unselected',arms=plan['arms']))
    for group in read(ROOT/plan['previous_run']/'groups.json'):
        case, arms = group['case'],group['arms']
        if case['panel']!='calibration':
            continue
        ctrl = arms['control']
        failure = ctrl['final_stage']==2 and ctrl['final_phase']==1
        harmed = ctrl['success'] and not arms['grasp_completion']['success']
        if not (failure or harmed):
            continue
        if smoke and not (failure and case['seed']==2026193009):
            continue
        cases.append(dict(id='grasp_'+case['id'],seed=case['seed'],block=case['block'],model=case['model'],
            panel='known',stratum='grasp_failure' if failure else 'grasp_success_control',arms=plan['grasp_arms'],
            archived={name:ctrl[name] for name in res.ARCHIVE_FIELDS}))
    old = res.select_cases(read(HERE.parent/'residual_phase_diagnosis_v1/config.json'))
    for case in old:
        if case['placement']!=2 or case['phase']!=6:
            continue
        if smoke and case['model']!='mixed_s3_u30000':
            continue
        cases.append(dict(id='release_'+case['id'],seed=case['seed'],block=case['block'],model=case['model'],
            panel='known',stratum='release_failure' if case['role']=='failure' else 'release_success_control',
            arms=plan['release_arms'],archived=case['archived']))
    return cases


def episode(env, model, case, arm, plan, out, deadline):
    base, torch, np = h.libraries()
    controller = base.backend()
    obs, initial, z = h.reset(env,case['seed'])
    initial_hash = hashlib.sha256(initial.tobytes()).hexdigest()
    pos0 = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    initial_features = {f'initial_center_distance_{i}{j}_xy_m':float(np.linalg.norm(pos0[i,:2]-pos0[j,:2])) for i,j in ((0,1),(0,2),(1,2))}
    initial_features.update({f'initial_eef_to_source_{i}_m':float(np.linalg.norm(obs['robot0_eef_pos']-pos0[i])) for i in (1,2)})
    seq = controller.GuardedSequencer(model,3,controller.Clearance(env))
    seq.policy = h.validation.adapter.make_policy(base,controller.native.historical,model,.8,lambda:seq.stage,17)
    digest = hashlib.sha256(initial.tobytes())
    entries, events, trace, control_prefixes = {},[],[],{}
    lift, tail, first_seen, adapted = None,0,False,0
    grasp_streak, placement_streak = 0,0
    first_intervention, release_controller = None,None
    action_frames, completion_frames, blocked_frames = 0,0,0
    guarded, motion = release_profile(arm)
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline)
        stage, phase, retreat = seq.stage,seq.policy.phase,seq.retreat
        target = stage==plan['target_placement'] and not retreat
        model.active = stage==2 and phase==0 and not retreat
        adapted += int(model.active)
        pos = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        steps = seq.policy.steps
        anchor = (pos[stage] if phase<4 else pos[stage-1]).copy() if seq.policy.anchor is None else seq.policy.anchor.copy()
        key = f'{stage}/{phase}'
        if not retreat and phase in (1,5,6) and key not in entries:
            entries[key] = dict(frame=frame,history_sha256=digest.hexdigest(),
                state_sha256=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest())
        if stage==2 and phase==3 and not retreat and lift is None:
            lift = dict(frame=frame,held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[2].contact_geoms)))
        features = engine.placement_features(env,stage,controller,np) if phase in (5,6) and not retreat else [-1]*6
        placement_ready = engine.readiness(features,plan['placement_readiness']) if phase in (5,6) and not retreat else False
        placement_streak = placement_streak+1 if target and phase==5 and placement_ready else 0
        with torch.no_grad():
            bc_action, _, probability = seq.policy.action(obs,pos[stage-1],pos[stage])
        x = seq.policy.last_x.copy()
        ready = bool(phase==1 and steps+1>=5 and np.linalg.norm(.1*x[:3]-np.asarray(plan['grasp']['goal_offset_m']))<plan['grasp']['goal_distance_max_m'])
        grasp_streak = grasp_streak+1 if target and phase==1 and ready else 0
        action, forced, blocked, replaced, release_age = bc_action,False,False,False,-1
        if target and phase==1 and grasp_decision(arm,steps,seq.policy.phase!=phase,grasp_streak,plan['grasp']):
            seq.policy.phase,seq.policy.steps,seq.policy.anchor = 2,0,None
            forced = True
        if target and phase==5 and guarded:
            blocked = engine.guard(seq.policy,phase,steps,anchor,probability>=.8,placement_streak,plan['placement_readiness'])
        if target and phase==6 and motion!='bc':
            if release_controller is None:
                release_controller = ReleaseController(motion,np.asarray(obs['robot0_eef_pos']),plan['release'])
            release_age = release_controller.age
            action = release_controller.action(np.asarray(obs['robot0_eef_pos']),pos[stage],pos[stage-1],np)
            replaced = True
        prefix = None
        if (arm=='control' and target and phase in (1,5,6)) or ((forced or blocked or replaced) and first_intervention is None):
            prefix = dict(frame=frame,history_sha256=digest.hexdigest(),
                state_sha256=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest())
        if arm=='control' and prefix is not None:
            control_prefixes[str(frame)] = prefix
        if (forced or blocked or replaced) and first_intervention is None:
            first_intervention = dict(prefix,phase=phase)
        after_phase = seq.policy.phase
        if target and (forced or (phase==5 and after_phase!=phase) or (phase==6 and release_age==0)):
            events.append(dict(frame=frame,phase=phase,raw_steps=steps,bc_probability=probability,
                grasp_ready=ready,grasp_ready_streak=grasp_streak,forced=forced,
                placement_ready=placement_ready,pre_placement_features=features if phase in (5,6) else None))
        action_frames += int(replaced)
        completion_frames += int(forced)
        blocked_frames += int(blocked)
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        digest.update(action.tobytes())
        digest.update(env.sim.get_state().flatten().tobytes())
        m = h.measurement(env,obs,stage,z[stage],pos[stage],controller)
        first_seen |= m['valid'][0]
        event = seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        tail = tail+1 if m['valid'][-1] else 0
        trace.append(np.r_[frame,stage,phase,retreat,steps,seq.policy.used_steps,probability,ready,grasp_streak,
            forced,blocked,{'bc':0,'hold':1,'feedback':2}[motion] if replaced else 0,release_age,
            after_phase,event,tail,*features,placement_ready if phase in (5,6) and not retreat else -1,placement_streak,
            m['xy_error'],m['height_above_target'],m['pair_contact'],m['held'],m['fingers'],m['valid'],
            m['eef'],m['positions'].ravel(),m['velocities'],action,bc_action,x])
        if tail>=plan['success_frames'] or seq.timed_out:
            break
    values = np.asarray(trace)
    if values.shape[1]!=len(TRACE_COLUMNS) or not np.isfinite(values).all():
        raise ValueError('Trace schema/nonfinite values')
    return dict(seed=case['seed'],arm=arm,success=tail>=plan['success_frames'],frames=frame+1,
        initial_sha256=initial_hash,initial_features=initial_features,entries=entries,events=events,
        first_intervention=first_intervention,verification_prefixes=control_prefixes,
        final_stage=seq.stage,final_phase=seq.policy.phase,retreat_timeout=seq.timed_out,second_lift=lift,
        adapted_frames=adapted,first_tower_seen=first_seen,action_override_frames=action_frames,
        completion_override_frames=completion_frames,guard_blocked_frames=blocked_frames,
        trajectory_sha256=digest.hexdigest()),values


def check_group(case, arms):
    ctrl = arms['control']
    for name,value in case.get('archived',{}).items():
        if ctrl[name]!=value:
            raise ValueError('Archived control mismatch: '+case['id']+' '+name)
    for arm,row in arms.items():
        if row['initial_sha256']!=ctrl['initial_sha256']:
            raise ValueError('Initial state mismatch')
        if arm=='control':
            continue
        entry = '2/1' if arm.startswith('grasp_') else '2/5' if arm.startswith('guarded_') else '2/6'
        if row['entries'].get(entry)!=ctrl['entries'].get(entry):
            raise ValueError('Target entry mismatch: '+arm)
        intervention = row['first_intervention']
        if intervention is None:
            if row['trajectory_sha256']!=ctrl['trajectory_sha256']:
                raise ValueError('Unexposed trajectory differs')
        else:
            prefix = {k:intervention[k] for k in ('frame','history_sha256','state_sha256')}
            if prefix!=ctrl['verification_prefixes'].get(str(intervention['frame'])):
                raise ValueError('Actual intervention prefix mismatch: '+arm)
    for candidates in (('control','release_hold','release_feedback'),('guarded_bc','guarded_hold','guarded_feedback')):
        available = [a for a in candidates if a in arms]
        if available and any(arms[a]['entries'].get('2/6')!=arms[available[0]]['entries'].get('2/6') for a in available):
            raise ValueError('Different release entry within veto condition')


def validate(plan):
    if plan['optimizer_updates']!=0 or plan['automatic_restart'] or plan['success_frames']!=50 or plan['episode_horizon']!=1000:
        raise ValueError('Require frozen policies and original endpoint')
    if plan['arms']!=ARMS or plan['release_arms']!=RELEASE_ARMS or plan['grasp_arms']!=ARMS[:3]:
        raise ValueError('Changed arm contract')
    if plan['calibration_seeds']!=[2026195000,2026195011] or plan['target_placement']!=2 or plan['maximum_seconds']!=2700:
        raise ValueError('Changed fixed panel/scope/budget')


def audit_seeds(plan):
    base, _, _ = h.libraries()
    new = set(range(plan['calibration_seeds'][0],plan['calibration_seeds'][1]+1))
    checked, conflicts = {},[]
    def walk(value, name, path):
        if isinstance(value,dict):
            for key,item in value.items():
                walk(item,key,path)
        elif isinstance(value,list):
            if 'seed' in name.lower() and value and all(type(x) is int for x in value):
                overlap = new.intersection(value)
                if len(value)==2:
                    overlap |= {x for x in new if value[0]<=x<=value[1]}
                if overlap:
                    conflicts.append(dict(path=path,key=name,seeds=sorted(overlap)))
            else:
                for item in value:
                    walk(item,name,path)
        elif type(value) is int and value in new:
            conflicts.append(dict(path=path,key=name,seeds=[value]))
    for directory in (ROOT/'experiments',ROOT/'praxis/results/curriculum'):
        for filename in ('plan.json','config.json'):
            for path in sorted(directory.rglob(filename)):
                if path.is_relative_to(HERE) or path.is_relative_to(ROOT/'praxis/results/curriculum'/HERE.name):
                    continue
                relative = str(path.relative_to(ROOT))
                walk(read(path),'',relative)
                checked[relative] = base.sha(path)
    if conflicts:
        raise ValueError('Seed collision: '+json.dumps(conflicts))
    return dict(checked_plan_hashes=checked,conflicts=conflicts,scope='Recorded experiment/curriculum plans; unlogged historical starts not ruled out')


def dependency_files():
    """Include dynamically imported workspace helpers as well as normal imports."""
    files,seen,pending = {ENGINE_PATH},set(),[engine,res,prior,h]
    while pending:
        module = pending.pop()
        if id(module) in seen:
            continue
        seen.add(id(module))
        filename = getattr(module,'__file__',None)
        if not filename or not str(filename).endswith('.py'):
            continue
        path = Path(filename).resolve()
        if not path.is_relative_to(ROOT) or ROOT/'praxis/.venv' in path.parents:
            continue
        files.add(path)
        pending.extend(value for value in vars(module).values() if isinstance(value,ModuleType))
    return files


def prepare(out, smoke=False):
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Require new workspace output')
    plan = read(HERE/'config.json')
    validate(plan)
    audit = audit_seeds(plan)
    cases = cases_for(plan,smoke)
    plan.update(technical_only=smoke,cases=cases,episodes=sum(len(c['arms']) for c in cases))
    if len(cases)!=(5 if smoke else 52) or plan['episodes']!=(21 if smoke else 354):
        raise ValueError('Unexpected fixed denominator')
    if smoke:
        plan['maximum_seconds']=600
    base, torch, np = h.libraries()
    base.backend()
    source = ROOT/plan['source_run']
    prior.verify(source)
    prior.verify_frozen(source)
    previous = ROOT/plan['previous_run']
    res.verify(previous)
    if any(read(p/'status.json')['state']!='COMPLETE' for p in (source,previous)):
        raise ValueError('Require completed sources')
    with (source/'rollouts.jsonl').open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    rows += [g['arms']['control'] for g in read(previous/'groups.json')]
    archived = dict(seeds=sorted({r['seed'] for r in rows}),initial_hashes=sorted({r['initial_sha256'] for r in rows}))
    if any(c['seed'] in archived['seeds'] for c in cases if c['panel']=='calibration'):
        raise ValueError('Calibration scene already opened')
    out.mkdir(parents=True)
    (out/'traces').mkdir()
    write(out/'plan.json',plan)
    write(out/'trace_schema.json',TRACE_COLUMNS)
    write(out/'seed_audit.json',audit)
    write(out/'archived_initial_states.json',archived)
    files = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)
        and str(m.__file__).endswith('.py') and Path(m.__file__).is_file()
        and Path(m.__file__).resolve().is_relative_to(ROOT) and ROOT/'praxis/.venv' not in Path(m.__file__).resolve().parents}
    files.update(HERE.glob('*.py'))
    files.update(dependency_files())
    files.update([ENGINE_PATH,HERE/'README.md',HERE/'config.json',out/'plan.json',out/'seed_audit.json',out/'archived_initial_states.json',
        source/'composition.json',source/'rollouts.jsonl',source/'frozen_components.json',source/'plan.json',
        previous/'groups.json',previous/'plan.json',previous/'integrity.json'])
    composition = read(source/'composition.json')
    registry = read(HERE.parent/'models.json')['models']
    for case in cases:
        item = composition[case['block']+'/'+case['model']+'/'+plan['source_policy']]
        files.update(ROOT/item[name] for name in ('actor','completion'))
        files.add(ROOT/registry[case['model']]['checkpoint'])
    write(out/'provenance.json',{str(path.relative_to(ROOT)):base.sha(path) for path in sorted(files)})
    for path in files:
        if path.suffix in ('.py','.md','.json'):
            target = out/'sources'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(path.read_bytes())
    write(out/'environment.json',dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0)))
    write(out/'status.json',dict(state='READY',episodes=plan['episodes'],technical_only=smoke,optimizer_updates=0,updated_unix=time.time()))
    print(json.dumps(dict(state='READY',cases=len(cases),episodes=plan['episodes'],technical_only=smoke)))


# Reuse the proven bounded supervisor and frozen-model worker in an isolated
# imported module. No historical source file is edited; original engine hash
# is explicitly included in provenance even though its launch path is adapted.
engine.HERE, engine.__file__ = HERE,__file__
engine.episode, engine.check_group, engine.TRACE_COLUMNS = episode,check_group,TRACE_COLUMNS


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run','worker','verify'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--deadline',type=float)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        parser.error('Output must stay in workspace')
    if args.command=='prepare':
        prepare(out,args.smoke)
    elif args.command=='run':
        engine.run(out)
    elif args.command=='worker':
        engine.worker(out,args.deadline)
    else:
        res.verify(out)
        print('Diagnostic inputs verified')
