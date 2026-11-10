"""Post-hoc explanation of zero coverage, not a fresh proxy validation."""
import json,hashlib
from pathlib import Path
from collections import Counter
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read(O/'result.json');a=read(O/'filter_analysis.json');assert a['raw_sha256']==sha(O/'result.json')
rows=[];counts=Counter()
for row in r['rows']:
    q=row['pre_response_filter'];p=q['proximity'];names=set(p['robot_geometry_names']);near=p['nearby_robot_contacts']
    internal=[c for c in near if all(n in names for n in c['names'])]
    external=[c for c in near if not all(n in names for n in c['names'])]
    counts.update(tuple(c['names']) for c in internal)
    mask=not q['initial_robot_contacts'] and not external
    rows.append(dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],internal_near_pairs=internal,external_near_pairs=external,
                     exploratory_external_only_accept=mask,dynamic_domain_eligible=row['gates']['passed']))
result=dict(state='EXPLORATORY_POSTHOC_PAIR_SCOPE_ONLY',new_independent_validation=False,rows=rows,
            internal_pair_frequency=[dict(names=list(names),anchor_count=count) for names,count in counts.items()],
            external_only_descriptive=dict(planned_anchors=12,accepted=sum(x['exploratory_external_only_accept'] for x in rows),
                                          true_accept=sum(x['exploratory_external_only_accept'] and x['dynamic_domain_eligible'] for x in rows),
                                          false_accept=sum(x['exploratory_external_only_accept'] and not x['dynamic_domain_eligible'] for x in rows),
                                          false_reject=sum(not x['exploratory_external_only_accept'] and x['dynamic_domain_eligible'] for x in rows)),
            raw_sha256=sha(O/'result.json'),filter_analysis_sha256=sha(O/'filter_analysis.json'),source_sha256=sha(Path(__file__)),
            new_physics_steps=0,policy_updates=0,fit_updates=0,
            decision='No replacement of the failed all-pair mask and no training approval. External-only predictor requires a predeclared test on fresh demos; dynamic domain must retain all actual robot/self contacts.')
with (O/'pair_scope_exploration.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
