"""Reconstruct the primary outcome directly from saved physical/action responses."""
import hashlib
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
r = read(OUT / 'result.json')
assert r['state'] == 'COMPLETE' and read(OUT / 'verification.json')['state'] == 'VERIFIED'
assert len(r['rows']) == 12 and all(x['gates']['passed'] for x in r['rows'])
selection = read(OUT / 'selection.json')
assert not set(selection['selected_demos']) & set(selection['excluded_prior_demos'])
assert not set(selection['identification_demos']) & set(selection['heldout_demos'])
assert all(len(x['branches']) == 34 for x in r['rows'])
steps = int(r['environment']['control_timestep'] / r['environment']['model_timestep'])
assert r['counts']['physics_steps'] == steps * (r['counts']['prefix_actions'] + r['counts']['probe_actions'])
Ax, Ay, Bx, By = [], [], [], []
for row in r['rows']:
    if row['split'] != 'identification':
        continue
    for axis in range(7):
        lo, hi = [row['branches'][f'B_{axis}_{s}'] for s in ['minus', 'plus']]
        Bx.append(np.asarray(hi['action']) - lo['action'])
        By.append(np.asarray(hi['next_eef_m']) - lo['next_eef_m'])
    for axis in range(3):
        lo, hi = [row['branches'][f'A_{axis}_{s}'] for s in ['minus', 'plus']]
        Ax.append(np.asarray(hi['before_measure']['eef_m']) - lo['before_measure']['eef_m'])
        Ay.append(np.asarray(hi['next_eef_m']) - lo['next_eef_m'])
A, B7 = np.linalg.lstsq(Ax, Ay, rcond=None)[0], np.linalg.lstsq(Bx, By, rcond=None)[0]
assert np.linalg.matrix_rank(Bx) == 7
np.testing.assert_allclose(A, r['identification']['A'], rtol=0, atol=1e-12)
np.testing.assert_allclose(B7, r['identification']['B7'], rtol=0, atol=1e-12)
np.testing.assert_allclose(B7[:3], r['identification']['B3'], rtol=0, atol=1e-12)
all3, all7, paired, contributions = [], [], [], []
for row in r['rows']:
    if row['split'] != 'heldout':
        continue
    ref = row['branches']['reference']; errors3, errors7 = [], []
    for axis in range(3):
        for sign in ['minus', 'plus']:
            b = row['branches'][f'Pfull_{axis}_{sign}']
            delta = np.asarray(b['before_measure']['eef_m']) - ref['before_measure']['eef_m']
            da = np.asarray(b['action']) - ref['action']
            observed = np.asarray(b['next_eef_m']) - ref['next_eef_m']
            obs_ratio = np.linalg.norm(observed) / np.linalg.norm(delta)
            prediction3 = delta @ A + da[:3] @ B7[:3]
            prediction7 = delta @ A + da @ B7
            errors3.append(abs(obs_ratio - np.linalg.norm(prediction3) / np.linalg.norm(delta)))
            errors7.append(abs(obs_ratio - np.linalg.norm(prediction7) / np.linalg.norm(delta)))
            contributions.append(dict(rotation_m=float(np.linalg.norm(da[3:6] @ B7[3:6])), gripper_m=float(np.linalg.norm(da[6:] @ B7[6:]))))
    all3.extend(errors3); all7.extend(errors7)
    paired.append(dict(demo=row['demo'], t=row['t'], B7_better=bool(np.median(errors7) < np.median(errors3))))
e3, e7 = float(np.median(all3)), float(np.median(all7))
assert abs(e3 - r['primary']['median_ratio_error_B3']) < 1e-12
assert abs(e7 - r['primary']['median_ratio_error_B7']) < 1e-12
better = sum(p['B7_better'] for p in paired)
gate = bool(1 - e7 / e3 >= .2 and better >= 4)
assert gate == r['primary']['predefined_gate_passed'] and better == r['primary']['better_anchors']
value = dict(state='VERIFIED', primary_recomputed=True, identification_rank=7, no_fit_heldout_overlap=True,
             primary_gate=gate, better_anchors=better, source_result_sha256=digest(OUT / 'result.json'),
             audit_source_sha256=digest(Path(__file__)), policy_training_updates=0,
             median_modeled_rotation_contribution_m=float(np.median([x['rotation_m'] for x in contributions])),
             median_modeled_gripper_contribution_m=float(np.median([x['gripper_m'] for x in contributions])),
             additional_component_decomposition_exploratory=True)
with (OUT / 'prediction_verification.json').open('x', encoding='utf-8') as f:
    json.dump(value, f, indent=2)
print(json.dumps(value, indent=2))
