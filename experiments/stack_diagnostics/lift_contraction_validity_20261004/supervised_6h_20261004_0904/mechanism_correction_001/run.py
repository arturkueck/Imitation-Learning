"""Execute fixed model-based correction arms on new physical held-out states."""
import importlib.util
from pathlib import Path
import sys
import time
import traceback
import h5py
import numpy as np
import helpers as h

OUT, SESSION, ROOT, PILOT = h.OUT, h.SESSION, h.ROOT, h.PILOT

def auxiliary_gate(b):
    a, z = b['anchor'], b['before']
    errors = [h.difference(a['sim'][k], z['sim'][k]) for k in a['sim'] if k not in ['qpos', 'qvel']]
    errors += [h.difference(a['gripper_memory'], z['gripper_memory']),
               h.difference(a['controllers']['right_gripper'], z['controllers']['right_gripper'])]
    obs = b['observation']
    errors += [float(np.linalg.norm(np.asarray(obs['robot0_eef_pos']) - b['before_measure']['eef_m'])),
               float(np.linalg.norm(np.asarray(obs['object'])[-3:] - (np.asarray(obs['object'])[:3] - obs['robot0_eef_pos'])))]
    return dict(max_error=max(errors), passed=bool(max(errors) <= 1e-9))

def correction(arm, delta, base, reference, matrices, selection):
    start = time.perf_counter()
    da = base - reference
    A, B3, B7, old = [matrices[k] for k in ['A', 'B3', 'B7', 'K_OLS']]
    if arm == 'C1':
        e, G = delta + da[:3] @ old, old
    elif arm == 'C2':
        e, G = delta @ A + da[:3] @ B3, B3
    else:
        e, G = delta @ A + da @ B7, B3
    radius = selection['design_target_ratio'] * float(np.linalg.norm(delta))
    u = np.zeros(3)
    if arm != 'C0' and np.linalg.norm(e) > radius:
        required = (radius / float(np.linalg.norm(e)) - 1.) * e
        u = np.linalg.lstsq(G.T, required, rcond=None)[0]
    ideal = u.copy(); norm = float(np.linalg.norm(u)); capped = norm > selection['correction_norm_limit']
    if capped:
        u *= selection['correction_norm_limit'] / norm
    proposed = base.copy(); proposed[:3] += u
    action = np.clip(proposed, -1, 1)
    actual_u = action[:3] - base[:3]
    predicted = e + actual_u @ G
    return action, dict(model_before_error_m=e.tolist(), predicted_after_error_m=predicted.tolist(),
                        predicted_ratio=float(np.linalg.norm(predicted) / np.linalg.norm(delta)),
                        design_radius_m=radius, ideal_u_xyz=ideal.tolist(), actual_u_xyz=actual_u.tolist(),
                        correction_norm=float(np.linalg.norm(actual_u)), norm_capped=bool(capped),
                        action_clipped=bool(np.any(proposed != action)), zero_correction=bool(not np.any(actual_u)),
                        predicted_design_target_reached=bool(np.linalg.norm(predicted) <= radius + 1e-9),
                        solve_seconds=time.perf_counter() - start)

def run():
    start = time.monotonic(); env = None
    assert not (OUT / 'result.json').exists()
    selection = h.read(OUT / 'selection.json'); calib = h.read(OUT / 'calibration.json')
    matrices = {k: np.asarray(calib[k]) for k in ['A', 'B3', 'B7', 'K_OLS']}
    assert not set(selection['selected_demos']) & set(selection['excluded_prior_demos'])
    assert not set(selection['selected_demos']) & set(calib['fit_demos'])
    result = dict(state='RUNNING', policy_training_updates=0, fit_updates=0, selection=selection,
                  source_sha256=h.sha(Path(__file__)), protocol_sha256=h.sha(OUT / 'PROTOCOL.md'),
                  calibration_sha256=h.sha(OUT / 'calibration.json'), rows=[], counts=h.COUNTS)
    h.write(OUT / 'result.json', result)
    try:
        spec = importlib.util.spec_from_file_location('frozen_pilot', PILOT / 'run.py')
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core); core.bootstrap()
        import torch
        torch.set_num_threads(2)
        from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
        checkpoint, data = PILOT / 'B0/model_final.pth', ROOT / 'praxis/data/lift/ph/low_dim_v15.hdf5'
        assert h.sha(checkpoint) == selection['checkpoint_sha256'] and h.sha(data) == selection['dataset_sha256']
        for name, digest in calib['calibration_sources'].items():
            assert h.sha(Path(name)) == digest
        policy, ckpt = policy_from_checkpoint(ckpt_path=str(checkpoint), verbose=False)
        env, _ = env_from_checkpoint(ckpt_dict=ckpt, render=False, render_offscreen=False)
        result['environment'] = dict(lite_physics=env.env.lite_physics, control_timestep=env.env.control_timestep,
                                    model_timestep=env.env.model_timestep)
        def policy_action(obs):
            policy.start_episode(); h.COUNTS['policy_calls'] += 1
            with torch.inference_mode():
                return np.clip(np.asarray(policy(obs)), -1, 1)
        with h5py.File(data, 'r') as f:
            for demo in selection['selected_demos']:
                d = f[f'data/{demo}']; actions, states = d['actions'][:], d['states'][:]
                times = [int(frac * (len(actions) - 1)) for frac in selection['anchor_fractions']]
                assert len(set(times)) == 3
                for t in times:
                    row = dict(demo=demo, t=t, split='heldout', branches={}); result['rows'].append(row)
                    variants = [('reference', None, 0, None), ('repeat', None, 0, None)]
                    variants += [(f'{arm}_{axis}_{sign}', axis, -1 if sign == 'minus' else 1, arm)
                                 for arm in selection['arms'] for axis in range(3) for sign in ['minus', 'plus']]
                    ref_action, ref_eef = None, None
                    for name, axis, sign, arm in variants:
                        h.stop_check(); np.random.seed(selection['seed']); torch.manual_seed(selection['seed'])
                        env.reset_to({'model': d.attrs['model_file'], 'states': states[0]}); h.COUNTS['resets'] += 1
                        robot, sim = env.env.robots[0], env.env.sim
                        ctrl = robot.composite_controller.part_controllers['right']
                        monitor = {'active': False, 'contacts': []}; originals = {k: getattr(sim, k) for k in ['step', 'step2']}
                        def instrument(method):
                            def step():
                                method(); h.COUNTS['physics_steps'] += 1
                                if monitor['active']:
                                    monitor['contacts'].extend(h.robot_contacts(sim, robot))
                            return step
                        for method, original in originals.items(): setattr(sim, method, instrument(original))
                        try:
                            ctrl.update_initial_joints(d['obs/robot0_joint_pos'][0])
                            for action in actions[:t]: env.step(action); h.COUNTS['prefix_actions'] += 1
                            ctrl.update(force=True); anchor, anchor_measure = h.snapshot(env, ctrl), h.measured(sim, ctrl)
                            intervention = None
                            if arm is not None:
                                delta = np.zeros(3); delta[axis] = sign * selection['physical_eef_delta_m']
                                intervention = h.shift_state(env, ctrl, delta)
                            obs = env.get_observation(); physical = h.measured(sim, ctrl)
                            if ref_action is None:
                                ref_action, ref_eef = policy_action(obs), np.asarray(physical['eef_m'])
                            base = ref_action.copy() if arm is None else policy_action(obs)
                            action, info = base.copy(), None
                            if arm is not None:
                                actual_delta = np.asarray(physical['eef_m']) - ref_eef
                                action, info = correction(arm, actual_delta, base, ref_action, matrices, selection)
                            branch = dict(anchor=anchor, anchor_measure=anchor_measure, before=h.snapshot(env, ctrl),
                                          before_measure=physical, intervention=intervention,
                                          observation={k: np.asarray(v).tolist() for k, v in obs.items()},
                                          action=action.tolist(), base_policy_action=base.tolist(), correction=info,
                                          initial_robot_contacts=h.robot_contacts(sim, robot))
                            branch['auxiliary_gate'] = auxiliary_gate(branch); monitor['active'] = True
                            nxt, _, _, _ = env.step(action); h.COUNTS['probe_actions'] += 1
                            branch['next_eef_m'] = np.asarray(nxt['robot0_eef_pos']).tolist()
                            sim.forward(); branch['final_robot_contacts'] = h.robot_contacts(sim, robot)
                            branch['step_robot_contacts'] = monitor['contacts']; row['branches'][name] = branch
                        finally:
                            for method, original in originals.items(): setattr(sim, method, original)
                        result['elapsed_seconds'] = time.monotonic() - start; h.write(OUT / 'result.json', result)
                    b = row['branches']; ref, repeat = b['reference'], b['repeat']
                    matched = [h.difference(b[f'C0_{axis}_{sign}']['before'], b[f'{arm}_{axis}_{sign}']['before'])
                               for axis in range(3) for sign in ['minus', 'plus'] for arm in ['C1','C2','C3']]
                    base_errors = [float(np.max(np.abs(np.asarray(b[f'C0_{axis}_{sign}']['base_policy_action']) - b[f'{arm}_{axis}_{sign}']['base_policy_action'])))
                                   for axis in range(3) for sign in ['minus','plus'] for arm in ['C1','C2','C3']]
                    action_tail = [float(np.max(np.abs(np.asarray(v['action'])[3:] - np.asarray(v['base_policy_action'])[3:]))) for v in b.values()]
                    g = dict(anchor_start_error_max=max(h.difference(ref['anchor'], v['anchor']) for v in b.values()),
                             reference_repeat_error_m=float(np.linalg.norm(np.asarray(ref['next_eef_m']) - repeat['next_eef_m'])),
                             same_probe_start_error_max=max(matched), base_policy_difference_max=max(base_errors),
                             correction_tail_difference_max=max(action_tail),
                             auxiliary_fields_passed=all(v['auxiliary_gate']['passed'] for v in b.values()),
                             interventions_passed=all(v['intervention']['passed'] for v in b.values() if v['intervention']),
                             contact_free=all(not v['initial_robot_contacts'] and not v['step_robot_contacts'] and not v['final_robot_contacts'] for v in b.values()))
                    g['passed'] = bool(max(g[k] for k in ['anchor_start_error_max','same_probe_start_error_max','base_policy_difference_max','correction_tail_difference_max']) <= 1e-9
                                       and g['reference_repeat_error_m'] <= 1e-6 and g['auxiliary_fields_passed'] and g['interventions_passed'] and g['contact_free'])
                    row['gates'] = g; print(f'{demo} t={t}: {g}', flush=True); h.write(OUT / 'result.json', result)
        if not all(r['gates']['passed'] for r in result['rows']):
            result.update(state='GATE_FAILED', decision='No global correction effect inference: physical gate failed; preserve all outputs.')
            return 0
        groups = {arm: [] for arm in selection['arms']}; pairs = []
        for row in result['rows']:
            ref = row['branches']['reference']; row['correction_results'] = []
            per_arm = {arm: [] for arm in selection['arms']}
            for axis in range(3):
                for sign in ['minus','plus']:
                    for arm in selection['arms']:
                        b = row['branches'][f'{arm}_{axis}_{sign}']; info = b['correction']
                        delta = np.asarray(b['before_measure']['eef_m']) - ref['before_measure']['eef_m']
                        next_error = np.asarray(b['next_eef_m']) - ref['next_eef_m']
                        ratio = float(np.linalg.norm(next_error) / np.linalg.norm(delta))
                        rec = dict(arm=arm, axis=axis, sign=sign, observed_ratio=ratio, predicted_ratio=info['predicted_ratio'],
                                   absolute_ratio_error=abs(ratio-info['predicted_ratio']), actual_next_error_m=next_error.tolist(),
                                   eval_target_reached=bool(ratio <= selection['evaluation_ratio_threshold']), **info)
                        row['correction_results'].append(rec); groups[arm].append(rec); per_arm[arm].append(rec)
            errors = {arm: float(np.median([x['absolute_ratio_error'] for x in per_arm[arm]])) for arm in ['C2','C3']}
            pairs.append(dict(demo=row['demo'], t=row['t'], median_ratio_errors=errors, C3_better=errors['C3'] < errors['C2']))
        summaries = {}
        for arm, rows in groups.items():
            summaries[arm] = dict(cases=len(rows), eval_target_reached=sum(x['eval_target_reached'] for x in rows),
                                  median_observed_ratio=float(np.median([x['observed_ratio'] for x in rows])),
                                  median_absolute_ratio_error=float(np.median([x['absolute_ratio_error'] for x in rows])),
                                  median_correction_norm=float(np.median([x['correction_norm'] for x in rows])),
                                  capped=sum(x['norm_capped'] for x in rows), clipped=sum(x['action_clipped'] for x in rows),
                                  zero_corrections=sum(x['zero_correction'] for x in rows),
                                  predicted_design_target_reached=sum(x['predicted_design_target_reached'] for x in rows),
                                  total_solve_seconds=sum(x['solve_seconds'] for x in rows))
        e2, e3 = [summaries[arm]['median_absolute_ratio_error'] for arm in ['C2','C3']]
        reduction = 1-e3/max(e2,1e-15); better = sum(x['C3_better'] for x in pairs)
        result.update(state='COMPLETE', summaries=summaries,
                      primary=dict(relative_reduction=reduction, better_anchors=better, total_anchors=12,
                                   predefined_gate_passed=bool(reduction >= .2 and better >= 8), paired_anchor_results=pairs),
                      decision='Oracle one-step correction evidence only; no policy training or task robustness claim.')
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc,InterruptedError) else 'FAILED', error=traceback.format_exc())
        traceback.print_exc(); return 2
    finally:
        if env is not None: env.env.close()
        result['elapsed_seconds']=time.monotonic()-start; result['counts']=h.COUNTS
        h.write(OUT/'result.json',result)

if __name__ == '__main__': sys.exit(run())
