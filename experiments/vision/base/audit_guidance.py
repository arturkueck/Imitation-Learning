"""Audit complete resumed routes and all actual capture hashes without training."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent/'guidance_002'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(s) for s in (out/'families.jsonl').read_text().splitlines()]
assert len(rows)==200 and [r['index'] for r in rows]==list(range(200))
bank={e['id']:e for e in json.loads((out/'bank.json').read_text())['entries']}
for e in bank.values():assert sha(out/f'certificate_{e["id"]:03d}.npz')==e['certificate_sha256']
accepted={r['index']:r for r in rows if r['stage']=='captured'}
for r in accepted.values():
    route=np.array(r['waypoints']);prefix=np.array(bank[r['bank_id']]['waypoints'])
    assert route.ndim==2 and route.shape[1]==7 and np.isfinite(route).all()
    np.testing.assert_allclose(route[:len(prefix)],prefix,atol=1e-8,rtol=0)
    np.testing.assert_allclose(route[-1],r['q'],atol=1e-8,rtol=0)
audit=json.loads((out/'capture_audit.json').read_text());assert audit['passed']
assert len(accepted)==147 and {r['index'] for r in audit['captures']}==set(accepted)
for r in audit['captures']:
    p=out/'captures'/f'{r["index"]:04d}.npz';assert sha(p)==r['array_sha256']
    assert sha(out/'captures'/f'{r["index"]:04d}_wrist.png')==r['image_sha256']
    with np.load(p) as z:
        np.testing.assert_allclose(z['camera_positions'][2],accepted[r['index']]['actual_camera']['position'],atol=1e-6,rtol=0)
original=json.loads((out.parent/'pilot_002/checkpoint_hashes.json').read_text())
assert all(sha(ROOT/'experiments/vision/visual_active_v3_20261101/run_001/checkpoints'/name)==value for name,value in original.items())
result=dict(passed=True,unique_development_families=200,actual_captures=147,certificate_hashes_verified=26,
    complete_route_prefix_and_endpoint_contracts_verified=True,all_image_and_array_hashes_verified=True,
    original_checkpoint_hashes_unchanged=True,training_started=False)
(out/'FINAL_AUDIT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
