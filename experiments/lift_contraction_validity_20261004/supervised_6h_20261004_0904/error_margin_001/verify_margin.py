"""Independent direct linear equations and vector/norm/decision reconstruction."""
import json,hashlib,time
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent; S=O.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=time.perf_counter(); r=read(O/'result.json'); a=read(O/'analysis_verification.json'); f=read(O/'filter_analysis.json'); m=read(O/'margin_analysis.json'); spec=read(O/'margin_spec.json')
assert m['raw_sha256']==a['raw_sha256']==f['raw_sha256']==sha(O/'result.json')
assert m['frozen_margin_spec_sha256']==sha(O/'margin_spec.json')
old=read(S/Path(spec['calibration_source'])); empirical=[]
for c in old['conditional_policy_raw']:
    y=np.asarray(c['observed_vector_m']); p=np.asarray(c['models']['A_B7_local']['predicted_vector_m'])
    empirical.append(float(np.linalg.norm(y-p)/np.linalg.norm(c['delta_m'])))
assert max(empirical)==spec['empirical_normalized_vector_error_max']; epsilon=max(empirical)
A=np.asarray(read(O/'calibration.json')['A']); cases=[]; matrix_errors=[]; ratio_errors=[]; error_errors=[]
local=read(O/'local_identification.json'); localrows={(x['demo'],x['t']):x for x in local['rows']}
for row,physical in zip(r['rows'],a['physical_audits']):
    if not physical['eligible']:continue
    D=[];Y=[]
    for axis in range(7):
        minus=row['branches'][f'B_{axis}_minus']; plus=row['branches'][f'B_{axis}_plus']
        D.append(np.asarray(plus['action'])-minus['action']);Y.append(np.asarray(plus['next_eef_m'])-minus['next_eef_m'])
    B=np.linalg.solve(np.asarray(D),np.asarray(Y)); stored=localrows[(row['demo'],row['t'])]
    matrix_errors.append(float(np.max(np.abs(B-np.asarray(stored['B_local'])))))
    ref=row['branches']['reference']
    for axis in range(3):
        for sign in ['minus','plus']:
            p=row['branches'][f'Pfull_{axis}_{sign}']; delta=np.asarray(p['before_measure']['eef_m'])-ref['before_measure']['eef_m']
            da=np.asarray(p['action'])-ref['action']; observed=np.asarray(p['next_eef_m'])-ref['next_eef_m']
            prediction=delta@A+da@B; scale=float(np.linalg.norm(delta)); ratio=float(np.linalg.norm(prediction)/scale)
            error=float(np.linalg.norm(prediction-observed)/scale); actual=float(np.linalg.norm(observed)/scale)
            index=len(cases); c=m['cases'][index]; assert (c['demo'],c['t'],c['axis'],c['sign'])==(row['demo'],row['t'],axis,sign)
            ratio_errors.append(abs(c['raw_ratio']-ratio)); error_errors.append(abs(c['normalized_vector_error']-error))
            assert abs(c['observed_ratio']-actual)<1e-12 and abs(c['upper_ratio']-(ratio+epsilon))<1e-12
            assert c['raw_safe']==(ratio<.99) and c['upper_safe']==(ratio+epsilon<.99) and c['observed_safe']==(actual<.99)
            assert c['bound_violated']==(error>epsilon)
            cases.append(dict(raw=ratio<.99,upper=ratio+epsilon<.99,actual=actual<.99,error=error))
assert len(cases)==m['conditional_policy_cases']
assert max(matrix_errors,default=0)<1e-12 and max(ratio_errors,default=0)<1e-12 and max(error_errors,default=0)<1e-12
for name in ['raw','upper']:
    counts=dict(true_safe=sum(c[name] and c['actual'] for c in cases),false_safe=sum(c[name] and not c['actual'] for c in cases),
                false_reject=sum(not c[name] and c['actual'] for c in cases),true_reject=sum(not c[name] and not c['actual'] for c in cases))
    assert counts==m['primary'][name]
assert sum(c['error']>epsilon for c in cases)==m['primary']['bound_violations']
result=dict(state='DIRECT_SOLVE_AND_MARGIN_DECISIONS_INDEPENDENTLY_VERIFIED',local_fits_verified=len(matrix_errors),policy_cases_verified=len(cases),
            maximum_B_difference=max(matrix_errors,default=0),maximum_ratio_difference=max(ratio_errors,default=0),maximum_error_difference=max(error_errors,default=0),
            raw_sha256=sha(O/'result.json'),margin_analysis_sha256=sha(O/'margin_analysis.json'),source_sha256=sha(Path(__file__)),
            policy_updates=0,new_physics_steps=0,elapsed_seconds=time.perf_counter()-start)
with (O/'margin_verification.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2,allow_nan=False)
print(json.dumps(result,indent=2))
