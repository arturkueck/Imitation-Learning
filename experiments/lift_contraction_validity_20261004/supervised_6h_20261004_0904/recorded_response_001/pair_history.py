"""Descriptive paired analysis of the predeclared histories, no new simulation/fit."""
import json,hashlib
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=read(O/'analysis_verification.json');r=read(O/'result.json')
assert a['raw_sha256']==sha(O/'result.json')
pairs=[]
for pair in a['prepared_history_audit']['cross_history_pairs']:
    item=dict(pair)
    if pair['both_domain_eligible']:
        groups=[a['strata'][h+'_'+str(pair['fraction'])] for h in ['H_prefix','H_reset']]
        action=[];policy=[]
        for g in groups:
            scores=[s for values in g['B7']['by_component'].values() for s in values['raw'] if s['demo']==pair['demo'] and s['t']==pair['t']]
            # The summaries explicitly exclude zero/near-zero response vectors.
            relative=[s['relative_error'] for s in scores if not s['degenerate']]
            probes=[p for p in g['conditional_policy_raw'] if p['demo']==pair['demo'] and p['t']==pair['t']]
            action.append(float(np.median(relative)))
            policy.append(float(np.median([p['models']['A_B7']['absolute_ratio_error'] for p in probes])))
        item.update(B7_median_relative_error_by_history=action,policy_median_absolute_ratio_error_by_history=policy,
                    B7_relative_error_prefix_minus_reset=action[0]-action[1],policy_ratio_error_prefix_minus_reset=policy[0]-policy[1])
    pairs.append(item)
valid=[p for p in pairs if p['both_domain_eligible']]
result=dict(state='PAIRED_HISTORY_COMPARISON_VERIFIED',planned_unique_pairs=12,eligible_pairs=len(valid),histories=['H_prefix','H_reset'],pairs=pairs,
            median_reference_next_eef_difference_m=float(np.median([p['reference_next_eef_difference_m'] for p in valid])),
            max_reference_next_eef_difference_m=max(p['reference_next_eef_difference_m'] for p in valid),
            median_absolute_B7_error_history_difference=float(np.median([abs(p['B7_relative_error_prefix_minus_reset']) for p in valid])),
            median_absolute_policy_ratio_error_history_difference=float(np.median([abs(p['policy_ratio_error_prefix_minus_reset']) for p in valid])),
            source_sha256=sha(Path(__file__)),history_audit_source_sha256=sha(O/'history_audit.py'),analysis_sha256=sha(O/'analysis_verification.json'),raw_sha256=sha(O/'result.json'),
            new_physics_steps=0,optimizer_updates=0,fit_updates=0,
            limitation='Two controlled replacement histories only; excluded late-contact pairs unscored; no original history or independent training-seed claim.')
with (O/'history_comparison.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k!='pairs'},indent=2))
