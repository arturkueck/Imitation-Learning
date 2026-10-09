"""Independent pre-response mask classification from contact lists and state audit."""
import json,hashlib,time
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def diff(a,b):
    if isinstance(a,dict):
        assert set(a)==set(b);return max([diff(a[k],b[k]) for k in a]+[0.])
    if a is None or isinstance(a,(str,bool)):return 0. if a==b else float('inf')
    return float(np.max(np.abs(np.asarray(a)-np.asarray(b)),initial=0))
def summary(rows,mask):
    technical=[x for x in rows if x['technical_passed']]
    return dict(planned_anchors=len(rows),technical_failed=len(rows)-len(technical),accepted=sum(x['masks'][mask] for x in technical),
                rejected=sum(not x['masks'][mask] for x in technical),true_accept=sum(x['masks'][mask] and x['dynamic_domain_eligible'] for x in technical),
                false_accept=sum(x['masks'][mask] and not x['dynamic_domain_eligible'] for x in technical),
                false_reject=sum(not x['masks'][mask] and x['dynamic_domain_eligible'] for x in technical),
                true_reject=sum(not x['masks'][mask] and not x['dynamic_domain_eligible'] for x in technical))
start=time.perf_counter();r=read(O/'result.json');a=read(O/'analysis_verification.json');sel=read(O/'selection.json')
assert a['raw_sha256']==sha(O/'result.json') and a['source_hashes_verified']
rows=[]
for row,physical in zip(r['rows'],a['physical_audits']):
    q=row['pre_response_filter'];p=q['proximity'];ref=row['branches']['reference']
    assert q['computed_before_any_response_action'] and p['integration_steps']==0 and p['explicit_forward_calls']==1
    assert q['full_snapshot_error_after_query']==diff(q['anchor_before_query'],q['anchor_after_query'])==0
    assert diff(q['anchor_after_query'],ref['anchor'])==0
    assert q['initial_robot_contacts']==ref['initial_robot_contacts']
    assert p['native_version']=='3.2.3' and p['query_margin_m']==.015
    assert p['copied_model_restored'] and p['original_model_unchanged'] and p['original_data_unchanged'] and p['same_qpos_qvel_after_forward']
    if not p['island_discovery_enabled']:assert q['anchor_before_query']['sim'] is not None and p['excluded_inactive_data_arrays']
    if not p['dual_solver_active']:assert set(p['excluded_inactive_dual_arrays'])=={'efc_AR','efc_AR_rownnz','efc_AR_rowadr','efc_AR_colind'}
    for values in p['effective_margin_gap_values'].values():assert all(v==.015 for v in values)
    near=p['nearby_robot_contacts'];names=set(p['robot_geometry_names'])
    assert all(any(n in names for n in c['names']) for c in near)
    masks=dict(M0=not q['initial_robot_contacts'],M1=not q['initial_robot_contacts'] and not near)
    assert masks['M0']==q['M0_initial_contact_free'] and masks['M1']==q['M1_initial_and_proximity_contact_free']
    assert row['demo']==physical['demo'] and row['t']==physical['t']
    rows.append(dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],technical_passed=physical['technical_passed'],
                     dynamic_domain_eligible=physical['eligible'],masks=masks,initial_contacts=q['initial_robot_contacts'],nearby_contacts=near,
                     canonical_state_and_controller_unchanged=True,query_before_response=True))
result=dict(state='PRE_RESPONSE_FILTER_CLASSIFICATION_VERIFIED',domain_state=a['state'],planned_anchors=12,executed_branches=336,
            eligible_anchors=a['eligible_anchors'],masks={m:summary(rows,m) for m in ['M0','M1']},
            strata={str(frac):{m:summary([x for x in rows if x['fraction']==frac],m) for m in ['M0','M1']} for frac in sel['anchor_fractions']},rows=rows,
            raw_sha256=sha(O/'result.json'),physical_audit_sha256=sha(O/'analysis_verification.json'),source_sha256=sha(Path(__file__)),
            query_forward_calls=12,policy_training_updates=0,fit_updates=0,new_physics_steps=0,analysis_elapsed_seconds=time.perf_counter()-start,
            limitation='Contact-list proxy with fixed native model settings, not exact signed-distance or universal future-policy validity. Inactive island/dual work arrays excluded from native-data hash; core physical/controller snapshots exact.')
with (O/'filter_analysis.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
