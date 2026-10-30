from pathlib import Path
import urllib.request,json,hashlib,h5py,numpy as np
out=Path('experiments/stack_transition_quality_20261024/web_dataset_audit');target=out/'mimicgen_stack_three_source.hdf5'
expected='68b9033fefe904a5575e79bdf5040c2d2d207c1bfcc939bbaec5b438a9d7fcfe';url='https://huggingface.co/datasets/amandlek/mimicgen_datasets/resolve/main/source/stack_three.hdf5'
if not target.exists():
 tmp=target.with_suffix('.part');total=0;h=hashlib.sha256()
 with urllib.request.urlopen(url,timeout=60) as r,tmp.open('wb') as f:
  while True:
   b=r.read(1024*1024)
   if not b:break
   total+=len(b)
   if total>30000000:raise RuntimeError('Download cap30MB')
   h.update(b);f.write(b)
 assert h.hexdigest()==expected;tmp.replace(target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
with h5py.File(target,'r') as f:
 d=f['data'];names=list(d);first=d[names[0]];acts=np.concatenate([d[n]['actions'][:] for n in names]);attrs={k:(v.decode() if isinstance(v,bytes) else str(v)) for k,v in d.attrs.items()}
 report=dict(source=url,sha256=expected,bytes=target.stat().st_size,demos=len(names),frames=len(acts),data_attributes=attrs,first_demo_keys=list(first),first_demo_attrs={k:(v.decode() if isinstance(v,bytes) else str(v))[:2000] for k,v in first.attrs.items()},action_shape=list(acts.shape),action_min=acts.min(0).tolist(),action_max=acts.max(0).tolist(),nonzero_rotation_fraction=float(np.mean(np.any(np.abs(acts[:,3:6])>1e-6,axis=1))),observations=list(first['obs']) if 'obs' in first else None)
(out/'mimicgen_inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['first_demo_attrs']},indent=2))
