"""Separate nominal-action identification versus held intervention responses."""
import hashlib,json,time
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def central(row,kind,axis):
    m,p=[row['branches'][f'{kind}_{axis}_{sign}'] for sign in ['minus','plus']]
    return np.asarray(p['action'])-m['action'],np.asarray(p['next_eef_m'])-m['next_eef_m']
def summary(cases,model):
    errors=[x['models'][model]['absolute_ratio_error'] for x in cases]
    return dict(cases=len(cases),median_absolute_ratio_error=float(np.median(errors)) if errors else None,
                p90_absolute_ratio_error=float(np.quantile(errors,.9)) if errors else None,
                observed_below_threshold=sum(x['observed_ratio']<.99 for x in cases),
                predicted_below_threshold=sum(x['models'][model]['predicted_ratio']<.99 for x in cases),
                false_pass=sum(x['models'][model]['false_pass'] for x in cases),
                false_penalty=sum(x['models'][model]['false_penalty'] for x in cases))
start=time.perf_counter();r=read(O/'result.json');a=read(O/'analysis_verification.json');sel=read(O/'selection.json');cal=read(O/'calibration.json')
assert a['raw_sha256']==sha(O/'result.json') and a['source_hashes_verified']
A,B7=np.asarray(cal['A']),np.asarray(cal['B7']);models=['A_B7_fixed','A_B7_local','I_B7_local']
rows=[];cases=[];fits=0
for row,audit in zip(r['rows'],a['physical_audits']):
    assert row['demo']==audit['demo'] and row['t']==audit['t'] and row['history']=='H_reset'
    info=dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],history=row['history'],domain_eligible=audit['eligible'])
    if not audit['eligible']:
        info.update(identification_performed=False,reason='Contact or physical gate failed; no response-fit score assigned.')
        rows.append(info);continue
    D,Y=map(np.asarray,zip(*[central(row,'B',axis) for axis in range(7)]))
    local,residuals,rank,singular=np.linalg.lstsq(D,Y,rcond=None)
    assert rank==7,'Identification rank failed: do not infer a 7D response'
    fits+=1
    # Identifying equations are not an independent model test.
    info.update(identification_performed=True,identification_action_difference_matrix=D.tolist(),identification_response_matrix_m=Y.tolist(),
                B_local=local.tolist(),rank=int(rank),singular_values=singular.tolist(),condition_number=float(singular[0]/singular[-1]),
                nominal_identification_residual_not_validation_m=float(np.linalg.norm(D@local-Y)),
                clipped_identification_branches=sum(abs(b['actual_action_difference'][b['requested_component']])<.1-1e-12 for n,b in row['branches'].items() if n.startswith('B_')),
                training_updates=0)
    ref=row['branches']['reference'];here=[]
    for axis in range(3):
        for sign in ['minus','plus']:
            p=row['branches'][f'Pfull_{axis}_{sign}'];z=row['branches'][f'A_{axis}_{sign}']
            delta=np.asarray(p['before_measure']['eef_m'])-ref['before_measure']['eef_m'];da=np.asarray(p['action'])-ref['action']
            observed=np.asarray(p['next_eef_m'])-ref['next_eef_m'];observed_ratio=float(np.linalg.norm(observed)/np.linalg.norm(delta))
            # Also store the separately observed open-state response. It is a
            # diagnostic of joint linearity; not a fourth fitted primary model.
            open_state=np.asarray(z['next_eef_m'])-ref['next_eef_m']
            predictions={'A_B7_fixed':delta@A+da@B7,'A_B7_local':delta@A+da@local,'I_B7_local':delta+da@local}
            measures={}
            for name,pred in predictions.items():
                ratio=float(np.linalg.norm(pred)/np.linalg.norm(delta))
                measures[name]=dict(predicted_vector_m=pred.tolist(),predicted_ratio=ratio,absolute_ratio_error=abs(ratio-observed_ratio),
                                    vector_error_m=float(np.linalg.norm(pred-observed)),false_pass=ratio<.99 and not observed_ratio<.99,
                                    false_penalty=not ratio<.99 and observed_ratio<.99)
            probe=dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],axis=axis,sign=sign,delta_m=delta.tolist(),action_difference_7d=da.tolist(),
                       observed_vector_m=observed.tolist(),observed_ratio=observed_ratio,models=measures,
                       measured_open_state_response_m=open_state.tolist(),
                       local_joint_linearity_residual_m=float(np.linalg.norm(observed-(open_state+da@local))),
                       fixed_joint_linearity_residual_m=float(np.linalg.norm(observed-(open_state+da@B7))),
                       frozen_A_open_state_error_m=float(np.linalg.norm(open_state-delta@A)))
            cases.append(probe);here.append(probe)
    info['policy']=dict((m,summary(here,m)) for m in models)
    diff=info['policy']['A_B7_local']['median_absolute_ratio_error']-info['policy']['A_B7_fixed']['median_absolute_ratio_error']
    info.update(primary_local_minus_fixed_median_ratio_error=diff,primary_local_better=diff<0,primary_local_equal=diff==0)
    rows.append(info)
eligible=[x for x in rows if x['identification_performed']];assert fits==a['eligible_anchors']
strata={}
for fraction in sel['anchor_fractions']:
    group=[x for x in eligible if x['fraction']==fraction];probes=[x for x in cases if x['fraction']==fraction]
    strata[str(fraction)]=dict(planned_anchors=4,eligible_anchors=len(group),planned_policy_probes=24,conditional_policy_probes=len(probes),
                              better=sum(x['primary_local_better'] for x in group),equal=sum(x['primary_local_equal'] for x in group),
                              worse=sum(not x['primary_local_better'] and not x['primary_local_equal'] for x in group),
                              policy={m:summary(probes,m) for m in models})
result=dict(state='LOCAL_IDENTIFICATION_AND_HELD_RESPONSE_VERIFIED',domain_state=a['state'],planned_anchors=12,eligible_anchors=len(eligible),
            local_identification_fits=fits,coefficients_per_fit=21,optimizer_updates=0,policy_training_updates=0,
            primary_better=sum(x['primary_local_better'] for x in eligible),primary_equal=sum(x['primary_local_equal'] for x in eligible),
            primary_worse=sum(not x['primary_local_better'] and not x['primary_local_equal'] for x in eligible),
            policy={m:summary(cases,m) for m in models},strata=strata,rows=rows,conditional_policy_raw=cases,
            median_local_joint_linearity_residual_m=float(np.median([x['local_joint_linearity_residual_m'] for x in cases])) if cases else None,
            median_fixed_joint_linearity_residual_m=float(np.median([x['fixed_joint_linearity_residual_m'] for x in cases])) if cases else None,
            median_frozen_A_open_state_error_m=float(np.median([x['frozen_A_open_state_error_m'] for x in cases])) if cases else None,
            raw_sha256=sha(O/'result.json'),physical_audit_sha256=sha(O/'analysis_verification.json'),source_sha256=sha(Path(__file__)),
            elapsed_seconds=time.perf_counter()-start,new_physics_steps=0,
            limitation='Privileged per-anchor simulator identification; no original expert history, policy improvement, independent training seed, or universal stability claim.')
with (O/'local_identification.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','conditional_policy_raw']},indent=2))
