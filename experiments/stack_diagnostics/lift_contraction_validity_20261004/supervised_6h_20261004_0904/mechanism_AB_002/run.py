"""No-training physical A/B diagnostic with frozen selection and explicit gates."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

import h5py
import numpy as np

OUT = Path(__file__).resolve().parent
SESSION = OUT.parent
ROOT = SESSION.parents[2]
PILOT = SESSION / 'attempts/attempt_002'
COUNTS = dict(resets=0, prefix_actions=0, probe_actions=0, physics_steps=0, ik_iterations=0, policy_calls=0)

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def write(p, value):
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(p)

def stop_check():
    if (OUT / 'STOP_REQUESTED').exists() or time.time() >= read(OUT / 'launch.json')['deadline_unix']:
        raise InterruptedError('Fixed bounded diagnostic deadline or safe-stop request')

def simple(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    if isinstance(value, (tuple, list)) and all(isinstance(x, (int, float, np.generic)) for x in value):
        return np.asarray(value).tolist()
    raise TypeError()

def numeric_memory(obj):
    result = {}
    for name, value in vars(obj).items():
        try:
            result[name] = simple(value)
        except TypeError:
            pass
    return result

def snapshot(env, ctrl):
    sim = env.env.sim
    fields = ['qpos', 'qvel', 'qacc_warmstart', 'act', 'ctrl', 'mocap_pos', 'mocap_quat',
              'qfrc_applied', 'xfrc_applied', 'userdata']
    robot = env.env.robots[0]
    return {'sim': {k: np.array(getattr(sim.data, k), copy=True).tolist() for k in fields},
            'sim_time': float(sim.data.time),
            'controllers': {k: numeric_memory(c) for k, c in robot.composite_controller.part_controllers.items()},
            'gripper_memory': numeric_memory(robot.gripper['right']),
            'env_time': {k: simple(getattr(env.env, k)) for k in ['timestep', 'cur_time', 'done'] if hasattr(env.env, k)}}

def difference(a, b):
    if isinstance(a, dict):
        assert set(a) == set(b)
        return max([difference(a[k], b[k]) for k in a] + [0.])
    if a is None or isinstance(a, (str, bool)):
        return 0. if a == b else float('inf')
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b)), initial=0.))

HISTORY = ['goal_pos', 'goal_ori', 'initial_joint', 'initial_ref_pos', 'initial_ref_ori_mat',
           'origin_pos', 'origin_ori', '_goal_update_mode', 'kp', 'kd', 'action_scale',
           'action_input_transform', 'action_output_transform']

def history(ctrl):
    return {k: copy.deepcopy(getattr(ctrl, k)) for k in HISTORY if hasattr(ctrl, k)}

def restore_history(ctrl, values):
    for k, v in values.items():
        setattr(ctrl, k, copy.deepcopy(v))

def robot_contacts(sim, robot):
    names = set(robot.robot_model.contact_geoms) | set(robot.gripper['right'].contact_geoms)
    pairs = []
    for i in range(sim.data.ncon):
        c = sim.data.contact[i]
        pair = [sim.model.geom_id2name(c.geom1), sim.model.geom_id2name(c.geom2)]
        if any(n in names for n in pair):
            pairs.append(pair)
    return pairs

def measured(sim, ctrl):
    return {'eef_m': sim.data.get_site_xpos(ctrl.ref_name).copy().tolist(),
            'orientation': sim.data.get_site_xmat(ctrl.ref_name).copy().tolist(),
            'linear_velocity': sim.data.get_site_xvelp(ctrl.ref_name).copy().tolist(),
            'angular_velocity': sim.data.get_site_xvelr(ctrl.ref_name).copy().tolist()}

def shift_state(env, ctrl, delta):
    from robosuite.utils.control_utils import orientation_error
    sim = env.env.sim
    before = measured(sim, ctrl)
    original_qpos = sim.data.qpos.copy()
    original_qvel = sim.data.qvel.copy()
    original_warmstart = sim.data.qacc_warmstart.copy()
    q = np.asarray(ctrl.qpos_index, dtype=int)
    v = np.asarray(ctrl.qvel_index, dtype=int)
    target = np.asarray(before['eef_m']) + delta
    target_R = np.asarray(before['orientation']).reshape(3, 3)
    memory = history(ctrl)
    for iteration in range(30):
        stop_check()
        ctrl.update(force=True)
        error = np.r_[target - ctrl.ref_pos, orientation_error(target_R, ctrl.ref_ori_mat)]
        if np.linalg.norm(error[:3]) < 1e-7 and np.linalg.norm(error[3:]) < 1e-7:
            break
        J = ctrl.J_full.copy()
        dq = J.T @ np.linalg.solve(J @ J.T + 1e-6 * np.eye(6), error)
        dq *= min(1., .05 / max(float(np.max(np.abs(dq))), 1e-15))
        sim.data.qpos[q] += dq
        sim.forward()
        COUNTS['ik_iterations'] += 1
    ctrl.update(force=True)
    desired_vel = np.r_[before['linear_velocity'], before['angular_velocity']]
    J = ctrl.J_full.copy()
    # Minimum correction of joint velocities to hold the spatial EEF velocity.
    sim.data.qvel[v] += np.linalg.lstsq(J, desired_vel - J @ sim.data.qvel[v], rcond=None)[0]
    sim.forward()
    ctrl.update(force=True)
    restore_history(ctrl, memory)
    # forward / forced controller refresh writes this solver-history field.
    # Restore after the final refresh, before measuring / executing a step.
    sim.data.qacc_warmstart[:] = original_warmstart
    after = measured(sim, ctrl)
    R = np.asarray(after['orientation']).reshape(3, 3)
    angle = float(np.arccos(np.clip((np.trace(target_R.T @ R) - 1) / 2, -1, 1)))
    untouched_q = np.setdiff1d(np.arange(len(original_qpos)), q)
    untouched_v = np.setdiff1d(np.arange(len(original_qvel)), v)
    limits = sim.model.jnt_range[np.asarray(ctrl.joint_index)]
    values = sim.data.qpos[q]
    metrics = dict(position_error_m=float(np.linalg.norm(np.asarray(after['eef_m']) - target)),
                   orientation_error_rad=angle,
                   linear_velocity_error=float(np.linalg.norm(np.asarray(after['linear_velocity']) - before['linear_velocity'])),
                   angular_velocity_error=float(np.linalg.norm(np.asarray(after['angular_velocity']) - before['angular_velocity'])),
                   untouched_qpos_error=float(np.max(np.abs(sim.data.qpos[untouched_q] - original_qpos[untouched_q]), initial=0)),
                   untouched_qvel_error=float(np.max(np.abs(sim.data.qvel[untouched_v] - original_qvel[untouched_v]), initial=0)),
                   controller_history_error=difference({k: simple(vv) for k, vv in memory.items()}, {k: simple(vv) for k, vv in history(ctrl).items()}),
                   solver_warmstart_error=float(np.max(np.abs(sim.data.qacc_warmstart - original_warmstart), initial=0)),
                   joint_limits_passed=bool(np.all(values >= limits[:, 0]) and np.all(values <= limits[:, 1])),
                   joint_velocity_correction=(sim.data.qvel[v] - original_qvel[v]).tolist(),
                   actual_delta_m=(np.asarray(after['eef_m']) - before['eef_m']).tolist())
    metrics['passed'] = bool(metrics['position_error_m'] <= 5e-5 and angle <= 1e-4
                             and metrics['linear_velocity_error'] <= 1e-5 and metrics['angular_velocity_error'] <= 1e-4
                             and metrics['untouched_qpos_error'] <= 1e-9 and metrics['untouched_qvel_error'] <= 1e-9
                             and metrics['controller_history_error'] <= 1e-9 and metrics['solver_warmstart_error'] <= 1e-9 and metrics['joint_limits_passed'])
    return metrics

def score(observed, prediction):
    norm = float(np.linalg.norm(observed))
    error = float(np.linalg.norm(prediction - observed))
    cosine = float(observed @ prediction / max(norm * float(np.linalg.norm(prediction)), 1e-15))
    rel = error / max(norm, 1e-15)
    return dict(observed_m=observed.tolist(), predicted_m=prediction.tolist(), error_m=error,
                relative_error=rel, cosine=cosine, degenerate=norm < 1e-5,
                passed=bool(norm >= 1e-5 and cosine >= .8 and rel <= .5))

def summary(rows):
    return {'count': len(rows), 'passed': sum(x['passed'] for x in rows),
            'degenerate': sum(x['degenerate'] for x in rows),
            'median_error_m': float(np.median([x['error_m'] for x in rows])),
            'median_relative_error': float(np.median([x['relative_error'] for x in rows])),
            'p90_relative_error': float(np.quantile([x['relative_error'] for x in rows], .9))}

def run():
    start = time.monotonic()
    assert not (OUT / 'result.json').exists(), 'Preserve existing result; never resume a diagnosis'
    selection = read(OUT / 'selection.json')
    result = dict(state='RUNNING', policy_training_updates=0, seed=selection['seed'], selection=selection,
                  source_sha256=sha(Path(__file__)), protocol_sha256=sha(OUT / 'PROTOCOL.md'), rows=[], counts=COUNTS)
    env = None
    write(OUT / 'result.json', result)
    try:
        spec = importlib.util.spec_from_file_location('frozen_pilot', PILOT / 'run.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        core.bootstrap()
        import torch
        torch.set_num_threads(2)
        from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
        ckpt = PILOT / 'B0/model_final.pth'
        assert sha(ckpt) == selection['checkpoint_sha256']
        data = ROOT / 'praxis/data/lift/ph/low_dim_v15.hdf5'
        assert sha(data) == selection['dataset_sha256']
        policy, ckpt_dict = policy_from_checkpoint(ckpt_path=str(ckpt), verbose=False)
        env, _ = env_from_checkpoint(ckpt_dict=ckpt_dict, render=False, render_offscreen=False)
        def policy_action(obs):
            policy.start_episode()
            COUNTS['policy_calls'] += 1
            with torch.inference_mode():
                return np.clip(np.asarray(policy(obs)), -1, 1)
        with h5py.File(data, 'r') as f:
            for demo in selection['selected_demos']:
                d = f[f'data/{demo}']
                actions, states = d['actions'][:], d['states'][:]
                times = [int(frac * (len(actions) - 1)) for frac in selection['anchor_fractions']]
                assert len(set(times)) == 3, 'Predetermined anchors must be distinct'
                for t in times:
                    row = {'demo': demo, 't': t, 'split': 'identification' if demo in selection['identification_demos'] else 'heldout', 'branches': {}}
                    result['rows'].append(row)
                    variants = [('reference', None, 0, 'reference'), ('repeat', None, 0, 'reference')]
                    variants += [(f'{kind}_{axis}_{sign}', axis, -1 if sign == 'minus' else 1, kind)
                                 for kind in ['B', 'A', 'Pxyz', 'Pfull'] for axis in range(3) for sign in ['minus', 'plus']]
                    ref_action = None
                    for name, axis, sign, kind in variants:
                        stop_check()
                        np.random.seed(selection['seed'])
                        torch.manual_seed(selection['seed'])
                        env.reset_to({'model': d.attrs['model_file'], 'states': states[0]})
                        COUNTS['resets'] += 1
                        robot = env.env.robots[0]
                        sim = env.env.sim
                        ctrl = robot.composite_controller.part_controllers['right']
                        monitor = {'active': False, 'contacts': []}
                        original_step = sim.step
                        def instrumented_step():
                            original_step()
                            COUNTS['physics_steps'] += 1
                            if monitor['active']:
                                monitor['contacts'].extend(robot_contacts(sim, robot))
                        sim.step = instrumented_step
                        try:
                            ctrl.update_initial_joints(d['obs/robot0_joint_pos'][0])
                            for action in actions[:t]:
                                env.step(action)
                                COUNTS['prefix_actions'] += 1
                            ctrl.update(force=True)
                            anchor = snapshot(env, ctrl)
                            anchor_measure = measured(sim, ctrl)
                            intervention = None
                            if kind in ['A', 'Pxyz', 'Pfull']:
                                delta = np.zeros(3)
                                delta[axis] = sign * .005
                                intervention = shift_state(env, ctrl, delta)
                            obs = env.get_observation()
                            if ref_action is None:
                                ref_action = policy_action(obs)
                            action = ref_action.copy()
                            if kind == 'B':
                                action[axis] = np.clip(action[axis] + sign * .1, -1, 1)
                            elif kind in ['Pxyz', 'Pfull']:
                                new_action = policy_action(obs)
                                action[:3] = new_action[:3]
                                if kind == 'Pfull':
                                    action = new_action
                            before = snapshot(env, ctrl)
                            physical = measured(sim, ctrl)
                            initial_contacts = robot_contacts(sim, robot)
                            monitor['active'] = True
                            next_obs, _, _, _ = env.step(action)
                            COUNTS['probe_actions'] += 1
                            row['branches'][name] = dict(anchor=anchor, anchor_measure=anchor_measure,
                                before=before, before_measure=physical, intervention=intervention,
                                observation={k: np.asarray(v).tolist() for k, v in obs.items()},
                                action=action.tolist(), next_eef_m=np.asarray(next_obs['robot0_eef_pos']).tolist(),
                                initial_robot_contacts=initial_contacts, step_robot_contacts=monitor['contacts'])
                        finally:
                            sim.step = original_step
                        result['elapsed_seconds'] = time.monotonic() - start
                        write(OUT / 'result.json', result)
                    branches = row['branches']
                    ref, repeat = branches['reference'], branches['repeat']
                    anchor_error = max(difference(ref['anchor'], b['anchor']) for b in branches.values())
                    repeat_error = float(np.linalg.norm(np.asarray(ref['next_eef_m']) - repeat['next_eef_m']))
                    state_errors = [difference(branches[f'A_{axis}_{sign}']['before'], branches[f'{kind}_{axis}_{sign}']['before'])
                                    for axis in range(3) for sign in ['minus', 'plus'] for kind in ['Pxyz', 'Pfull']]
                    same_start_error = max([difference(ref['before'], b['before']) for n, b in branches.items() if n.startswith('B_')] + state_errors)
                    row['gates'] = dict(anchor_start_error_max=anchor_error, reference_repeat_error_m=repeat_error,
                                        same_probe_start_error_max=same_start_error,
                                        interventions_passed=all(b['intervention']['passed'] for b in branches.values() if b['intervention']),
                                        contact_free=all(not b['initial_robot_contacts'] and not b['step_robot_contacts'] for b in branches.values()))
                    row['gates']['passed'] = bool(anchor_error <= 1e-9 and repeat_error <= 1e-6 and same_start_error <= 1e-9
                                                   and row['gates']['interventions_passed'] and row['gates']['contact_free'])
                    print(f'{demo} t={t}: {json.dumps(row["gates"])}', flush=True)
                    write(OUT / 'result.json', result)
        if not all(r['gates']['passed'] for r in result['rows']):
            result.update(state='GATE_FAILED', decision='No A/B fitting or mechanism inference: physical validity gate failed; preserve outputs and do not loosen gates.')
            return 0
        fit_start = time.monotonic()
        old = np.asarray(read(SESSION.parent / 'offline.json')['dynamics_matrix'])
        partial = np.asarray(read(SESSION.parent / 'partial_action_calibration.json')['dynamics_matrix'])
        def central(row, kind, axis):
            minus, plus = [row['branches'][f'{kind}_{axis}_{sign}'] for sign in ['minus', 'plus']]
            dx = np.asarray(plus['before_measure']['eef_m']) - minus['before_measure']['eef_m']
            da = np.asarray(plus['action'])[:3] - np.asarray(minus['action'])[:3]
            dy = np.asarray(plus['next_eef_m']) - minus['next_eef_m']
            return dx, da, dy
        fit_rows = [r for r in result['rows'] if r['split'] == 'identification']
        Ax, Ay, Bx, By = [], [], [], []
        for r in fit_rows:
            for axis in range(3):
                dx, _, dy = central(r, 'A', axis)
                _, da, dyb = central(r, 'B', axis)
                Ax.append(dx); Ay.append(dy); Bx.append(da); By.append(dyb)
        A = np.linalg.lstsq(Ax, Ay, rcond=None)[0]
        B = np.linalg.lstsq(Bx, By, rcond=None)[0]
        assert np.linalg.matrix_rank(Ax) == np.linalg.matrix_rank(Bx) == 3
        result['identification'] = {'A': A.tolist(), 'B': B.tolist(), 'rows_each': len(Ax),
                                     'fit_seconds': time.monotonic() - fit_start}
        b_scores = {k: [] for k in ['expert_OLS', 'previous_partial', 'new_B']}
        a_scores = {k: [] for k in ['identity', 'new_A']}
        policy_scores = {kind: {k: [] for k in ['I_OLS', 'I_previous_partial', 'new_AB']} for kind in ['Pxyz', 'Pfull']}
        for row in [r for r in result['rows'] if r['split'] == 'heldout']:
            probes = []
            ref = row['branches']['reference']
            for axis in range(3):
                dx, _, dy = central(row, 'A', axis)
                for key, matrix in [('identity', np.eye(3)), ('new_A', A)]:
                    a_scores[key].append(score(dy, dx @ matrix))
                _, da, dy = central(row, 'B', axis)
                for key, matrix in [('expert_OLS', old), ('previous_partial', partial), ('new_B', B)]:
                    b_scores[key].append(score(dy, da @ matrix))
                for sign in ['minus', 'plus']:
                    for kind in ['Pxyz', 'Pfull']:
                        branch = row['branches'][f'{kind}_{axis}_{sign}']
                        delta = np.asarray(branch['before_measure']['eef_m']) - ref['before_measure']['eef_m']
                        da7 = np.asarray(branch['action']) - ref['action']
                        actual = np.asarray(branch['next_eef_m']) - ref['next_eef_m']
                        models = {'I_OLS': delta + da7[:3] @ old,
                                  'I_previous_partial': delta + da7[:3] @ partial,
                                  'new_AB': delta @ A + da7[:3] @ B}
                        rec = {'axis': axis, 'sign': sign, 'kind': kind, 'actual_delta_m': delta.tolist(),
                               'action_difference_7d': da7.tolist(),
                               'observed_one_step_ratio': float(np.linalg.norm(actual) / np.linalg.norm(delta)), 'scores': {}}
                        for key, predicted in models.items():
                            s = score(actual, predicted)
                            s['predicted_one_step_ratio'] = float(np.linalg.norm(predicted) / np.linalg.norm(delta))
                            policy_scores[kind][key].append(s); rec['scores'][key] = s
                        probes.append(rec)
            row['heldout_policy_probes'] = probes
        result['heldout'] = {'B': {k: summary(v) for k, v in b_scores.items()},
                             'A': {k: summary(v) for k, v in a_scores.items()},
                             'policy': {kind: {k: summary(v) for k, v in models.items()} for kind, models in policy_scores.items()}}
        ident = result['heldout']['A']['identity']
        result['identity_A_compatible_in_this_probe'] = ident['median_relative_error'] <= .1 and ident['p90_relative_error'] <= .2
        valid = result['heldout']['policy']['Pxyz']['new_AB']
        result['AB_local_prediction_gate'] = valid['passed'] / valid['count'] >= .8
        result.update(state='COMPLETE', decision='Local model diagnosis only; no automatic policy training or robust improvement claim.')
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc, InterruptedError) else 'FAILED', error=traceback.format_exc())
        traceback.print_exc()
        return 2
    finally:
        if env is not None:
            env.env.close()
        result['elapsed_seconds'] = time.monotonic() - start
        result['counts'] = COUNTS
        write(OUT / 'result.json', result)

if __name__ == '__main__':
    sys.exit(run())
