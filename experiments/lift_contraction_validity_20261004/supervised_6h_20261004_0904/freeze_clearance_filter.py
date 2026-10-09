import json,hashlib,shutil,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'clearance_filter_001';OLD=S/'local_response_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(O/'preflight_003/result.json')['state']=='PREFLIGHT_PASSED'
assert read(O/'preflight_003/result.json')['synthetic_cases_passed']==6
assert read(O/'preflight_003/result.json')['known_frame']['query']['full_snapshot_error_after_query']==0
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
for name in ['history_audit.py','analyze_audit.py']:shutil.copy2(OLD/name,O/name)
with (O/'PROTOCOL.md').open('a',encoding='utf-8') as f:
    f.write('\nVor Primärlaunch technisch fixiert: copy.copy(MjModel) mit unabhängigen Margin-/Gap-Arrays, separate MjData, ein mj_forward ohne Integration; Primärmodel-/Databuffer und voller Controller-/Physicalsnapshot unverändert. Inaktive Inselarrays nur bei deaktiviertem mjENBL_ISLAND und nisland=0, efc_AR-Arbeitsarrays nur bei nativem mj_isDual=false aus Datahash ausgeschlossen; gemäß 3.2.3 mjData-Headern dann nicht berechnet und in Vorprüfung selbst ohne Query wechselnd. Keine Änderung physischer Gates. Originalfailures und Quellen erhalten, preflight_003 mit sechs synthetischen Cases und bekanntem Recorded-Frame bestanden. Primärmasken vor Antwortschritt gesichert, Proxyparameter unverändert 0,015m. Explizite Queryforwardcalls getrennt von instrumentierter Antwortphysik; Setup-/Resetforwards nicht voll instrumentiert.\n')
names=['run.py','run_valid_arrays.py','run_defined_arrays.py','helpers.py','preparation.py','clearance.py','clearance_valid_arrays.py','clearance_defined_arrays.py',
       'supervise.py','supervise_primary.py','supervise_defined.py','selection.json','calibration.json','PROTOCOL.md','analyze_filter.py','analyze_audit.py','history_audit.py']
for d in ['preflight_001','preflight_002','preflight_003']:
    names += [d+'/'+n for n in ['run.py','supervise.py','result.json']]
for name in names:
    if name.endswith('.py'):py_compile.compile(str(O/name),doraise=True)
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump({n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in names},f,indent=2)
print('Final native query preflight passed; original failures preserved; fixed sources/masks/protocol frozen before 336 response branches.')
