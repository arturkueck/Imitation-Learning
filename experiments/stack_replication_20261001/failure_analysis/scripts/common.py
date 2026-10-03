"""Read-only access to frozen experiments; no training entry points."""
from pathlib import Path
import sys, json, csv, hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'experiments/stack_followup_20261001/scripts'))
from replication_common import checkpoint, rollouts, folder
from direct_common import DirectChunk, flatten, KEYS
from balance_common import digest
from dynamics_common import extra_metrics

OUT = ROOT / 'experiments/stack_replication_20261001/failure_analysis'
PRIOR = ROOT / 'experiments/stack_switch_20261001'
PROTOCOL = json.loads((OUT.parent / 'protocol.json').read_text())
PANEL = np.load(PRIOR / 'panel.npz')
META = json.loads((PRIOR / 'panel.json').read_text())
OFFSETS = np.array([r['offset'] for r in META])
GOAL = PANEL['object'][:, -1, :2] - PANEL['robot0_eef_pos'][:, -1, :2]

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def csvwrite(name, rows):
    if not rows: return
    with (OUT / name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def direct_chunks(seed):
    p = ROOT / 'experiments/stack_direct_20261001/offline_predictions.npz' if seed == 1 else folder('direct',seed) / 'offline_predictions.npz'
    return np.load(p)['chunks']

def existing_diffusion(seed, steps=10):
    p = PRIOR / f'source/ddim{steps}.npz' if seed == 1 else folder('diffusion',seed) / 'common_offline.npz'
    if seed != 1 and steps != 10: return None
    if not p.exists(): return None
    z = np.load(p); a = np.empty((len(META),8,16,7),np.float32)
    m = z['draw'] < 8; a[z['panel_index'][m],z['draw'][m]] = z['chunks'][m]
    return a

def numerics():
    import torch
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False

def fields(a, goal=GOAL):
    xy = np.linalg.norm(a[..., :2],axis=-1); xyz=np.linalg.norm(a[..., :3],axis=-1)
    g=goal[:,None,None,:] if a.ndim == 4 else goal[:,None,:]
    cos=(a[...,:2]*g).sum(-1)/np.maximum(xy*np.linalg.norm(g,axis=-1),1e-9)
    return xy,xyz,cos
