"""Prepare and execute a fresh paired validation of a BC input adapter."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE.with_name('axis_bc_completion_10h_20261111')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
spec = importlib.util.spec_from_file_location('clock_validation_monitor', HERE.with_name('axis_bc_extension_20261110')/'night.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
read, write = monitor.read, monitor.write
adapter_spec = importlib.util.spec_from_file_location('bc_release_clock_adapter', HERE/'policy.py')
adapter = importlib.util.module_from_spec(adapter_spec)
adapter_spec.loader.exec_module(adapter)


def libraries():
    # Late import keeps status free of torch/numpy/simulator imports.
    sys.path.insert(0, str(SOURCE))
    import night as study
    base, torch, np = study.runtime.libraries()
    return study, base, torch, np


def validate(plan, cfg, previous):
    if plan['conditions'] != ['original', 'bounded_clock'] or plan['optimizer_updates'] != 0:
        raise ValueError('This version validates fixed BC weights; no optimizer updates')
    if (plan['phase'], plan['placement_stage'], plan['success_frames']) != (6, 2, 50):
        raise ValueError('Intervention scope or success criterion changed')
    if not 0 < plan['shutdown_reserve_seconds'] < plan['wall_clock_cap_seconds'] <= 36000:
        raise ValueError('Shutdown must fit inside the ten-hour maximum')
    ranges = [cfg['development_seeds'], cfg['final_seeds'], previous['confirmation_seeds'],
              plan['confirmation_seeds'], plan['negative_control_seeds']]
    # The source night also inherited the extension's confirmation panel.
    ranges.append([2026115000, 2026115099])
    sets = [set(range(r[0], r[1]+1)) for r in ranges]
    if any(not s for s in sets) or any(a & b for i, a in enumerate(sets) for b in sets[i+1:]):
        raise ValueError('Fresh evaluation namespaces overlap')
    fresh = sets[3] | sets[4]
    if plan['technical_negative_seed'] in fresh or plan['technical_regression_seed'] in fresh:
        raise ValueError('Technical fixtures overlap fresh confirmation')


def prepare(out):
    study, base, torch, np = libraries()
    if out.exists():
        raise FileExistsError('Use a new output directory')
    plan = read(HERE/'config.json')
    source = ROOT/plan['source']
    study.runtime.verify(source)
    if read(source/'status.json')['state'] != 'COMPLETE':
        raise ValueError('Source experiment is not complete')
    cfg = read(source/'base_config.json')
    validate(plan, cfg, read(source/'plan.json'))
    data = base.load_data()
    values = data['train'][0][data['train'][2] == 6, 9]
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Missing or invalid training clock values')
    cap = int(round(float(values.max())*20))
    if abs(cap/20-float(values.max())) > 1e-6 or cap != 17:
        raise ValueError('Training-derived clock cap changed; review a new protocol')
    controls = read(source/'controls.json')
    proof = read(source/'provenance.json')
    inputs = dict(proof['input_hashes'])
    for path in list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+[HERE/'config.json']:
        inputs[str(path.relative_to(ROOT))] = base.sha(path)
    # Validate all sources before creating the output; then freeze every model
    # before reading ANY new scene outcome.
    for name, entry in controls.items():
        path = ROOT/entry['path']
        if base.sha(path) != entry['sha256']:
            raise ValueError('Control checkpoint changed: '+name)
        ck = torch.load(path, map_location='cpu', weights_only=False)
        if ck['update'] != 60000 or ck['technical_only']:
            raise ValueError('Expected an ordinary fixed 60k BC checkpoint')
    out.mkdir(parents=True)
    (out/'frozen').mkdir()
    models = {}
    for name, entry in controls.items():
        path = out/'frozen'/f'{name}.pth'
        shutil.copy2(ROOT/entry['path'], path)
        models[name] = dict(path=str(path.relative_to(ROOT)), sha256=base.sha(path),
                            source=entry['path'], history=name.rsplit('_seed', 1)[0])
        inputs[str(path.relative_to(ROOT))] = base.sha(path)
    for name, value in (('plan.json', plan), ('base_config.json', cfg), ('models.json', models),
                        ('clock_contract.json', dict(phase=6, placement_stage=2, maximum_input_steps=cap,
                         maximum_training_time_feature=float(values.max()), input_scale_steps=20,
                         physical_elapsed_time_unchanged=True, optimizer_updates=0))):
        write(out/name, value)
        inputs[str((out/name).relative_to(ROOT))] = base.sha(out/name)
    write(out/'trace_layout.json', {count: ['frame','placement_stage','phase','completion_probability','raw_phase_steps','input_phase_steps',
        'eef_x','eef_y','eef_z']+[f'{letter}_{axis}' for letter in 'ABC'[:count] for axis in 'xyz']+
        ['action_x','action_y','action_z','rotation_x','rotation_y','rotation_z','gripper']+
        [f'finger_contact_{letter}' for letter in 'ABC'[:count]]+[f'valid_prefix_{k}' for k in range(2, count+1)]+['stable_tail']
        for count in (2, 3)})
    for path in list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+[HERE/'config.json']:
        target = out/'source_snapshot'/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
    write(out/'provenance.json', dict(input_hashes=inputs, library_source_hashes=proof['library_source_hashes'],
          versions=proof['versions'], prepared_unix=time.time()))
    write(out/'status.json', dict(state='READY', completed_round=0, optimizer_updates=0, updated_unix=time.time()))
    print(json.dumps(dict(state='READY', models=len(models), primary_pairs=600, negative_control_pairs=120,
                         clock_cap=cap, optimizer_updates=0, output=str(out))))


def verify(out):
    monitor.verify(out)


def compare_pair(original, bounded, require_identical=False):
    if original['initial_sha256'] != bounded['initial_sha256']:
        raise ValueError('Paired scene initialization differs')
    first = bounded['first_intervention_frame']
    if first is not None:
        if first >= len(original['_prefixes']) or original['_prefixes'][first] != bounded['history_before_intervention']:
            raise ValueError('Paired history differs before the first changed input')
    elif original['trajectory_sha256'] != bounded['trajectory_sha256']:
        raise ValueError('Trajectories differ although no input was changed')
    if require_identical and (first is not None or original['trajectory_sha256'] != bounded['trajectory_sha256']):
        raise ValueError('Negative control changed')
    if require_identical and (original['success'] != bounded['success'] or original['frames'] != bounded['frames']):
        raise ValueError('Negative-control outcome changed')
    return dict(gain=not original['success'] and bounded['success'],
                loss=original['success'] and not bounded['success'], negative_identical=require_identical)


def episode(env, model, cfg, seed, cap, out, deadline):
    _, base, torch, np = libraries()
    controller = base.backend()
    historical = controller.native.historical
    count = len(env.cubes)
    horizon = 500*(count-1)
    import random
    random.seed(seed)
    np.random.seed(seed)
    env.reset()
    env.sim.forward()
    obs = env._get_observations(force_update=True)
    initial = env.sim.get_state().flatten().copy()
    seq = controller.GuardedSequencer(model, count, controller.Clearance(env))
    seq.policy = adapter.make_policy(base, historical, model, cfg['completion_threshold'], lambda: seq.stage, cap)
    digest, prefixes = hashlib.sha256(), []
    tail = longest = interventions = renewed_contact = 0
    first = history = None
    final_release_free_seen = False
    traces = []
    model.eval()
    with torch.no_grad():
        for frame in range(horizon):
            base.check_stop(out, deadline)
            stage, phase = seq.stage, seq.policy.phase
            state = env.sim.get_state().flatten()
            digest.update(state.tobytes())
            prefixes.append(digest.hexdigest())
            positions = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            action, _, probability = seq.policy.action(obs, positions[stage-1], positions[stage])
            if seq.policy.intervened:
                interventions += 1
                if first is None:
                    first, history = frame, prefixes[-1]
            digest.update(action.tobytes())
            env.step(action)
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            fingers = [controller.native.finger_contact(env, c) for c in env.cubes]
            valid = [historical.old.prefix_valid(env, k) and not any(fingers[:k]) for k in range(2, count+1)]
            seq.advance(valid[stage-1], env.sim.data.body_xpos[env.cube_ids[stage]])
            tail = tail+1 if valid[-1] else 0
            longest = max(longest, tail)
            if stage == 2 and phase == 6:
                if final_release_free_seen and fingers[-1]:
                    renewed_contact += 1
                if not fingers[-1]:
                    final_release_free_seen = True
            traces.append(np.r_[frame, stage, phase, probability, seq.policy.raw_steps, seq.policy.used_steps,
                obs['robot0_eef_pos'], np.concatenate([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]),
                action, fingers, valid, tail])
            if tail >= 50 or seq.timed_out:
                break
    digest.update(env.sim.get_state().flatten().tobytes())
    return dict(seed=seed, success=tail >= 50, frames=frame+1, max_stable_frames=longest,
                renewed_final_finger_contact_frames=renewed_contact, intervention_frames=interventions,
                first_intervention_frame=first, history_before_intervention=history,
                trajectory_sha256=digest.hexdigest(), initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
                _prefixes=prefixes, _trace=np.asarray(traces), _initial=initial)


def public(result):
    return {k: v for k, v in result.items() if not k.startswith('_')}


def summarize(results, plan, complete):
    models = {}
    for name, panels in results.items():
        models[name] = {}
        for count, rows in panels.items():
            n = len(rows)
            models[name][count] = dict(n=n, original_successes=sum(r['original']['success'] for r in rows),
                bounded_successes=sum(r['bounded_clock']['success'] for r in rows), gains=sum(r['gain'] for r in rows),
                losses=sum(r['loss'] for r in rows), negative_identical=all(r['negative_identical'] for r in rows) if count == '2' else None)
    primary = [v['3'] for v in models.values() if '3' in v and v['3']['n']]
    means = {}
    for history in ('mixed', 'curriculum'):
        rows = [v['3'] for name, v in models.items() if name.startswith(history+'_') and '3' in v and v['3']['n']]
        means[history] = sum(100*(r['bounded_successes']-r['original_successes'])/r['n'] for r in rows)/len(rows) if rows else None
    thresholds = plan['review_thresholds']
    candidate = complete and bool(primary) and all(v is not None and v >= thresholds['minimum_mean_gain_percentage_points_each_history'] for v in means.values())
    candidate = candidate and all(100*(r['original_successes']-r['bounded_successes'])/r['n'] <= thresholds['maximum_regression_percentage_points_per_model'] for r in primary)
    candidate = candidate and all(v.get('2', {}).get('negative_identical', False) for v in models.values())
    return dict(complete=complete, models=models, mean_gain_percentage_points_by_history=means,
                candidate_for_review=bool(candidate), automatic_promotion=False, optimizer_updates=0,
                interpretation='Per-seed paired scene results. Review thresholds are practical exploratory criteria, not statistical proof; no automatic changes to existing policies.')


def run(out, device, deadline=None, prepared=None):
    _, base, torch, np = libraries()
    technical = prepared is not None
    verify(prepared or out)
    plan, cfg = read((prepared or out)/'plan.json'), read((prepared or out)/'base_config.json')
    models = read((prepared or out)/'models.json')
    cap = read((prepared or out)/'clock_contract.json')['maximum_input_steps']
    if technical:
        models = {k: v for k, v in models.items() if k.endswith('seed1')}
        out.mkdir(parents=True, exist_ok=False)
        write(out/'plan.json', plan)
    elif read(out/'status.json')['state'] != 'READY':
        raise ValueError('Expected a fresh READY experiment')
    if (out/'STOP').exists():
        raise InterruptedError('STOP requested before launch')
    with (out/'launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time(), technical_only=technical), stream)
    started = time.time()
    deadline = deadline or started+(600 if technical else plan['wall_clock_cap_seconds']-plan['shutdown_reserve_seconds'])
    state = dict(state='INITIALIZING', pid=os.getpid(), started_unix=started, completed_round=0,
                 optimizer_updates=0, technical_only=technical, deadline=deadline, updated_unix=started)
    write(out/'status.json', state)
    results, done = {}, 0
    try:
        base.configure(1)
        for name, entry in models.items():
            if base.sha(ROOT/entry['path']) != entry['sha256']:
                raise ValueError('Frozen model changed')
            ck = torch.load(ROOT/entry['path'], map_location='cpu', weights_only=False)
            model = base.backend().native.historical.PhaseNet(cfg['width']).to(device)
            model.load_state_dict(ck['model'])
            results[name] = {}
            for count in (3, 2):
                scene_range = plan['confirmation_seeds'] if count == 3 else plan['negative_control_seeds']
                seeds = ([plan['technical_regression_seed'] if count == 3 else plan['technical_negative_seed']]
                         if technical else range(scene_range[0], scene_range[1]+1))
                env = base.backend().native.historical.make_env(count)
                panel = []
                results[name][str(count)] = panel
                try:
                    for seed in seeds:
                        state.update(state='EVALUATING', model=name, count=count, seed=seed, updated_unix=time.time())
                        write(out/'status.json', state)
                        original = episode(env, model, cfg, seed, None, out, deadline)
                        bounded = episode(env, model, cfg, seed, cap, out, deadline)
                        pairing = compare_pair(original, bounded, require_identical=count == 2)
                        row = dict(seed=seed, original=public(original), bounded_clock=public(bounded), **pairing)
                        panel.append(row)
                        if len(panel) == 1:
                            traces = out/'traces'
                            traces.mkdir(exist_ok=True)
                            for condition, result in (('original', original), ('bounded_clock', bounded)):
                                np.savez_compressed(traces/f'{name}_count{count}_{seed}_{condition}.npz',
                                                    trace=result['_trace'], initial=result['_initial'])
                        done += 1
                        state.update(completed_round=done, updated_unix=time.time())
                        write(out/'status.json', state)
                        write(out/f'{name}_count{count}.json', dict(technical_only=technical, rows=panel))
                        with (out/'events.jsonl').open('a') as stream:
                            stream.write(json.dumps(dict(model=name, count=count, **row))+'\n')
                finally:
                    env.close()
                results[name][str(count)] = panel
                write(out/'partial_summary.json', summarize(results, plan, False))
        state['state'] = 'SMOKE_COMPLETE' if technical else 'COMPLETE'
        summary = summarize(results, plan, True)
        if technical:
            summary['candidate_for_review'] = False
        write(out/'result_summary.json', dict(technical_only=technical, **summary))
    except (TimeoutError, InterruptedError) as exc:
        state.update(state='PARTIAL_TIME_CAP' if isinstance(exc, TimeoutError) else 'STOPPED', reason=str(exc))
        write(out/'partial_summary.json', summarize(results, plan, False))
    except BaseException as exc:
        state.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        state.update(updated_unix=time.time(), completed_round=done)
        write(out/'status.json', state)
    print(json.dumps(dict(state=state['state'], completed_pairs=done, optimizer_updates=0)))


def supervise(out, device):
    started = time.time()
    verify(out)
    if read(out/'status.json')['state'] != 'READY' or (out/'STOP').exists():
        raise ValueError('Expected READY without STOP')
    with (out/'supervisor_launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=started), stream)
    plan = read(out/'plan.json')
    hard = started+plan['wall_clock_cap_seconds']
    deadline = hard-plan['shutdown_reserve_seconds']
    state = dict(state='STARTING', pid=os.getpid(), started_unix=started, deadline=deadline, hard_deadline=hard)
    worker, awake = None, False
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        worker = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), 'run',
            '--output', str(out), '--device', device, '--deadline', str(deadline)], cwd=ROOT)
        state.update(state='VALIDATING', worker_pid=worker.pid, sleep_prevention_active=awake, updated_unix=time.time())
        write(out/'supervisor_status.json', state)
        try:
            code = worker.wait(timeout=max(.001, hard-time.time()))
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
            raise TimeoutError('Hard ten-hour total limit reached')
        if code:
            raise RuntimeError('Validation worker failed with exit code '+str(code))
        state['state'] = read(out/'status.json')['state']
    except BaseException as exc:
        state.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        if worker is not None and worker.poll() is None:
            worker.kill()
            worker.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(), sleep_prevention_active=False)
        write(out/'supervisor_status.json', state)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare','preflight','smoke','run','supervise','status'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prepared', type=Path)
    p.add_argument('--device', choices=('cuda','cpu'), default='cuda')
    p.add_argument('--deadline', type=float)
    args = p.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        p.error('Output must remain inside the workspace')
    if args.command == 'prepare':
        prepare(out)
    elif args.command == 'preflight':
        verify(out)
        if read(out/'status.json')['state'] != 'READY' or any((out/x).exists() for x in ('launch.json','supervisor_launch.json','STOP')):
            raise ValueError('Not startable; use a new prepared run')
        print(json.dumps(dict(state='READY', input_hashes_verified=True)))
    elif args.command == 'smoke':
        if args.prepared is None:
            p.error('--prepared required')
        run(out, args.device, prepared=args.prepared.resolve())
    elif args.command == 'run':
        run(out, args.device, args.deadline)
    elif args.command == 'supervise':
        supervise(out, args.device)
    else:
        monitor.status(out)


if __name__ == '__main__':
    main()
