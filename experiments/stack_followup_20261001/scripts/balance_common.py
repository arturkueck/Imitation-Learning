"""Predeclared common protocol, data windows and metrics; no action corrections."""
import json,hashlib
import numpy as np
from transport_data import ROOT,DATA,KEYS,demos,history,summary
EXP=ROOT/'experiments/stack_balance_20261001';EXP.mkdir(exist_ok=True)
SOURCE=json.loads((ROOT/'experiments/stack_followup_20261001/evaluation/fixed_scheduler_h2/evaluation_results.json').read_text())

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def event(d):
    o=d['obs']['object'];e=d['obs']['robot0_eef_pos'];a=d['actions'];m=np.linalg.norm(a[:,:2],axis=1)
    v=o[:,:2]-e[:,:2];cos=(a[:,:2]*v).sum(axis=1)/np.maximum(m*np.linalg.norm(v,axis=1),1e-9)
    valid=(o[:,5]>.98)&(a[:,-1]>0)&(m>.25)&(cos>.85)&(np.linalg.norm(e-o[:,3:],axis=1)<.012)
    ids=[int(i) for i in np.flatnonzero(valid) if i>=6 and i+3<=len(a) and np.all(m[i-3:i]<.12) and np.all(m[i:i+3]>.25)]
    assert len(ids)==1,(d['name'],ids)
    return ids[0]

def load_training():
    ds=sorted(demos(),key=lambda d:int(d['name'].split('_')[-1]));obs=[];actions=[];critical=[];refs=[];events=[]
    for d in ds:
        k=event(d);events.append(dict(demo=d['name'],split=d['split'],event=k,window=[k-6,k+8],
            reconstructed_expert_phase_match=bool(d['phase'][k]==4)))
        if d['split']!='train':continue
        for i in range(len(d['actions'])):
            obs.append(history(d,i));idx=np.clip(np.arange(i-1,i+15),0,len(d['actions'])-1)
            actions.append(d['actions'][idx]);critical.append(k-6<=i<=k+8);refs.append([d['name'],i])
    arrays={k:np.stack([o[k] for o in obs]) for k in KEYS};a=np.stack(actions);c=np.array(critical)
    weights=np.where(c,.5/c.sum(),.5/(~c).sum());assert np.isclose(weights.sum(),1)
    return ds,arrays,a,c,weights,refs,events

def prepare():
    if (EXP/'protocol.json').exists():raise RuntimeError('Existing frozen protocol; refusing overwrite')
    ds,obs,a,c,w,refs,events=load_training()
    original=json.loads((ROOT/'experiments/stack_transport_20261001/verification.json').read_text())
    assert digest(DATA)==original['dataset_sha256'];assert digest(SOURCE['checkpoint'])==original['checkpoint_sha256']
    p=dict(source_checkpoint=SOURCE['checkpoint'],source_sha256=original['checkpoint_sha256'],dataset_sha256=original['dataset_sha256'],
        gradient_updates=5000,batch_size=8,seed=1,initial_optimizer_steps=30000,
        continuation_schedule=dict(type='cosine_restart',initial_lr=.0001,warmup_steps=500,num_cycles=.5,total_steps=5000),
        optimizer='restore AdamW moments from source',ema='restore source EMA weights; restore optimization_step=30000 inferred from optimizer',
        event_criterion=dict(B_z_gt=.98,gripper_action_gt=0,xy_action_norm_gt=.25,goal_cosine_gt=.85,eef_B_distance_lt=.012,
            previous_3_xy_norm_lt=.12,next_3_xy_norm_gt=.25),window_offsets=[-6,8],critical_mass=.5,
        uniform_critical_mass=float(c.mean()),training_frames=len(c),critical_frames=int(c.sum()),other_frames=int((~c).sum()),
        inference_action_horizon=2,ddim_steps=10,observation_horizon=2,prediction_horizon=16,
        offline=dict(train_demos=180,valid_demos=20,boundary_offsets=[-10,30],draws=3,
            significant_xy_norm=.25,significant_goal_cosine=.5,sustained_steps=3),
        rollouts=dict(seeds=list(range(46000,46020)),horizon=500,tail_steps=40,
            lift_metric_B_z_gt=.88,full_lift_end_B_z_ge=1.045,full_lift_end_EEF_z_ge=1.049,sustained_full_lift_steps=3,
            transport_velocity_gt=.02,transport_goal_cosine_gt=.5,transport_sustained_steps=3,
            transport_requires_grasp=True,distance_offsets_steps=[10,20,40]),
        common_random_numbers=True,checkpoint_selection='final_update_5000_only',
        data_unchanged=True,black_image_demos_documented=62,black_image_transport_frames=1266)
    (EXP/'protocol.json').write_text(json.dumps(p,indent=2));(EXP/'events.json').write_text(json.dumps(events,indent=2))
    np.savez_compressed(EXP/'sampling_weights.npz',critical=c,weights=w,refs=np.array(refs))
    print(json.dumps(p,indent=2))

def first_run(mask,steps=3):
    valid=np.convolve(np.asarray(mask,dtype=int),np.ones(steps,int),'valid')==steps
    ids=np.flatnonzero(valid);return int(ids[0]) if len(ids) else None

def rollout_metrics(t,measured):
    a=t[:measured];o=a[:,1:7];delta=o[:,3:]-o[:,:3];dist=np.linalg.norm(delta[:,:2],axis=1);held=a[:,34]>0
    lifted=o[:,5]>.88;post=np.maximum.accumulate(lifted);full=first_run(held&(o[:,5]>=1.045)&(a[:,17]>=1.049))
    vel=np.vstack([np.zeros(2),np.diff(o[:,3:5],axis=0)*20]);vnorm=np.linalg.norm(vel,axis=1);towards=-delta[:,:2]
    cos=(vel*towards).sum(axis=1)/np.maximum(vnorm*dist,1e-9)
    transport=first_run(post&held&(o[:,5]>.98)&(vnorm>.02)&(cos>.5))
    am=np.linalg.norm(a[:,20:22],axis=1);acos=(a[:,20:22]*towards).sum(axis=1)/np.maximum(am*dist,1e-9)
    command=first_run(post&held&(am>.25)&(acos>.5))
    near=post&(dist<.03)&(delta[:,2]>.032);pos=post&(dist<.009)&(delta[:,2]>.032);lower=pos&(abs(delta[:,2]-.04)<.008)
    release=lower&(~held)&(a[:,35]>0)
    start=full if full is not None else (int(np.flatnonzero(lifted)[0]) if lifted.any() else None)
    mask=held&post&(dist>.02)&(am>.01)
    if start is not None:mask&=(np.arange(measured)>=start)
    ids=np.flatnonzero(mask&(a[:,0].astype(int)%2==0));pairs=np.diff(ids)==2
    reversals=int((((a[ids[1:],20:22]*a[ids[:-1],20:22]).sum(axis=1)<0)&pairs).sum())
    distances={}
    for seconds,offset in ((.5,10),(1.,20),(2.,40)):
        i=full+offset if full is not None else None
        distances[str(seconds)]=float(np.linalg.norm(t[i,4:6]-t[i,1:3])) if i is not None and i<len(t) else None
    stages=dict(grasp=held,lift=lifted,near=near,position=pos,lower=lower,release=release,stack=a[:,36]>0)
    return dict(**{k:bool(v.any()) for k,v in stages.items()},full_lift_end=full,transport_start=transport,
        transport_command_start=command,transport_started=transport is not None,
        transport_delay_steps=(transport-full) if transport is not None and full is not None else None,
        relative_xy_distance_after_lift_end_m=distances,xy_action_reversals=reversals,replan_pairs=int(pairs.sum()),
        first_steps={k:int(np.flatnonzero(v)[0]) if v.any() else None for k,v in stages.items()})

if __name__=='__main__':prepare()
