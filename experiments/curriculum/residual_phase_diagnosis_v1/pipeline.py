"""Bounded, frozen-policy causal probes of already observed residual failures."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('residual_existing_v2', HERE.parent/'targeted_correction_budget_v2/pipeline.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
h, bc = prior.h, prior.bc
read, write = prior.read, prior.write

ARCHIVE_FIELDS = ('success', 'frames', 'initial_sha256', 'final_stage', 'final_phase', 'retreat_timeout',
                  'second_lift', 'adapted_frames', 'first_tower_seen')
TRACE_COLUMNS = ['frame','placement','phase','retreat','raw_phase_steps','used_phase_steps',
    'bc_completion_probability','teacher_ready','action_override','completion_override','sequencer_event',
    'valid_tail','held_post','lift_m','xy_error_m','height_above_target_m','eef_to_source_m','pair_contact',
    'valid_two','valid_three','finger_cube_0','finger_cube_1','finger_cube_2']
TRACE_COLUMNS += [f'eef_{axis}' for axis in 'xyz']+[f'cube_{i}_{axis}' for i in range(3) for axis in 'xyz']
TRACE_COLUMNS += [f'action_{i}' for i in range(7)]+[f'bc_action_{i}' for i in range(7)]
TRACE_COLUMNS += [f'cube_velocity_{i}' for i in range(18)]+['eef_to_oracle_goal_m']


def targets(stage, phase, retreat, case):
    return stage == case['placement'] and phase == case['phase'] and not retreat


def select_cases(plan):
    source = ROOT/plan['source_run']
    source_plan = read(source/'plan.json')
    held = {b['id']:b['heldout_model'] for b in source_plan['blocks']}
    with (source/'rollouts.jsonl').open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    rows = [r for r in rows if r['panel'] == 'confirmation' and r['policy'] == plan['source_policy'] and r['model'] == held[r['block']]]
    groups = {}
    for row in rows:
        if not row['success']:
            if row['final_phase'] not in plan['phases']:
                raise ValueError('Unregistered failure phase')
            key = row['block'], row['model'], row['final_stage'], row['final_phase']
            groups.setdefault(key, []).append(row)
    selected = {key:min(values, key=lambda r:r['seed']) for key,values in groups.items()}
    failure_seeds = {row['seed'] for row in selected.values()}
    used_controls, cases = set(), []
    for number, (key, failure) in enumerate(sorted(selected.items())):
        block, model, placement, phase = key
        candidates = [r for r in rows if r['block'] == block and r['model'] == model and r['success']
                      and r['seed'] not in failure_seeds | used_controls]
        control = min(candidates, key=lambda r:r['seed'])
        used_controls.add(control['seed'])
        for role, row in (('failure',failure), ('success_control',control)):
            cases.append(dict(id=f'g{number:02}_{role}', block=block, model=model, placement=placement, phase=phase,
                role=role, seed=row['seed'], archived={name:row[name] for name in ARCHIVE_FIELDS},
                stratum_total_failures=len(groups[key])))
    return cases


def validate(plan):
    if plan['optimizer_updates'] != 0 or plan['automatic_restart'] or plan['success_frames'] != 50:
        raise ValueError('Require frozen diagnosis and unchanged endpoint')
    if not 30 < plan['maximum_seconds'] <= 1800 or plan['episode_horizon'] != 1000:
        raise ValueError('Invalid fixed cap')
    for phase, arms in plan['arms_by_phase'].items():
        expected = ['control','action'] if phase == '6' else ['control','action','completion','both']
        if phase not in ('1','4','6') or arms != expected:
            raise ValueError('Unsupported completion intervention, especially phase 6')


class FixedPhaseExpert:
    """Keep the expert in one phase after readiness, without changing its goal."""
    def __init__(self, expert_class, env, placement, phase):
        self.expert = expert_class(SimpleNamespace(base_env=env))
        self.expert.cube_index, self.expert.phase = placement, phase
        self.phase, self.steps, self.goal = phase, 0, None

    def action(self, obs):
        action = self.expert(obs)
        ready = self.expert.phase != self.phase
        if self.goal is None:
            if ready or self.expert.target is None:
                raise ValueError('Expert transitioned before its minimum initial dwell')
            self.goal = self.expert.target.copy()
        self.steps += 1
        self.expert.phase, self.expert.phase_steps = self.phase, self.steps
        self.expert.target = self.goal.copy()
        return action, ready


def apply_intervention(policy, phase, raw_steps, anchor, bc_action, expert_action, expert_ready, arm):
    if arm not in ('control','action','completion','both') or (phase == 6 and arm in ('completion','both')):
        raise ValueError('Invalid intervention')
    if arm in ('completion','both'):
        if expert_ready:
            policy.phase, policy.steps, policy.anchor = phase+1, 0, None
        else:
            policy.phase, policy.steps, policy.anchor = phase, raw_steps+1, anchor.copy()
    return expert_action if arm in ('action','both') else bc_action


def episode(env, model, case, arm, plan, out, deadline):
    base, torch, np = h.libraries()
    controller = base.backend()
    from task_extensions.stack_expert import StackExpert
    obs, initial, z = h.reset(env, case['seed'])
    seq = controller.GuardedSequencer(model, 3, controller.Clearance(env))
    seq.policy = h.validation.adapter.make_policy(base, controller.native.historical, model, .8, lambda:seq.stage, 17)
    digest = hashlib.sha256(initial.tobytes())
    entry, oracle, trace = None, None, []
    lift, tail, first_seen, adapted = None, 0, False, 0
    action_frames, completion_frames, disagreement = 0, 0, 0
    for frame in range(plan['episode_horizon']):
        base.check_stop(out, deadline)
        stage, phase, retreat = seq.stage, seq.policy.phase, seq.retreat
        model.active = stage == 2 and phase == 0 and not retreat
        adapted += int(model.active)
        eligible = targets(stage, phase, retreat, case)
        pos = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        raw_steps = seq.policy.steps
        anchor = (pos[stage] if phase < 4 else pos[stage-1]).copy() if seq.policy.anchor is None else seq.policy.anchor.copy()
        if eligible and entry is None:
            entry = dict(frame=frame, history_sha256=digest.hexdigest(), state_sha256=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest())
            oracle = FixedPhaseExpert(StackExpert, env, stage, phase)
        if stage == 2 and phase == 3 and not retreat and lift is None:
            lift = dict(frame=frame, held=bool(env._check_grasp(env.robots[0].gripper, env.cubes[2].contact_geoms)))
        with torch.no_grad():
            bc_action, _, probability = seq.policy.action(obs, pos[stage-1], pos[stage])
        action = bc_action
        teacher_ready = -1
        override_action = eligible and arm in ('action','both')
        override_completion = eligible and arm in ('completion','both')
        if eligible:
            expert_action, teacher_ready = oracle.action(obs)
            disagreement += int(phase < 6 and (probability >= .8) != teacher_ready)
            action = apply_intervention(seq.policy, phase, raw_steps, anchor, bc_action, expert_action, teacher_ready, arm)
        action_frames += int(override_action)
        completion_frames += int(override_completion)
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        digest.update(action.tobytes())
        digest.update(env.sim.get_state().flatten().tobytes())
        measurement = h.measurement(env, obs, stage, z[stage], pos[stage], controller)
        first_seen |= measurement['valid'][0]
        event = seq.advance(measurement['valid'][stage-1], env.sim.data.body_xpos[env.cube_ids[stage]])
        tail = tail+1 if measurement['valid'][-1] else 0
        trace.append(np.r_[frame,stage,phase,retreat,raw_steps,seq.policy.used_steps,probability,teacher_ready,
            override_action,override_completion,event,tail,measurement['held'],measurement['lift'],measurement['xy_error'],
            measurement['height_above_target'],np.linalg.norm(measurement['eef']-measurement['positions'][stage]),measurement['pair_contact'],
            measurement['valid'],measurement['fingers'],measurement['eef'],measurement['positions'].ravel(),action,bc_action,
            measurement['velocities'],np.linalg.norm(measurement['eef']-oracle.goal) if eligible else -1])
        if tail >= plan['success_frames'] or seq.timed_out:
            break
    values = np.asarray(trace)
    if values.shape[1] != len(TRACE_COLUMNS):
        raise ValueError('Trace schema mismatch')
    return dict(seed=case['seed'], arm=arm, success=tail >= plan['success_frames'], frames=frame+1,
        initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(), final_stage=seq.stage, final_phase=seq.policy.phase,
        retreat_timeout=seq.timed_out, second_lift=lift, adapted_frames=adapted, first_tower_seen=first_seen,
        entry=entry, action_override_frames=action_frames, completion_override_frames=completion_frames,
        completion_disagreement_frames=disagreement, trajectory_sha256=digest.hexdigest()), values


def check_group(case, arms):
    control = arms['control']
    for name in ARCHIVE_FIELDS:
        if control[name] != case['archived'][name]:
            raise ValueError('Archived control regression: '+case['id']+' '+name)
    for arm, row in arms.items():
        if row['initial_sha256'] != control['initial_sha256'] or row['entry'] != control['entry']:
            raise ValueError('Pre-intervention history/state mismatch: '+arm)
        if control['entry'] is None and any(row[name] != control[name] for name in ARCHIVE_FIELDS):
            raise ValueError('Unexposed arm differs')


def verify(out):
    base, _, _ = h.libraries()
    for name, digest in read(out/'provenance.json').items():
        if base.sha(ROOT/name) != digest:
            raise ValueError('Frozen diagnostic input changed: '+name)


def prepare(out, smoke=False):
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Require new workspace output')
    plan = read(HERE/'config.json')
    validate(plan)
    cases = select_cases(plan)
    if len(cases) != 34:
        raise ValueError('Expected 17 existing failure strata and 17 successful controls')
    if smoke:
        cases = [c for c in cases if [c['model'],c['placement'],c['phase']] in plan['smoke_strata']]
        plan['maximum_seconds'] = 600
    plan.update(technical_only=smoke, cases=cases, episodes=sum(len(plan['arms_by_phase'][str(c['phase'])]) for c in cases))
    base, torch, np = h.libraries()
    base.backend()
    source = ROOT/plan['source_run']
    prior.verify(source)
    prior.verify_frozen(source)
    if read(source/'status.json')['state'] != 'COMPLETE':
        raise ValueError('Require completed source study')
    out.mkdir(parents=True)
    (out/'traces').mkdir()
    write(out/'plan.json', plan)
    write(out/'trace_schema.json', TRACE_COLUMNS)
    files = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT) and ROOT/'praxis/.venv' not in Path(m.__file__).resolve().parents}
    files.update(HERE.glob('*.py'))
    files.update([HERE/'README.md',HERE/'config.json',out/'plan.json',source/'composition.json',source/'rollouts.jsonl',source/'frozen_components.json',source/'plan.json'])
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
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    write(out/'environment.json', dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0)))
    write(out/'status.json',dict(state='READY',technical_only=smoke,episodes=plan['episodes'],optimizer_updates=0,updated_unix=time.time()))
    print(json.dumps(dict(state='READY',technical_only=smoke,cases=len(cases),episodes=plan['episodes'])))


def load_model(case, plan):
    source = ROOT/plan['source_run']
    composition = read(source/'composition.json')[case['block']+'/'+case['model']+'/'+plan['source_policy']]
    reference = h.registry.restore(case['model'],'cuda')[0]
    actor = bc.restore_branch(ROOT/composition['actor'])[0]
    completion = bc.restore_branch(ROOT/composition['completion'])[0]
    return bc.compose(reference,actor,completion).eval().requires_grad_(False)


def summary(groups):
    rows = []
    for group in groups:
        case, arms = group['case'], group['arms']
        rows.append(dict(case=case['id'],model=case['model'],seed=case['seed'],placement=case['placement'],phase=case['phase'],role=case['role'],
            exposed=arms['control']['entry'] is not None, outcomes={arm:dict(success=row['success'],frames=row['frames'],
                gain=bool(row['success'] and not arms['control']['success']),loss=bool(not row['success'] and arms['control']['success']),
                action_frames=row['action_override_frames'],completion_frames=row['completion_override_frames']) for arm,row in arms.items()}))
    return dict(optimizer_updates=0,completed_groups=len(groups),rows=rows,
        scope='Selected already-opened diagnostic cases; not a new success-rate estimate or independent training replication')


def report(out, groups, plan):
    lines = ['# Restfehlerdiagnose mit eingefrorenen Modellen','',f"Technical only: {plan['technical_only']}; optimizer updates: 0.",'',
        '| Parent | Szene | Fall | Platzierung/Phase | Control | Action | Completion | Both |',
        '|---|---:|---|---|---:|---:|---:|---:|']
    for group in groups:
        case, arms = group['case'], group['arms']
        outcomes = [str(int(arms[a]['success'])) if a in arms else 'n/a' for a in ('control','action','completion','both')]
        lines.append('| '+case['model']+' | '+str(case['seed'])+' | '+case['role']+' | '+str(case['placement'])+'/'+str(case['phase'])+' | '+' | '.join(outcomes)+' |')
    lines += ['', 'Erfolg = vollständiger Dreierturm über unveränderte 50 strenge Frames. Auswahl bekannte Fehler und Erfolgskontrollen; keine neue allgemeine Erfolgsquote. Phase 6 besitzt keinen verwendeten gelernten Abschluss; Completion/Both sind dort nicht anwendbar. Ein Eingriff kann über veränderte Folgezustände wirken.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def worker(out, deadline):
    base, torch, np = h.libraries()
    base.configure(1)
    plan = read(out/'plan.json')
    verify(out)
    source = ROOT/plan['source_run']
    prior.verify(source)
    prior.verify_frozen(source)
    models, digests, groups = {}, {}, []
    started = time.time()
    try:
        for case in plan['cases']:
            key = case['block'],case['model']
            if key not in models:
                models[key] = load_model(case,plan)
                digests[key] = h.registry.tensor_digest(models[key].state_dict())
            model = models[key]
            group = dict(case=case,arms={})
            env = base.backend().native.historical.make_env(3)
            try:
                for arm in plan['arms_by_phase'][str(case['phase'])]:
                    base.check_stop(out,deadline)
                    write(out/'status.json',dict(state='DIAGNOSING',pid=os.getpid(),case=case['id'],model=case['model'],phase=case['phase'],arm=arm,
                        completed_groups=len(groups),total_groups=len(plan['cases']),optimizer_updates=0,updated_unix=time.time()))
                    row, trace = episode(env,model,case,arm,plan,out,deadline)
                    group['arms'][arm] = row
                    np.savez_compressed(out/'traces'/f"{case['id']}_{arm}.npz",trace=trace)
                    write(out/'current_group.json',group)
            finally:
                env.close()
            check_group(case,group['arms'])
            if h.registry.tensor_digest(model.state_dict()) != digests[key] or any(parameter.requires_grad for parameter in model.parameters()):
                raise ValueError('Frozen model changed')
            groups.append(group)
            write(out/'groups.json',groups)
            write(out/'summary.json',summary(groups))
        verify(out)
        prior.verify(source)
        prior.verify_frozen(source)
        report(out,groups,plan)
        write(out/'integrity.json',dict(inputs_verified=True,source_night_unchanged=True,parameters_unchanged=True,optimizer_updates=0,
            archived_controls_reproduced=True,preintervention_histories_equal=True))
        write(out/'status.json',dict(state='COMPLETE',technical_only=plan['technical_only'],completed_groups=len(groups),episodes=plan['episodes'],
            optimizer_updates=0,elapsed_seconds=time.time()-started,updated_unix=time.time()))
    except BaseException as exc:
        write(out/'status.json',dict(state='PARTIAL_TIME_CAP' if isinstance(exc,TimeoutError) else ('STOPPED' if isinstance(exc,InterruptedError) else 'FAILED'),
            error=repr(exc),traceback=traceback.format_exc(),completed_groups=len(groups),optimizer_updates=0,updated_unix=time.time()))
        raise


def run(out):
    if read(out/'status.json')['state'] != 'READY':
        raise ValueError('Require READY; no automatic restart')
    verify(out)
    plan = read(out/'plan.json')
    start = time.time()
    deadline = start+plan['maximum_seconds']-plan['exit_reserve_seconds']
    with (out/'launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(),started_unix=start,deadline=deadline),stream)
    watchdog = h.module('residual_existing_watchdog',HERE.parent/'grasp_phase_ablation_v1/pipeline.py')
    proc, awake = None, False
    state = dict(state='STARTING',pid=os.getpid(),started_unix=start,deadline=deadline)
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('x',encoding='utf-8') as stream:
            proc = subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker','--output',str(out),'--deadline',str(deadline)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
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
    if state['state'] != 'COMPLETE':
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run','worker','verify'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--deadline',type=float)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        parser.error('Output must stay in workspace')
    if args.command == 'prepare':
        prepare(out,args.smoke)
    elif args.command == 'run':
        run(out)
    elif args.command == 'worker':
        worker(out,args.deadline)
    else:
        verify(out)
        print('Diagnostic inputs verified')
