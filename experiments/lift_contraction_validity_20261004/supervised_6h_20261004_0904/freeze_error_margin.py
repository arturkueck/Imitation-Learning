import json,hashlib,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'error_margin_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(O/'preflight_001/result.json')['state']=='PREFLIGHT_PASSED'
assert read(O/'preflight_001/result.json')['synthetic_cases_passed']==6
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
assert read(O/'margin_spec.json')==read(S/'NEXT_ERROR_MARGIN.json')
with (O/'PROTOCOL.md').open('a',encoding='utf-8') as f:
    f.write('\nImplementationsfreeze vor Primärlaunch: unveränderter Recorded-H_reset-/28-Zweig-Runner mit unveränderten physikalischen und tatsächlichen Kontaktgates. Pre-responseM0/M1/M2 ohne Model-/Stateänderung; feste 15-mm-Query. Lokale Antwort erst aus nominalen14Aktionszweigen identifiziert, getrennte Pfull-Physikantworten nur zur Prüfung. Fehlermarge ausschließlich aus alten48Trainfällen; keine neue Fit-/Loss-/Maskenschwelle. Native technische Vorprüfung bestanden, sechs bekannte synthetische Fälle plus alter Recorded-Frame, keine frischen Primäroutcomes. Unabhängige direkte Matrixlösung/Ratio-/Fehlerprüfung und separate native Queryneuherstellung sind vor Primärdaten gespeichert.\n')
names=['run.py','helpers.py','preparation.py','clearance_defined_arrays.py','supervise.py','selection.json','calibration.json','margin_spec.json','PROTOCOL.md',
       'analyze_filter.py','analyze_audit.py','history_audit.py','analyze_local.py','analyze_margin.py','verify_margin.py',
       'preflight_001/run.py','preflight_001/supervise.py','preflight_001/result.json','query_verification_001/run.py','query_verification_001/supervise.py']
for name in names:
    if name.endswith('.py'):py_compile.compile(str(O/name),doraise=True)
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump({n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in names},f,indent=2)
print('Preflight passed; effective frozen margin/selection/sources/independent analyses saved before fresh response data.')
