"""Score saved C trajectories only; never infer actions or run a simulator."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
OUT=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(OUT/'scripts'))
from sanity_metrics import metrics
source=ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/C/diffusion/seed_1/rollouts'
metadata=json.loads((source/'results.json').read_text());rows=[];hashes={}
for row in metadata:
    path=source/f"{row['seed']}.npz";hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    trace=np.load(path)['trace'][:500];found=None
    for length in range(3,len(trace)+1):
        m=metrics(trace[:length])
        if m['simplified_success']:found=length;break
    if found is None:m=metrics(trace)
    rows.append(dict(seed=row['seed'],first_simple_success_step=found,available_frames=len(trace),**m))
result=dict(no_training_or_inference=True,reference='Existing full-task C/seed1 trace prefixes, not fresh simplified-task rollouts',n=len(rows),simplified_successes=sum(r['simplified_success'] for r in rows),grasp=sum(r['grasp_success'] for r in rows),lift=sum(r['lift_success'] for r in rows),transport_started=sum(r['transport_started_sanity'] for r in rows),rows=rows,source_trace_hashes=hashes)
(OUT/'C_existing_simple_task.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('n','simplified_successes','grasp','lift','transport_started')}))
