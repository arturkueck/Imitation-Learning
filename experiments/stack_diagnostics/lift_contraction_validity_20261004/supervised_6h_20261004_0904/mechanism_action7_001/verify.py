"""Independent physical-state/provenance audit after the bounded worker exits."""
import hashlib
import json
from pathlib import Path
import numpy as np
import psutil

OUT = Path(__file__).resolve().parent

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def diff(a, b):
    if isinstance(a, dict):
        assert set(a) == set(b)
        return max([diff(a[k], b[k]) for k in a] + [0.])
    if a is None or isinstance(a, (str, bool)):
        return 0. if a == b else float('inf')
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b)), initial=0))

def alive(identity):
    try:
        p = psutil.Process(identity['pid'])
        return abs(p.create_time() - identity['create_time']) < .1 and p.is_running()
    except psutil.NoSuchProcess:
        return False

result = read(OUT / 'result.json')
supervisor = read(OUT / 'supervisor_result.json')
launch = read(OUT / 'launch.json')
assert supervisor['worker_job_closed'] and supervisor['supervisor_exiting']
assert not alive(supervisor['worker'])
assert not alive({'pid': launch['supervisor_pid'], 'create_time': launch['supervisor_create_time']})
for name, digest in read(OUT / 'source_hashes.json').items():
    assert sha(OUT / name) == digest, name
assert result['policy_training_updates'] == 0
checks = []
for row in result['rows']:
    ref = row['branches']['reference']
    for name, branch in row['branches'].items():
        after, before = branch['before'], branch['anchor']
        extra_fields = [k for k in before['sim'] if k not in ['qpos', 'qvel']]
        untouched = max([diff(before['sim'][k], after['sim'][k]) for k in extra_fields] + [0.])
        gripper = diff(before['gripper_memory'], after['gripper_memory'])
        gripper_controller = diff(before['controllers']['right_gripper'], after['controllers']['right_gripper'])
        obs = branch['observation']
        eef_error = float(np.linalg.norm(np.asarray(obs['robot0_eef_pos']) - branch['before_measure']['eef_m']))
        object_relative_error = float(np.linalg.norm(np.asarray(obs['object'])[-3:] - (np.asarray(obs['object'])[:3] - obs['robot0_eef_pos'])))
        if branch['intervention']:
            obs_object_error = diff(ref['observation']['object'][:7], obs['object'][:7])
            q1, q2 = np.asarray(ref['observation']['robot0_eef_quat']), np.asarray(obs['robot0_eef_quat'])
            angle = float(2 * np.arccos(np.clip(abs(q1 @ q2) / (np.linalg.norm(q1) * np.linalg.norm(q2)), 0, 1)))
        else:
            obs_object_error = 0.
            angle = 0.
        passed = untouched <= 1e-9 and gripper <= 1e-9 and gripper_controller <= 1e-9 and eef_error <= 1e-9 and object_relative_error <= 1e-9 and obs_object_error <= 1e-9 and angle <= 1e-4
        checks.append(dict(demo=row['demo'], t=row['t'], branch=name, passed=bool(passed),
                           untouched_simulator_error=untouched, gripper_error=gripper,
                           gripper_controller_error=gripper_controller, observation_eef_error_m=eef_error,
                           object_relative_consistency_error_m=object_relative_error,
                           object_pose_error=obs_object_error, observed_orientation_error_rad=angle))
audit = dict(state='VERIFIED' if all(x['passed'] for x in checks) else 'PHYSICAL_AUDIT_FAILED',
             result_sha256=sha(OUT / 'result.json'), supervisor_exited=True, worker_exited=True,
             source_hashes_verified=True, policy_training_updates=0, branches=len(checks),
             source_sha256=sha(Path(__file__)), checks=checks,
             no_mechanism_claim_if_failed=True)
assert not (OUT / 'verification.json').exists()
with (OUT / 'verification.json').open('x', encoding='utf-8') as f:
    json.dump(audit, f, indent=2, allow_nan=False)
print(json.dumps({k: v for k, v in audit.items() if k != 'checks'}, indent=2))
