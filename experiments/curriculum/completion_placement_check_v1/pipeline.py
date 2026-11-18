"""Bounded frozen-policy completion and pre-release placement calibration."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('placement_existing_residual', HERE.parent/'residual_phase_diagnosis_v1/pipeline.py')
res = importlib.util.module_from_spec(spec)
spec.loader.exec_module(res)
h, prior = res.h, res.prior
read, write = res.read, res.write
ARMS = ['control','grasp_completion','place_action','place_completion','place_both','place_guard']
EXTRA_COLUMNS = ['phase_after_decision','pre_place_xy_m','pre_place_height_m','pre_place_contact',
    'pre_place_linear_m_s','pre_place_angular_rad_s','pre_lower_valid','pre_place_ready',
    'ready_streak','guard_blocked','actual_done','oracle_distance_pre_m']
TRACE_COLUMNS = res.TRACE_COLUMNS + EXTRA_COLUMNS


def profile(arm, phase):
    if arm not in ARMS:
        raise ValueError('Unknown arm')
    if phase == 1 and arm == 'grasp_completion':
        return 'completion'
    if phase == 5 and arm.startswith('place_'):
        return arm.removeprefix('place_')
    return 'control'


def readiness(features, cfg):
    xy, height, contact, speed, angular, lower_valid = features
    return bool(xy <= cfg['xy_max_m'] and abs(height-cfg['height_m']) <= cfg['height_tolerance_m']
        and (contact or not cfg['require_pair_contact']) and speed <= cfg['source_linear_max_m_s']
        and angular <= cfg['source_angular_max_rad_s']
        and (lower_valid or not cfg['require_lower_prefix_valid']))


def guard(policy, phase, steps, anchor, learned_done, ready_streak, cfg):
    allow = learned_done and ready_streak >= cfg['consecutive_frames'] and steps+1 >= cfg['minimum_phase_frames']
    if learned_done and not allow:
        policy.phase, policy.steps, policy.anchor = phase, steps+1, anchor.copy()
        return True
    return False


def cases_for(plan, smoke=False):
    source = read(ROOT/plan['source_run']/'plan.json')
    seeds = [plan['technical_seed']] if smoke else range(plan['calibration_seeds'][0],plan['calibration_seeds'][1]+1)
    cases = [dict(id=f"{'technical' if smoke else 'cal'}_{seed}_s{i+1}",block=b['id'],model=b['heldout_model'],
        seed=seed,panel='technical' if smoke else 'calibration',intervention_placement=None,
        arms=plan['arms']) for i,b in enumerate(source['blocks']) for seed in seeds]
    old = res.select_cases(read(HERE.parent/'residual_phase_diagnosis_v1/config.json'))
    known = [c for c in old if c['role']=='failure' and c['phase']==6]
    if smoke:
        known = [c for c in known if c['model']=='mixed_s3_u30000' and c['placement']==2]
    cases += [dict(id='known_'+c['id'],block=c['block'],model=c['model'],seed=c['seed'],panel='known',
        intervention_placement=c['placement'],arms=plan['known_case_arms'],archived=c['archived']) for c in known]
    return cases


def audit_seeds(plan):
    """Conservative seed/range check of existing recorded curriculum plans."""
    base, _, _ = h.libraries()
    new = set(range(plan['calibration_seeds'][0],plan['calibration_seeds'][1]+1)) | {plan['technical_seed']}
    paths = []
    for directory in (ROOT/'experiments',ROOT/'praxis/results/curriculum'):
        for name in ('config.json','plan.json'):
            paths.extend(directory.rglob(name))
    checked, conflicts = {}, []
    def walk(value, name, path):
        if isinstance(value,dict):
            for key,item in value.items():
                walk(item,key,path)
        elif isinstance(value,list):
            if 'seed' in name.lower() and value and all(type(x) is int for x in value):
                overlap = new.intersection(value)
                if len(value)==2:
                    overlap |= {x for x in new if value[0] <= x <= value[1]}
                if overlap:
                    conflicts.append(dict(path=path,key=name,overlap=sorted(overlap)))
            else:
                for item in value:
                    walk(item,name,path)
        elif type(value) is int and value in new:
            conflicts.append(dict(path=path,key=name,overlap=[value]))
    for path in sorted(set(paths)):
        if path.is_relative_to(HERE) or path.is_relative_to(ROOT/'praxis/results/curriculum/completion_placement_check_v1'):
            continue
        relative = str(path.relative_to(ROOT))
        walk(read(path),'',relative)
        checked[relative] = base.sha(path)
    if conflicts:
        raise ValueError('New calibration seed collision: '+json.dumps(conflicts))
    return dict(checked_plan_hashes=checked,conflicts=conflicts,
        scope='Recorded experiment/curriculum configs and plans; unlogged historical starts cannot be ruled out')


def placement_features(env, stage, controller, np):
    pos = env.sim.data.body_xpos
    source, target = pos[env.cube_ids[stage]],pos[env.cube_ids[stage-1]]
    velocity = env.sim.data.get_joint_qvel(env.cubes[stage].joints[0])
    return [float(np.linalg.norm(source[:2]-target[:2])),float(source[2]-target[2]),
        bool(env.check_contact(env.cubes[stage-1],env.cubes[stage])),
        float(np.linalg.norm(velocity[:3])),float(np.linalg.norm(velocity[3:])),
        bool(controller.native.historical.old.prefix_valid(env,stage))]


def episode(env, model, case, arm, plan, out, deadline):
    base, torch, np = h.libraries()
    controller = base.backend()
    from task_extensions.stack_expert import StackExpert
    obs, initial, z = h.reset(env,case['seed'])
    initial_hash = hashlib.sha256(initial.tobytes()).hexdigest()
    pos0 = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    initial_features = dict(eef_to_source_1_m=float(np.linalg.norm(obs['robot0_eef_pos']-pos0[1])),
        eef_to_source_2_m=float(np.linalg.norm(obs['robot0_eef_pos']-pos0[2])),
        transport_1_xy_m=float(np.linalg.norm(pos0[1,:2]-pos0[0,:2])),
        transport_2_xy_m=float(np.linalg.norm(pos0[2,:2]-pos0[1,:2])),
        minimum_cube_center_distance_xy_m=min(float(np.linalg.norm(pos0[i,:2]-pos0[j,:2])) for i,j in ((0,1),(0,2),(1,2))))
    seq = controller.GuardedSequencer(model,3,controller.Clearance(env))
    seq.policy = h.validation.adapter.make_policy(base,controller.native.historical,model,.8,lambda:seq.stage,17)
    digest = hashlib.sha256(initial.tobytes())
    entries, oracles, streaks, events, trace = {}, {}, {}, [], []
    lift, tail, first_seen, adapted = None, 0, False, 0
    action_frames, completion_frames, disagreement, blocked_frames = 0, 0, 0, 0
    for frame in range(plan['episode_horizon']):
        base.check_stop(out,deadline)
        stage, phase, retreat = seq.stage, seq.policy.phase, seq.retreat
        model.active = stage==2 and phase==0 and not retreat
        adapted += int(model.active)
        pos = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        steps = seq.policy.steps
        anchor = (pos[stage] if phase<4 else pos[stage-1]).copy() if seq.policy.anchor is None else seq.policy.anchor.copy()
        observed = phase in (1,5) and not retreat
        key = f'{stage}/{phase}'
        if observed and key not in entries:
            entries[key] = dict(frame=frame,history_sha256=digest.hexdigest(),
                state_sha256=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest())
            oracles[key] = res.FixedPhaseExpert(StackExpert,env,stage,phase)
            streaks[key] = 0
        if stage==2 and phase==3 and not retreat and lift is None:
            lift = dict(frame=frame,held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[2].contact_geoms)))
        features = placement_features(env,stage,controller,np) if phase==5 and not retreat else [-1]*6
        ready = readiness(features,plan['placement_readiness']) if phase==5 and not retreat else False
        if observed:
            streaks[key] = streaks[key]+1 if ready else 0
        with torch.no_grad():
            bc_action, _, probability = seq.policy.action(obs,pos[stage-1],pos[stage])
        action, teacher_ready, oracle_pre_distance = bc_action, -1, -1
        override_action, override_completion, blocked = False, False, False
        intervention_allowed = not retreat and (case['intervention_placement'] is None or stage==case['intervention_placement'])
        mode = profile(arm,phase) if intervention_allowed else 'control'
        if observed:
            expert_action, teacher_ready = oracles[key].action(obs)
            oracle_pre_distance = float(np.linalg.norm(obs['robot0_eef_pos']-oracles[key].goal))
            disagreement += int((probability>=.8) != teacher_ready)
            if mode=='guard':
                blocked = guard(seq.policy,phase,steps,anchor,probability>=.8,streaks[key],plan['placement_readiness'])
            else:
                action = res.apply_intervention(seq.policy,phase,steps,anchor,bc_action,expert_action,teacher_ready,mode)
            override_action = mode in ('action','both')
            override_completion = mode in ('completion','both')
        action_frames += int(override_action)
        completion_frames += int(override_completion)
        blocked_frames += int(blocked)
        after_phase = seq.policy.phase
        done = bool(observed and after_phase!=phase)
        if done:
            events.append(dict(frame=frame,placement=stage,phase=phase,bc_probability=probability,
                teacher_ready=bool(teacher_ready),pre_placement_features=features if phase==5 else None,
                pre_placement_ready=ready if phase==5 else None,readiness_streak=streaks[key]))
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        digest.update(action.tobytes())
        digest.update(env.sim.get_state().flatten().tobytes())
        m = h.measurement(env,obs,stage,z[stage],pos[stage],controller)
        first_seen |= m['valid'][0]
        event = seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        tail = tail+1 if m['valid'][-1] else 0
        if done and phase==5:
            events[-1]['release_entry_features'] = placement_features(env,stage,controller,np)
            events[-1]['release_entry_ready'] = readiness(events[-1]['release_entry_features'],plan['placement_readiness'])
        trace.append(np.r_[frame,stage,phase,retreat,steps,seq.policy.used_steps,probability,teacher_ready,
            override_action,override_completion,event,tail,m['held'],m['lift'],m['xy_error'],m['height_above_target'],
            np.linalg.norm(m['eef']-m['positions'][stage]),m['pair_contact'],m['valid'],m['fingers'],m['eef'],
            m['positions'].ravel(),action,bc_action,m['velocities'],
            np.linalg.norm(m['eef']-oracles[key].goal) if observed else -1,
            after_phase,*features,ready if phase==5 and not retreat else -1,
            streaks.get(key,0),blocked,done,oracle_pre_distance])
        if tail>=plan['success_frames'] or seq.timed_out:
            break
    values = np.asarray(trace)
    if values.shape[1]!=len(TRACE_COLUMNS) or not np.isfinite(values).all():
        raise ValueError('Trace schema/nonfinite values')
    return dict(seed=case['seed'],arm=arm,success=tail>=plan['success_frames'],frames=frame+1,
        initial_sha256=initial_hash,initial_features=initial_features,entries=entries,events=events,
        final_stage=seq.stage,final_phase=seq.policy.phase,retreat_timeout=seq.timed_out,second_lift=lift,
        adapted_frames=adapted,first_tower_seen=first_seen,action_override_frames=action_frames,
        completion_override_frames=completion_frames,guard_blocked_frames=blocked_frames,
        completion_disagreement_frames=disagreement,trajectory_sha256=digest.hexdigest()),values


def first_target(case, arm):
    phase = 1 if arm=='grasp_completion' else 5
    return f"{case['intervention_placement'] or 1}/{phase}"


def check_group(case, arms):
    control = arms['control']
    if 'archived' in case:
        for name in res.ARCHIVE_FIELDS:
            if control[name]!=case['archived'][name]:
                raise ValueError('Archived control mismatch: '+case['id']+' '+name)
    for arm,row in arms.items():
        if row['initial_sha256']!=control['initial_sha256']:
            raise ValueError('Initial state mismatch')
        if arm=='control':
            continue
        key = first_target(case,arm)
        if row['entries'].get(key)!=control['entries'].get(key):
            raise ValueError('Pre-intervention history/state mismatch: '+arm)
        if key not in control['entries'] and row['trajectory_sha256']!=control['trajectory_sha256']:
            raise ValueError('Unexposed arm differs')


def validate(plan):
    if plan['optimizer_updates']!=0 or plan['automatic_restart'] or plan['success_frames']!=50 or plan['episode_horizon']!=1000:
        raise ValueError('Require frozen policies and unchanged endpoint')
    if plan['arms']!=ARMS or plan['known_case_arms']!=[a for a in ARMS if a!='grasp_completion']:
        raise ValueError('Changed arm contract')
    if plan['maximum_seconds']!=2700 or plan['calibration_seeds']!=[2026193000,2026193017]:
        raise ValueError('Changed fixed budget or panel')


def prepare(out, smoke=False):
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Require new workspace output')
    plan = read(HERE/'config.json')
    validate(plan)
    audit = audit_seeds(plan)
    cases = cases_for(plan,smoke)
    plan.update(technical_only=smoke,cases=cases,episodes=sum(len(c['arms']) for c in cases))
    if plan['episodes']!=(23 if smoke else 354):
        raise ValueError('Unexpected planned denominator')
    if smoke:
        plan['maximum_seconds']=600
    base, torch, np = h.libraries()
    base.backend()
    source = ROOT/plan['source_run']
    prior.verify(source)
    prior.verify_frozen(source)
    if read(source/'status.json')['state']!='COMPLETE':
        raise ValueError('Require completed source')
    with (source/'rollouts.jsonl').open(encoding='utf-8') as stream:
        source_rows = [json.loads(line) for line in stream]
    archived = dict(seeds=sorted({r['seed'] for r in source_rows}),initial_hashes=sorted({r['initial_sha256'] for r in source_rows}))
    if any(c['seed'] in archived['seeds'] for c in cases if c['panel']!='known'):
        raise ValueError('Seed already exposed in source night')
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
    files.update([HERE/'README.md',HERE/'config.json',out/'plan.json',out/'seed_audit.json',out/'archived_initial_states.json',
        source/'composition.json',source/'rollouts.jsonl',source/'frozen_components.json',source/'plan.json'])
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
    write(out/'environment.json',dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,
        cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0)))
    write(out/'status.json',dict(state='READY',episodes=plan['episodes'],technical_only=smoke,
        optimizer_updates=0,updated_unix=time.time()))
    print(json.dumps(dict(state='READY',cases=len(cases),episodes=plan['episodes'],technical_only=smoke)))


def worker(out, deadline):
    base, torch, np = h.libraries()
    base.configure(1)
    plan = read(out/'plan.json')
    res.verify(out)
    source = ROOT/plan['source_run']
    prior.verify(source)
    prior.verify_frozen(source)
    models, digests, groups, scene_hashes = {}, {}, [], {}
    archived_hashes = set(read(out/'archived_initial_states.json')['initial_hashes'])
    started = time.time()
    try:
        for case in plan['cases']:
            key = case['block'],case['model']
            if key not in models:
                models[key] = res.load_model(case,plan)
                digests[key] = h.registry.tensor_digest(models[key].state_dict())
            model = models[key]
            group = dict(case=case,arms={})
            env = base.backend().native.historical.make_env(3)
            try:
                for arm in case['arms']:
                    write(out/'status.json',dict(state='DIAGNOSING',pid=os.getpid(),case=case['id'],arm=arm,
                        completed_groups=len(groups),total_groups=len(plan['cases']),optimizer_updates=0,updated_unix=time.time()))
                    row, trace = episode(env,model,case,arm,plan,out,deadline)
                    group['arms'][arm] = row
                    np.savez_compressed(out/'traces'/f"{case['id']}_{arm}.npz",trace=trace)
                    write(out/'current_group.json',group)
            finally:
                env.close()
            check_group(case,group['arms'])
            initial = group['arms']['control']['initial_sha256']
            if case['panel']!='known' and initial in archived_hashes:
                raise ValueError('New calibration state duplicates archived night state')
            if case['seed'] in scene_hashes and scene_hashes[case['seed']]!=initial:
                raise ValueError('Different initial state across parents')
            scene_hashes[case['seed']] = initial
            if h.registry.tensor_digest(model.state_dict())!=digests[key] or any(p.requires_grad for p in model.parameters()):
                raise ValueError('Frozen model changed')
            groups.append(group)
            write(out/'groups.json',groups)
        res.verify(out)
        prior.verify(source)
        prior.verify_frozen(source)
        write(out/'integrity.json',dict(inputs_verified=True,source_night_unchanged=True,parameters_unchanged=True,
            optimizer_updates=0,archived_controls_reproduced=True,preintervention_histories_equal=True,
            unseen_initial_states_distinct_from_source=True,initial_states_paired_across_parents=True,
            unique_scene_families=len(scene_hashes)))
        write(out/'status.json',dict(state='COMPLETE',technical_only=plan['technical_only'],completed_groups=len(groups),
            episodes=plan['episodes'],optimizer_updates=0,elapsed_seconds=time.time()-started,updated_unix=time.time()))
        analyzer = h.module('placement_calibration_analysis',HERE/'analyze.py')
        analyzer.analyze(out)
    except BaseException as exc:
        write(out/'status.json',dict(state='PARTIAL_TIME_CAP' if isinstance(exc,TimeoutError) else
            ('STOPPED' if isinstance(exc,InterruptedError) else 'FAILED'),error=repr(exc),traceback=traceback.format_exc(),
            completed_groups=len(groups),optimizer_updates=0,updated_unix=time.time()))
        raise


def run(out):
    if read(out/'status.json')['state']!='READY':
        raise ValueError('Require READY; no automatic restart')
    res.verify(out)
    plan = read(out/'plan.json')
    start = time.time()
    deadline = start+plan['maximum_seconds']-plan['exit_reserve_seconds']
    with (out/'launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(),started_unix=start,deadline=deadline),stream)
    watchdog = h.module('placement_existing_watchdog',HERE.parent/'grasp_phase_ablation_v1/pipeline.py')
    proc, awake = None, False
    state = dict(state='STARTING',pid=os.getpid(),started_unix=start,deadline=deadline)
    try:
        if os.name=='nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('x',encoding='utf-8') as stream:
            proc = subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker','--output',str(out),
                '--deadline',str(deadline)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            state.update(state='RUNNING',worker_pid=proc.pid,sleep_prevention_active=awake)
            write(out/'supervisor_status.json',state)
            try:
                code = proc.wait(timeout=max(1,deadline+5-time.time()))
            except subprocess.TimeoutExpired:
                watchdog.stop_worker(proc)
                raise TimeoutError('Hard diagnostic cap')
            state.update(state=read(out/'status.json')['state'],worker_returncode=code)
    except BaseException as exc:
        state.update(state='FAILED',error=repr(exc))
        raise
    finally:
        if proc is not None and proc.poll() is None:
            watchdog.stop_worker(proc)
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(),sleep_prevention_active=False)
        write(out/'supervisor_status.json',state)
    print(json.dumps(dict(state=state['state'],output=str(out))))
    if state['state']!='COMPLETE':
        raise SystemExit(1)


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
        run(out)
    elif args.command=='worker':
        worker(out,args.deadline)
    else:
        res.verify(out)
        print('Diagnostic inputs verified')
