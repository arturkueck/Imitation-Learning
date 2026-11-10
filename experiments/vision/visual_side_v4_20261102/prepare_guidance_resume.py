"""Preserve invalid resume artifacts; inherit only endpoint-verified prior rows."""
from pathlib import Path
import json,shutil
import numpy as np
ROOT=Path(__file__).resolve().parent
src=ROOT/'guidance_001';dst=ROOT/'guidance_002';dst.mkdir(exist_ok=False)
b=json.loads((src/'bank.json').read_text());rows=[json.loads(s) for s in (src/'families.jsonl').read_text().splitlines()]
prefix=rows[:138];start=b['entries'][0]['waypoints'][0]
assert len(prefix)==138 and all(r['index']==i for i,r in enumerate(prefix))
for r in prefix:
    if r['stage']=='captured':
        assert np.max(np.abs(np.array(r['waypoints'][0])-start))<1e-8
        assert np.max(np.abs(np.array(r['waypoints'][-1])-r['q']))<1e-8
shutil.copytree(src/'source',dst/'source');shutil.copy2(src/'bank.json',dst/'bank.json')
for e in b['entries']:
    name=f'certificate_{e["id"]:03d}.npz';shutil.copy2(src/name,dst/name)
(dst/'families.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in prefix),encoding='utf-8')
(dst/'INHERITED_PREFIX.json').write_text(json.dumps(dict(source='guidance_001',verified_rows=138,discarded_invalid_resume_rows=[138,139],
    route_endpoint_contract_verified=True,technical_fix='explicit route concatenation for both numpy and list inputs; exact stored-scene replay'),indent=2),encoding='utf-8')
print('Inherited 138 verified records and 26 certificates; invalid resume retained separately.')
