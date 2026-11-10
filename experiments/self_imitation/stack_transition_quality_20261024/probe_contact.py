from pathlib import Path
import numpy as np,json
out=Path('experiments/self_imitation/stack_five_curriculum_20261023/datasets/curriculum_n3_cycle0');rs=json.loads((out/'manifest.json').read_text())['rows']
for r in rs[:8]:
 with np.load(r['path']) as a:
  ev=np.flatnonzero(a['controller_event']==2)
  if not len(ev):continue
  j=int(ev[0])+1;s=2;z=a['post_obs'][:,3*s+2];contacts=a['fingers'][:,s]
  ix=np.flatnonzero((np.arange(len(z))>=j)&(z-z[j]>.03))
  print(r['seed'],'start',j,'max_z',float(z[j:].max()),'contact_total',int(contacts[j:].sum()),'liftframes',len(ix),'lift_contact',int(contacts[ix].sum()),'lift_phase',a['p'][ix[:12]].tolist(),'firstlift',int(ix[0]) if len(ix) else None)
