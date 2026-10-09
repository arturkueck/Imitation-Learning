import hashlib,json,py_compile
from pathlib import Path
O=Path(__file__).resolve().parent
for name in ['run.py','supervise.py']:py_compile.compile(str(O/name),doraise=True)
names=['run.py','supervise.py','freeze.py','PROTOCOL.md','selection.json','calibration.json']
manifest={name:hashlib.sha256((O/name).read_bytes()).hexdigest() for name in names}
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
print('Frozen syntax-checked source, fixed selection, protocol and calibration before audit launch.')
