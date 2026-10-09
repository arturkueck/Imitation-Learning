import json,hashlib,shutil,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'method_reference_001';D=O/'verification_001'
assert json.loads((O/'result.json').read_text())['state']=='REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE'
D.mkdir();shutil.copy2(S/'verify_method_source.py',D/'run.py');shutil.copy2(O/'preflight_001/supervise.py',D/'supervise.py')
for p in D.glob('*.py'):py_compile.compile(str(p),doraise=True)
with (D/'source_hashes.json').open('x',encoding='utf-8') as out:json.dump({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.py')},out,indent=2)
print('Fresh independent verification source saved; no change to frozen primary sources.')
