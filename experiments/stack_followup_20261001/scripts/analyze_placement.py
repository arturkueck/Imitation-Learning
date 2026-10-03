import json
from pathlib import Path
import numpy as np
import h5py
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/stack_placement_20261001'
def analyze(t):
    delta=t[:,4:7]-t[:,1:4]; xy=np.linalg.norm(delta[:,:2],axis=1)
    lifted=t[:,6]>.88
    # trace: step, positions(6), quats(8), eef(3), fingers(2), applied(7), predicted(7), grasp/contact/success
    grasp=t[:,34]>0
    post=np.maximum.accumulate(lifted)
    aligned=post&(xy<.009)&(delta[:,2]>.032)
    transported=post&(xy<.03)&(delta[:,2]>.032)
    lowered=aligned&(abs(delta[:,2]-.04)<.008)
    released=lowered&(~grasp)&(t[:,35]>0)
    switches=np.where((t[1:,26]<0)&(t[:-1,26]>=0)&post[1:])[0]+1
    rotations=t[:,11:15]
    # Equal-sided cube: any face can be horizontal. Respect 90-degree cube symmetries.
    w,x,y,z=rotations.T
    vertical=np.c_[2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]
    tilt=np.degrees(np.arccos(np.clip(abs(vertical).max(axis=1),-1,1)))
    stage_masks=dict(grasp=grasp,lift=lifted,transport=transported,position=aligned,lower=lowered,release=released,success=t[:,36]>0)
    return dict(**{k:bool(v.any()) for k,v in stage_masks.items()},
        first_steps={k:int(np.flatnonzero(v)[0]) if v.any() else None for k,v in stage_masks.items()},
        correct_release_steps=int(released.sum()),
        min_xy_after_lift=float(xy[post].min()) if post.any() else None,
        open_switches=[dict(step=int(i),xy=float(xy[i]),height=float(delta[i,2]),grasp=bool(grasp[i])) for i in switches],
        last_delta=delta[-1].tolist(), median_tilt_after_lift=float(np.median(tilt[post])) if post.any() else None,
        grip_range_after_lift=[float(t[post,26].min()),float(t[post,26].max())] if post.any() else None)
all_results={}
for folder in OUT.iterdir():
    if not folder.is_dir(): continue
    rows=[dict(seed=int(p.stem),**analyze(np.load(p)['trace'])) for p in sorted(folder.glob('*.npz'))]
    if rows:
        all_results[folder.name]=dict(n=len(rows),counts={k:sum(r[k] for r in rows) for k in ('grasp','lift','transport','position','lower','release','success')},rollouts=rows)
with h5py.File(ROOT/'experiments/additional_tasks/stack_two/data/image_demonstrations.hdf5') as f:
    demos=[]
    for name in f['data']:
        d=f['data'][name]; a=d['actions'][:]; o=d['obs/object'][:]; e=d['obs/robot0_eef_pos'][:]
        changes=np.where((a[1:,-1]<0)&(a[:-1,-1]>0))[0]+1
        for i in changes:
            delta=o[i,3:]-o[i,:3]
            demos.append(dict(demo=name,step=int(i),xy=float(np.linalg.norm(delta[:2])),height=float(delta[2]),eef_offset=(e[i]-o[i,3:]).tolist(),open_steps=int((a[i:,-1]<0).sum())))
    all_results['demos']=dict(n=len(demos),release_xy_quantiles=np.quantile([r['xy'] for r in demos],[0,.5,.9,1]).tolist(),release_height_quantiles=np.quantile([r['height'] for r in demos],[0,.5,.9,1]).tolist(),rows=demos)
(OUT/'analysis.json').write_text(json.dumps(all_results,indent=2))
print(json.dumps({k:{a:b for a,b in v.items() if a not in ('rollouts','rows')} for k,v in all_results.items()},indent=2))
