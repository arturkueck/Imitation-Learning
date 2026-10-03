import json, re
from pathlib import Path
import h5py
import numpy as np
EXP = Path(__file__).resolve().parents[1]
report = json.loads((EXP/'collection_report.json').read_text())
stats = {}
with h5py.File(report['dataset'], 'r') as f:
    lengths = [len(d['actions']) for d in f['data'].values()]
    stats['dataset'] = dict(demos=len(lengths), train=len(f['mask/train']),
        valid=len(f['mask/valid']), total_steps=sum(lengths),
        lengths_min_median_max=[min(lengths),float(np.median(lengths)),max(lengths)],
        all_final_rewards_positive=all(d['rewards'][-1]>0 for d in f['data'].values()))
    stats['dataset']['image_shape'] = list(f['data/demo_0/obs/agentview_image'].shape)
for method in ('bc_rnn','bc_transformer'):
    log = (EXP/'logs'/f'{method}_training.log').read_text(errors='replace')
    values = {}
    for kind in ('Train','Validation'):
        matches = re.findall(kind+r' Epoch (\d+)\s*(\{.*?\})',log,re.S)
        points = [(int(e),json.loads(v)['Loss']) for e,v in matches]
        values[kind.lower()] = dict(final=points[-1],best=min(points,key=lambda p:p[1]),
            selected=[p for p in points if p[0] in (1,100,300,500,1000)])
    stats[method] = values
(EXP/'diagnostics/statistics.json').write_text(json.dumps(stats,indent=2))
print(json.dumps(stats,indent=2))
