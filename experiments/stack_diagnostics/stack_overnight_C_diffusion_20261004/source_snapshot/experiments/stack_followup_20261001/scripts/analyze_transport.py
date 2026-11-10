import json
import numpy as np
from transport_data import demos, summary, motion_metrics, ROOT, OUT
ds=demos(); records=[]; phase_frames=np.zeros(8,int); vectors=[]; dataset_errors=[]
for d in ds:
    phase=d['phase']; transport=phase==4; o=d['obs']['object']; e=d['obs']['robot0_eef_pos']; a=d['actions']
    phase_frames+=np.bincount(phase,minlength=8)[:8]
    ids=np.flatnonzero(transport); initial=o[0,:2]-o[0,3:5]; dist=np.linalg.norm(initial)
    vec=o[transport,:2]-o[transport,3:5]; vectors.extend(vec.tolist())
    dataset_errors.extend(d['label_error'][transport].tolist())
    angle=np.arctan2(initial[1],initial[0]); sector=int(np.floor((angle+np.pi)/(np.pi/4)))%8
    lifted=np.flatnonzero(o[:,5]>.88)
    reached=np.flatnonzero((np.linalg.norm(o[:,:2]-o[:,3:5],axis=1)<.009)&(o[:,5]-o[:,2]>.032))
    records.append(dict(demo=d['name'],split=d['split'],A_start=o[0,:3].tolist(),B_start=o[0,3:].tolist(),goal_vector=initial.tolist(),distance_m=float(dist),sector=sector,
        transport_start=int(ids[0]) if len(ids) else None,transport_frames=len(ids),
        lift_to_transport_start_frames=int(ids[0]-lifted[0]) if len(ids) and len(lifted) else None,
        lift_to_target_frames=int(reached[reached>=lifted[0]][0]-lifted[0]) if len(lifted) and len(reached[reached>=lifted[0]]) else None,
        label_error_transport_max=float(d['label_error'][transport].max()) if len(ids) else None,
        metrics=motion_metrics(o,e,a,transport)))
policy=[];policy_heights=[];policy_offsets=[]
for p in sorted((ROOT/'experiments/stack_placement_20261001/baseline').glob('*.npz')):
    t=np.load(p)['trace']; o=t[:,1:7]; a=t[:,20:27]; held=t[:,34]>0; lifted=o[:,5]>.88
    first=np.flatnonzero(held&lifted)
    if not len(first): continue
    # First 4 seconds after held lift, compared with 1-second lift and full closed-held windows.
    win=(np.arange(len(t))>=first[0])&(np.arange(len(t))<first[0]+80)&held
    policy_heights.extend(o[win,5].tolist());policy_offsets.extend(np.linalg.norm(t[win,15:18]-o[win,3:],axis=1).tolist())
    vec=o[:,:2]-o[:,3:5]; dist=np.linalg.norm(vec,axis=1)
    act=a[:,:2]; cosine=(act*vec).sum(axis=1)/np.maximum(np.linalg.norm(act,axis=1)*dist,1e-9)
    replans=np.flatnonzero(win&(t[:,0].astype(int)%2==0)&(dist>.02)&(np.linalg.norm(act,axis=1)>.01))
    adjacent=np.diff(replans)==2
    reversals=int((((act[replans[1:]]*act[replans[:-1]]).sum(axis=1)<0)&adjacent).sum())
    bins=[]
    for l,r in ((0,10),(10,20),(20,40),(40,80)):
        mask=(np.arange(len(t))>=first[0]+l)&(np.arange(len(t))<first[0]+r)&held
        bins.append(dict(offset_steps=[l,r],metrics=motion_metrics(o,t[:,15:18],a,mask)))
    policy.append(dict(seed=int(p.stem),first_held_lift=int(first[0]),start_goal_vector=vec[first[0]].tolist(),
        initial_distance_m=float(dist[first[0]]),distance_after_1s_m=float(dist[min(first[0]+20,len(t)-1)]),distance_after_4s_m=float(dist[min(first[0]+80,len(t)-1)]),
        replan_action_direction_reversals=reversals,replan_pairs=int(adjacent.sum()),
        metrics=motion_metrics(o,t[:,15:18],a,win),bins=bins))
sectors={str(i):sum(r['sector']==i for r in records) for i in range(8)}
vectors=np.asarray(vectors)
all_demo_pos=np.concatenate([d['obs']['object'] for d in ds]); all_demo_eef=np.concatenate([d['obs']['robot0_eef_pos'] for d in ds]); all_demo_a=np.concatenate([d['actions'] for d in ds]); all_demo_mask=np.concatenate([d['phase']==4 for d in ds])
expert_heights=all_demo_pos[all_demo_mask,5];expert_offsets=np.linalg.norm(all_demo_eef[all_demo_mask]-all_demo_pos[all_demo_mask,3:],axis=1)
result=dict(n_demos=len(ds),split_counts={s:sum(d['split']==s for d in ds) for s in ('train','valid')},
    expert_transport_B_z=summary(expert_heights),policy_held_B_z_first4s=summary(policy_heights),
    policy_fraction_below_expert_transport_min_z=float((np.array(policy_heights)<expert_heights.min()).mean()),
    expert_EEF_cube_offset_m=summary(expert_offsets),policy_EEF_cube_offset_m=summary(policy_offsets),
    A_start_quantiles=np.quantile([r['A_start'] for r in records],[0,.1,.5,.9,1],axis=0).tolist(),
    B_start_quantiles=np.quantile([r['B_start'] for r in records],[0,.1,.5,.9,1],axis=0).tolist(),
    phase_frames=phase_frames.tolist(),transport_fraction=float(phase_frames[4]/phase_frames.sum()),
    transport_frames=summary([r['transport_frames'] for r in records]),transport_seconds=summary([r['transport_frames']/20 for r in records]),
    lift_to_target_frames=summary([r['lift_to_target_frames'] for r in records if r['lift_to_target_frames'] is not None]),
    lift_to_transport_start_frames=summary([r['lift_to_transport_start_frames'] for r in records if r['lift_to_transport_start_frames'] is not None]),
    distances_m=summary([r['distance_m'] for r in records]),direction_sectors=sectors,
    training_sectors={str(i):sum(r['sector']==i and r['split']=='train' for r in records) for i in range(8)},
    distance_bin_counts=np.histogram([r['distance_m'] for r in records],bins=[0,.1,.2,.3,.5])[0].tolist(),
    relative_vectors_quantiles=np.quantile(vectors,[0,.1,.5,.9,1],axis=0).tolist(),
    transport_label_error=summary(dataset_errors),transport_label_match_fraction=float((np.asarray(dataset_errors)<.01).mean()),
    expert_transport=motion_metrics(all_demo_pos,all_demo_eef,all_demo_a,all_demo_mask),demos=records,policy=policy)
(OUT/'data_behavior.json').write_text(json.dumps(result,indent=2))
# Persist exact phase labels and indices for teacher forcing / matched training.
np.savez_compressed(OUT/'phase_indices.npz',**{d['name']:d['phase'] for d in ds})
print(json.dumps({k:v for k,v in result.items() if k not in ('demos','policy')},indent=2))
print('POLICY',json.dumps([{k:r[k] for k in ('seed','initial_distance_m','distance_after_1s_m','metrics')} for r in policy],indent=2))
