"""Read-only compact progress for supervising the sequential jobs."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
status=json.loads((root/'status.json').read_text())
out={k:status[k] for k in ('state','current') if k in status}
parts=status.get('current','').split('/')
if len(parts)>=3:
    dest=root.joinpath(*parts[:3])
    path=dest/'status.json'
    if path.exists():
        p=json.loads(path.read_text());out.update({k:p[k] for k in ('updates','loss_last500','elapsed_seconds') if k in p})
    path=dest/'rollouts/results.json'
    if path.exists():
        p=json.loads(path.read_text());out.update(rollouts=len(p),stable_stacks=sum(x['sustained_success'] for x in p))
out['failures']=len(status.get('failures',[]))
if 'fatal_error' in status:out['fatal_error']=status['fatal_error']
print(json.dumps(out))
