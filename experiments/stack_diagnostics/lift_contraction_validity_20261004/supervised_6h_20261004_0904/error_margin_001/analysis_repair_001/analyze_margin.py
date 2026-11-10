"""Frozen old-Train error envelope against new held intervention outcomes."""
import json, hashlib, time
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent.parent; S=O.parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def summary(cases,planned=72):
    return dict(conditional_cases=len(cases),planned_cases=planned,
                bound_violations=sum(x['bound_violated'] for x in cases),
                raw=dict(true_safe=sum(x['raw_safe'] and x['observed_safe'] for x in cases),false_safe=sum(x['raw_safe'] and not x['observed_safe'] for x in cases),
                         false_reject=sum(not x['raw_safe'] and x['observed_safe'] for x in cases),true_reject=sum(not x['raw_safe'] and not x['observed_safe'] for x in cases)),
                upper=dict(true_safe=sum(x['upper_safe'] and x['observed_safe'] for x in cases),false_safe=sum(x['upper_safe'] and not x['observed_safe'] for x in cases),
                           false_reject=sum(not x['upper_safe'] and x['observed_safe'] for x in cases),true_reject=sum(not x['upper_safe'] and not x['observed_safe'] for x in cases)),
                maximum_normalized_vector_error=max([x['normalized_vector_error'] for x in cases],default=None),
                median_absolute_ratio_error=float(np.median([x['absolute_ratio_error'] for x in cases])) if cases else None)
start=time.perf_counter(); spec=read(O/'margin_spec.json'); local=read(O/'local_identification.json'); audit=read(O/'analysis_verification.json'); filters=read(O/'filter_analysis.json')
calpath=S/Path(spec['calibration_source']); old=read(calpath)
assert sha(calpath)==spec['calibration_source_sha256'] and sha(S/'local_response_001/result.json')==spec['calibration_raw_sha256']
assert local['raw_sha256']==audit['raw_sha256']==filters['raw_sha256']==sha(O/'result.json')
errors=[x['models']['A_B7_local']['vector_error_m']/np.linalg.norm(x['delta_m']) for x in old['conditional_policy_raw']]
assert len(errors)==48 and max(errors)==spec['empirical_normalized_vector_error_max']
epsilon=spec['empirical_normalized_vector_error_max']; threshold=spec['threshold']; cases=[]
masks={(r['demo'],r['t']):r for r in filters['rows']}
for c in local['conditional_policy_raw']:
    m=c['models']['A_B7_local']; error=m['vector_error_m']/np.linalg.norm(c['delta_m']); pred=m['predicted_ratio']; observed=c['observed_ratio']
    assert abs(pred-observed)<=error+1e-12
    cases.append(dict(demo=c['demo'],t=c['t'],fraction=c['fraction'],axis=c['axis'],sign=c['sign'],
                      raw_ratio=pred,upper_ratio=pred+epsilon,observed_ratio=observed,normalized_vector_error=float(error),
                      absolute_ratio_error=m['absolute_ratio_error'],bound_violated=bool(error>epsilon),
                      raw_safe=pred<threshold,upper_safe=pred+epsilon<threshold,observed_safe=observed<threshold,
                      masks=masks[(c['demo'],c['t'])]['masks']))
assert len(cases)==6*audit['eligible_anchors']; primary=summary(cases)
secondary={name:dict(domain_anchors=filters['masks'][name],policy_conditional=summary([c for c in cases if c['masks'][name]]),
                      nominally_accepted_but_dynamic_invalid_anchors=filters['masks'][name]['false_accept']) for name in ['M0','M2']}
gate=primary['bound_violations']==0 and primary['upper']['false_safe']==0 and primary['upper']['true_safe']>=1
result=dict(state='EMPIRICAL_MARGIN_DEVELOPMENT_GATE_PASSED' if gate else 'EMPIRICAL_MARGIN_DEVELOPMENT_GATE_FAILED',
            epsilon_train=epsilon,threshold=threshold,calibration_cases=48,planned_policy_cases=72,conditional_policy_cases=len(cases),
            unscored_due_domain=72-len(cases),planned_anchors=12,eligible_anchors=audit['eligible_anchors'],
            local_identification_fits=local['local_identification_fits'],coefficients_per_fit=21,policy_training_updates=0,
            primary=primary,strata={str(fr):summary([c for c in cases if c['fraction']==fr],planned=24) for fr in [.1,.5,.85]},secondary_masks=secondary,
            cases=cases,raw_sha256=sha(O/'result.json'),physical_audit_sha256=sha(O/'analysis_verification.json'),
            local_analysis_sha256=sha(O/'local_identification.json'),filter_analysis_sha256=sha(O/'filter_analysis.json'),
            frozen_margin_spec_sha256=sha(O/'margin_spec.json'),old_calibration_sha256=sha(calpath),source_sha256=sha(Path(__file__)),
            elapsed_seconds=time.perf_counter()-start,new_physics_steps=0,
            decision='Finite empirical error envelope only; no general guarantee or training approval. No enlargement from new outcomes, no new seed or threshold sweep.')
with (Path(__file__).resolve().parent/'margin_analysis.json').open('x',encoding='utf-8') as f: json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
