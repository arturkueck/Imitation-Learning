import json,hashlib,py_compile
from pathlib import Path
O=Path(__file__).resolve().parent/'method_reference_001'
pref=json.loads((O/'preflight_001/result.json').read_text(encoding='utf-8'));assert pref['state']=='PREFLIGHT_PASSED'
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
names=['run.py','loss_reference.py','checks.py','supervise.py','selection.json','PROTOCOL.md','preflight_001/run.py','preflight_001/supervise.py','preflight_001/result.json']
for name in names:
    if name.endswith('.py'):py_compile.compile(str(O/name),doraise=True)
with (O/'source_hashes.json').open('x',encoding='utf-8') as out:json.dump({n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in names},out,indent=2)
print('Numerical preflight passed; all reference/audit/protocol/input sources frozen before exploratory parameter-gradient calculations.')
