"""Repair postprocessing only; immutable completed physical rollouts are inputs."""
import json
import hashlib
from pathlib import Path
import time
import numpy as np

OUT = Path(__file__).resolve().parent
RAW = OUT.parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    with p.open('x', encoding='utf-8') as f: json.dump(value, f, indent=2, allow_nan=False)

start = time.perf_counter()
r = read(RAW/'result.json'); s = read(RAW/'selection.json'); c = read(RAW/'calibration.json')
assert r['state'] == 'FAILED' and "multiple values for keyword argument 'predicted_ratio'" in r['error']
assert read(RAW/'verification.json')['state'] == 'VERIFIED'
assert read(RAW/'verification.json')['branches'] == 312
assert read(RAW/'verification.json')['result_sha256'] == sha(RAW/'result.json')
assert r['policy_training_updates'] == r['fit_updates'] == 0
assert len(r['rows']) == 12 and all(x['gates']['passed'] for x in r['rows'])
assert set(x['demo'] for x in r['rows']) == set(s['selected_demos'])
assert not set(s['selected_demos']) & (set(s['excluded_prior_demos']) | set(c['fit_demos']))
A, B3, B7, K = [np.array(c[k]) for k in ['A','B3','B7','K_OLS']]
assert np.allclose(B3, B7[:3], atol=1e-12, rtol=0)
for name, digest in c['calibration_sources'].items(): assert sha(Path(name)) == digest
groups = {arm: [] for arm in s['arms']}; pairs = []; cases = []; numerical_errors = []
for row in r['rows']:
    b = row['branches']; ref = b['reference']; anchor = {arm: [] for arm in s['arms']}
    assert len(b) == 26
    for axis in range(3):
        for sign in ['minus','plus']:
            common = b[f'C0_{axis}_{sign}']
            base = np.array(common['base_policy_action'])
            reference = np.array(ref['action'])
            da = base-reference
            for arm in s['arms']:
                branch = b[f'{arm}_{axis}_{sign}']; info = branch['correction']
                assert branch['base_policy_action'] == common['base_policy_action']
                assert branch['action'][3:] == branch['base_policy_action'][3:]
                delta = np.array(branch['before_measure']['eef_m'])-ref['before_measure']['eef_m']
                assert abs(np.linalg.norm(delta)-s['physical_eef_delta_m']) < 1e-6
                if arm == 'C1': e, G = delta+da[:3]@K, K
                elif arm == 'C2': e, G = delta@A+da[:3]@B3, B3
                else: e, G = delta@A+da@B7, B3
                radius = s['design_target_ratio']*np.linalg.norm(delta)
                ideal = np.zeros(3)
                if arm != 'C0' and np.linalg.norm(e)>radius:
                    ideal = np.linalg.lstsq(G.T, (radius/np.linalg.norm(e)-1)*e, rcond=None)[0]
                u = ideal.copy(); capped = np.linalg.norm(u)>s['correction_norm_limit']
                if capped: u *= s['correction_norm_limit']/np.linalg.norm(u)
                proposed = base.copy(); proposed[:3] += u
                action = np.clip(proposed,-1,1); actual_u = action[:3]-base[:3]
                prediction = e+actual_u@G
                predicted_ratio = float(np.linalg.norm(prediction)/np.linalg.norm(delta))
                errors = [np.max(np.abs(action-branch['action'])), np.max(np.abs(ideal-info['ideal_u_xyz'])),
                          np.max(np.abs(actual_u-info['actual_u_xyz'])), np.max(np.abs(e-info['model_before_error_m'])),
                          np.max(np.abs(prediction-info['predicted_after_error_m'])), abs(predicted_ratio-info['predicted_ratio'])]
                numerical_errors.extend(float(x) for x in errors)
                assert max(errors)<1e-9, (arm, row['demo'], row['t'], errors)
                assert bool(capped)==info['norm_capped']
                assert bool(np.any(proposed!=action))==info['action_clipped']
                assert bool(not np.any(actual_u))==info['zero_correction']
                assert bool(np.linalg.norm(prediction)<=radius+1e-9)==info['predicted_design_target_reached']
                actual_error = np.array(branch['next_eef_m'])-ref['next_eef_m']
                ratio = float(np.linalg.norm(actual_error)/np.linalg.norm(delta))
                rec = {**info, 'demo':row['demo'], 't':row['t'], 'arm':arm, 'axis':axis, 'sign':sign,
                       'observed_ratio':ratio, 'absolute_ratio_error':abs(ratio-predicted_ratio),
                       'actual_next_error_m':actual_error.tolist(), 'eval_target_reached':ratio<=s['evaluation_ratio_threshold']}
                groups[arm].append(rec); anchor[arm].append(rec); cases.append(rec)
    errors = {arm:float(np.median([x['absolute_ratio_error'] for x in anchor[arm]])) for arm in ['C2','C3']}
    pairs.append(dict(demo=row['demo'], t=row['t'], median_ratio_errors=errors, C3_better=errors['C3']<errors['C2']))
summaries = {}
for arm, rows in groups.items():
    assert len(rows)==72
    summaries[arm] = dict(cases=len(rows), eval_target_reached=sum(x['eval_target_reached'] for x in rows),
                         median_observed_ratio=float(np.median([x['observed_ratio'] for x in rows])),
                         median_absolute_ratio_error=float(np.median([x['absolute_ratio_error'] for x in rows])),
                         median_correction_norm=float(np.median([x['correction_norm'] for x in rows])),
                         capped=sum(x['norm_capped'] for x in rows), clipped=sum(x['action_clipped'] for x in rows),
                         zero_corrections=sum(x['zero_correction'] for x in rows),
                         predicted_design_target_reached=sum(x['predicted_design_target_reached'] for x in rows),
                         total_solve_seconds=sum(x['solve_seconds'] for x in rows))
e2,e3 = [summaries[x]['median_absolute_ratio_error'] for x in ['C2','C3']]
reduction = 1-e3/max(e2,1e-15); better = sum(x['C3_better'] for x in pairs)
secondary = {}
for arm in ['C1','C2','C3']:
    differences = np.array([x['observed_ratio']-z['observed_ratio'] for x,z in zip(groups[arm],groups['C0'])])
    secondary[arm] = dict(better_than_C0=int((differences<0).sum()), worse_than_C0=int((differences>0).sum()),
                         equal_C0=int((differences==0).sum()), median_paired_ratio_difference=float(np.median(differences)))
output = dict(state='ANALYSIS_REPAIRED_VERIFIED', raw_worker_state=r['state'], physical_audit_state='VERIFIED',
              reason='Duplicate predicted_ratio keyword in final dict construction; repair reprocesses stored raw branches only.',
              rerun_physical_branches=0, new_policy_training_updates=0, new_fit_updates=0,
              inputs={name:sha(RAW/name) for name in ['result.json','verification.json','selection.json','calibration.json','source_hashes.json','supervisor_result.json']},
              source_sha256=sha(Path(__file__)), summaries=summaries, secondary_vs_C0=secondary,
              primary=dict(relative_reduction=reduction, better_anchors=better, total_anchors=12,
                           predefined_gate_passed=bool(reduction>=.2 and better>=8), paired_anchor_results=pairs),
              max_recomputed_correction_error=max(numerical_errors), cases=cases,
              counts=r['counts'], original_worker_elapsed_seconds=r['elapsed_seconds'],
              analysis_elapsed_seconds=time.perf_counter()-start,
              interpretation='Oracle one-step corrections on four early free demos; no task recovery or BC improvement proof.')
save(OUT/'analysis_result.json',output)
print(json.dumps({k:v for k,v in output.items() if k not in ['cases','inputs']},indent=2))
