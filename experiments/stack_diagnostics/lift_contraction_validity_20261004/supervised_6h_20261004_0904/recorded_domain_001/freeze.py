import json,hashlib,py_compile
from pathlib import Path
O=Path(__file__).resolve().parent
for name in ['run.py','supervise.py']:py_compile.compile(str(O/name),doraise=True)
names=['run.py','helpers.py','supervise.py','freeze.py','PROTOCOL.md','selection.json']
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:
    json.dump({name:hashlib.sha256((O/name).read_bytes()).hexdigest() for name in names},f,indent=2)
print('Static-state audit sources/selection frozen before launch.')
