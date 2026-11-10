"""Audit demonstrator phase observability and transition coverage."""
from pathlib import Path
import json
import numpy as np
import h5py
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[3]
rows=[]; features=[]; labels=[]; transition_distances=[]; transition_angles=[]
with h5py.File(ROOT/'experiments/additional_tasks/stack_two/data/image_demonstrations.hdf5') as f:
    train=set(x.decode() for x in f['mask/train'][:])
    for name in f['data']:
        d=f['data'][name]; a=d['actions'][:]; o=d['obs/object'][:]; e=d['obs/robot0_eef_pos'][:]; g=d['obs/robot0_gripper_qpos'][:]
        for switch in np.flatnonzero((a[1:,-1]<0)&(a[:-1,-1]>0))+1:
            v=np.c_[e,o,g]
            transition_distances.append(float(np.linalg.norm(v[switch]-v[switch-1])))
            q=d['obs/robot0_eef_quat'][switch-1:switch+1]
            transition_angles.append(float(np.degrees(2*np.arccos(np.clip(abs(np.dot(q[0],q[1])),-1,1)))))
        phases=[]; phase=0; steps=0; target=None
        for i in range(len(a)):
            cube=o[i,3:]; base=o[i,:3]
            if target is None:
                target=[cube+[0,0,.14],cube+[0,0,.003],cube+[0,0,.003],cube+[0,0,.24],base+[0,0,.19],base+[0,0,.042],base+[0,0,.042],base+[0,0,.19]][phase]
            phases.append(phase); steps+=1
            ready=steps>=20 if phase in (2,6) else np.linalg.norm(target-e[i])<.006 and steps>=5
            if ready:
                phase+=1; steps=0; target=None
                if phase==8: phase=7; target=e[i]
        phases=np.array(phases)
        rows.append(dict(demo=name,split='train' if name in train else 'valid',counts={str(p):int((phases==p).sum()) for p in range(8)}))
        if name in train:
            # Use positions and finger displacement in meters; orientation stored separately by policy.
            features.append(np.c_[e,o,g]); labels.append(a[:,-1])
    x=np.concatenate(features); y=np.concatenate(labels)
    opened=x[y<0]; closed=x[y>0]; dist=cKDTree(opened).query(closed)[0]
result=dict(phase_names=['approach','descend_to_grasp','close','lift','transport','lower','release','retreat'],
    phase_count_method='Approximate expert phase reconstruction from recorded numerical observations; boundary tolerances can shift counts.',
    total_phase_steps={str(p):sum(r['counts'][str(p)] for r in rows) for p in range(8)},
    close_release_adjacent_feature_distance_quantiles_m=np.quantile(transition_distances,[0,.5,.9,1]).tolist(),
    close_release_adjacent_eef_angle_quantiles_degrees=np.quantile(transition_angles,[0,.5,.9,1]).tolist(),
    close_to_open_nearest_position_finger_distance_quantiles_m=np.quantile(dist,[0,.1,.5,.9,1]).tolist(),
    closed_samples_with_open_neighbor_within_2mm=int((dist<.002).sum()),closed_samples=len(closed),
    caveat='Neighbor audit excludes quaternion and observation history; measures geometric ambiguity, not identical full policy inputs.',demos=rows)
out=ROOT/'experiments/stack_placement_20261001/data_audit.json'; out.write_text(json.dumps(result,indent=2)); print(json.dumps({k:v for k,v in result.items() if k!='demos'},indent=2))
