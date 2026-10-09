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

