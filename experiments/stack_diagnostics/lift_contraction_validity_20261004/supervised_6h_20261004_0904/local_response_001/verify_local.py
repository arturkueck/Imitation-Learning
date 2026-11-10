"""Verify fitted matrices by direct solve and held predictions from raw states."""
import hashlib,json,time
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=time.perf_counter();r=read(O/'result.json');a=read(O/'analysis_verification.json');v=read(O/'local_identification.json');c=read(O/'calibration.json')
assert v['raw_sha256']==a['raw_sha256']==sha(O/'result.json')
assert v['physical_audit_sha256']==sha(O/'analysis_verification.json')
repair=read(O/'analysis_repair_001/REPAIR.json')
assert sha(O/'analysis_repair_001/analyze_local.py')==v['source_sha256']==repair['repair_source_sha256']
A,fixed=np.asarray(c['A']),np.asarray(c['B7']);maximum=0.;checked=0;fits=0
for row,fit,audit in zip(r['rows'],v['rows'],a['physical_audits']):
    assert fit['domain_eligible']==audit['eligible']==row['gates']['passed']
    if not fit['domain_eligible']:
        assert not fit['identification_performed'];continue
    fits+=1;D=[];Y=[]
    for axis in range(7):
        p,m=[row['branches'][f'B_{axis}_{s}'] for s in ['plus','minus']]
        D.append(np.array(p['action'])-m['action']);Y.append(np.array(p['next_eef_m'])-m['next_eef_m'])
    D,Y=np.array(D),np.array(Y);local=np.linalg.solve(D,Y)
    assert np.max(np.abs(local-fit['B_local']))<=1e-12
    assert fit['rank']==7 and np.array_equal(D,fit['identification_action_difference_matrix']) and np.array_equal(Y,fit['identification_response_matrix_m'])
    ref=row['branches']['reference']
    for axis in range(3):
        for sign in ['minus','plus']:
            b=row['branches'][f'Pfull_{axis}_{sign}'];p=next(p for p in v['conditional_policy_raw'] if p['demo']==row['demo'] and p['t']==row['t'] and p['axis']==axis and p['sign']==sign)
            dx=np.array(b['before_measure']['eef_m'])-ref['before_measure']['eef_m'];da=np.array(b['action'])-ref['action'];dy=np.array(b['next_eef_m'])-ref['next_eef_m']
            observed=np.linalg.norm(dy)/np.linalg.norm(dx)
            preds=dict(A_B7_fixed=dx@A+da@fixed,A_B7_local=dx@A+da@local,I_B7_local=dx+da@local)
            for name,vector in preds.items():
                saved=p['models'][name];ratio=np.linalg.norm(vector)/np.linalg.norm(dx)
                error=max(abs(ratio-saved['predicted_ratio']),abs(abs(ratio-observed)-saved['absolute_ratio_error']),np.max(np.abs(vector-saved['predicted_vector_m'])))
                maximum=max(maximum,float(error));assert error<=1e-12
                assert saved['false_pass']==bool(ratio<.99 and observed>=.99)
                assert saved['false_penalty']==bool(ratio>=.99 and observed<.99)
            checked+=1
assert fits==v['local_identification_fits']==a['eligible_anchors'] and checked==fits*6
for name,aggregate in v['policy'].items():
    probes=v['conditional_policy_raw'];assert aggregate['cases']==checked
    assert aggregate['false_pass']==sum(p['models'][name]['false_pass'] for p in probes)
    assert aggregate['false_penalty']==sum(p['models'][name]['false_penalty'] for p in probes)
    if probes:assert aggregate['median_absolute_ratio_error']==float(np.median([p['models'][name]['absolute_ratio_error'] for p in probes]))
result=dict(state='INDEPENDENT_LOCAL_FITS_AND_HELD_PREDICTIONS_VERIFIED',local_fits_checked=fits,held_probes_checked=checked,maximum_numeric_difference=maximum,
            identification_and_held_branch_names_disjoint=True,local_analysis_sha256=sha(O/'local_identification.json'),physical_audit_sha256=sha(O/'analysis_verification.json'),
            raw_sha256=sha(O/'result.json'),source_sha256=sha(Path(__file__)),elapsed_seconds=time.perf_counter()-start,
            optimizer_updates=0,new_physics_steps=0)
with (O/'local_verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
