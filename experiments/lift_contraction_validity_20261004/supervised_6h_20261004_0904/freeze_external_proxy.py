import json,hashlib,shutil,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'external_proxy_001';OLD=S/'clearance_filter_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(O/'preflight_001/result.json')['state']=='PREFLIGHT_PASSED'
assert read(O/'preflight_001/result.json')['synthetic_cases_passed']==6
assert read(O/'preflight_001/result.json')['known_frame']['query']['full_snapshot_error_after_query']==0
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
source=(OLD/'analyze_filter.py').read_text(encoding='utf-8')
source=source.replace("masks=dict(M0=not q['initial_robot_contacts'],M1=not q['initial_robot_contacts'] and not near)",
                      "internal=[c for c in near if all(n in names for n in c['names'])]\n    external=[c for c in near if not all(n in names for n in c['names'])]\n    assert all(sum(n in names for n in c['names'])==1 for c in external)\n    assert internal==q['internal_proximity_contacts'] and external==q['external_proximity_contacts']\n    assert q['dynamic_label_retains_all_actual_self_contacts'] and sel['dynamic_label_includes_all_actual_robot_self_contacts']\n    masks=dict(M0=not q['initial_robot_contacts'],M1=not q['initial_robot_contacts'] and not near,M2=not q['initial_robot_contacts'] and not external)")
source=source.replace("assert masks['M0']==q['M0_initial_contact_free']", "assert masks['M2']==q['M2_initial_and_external_proximity_contact_free']\n    assert masks['M0']==q['M0_initial_contact_free']")
source=source.replace("nearby_contacts=near,", "nearby_contacts=near,internal_proximity_contacts=internal,external_proximity_contacts=external,")
source=source.replace("for m in ['M0','M1']", "for m in ['M0','M1','M2']")
needle="with (O/'filter_analysis.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)"
assert source.count(needle)==1
source=source.replace(needle,"assert sel['useful_candidate_gate']==dict(false_accept=0,minimum_true_accept=4,denominator=12)\nresult['external_mask_development_gate_passed']=result['masks']['M2']['false_accept']==0 and result['masks']['M2']['true_accept']>=4\nresult['decision']='Local empirical mask support only, no training approval' if result['external_mask_development_gate_passed'] else 'External proximity rule failed the predeclared development gate; no threshold/scope/seed tuning'\n"+needle)
with (O/'analyze_filter.py').open('x',encoding='utf-8') as f:f.write(source)
verification=O/'query_verification_001';verification.mkdir()
shutil.copy2(O/'preflight_001/supervise.py',verification/'supervise.py')
source=(OLD/'query_verification_001/run.py').read_text(encoding='utf-8').replace("['M0_initial_contact_free','M1_initial_and_proximity_contact_free']","['M0_initial_contact_free','M1_initial_and_proximity_contact_free','M2_initial_and_external_proximity_contact_free']")
source=source.replace("            for mask in", "            assert q['internal_proximity_contacts']==previous['internal_proximity_contacts'] and q['external_proximity_contacts']==previous['external_proximity_contacts']\n            for mask in")
with (verification/'run.py').open('x',encoding='utf-8') as f:f.write(source)
with (O/'PROTOCOL.md').open('a',encoding='utf-8') as f:
    f.write('\nVor Primärlaunch: unveränderte native Modelcopy/MjData-Abfrage aus technisch und unabhängig verifiziertem clearance_filter_001, einschließlich dokumentierter konditional nicht berechneter Insel-/Dual-Arbeitsarrays. Alle modell-/physikalisch definierten Datenarrays und voller nominaler Controller-/Zustandssnapshot gleich. Scopezuordnung ausschließlich per gespeichertem vollständigem Robot-/Grippergeomnamenset; keine Entfernung einzelner Paare, keine Veränderung tatsächlicher Kontaktlabels. Vorprüfung auf sechs bekannten Boxcases und einem bereits gesehenen Recorded-Frame prüft M0/M1/M2 sowie Scopezuordnung. Neue Demos werden erst danach in Primärproben verwendet.\n')
names=['run.py','helpers.py','preparation.py','clearance_defined_arrays.py','supervise.py','selection.json','calibration.json','PROTOCOL.md',
       'analyze_filter.py','analyze_audit.py','history_audit.py','preflight_001/run.py','preflight_001/supervise.py','preflight_001/result.json',
       'query_verification_001/run.py','query_verification_001/supervise.py']
for name in names:
    if name.endswith('.py'):py_compile.compile(str(O/name),doraise=True)
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump({n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in names},f,indent=2)
print('New M2 scope passed known technical control. All three masks, selection and analyses frozen before fresh primary response data; actual self-contact eligibility unchanged.')
