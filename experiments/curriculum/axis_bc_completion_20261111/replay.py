"""Outcome-stratified historical trajectory diagnosis, never new training labels."""
import hashlib
import random
import time

import night


def select_cases(before, after, per_group=1):
    if [r['seed'] for r in before] != [r['seed'] for r in after]:
        raise ValueError('Historical scenes are not paired')
    groups = {name: [] for name in ('gain', 'loss', 'both_fail', 'both_success')}
    for a, b in zip(before, after):
        if a['initial_sha256'] != b['initial_sha256']:
            raise ValueError('Historical initial states differ')
        group = ('both_success' if a['success'] else 'gain') if b['success'] else ('loss' if a['success'] else 'both_fail')
        groups[group].append(dict(group=group, seed=a['seed'], initial_sha256=a['initial_sha256'],
                                 parent_success=a['success'], extended_success=b['success']))
    return [r for group in groups.values() for r in sorted(group, key=lambda row: row['seed'])[:per_group]]


def trace_episode(model, cfg, seed, out, deadline):
    base, torch, np = night.runtime.libraries()
    controller = base.backend()
    historical = controller.native.historical
    env = historical.make_env(3)
    trace = []
    model.eval()
    try:
        random.seed(seed)
        np.random.seed(seed)
        env.reset()
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        initial = env.sim.get_state().flatten().copy()
        seq = controller.GuardedSequencer(model, 3, controller.Clearance(env))
        seq.policy = base.DevicePolicy(model, historical, cfg['completion_threshold'])
        tail = 0
        with torch.no_grad():
            for frame in range(1000):
                base.check_stop(out, deadline)
                stage = seq.stage
                positions = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                action, phase, probability = seq.policy.action(obs, positions[stage-1], positions[stage])
                env.step(action)
                env.sim.forward()
                obs = env._get_observations(force_update=True)
                valid = [historical.old.prefix_valid(env, count) and
                         not any(controller.native.finger_contact(env, c) for c in env.cubes[:count])
                         for count in (2, 3)]
                event = seq.advance(valid[stage-1], env.sim.data.body_xpos[env.cube_ids[stage]])
                tail = tail+1 if valid[-1] else 0
                held = [env._check_grasp(env.robots[0].gripper, c.contact_geoms) for c in env.cubes]
                positions = np.concatenate([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                trace.append(np.r_[frame, stage, phase, seq.policy.phase, probability, event, tail,
                                   seq.clearance.gap(2), obs['robot0_eef_pos'], positions, action, held, valid])
                if tail >= 50 or seq.timed_out:
                    break
        return dict(success=tail >= 50, frames=len(trace), phase=seq.policy.phase, stage=seq.stage,
                    retreat_timeout=seq.timed_out, initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest()), np.asarray(trace), initial
    finally:
        env.close()


def replay_selected(out, cfg, plan, parents, controls, device, deadline, limit=None, technical=False):
    _, _, np = night.runtime.libraries()
    source = night.ROOT/plan['source']
    folder = out/('technical_replays' if technical else 'diagnosis/replays')
    folder.mkdir(parents=True, exist_ok=False)
    report = []
    started = time.time()
    for name, parent in parents.items():
        before = night.read(source/'confirmation'/f'{name}_parent_count3.json')['rows']
        after = night.read(source/'confirmation'/f'{name}_extended_count3.json')['rows']
        cases = select_cases(before, after, plan['replay_examples_per_outcome'])
        for case in cases:
            if limit is not None and len(report) >= limit:
                break
            models = dict(parent=night.load_model(night.ROOT/parent['path'], cfg, device),
                          extended=night.load_model(night.ROOT/controls[name]['path'], cfg, device))
            pair, traces = {}, {}
            for generation, model in models.items():
                night.write(out/'diagnostic_status.json', dict(state='DIAGNOSING', pid=night.os.getpid(),
                    started_unix=started, evaluating=f'replay:{name}:{case["seed"]}:{generation}', updated_unix=time.time()))
                result, trace, initial = trace_episode(model, cfg, case['seed'], out, deadline)
                path = folder/f'{name}_{case["group"]}_{case["seed"]}_{generation}.npz'
                np.savez_compressed(path, trace=trace, initial=initial)
                pair[generation] = result
                traces[generation] = trace
                expected = case[generation+'_success']
                if result['initial_sha256'] != case['initial_sha256'] or result['success'] != expected:
                    night.write(folder/'replay_mismatch.json', dict(model=name, case=case, generation=generation, observed=result))
                    raise ValueError('Historical replay mismatch; preserve traces and investigate before training')
            n = min(len(t) for t in traces.values())
            phase_changes = np.flatnonzero(np.any(traces['parent'][:n, 1:4] != traces['extended'][:n, 1:4], axis=1))
            action_changes = np.flatnonzero(np.max(np.abs(traces['parent'][:n, 20:27]-traces['extended'][:n, 20:27]), axis=1) > 1e-6)
            report.append(dict(model=name, **case, replay=pair,
                first_phase_or_stage_difference=int(phase_changes[0]) if len(phase_changes) else None,
                first_action_difference=int(action_changes[0]) if len(action_changes) else None))
            night.write(folder/'report.json', dict(cases=report,
                interpretation='Outcome-stratified examples selected by smallest scene seed per category. Descriptive traces, not population error rates or a causal phase diagnosis.',
                columns=['frame','stage_before','phase_before','phase_after','completion_probability','controller_event','stable_tail','gripper_gap',
                         'eef_x','eef_y','eef_z','A_x','A_y','A_z','B_x','B_y','B_z','C_x','C_y','C_z',
                         'action_x','action_y','action_z','rotation_x','rotation_y','rotation_z','gripper','held_A','held_B','held_C','valid2','valid3']))
        if limit is not None and len(report) >= limit:
            break
    return report
