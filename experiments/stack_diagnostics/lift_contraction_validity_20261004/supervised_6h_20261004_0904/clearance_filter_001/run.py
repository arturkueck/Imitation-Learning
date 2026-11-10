"""Predeclared held-only phase/domain rollout; frozen calibration and policy, no training."""
import importlib.util
from pathlib import Path
import sys
import time
import traceback
import h5py
import numpy as np
import helpers as h
import preparation
import clearance

OUT, SESSION, ROOT, PILOT = h.OUT, h.SESSION, h.ROOT, h.PILOT

def auxiliary_gate(branch):
    before, after = branch['anchor'], branch['before']
    fields = [k for k in before['sim'] if k not in ['qpos', 'qvel']]
    error = max([h.difference(before['sim'][k], after['sim'][k]) for k in fields] + [0.])
    gripper = h.difference(before['gripper_memory'], after['gripper_memory'])
    gripper_ctrl = h.difference(before['controllers']['right_gripper'], after['controllers']['right_gripper'])
    obs = branch['observation']
    eef = float(np.linalg.norm(np.asarray(obs['robot0_eef_pos']) - branch['before_measure']['eef_m']))
    geometry = float(np.linalg.norm(np.asarray(obs['object'])[-3:] - (np.asarray(obs['object'])[:3] - obs['robot0_eef_pos'])))
    return dict(untouched_simulator_error=error, gripper_error=gripper, gripper_controller_error=gripper_ctrl,
                observation_eef_error_m=eef, object_relative_consistency_error_m=geometry,
                passed=bool(max(error, gripper, gripper_ctrl, eef, geometry) <= 1e-9))

def central(row, kind, axis):
    minus, plus = [row['branches'][f'{kind}_{axis}_{sign}'] for sign in ['minus', 'plus']]
    dx = np.asarray(plus['before_measure']['eef_m']) - minus['before_measure']['eef_m']
    da = np.asarray(plus['action']) - minus['action']
    dy = np.asarray(plus['next_eef_m']) - minus['next_eef_m']
    return dx, da, dy

def ratio_summary(probes, model):
    observed = np.array([p['observed_ratio'] for p in probes])
    predicted = np.array([p['models'][model]['predicted_ratio'] for p in probes])
    obs_pass, pred_pass = observed < .99, predicted < .99
    error = np.abs(observed - predicted)
    return dict(n=len(probes), median_absolute_ratio_error=float(np.median(error)),
                p90_absolute_ratio_error=float(np.quantile(error, .9)),
                observed_below_0_99=int(obs_pass.sum()), predicted_below_0_99=int(pred_pass.sum()),
                false_pass=int((pred_pass & ~obs_pass).sum()), false_penalty=int((~pred_pass & obs_pass).sum()),
                vector=h.summary([p['models'][model] for p in probes]))

def run():
    start = time.monotonic()
    assert not (OUT / 'result.json').exists(), 'Fresh diagnostic only; preserve outputs'
    selection = h.read(OUT / 'selection.json')
    calibration = h.read(OUT / 'calibration.json')
    result = dict(state='RUNNING', policy_training_updates=0, seed=selection['seed'], selection=selection,
                  source_sha256=h.sha(Path(__file__)), protocol_sha256=h.sha(OUT / 'PROTOCOL.md'),
                  rows=[], counts=h.COUNTS, fit_updates=0, planned_branches=336)
    env = None
    h.write(OUT / 'result.json', result)
    try:
        spec = importlib.util.spec_from_file_location('frozen_pilot', PILOT / 'run.py')
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core); core.bootstrap()
        import torch
        torch.set_num_threads(2)
        from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
        checkpoint = PILOT / 'B0/model_final.pth'
        data = ROOT / 'praxis/data/lift/ph/low_dim_v15.hdf5'
        assert h.sha(checkpoint) == selection['checkpoint_sha256']
        assert h.sha(data) == selection['dataset_sha256']
        for path, digest in calibration['calibration_sources'].items():
            assert h.sha(Path(path)) == digest
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
                d = f[f'data/{demo}']
                actions, states = d['actions'][:], d['states'][:]
                times = [int(frac * (len(actions) - 1)) for frac in selection['anchor_fractions']]
                assert len(set(times)) == 3
                for fraction, t in zip(selection["anchor_fractions"], times):
                    for history in selection['histories']:
                        row = dict(demo=demo, t=t, split='heldout', fraction=fraction, stratum=str(fraction), history=history, branches={})
                        result['rows'].append(row)
                        variants = [('reference', None, 0, 'reference'), ('repeat', None, 0, 'reference')]
                        for kind in ['B', 'A', 'Pfull']:
                            variants += [(f'{kind}_{axis}_{sign}', axis, -1 if sign == 'minus' else 1, kind)
                                         for axis in range(7 if kind == 'B' else 3) for sign in ['minus', 'plus']]
                        ref_action = None
                        for name, axis, sign, kind in variants:
                            h.stop_check(); np.random.seed(selection['seed']); torch.manual_seed(selection['seed'])
                            env.reset_to({'model': d.attrs['model_file'], 'states': states[0]})
                            h.COUNTS['resets'] += 1
                            robot, sim = env.env.robots[0], env.env.sim
                            ctrl = robot.composite_controller.part_controllers['right']
                            monitor = {'active': False, 'contacts': []}
                            originals = {k: getattr(sim, k) for k in ['step', 'step2']}
                            def instrument(method):
                                def step():
                                    method(); h.COUNTS['physics_steps'] += 1
                                    if monitor['active']:
                                        monitor['contacts'].extend(h.robot_contacts(sim, robot))
                                return step
                            for method, original in originals.items():
                                setattr(sim, method, instrument(original))
                            try:
                                preparation_info = preparation.prepare(env, ctrl, d, t, actions, history, selection)
                                anchor, anchor_measure = h.snapshot(env, ctrl), h.measured(sim, ctrl)
                                if name == 'reference':
                                    row['pre_response_filter'] = clearance.filter_anchor(env, ctrl, selection['proximity_margin_m'])
                                    h.write(OUT / 'result.json', result)
                                intervention = None
                                if kind in ['A', 'Pxyz', 'Pfull']:
                                    delta = np.zeros(3); delta[axis] = sign * .005
                                    intervention = h.shift_state(env, ctrl, delta)
                                obs = env.get_observation()
                                if ref_action is None:
                                    ref_action = policy_action(obs)
                                action = ref_action.copy()
                                if kind == 'B':
                                    action[axis] = np.clip(action[axis] + sign * .1, -1, 1)
                                elif kind in ['Pxyz', 'Pfull']:
                                    changed = policy_action(obs)
                                    action[:3] = changed[:3]
                                    if kind == 'Pfull':
                                        action = changed
                                branch = dict(preparation=preparation_info, anchor=anchor, anchor_measure=anchor_measure,
                                              before=h.snapshot(env, ctrl), before_measure=h.measured(sim, ctrl),
                                              intervention=intervention,
                                              observation={k: np.asarray(v).tolist() for k, v in obs.items()},
                                              action=action.tolist(), requested_component=axis,
                                              requested_addition=sign * .1 if kind == 'B' else None,
                                              actual_action_difference=(action - ref_action).tolist(),
                                              initial_robot_contacts=h.robot_contacts(sim, robot))
                                branch['auxiliary_gate'] = auxiliary_gate(branch)
                                monitor['active'] = True
                                nxt, _, _, _ = env.step(action); h.COUNTS['probe_actions'] += 1
                                branch['next_eef_m'] = np.asarray(nxt['robot0_eef_pos']).tolist()
                                # End-step collision verification after the last integration.
                                sim.forward()
                                branch['final_robot_contacts'] = h.robot_contacts(sim, robot)
                                branch['step_robot_contacts'] = monitor['contacts']
                                row['branches'][name] = branch
                            finally:
                                for method, original in originals.items():
                                    setattr(sim, method, original)
                            result['elapsed_seconds'] = time.monotonic() - start
                            h.write(OUT / 'result.json', result)
                        b = row['branches']; ref, repeat = b['reference'], b['repeat']
                        anchor_error = max(h.difference(ref['anchor'], branch['anchor']) for branch in b.values())
                        repeat_error = float(np.linalg.norm(np.asarray(ref['next_eef_m']) - repeat['next_eef_m']))
                        paired = [h.difference(ref['before'], branch['before']) for name, branch in b.items() if name.startswith('B_')]
                        paired += [h.difference(b[f'A_{axis}_{sign}']['before'], b[f'{kind}_{axis}_{sign}']['before'])
                                   for axis in range(3) for sign in ['minus', 'plus'] for kind in ['Pfull']]
                        row['gates'] = dict(anchor_start_error_max=anchor_error, reference_repeat_error_m=repeat_error,
                                            same_probe_start_error_max=max(paired),
                                            auxiliary_fields_passed=all(v['auxiliary_gate']['passed'] for v in b.values()),
                                            recorded_geometry_passed=all(v['preparation']['geometry_passed'] for v in b.values()),
                                            interventions_passed=all(v['intervention']['passed'] and v['intervention']['position_error_m'] <= selection['position_tolerance_m'] for v in b.values() if v['intervention']),
                                            contact_free=all(not v['initial_robot_contacts'] and not v['step_robot_contacts'] and not v['final_robot_contacts'] for v in b.values()))
                        g = row['gates']
                        g['technical_passed'] = bool(anchor_error <= 1e-9 and repeat_error <= 1e-6 and max(paired) <= 1e-9
                                           and g['auxiliary_fields_passed'] and g['interventions_passed'] and g['recorded_geometry_passed'])
                        g['passed'] = bool(g['technical_passed'] and g['contact_free'])
                        g['failure_reasons'] = (["physical_or_pairing_gate"] if not g['technical_passed'] else []) + (["robot_contact"] if not g['contact_free'] else [])
                        print(f'{history} {demo} t={t}: {g}', flush=True); h.write(OUT / 'result.json', result)
        assert len(result['rows']) == 12 and sum(len(r['branches']) for r in result['rows']) == 336
        result.update(state='COMPLETE_DATA' if all(r['gates']['passed'] for r in result['rows']) else 'DOMAIN_GATE_FAILED',
                      decision='Complete fixed rollout inventory. Failed domain anchors preserved; no refit or training. Conditional analysis separately.')
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc, InterruptedError) else 'FAILED', error=traceback.format_exc())
        traceback.print_exc(); return 2
    finally:
        if env is not None:
            env.env.close()
        result['elapsed_seconds'] = time.monotonic() - start
        result['counts'] = h.COUNTS; h.write(OUT / 'result.json', result)

if __name__ == '__main__':
    sys.exit(run())
