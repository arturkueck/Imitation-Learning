import json,hashlib,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'local_response_001';OLD=S/'recorded_response_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(O/'preflight_001/result.json')['state']=='PREFLIGHT_PASSED'
assert read(O/'preflight_001/result.json')['same_recorded_physical_state_error']==0
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
source=(OLD/'history_audit.py').read_text(encoding='utf-8')
source=source.replace("    for demo in sel['selected_demos']:","    for demo in (sel['selected_demos'] if len(sel['histories'])==2 else []):")
source=source.replace('branch_count=672','branch_count=336')
with (O/'history_audit.py').open('x',encoding='utf-8') as f:f.write(source)
source=(OLD/'analyze_audit.py').read_text(encoding='utf-8')
source=source.replace('==24','==12').replace('==672','==336').replace('== 24','== 12').replace('== 672','== 336')
source=source.replace('planned_anchors=24,executed_anchors=24,planned_branches=672,executed_branches=672','planned_anchors=12,executed_anchors=12,planned_branches=336,executed_branches=336')
with (O/'analyze_audit.py').open('x',encoding='utf-8') as f:f.write(source)
names=['run.py','helpers.py','preparation.py','supervise.py','selection.json','calibration.json','PROTOCOL.md',
       'analyze_audit.py','history_audit.py','analyze_local.py','preflight_001/run.py','preflight_001/supervise.py','preflight_001/result.json']
for name in names:
    if name.endswith('.py'):py_compile.compile(str(O/name),doraise=True)
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump({n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in names},f,indent=2)
print('Fresh repeated H_reset preparation passed; worker, physical audit and local-identification analysis frozen before 336 primary branches.')
