"""Shared exact-observation data access for transport investigations."""
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
import h5py
import numpy as np
from task_extensions.stack_expert import StackExpert
OUT=ROOT/'experiments/stack_transport_20261001'
OUT.mkdir(exist_ok=True)
DATA=ROOT/'experiments/additional_tasks/stack_two/data/image_demonstrations.hdf5'
KEYS=['robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos','object']

def demos():
    rows=[]
    with h5py.File(DATA,'r') as f:
        train=set(x.decode() for x in f['mask/train'][:])
        for name in f['data']:
            d=f['data'][name]; obs={k:d['obs/'+k][:] for k in KEYS}; actions=d['actions'][:]
            raw=SimpleNamespace(cubes=[0,1],cube_ids=[0,1],sim=SimpleNamespace(data=SimpleNamespace(body_xpos=None)))
            expert=StackExpert(SimpleNamespace(base_env=raw)); phases=[]; labels=[]
            for i in range(len(actions)):
                raw.sim.data.body_xpos=obs['object'][i].reshape(2,3)
                phases.append(expert.phase); labels.append(expert({'robot0_eef_pos':obs['robot0_eef_pos'][i]}))
            label_error=np.max(np.abs(np.asarray(labels)-actions),axis=1)
            rows.append(dict(name=name,split='train' if name in train else 'valid',obs=obs,actions=actions,
                phase=np.array(phases),label_error=label_error))
    return rows

def history(d,i):
    ids=[max(0,i-1),i]
    return {k:d['obs'][k][ids] for k in KEYS}

def summary(values):
    v=np.asarray(values)
    return dict(n=len(v),mean=float(v.mean()),q=np.quantile(v,[0,.1,.5,.9,1]).tolist()) if len(v) else dict(n=0)

def motion_metrics(pos,eef,actions,mask):
    target=pos[:,:3]; cube=pos[:,3:]; vec=target[:,:2]-cube[:,:2]; eefvec=target[:,:2]-eef[:,:2]
    dist=np.linalg.norm(vec,axis=1); av=actions[:,:2]; mag=np.linalg.norm(av,axis=1)
    cosine=(av*vec).sum(axis=1)/np.maximum(mag*dist,1e-9)
    velocity=np.diff(cube[:,:2],axis=0)*20
    vv=np.linalg.norm(velocity,axis=1)
    valid=mask&(dist>.02); active=valid&(mag>.01)
    vm=mask[:-1]&mask[1:]
    dot=(velocity[1:]*velocity[:-1]).sum(axis=1)
    rev=vm[1:]&vm[:-1]&(vv[1:]>.005)&(vv[:-1]>.005)
    return dict(frames=int(mask.sum()),distance_mm=summary(dist[mask]*1000),eef_distance_mm=summary(np.linalg.norm(eefvec[mask],axis=1)*1000),
        action_magnitude=summary(mag[valid]),goal_cosine=summary(cosine[active]),
        away_action_fraction=float((cosine[active]<0).mean()) if active.any() else None,
        stalled_action_fraction=float((mag[valid]<.05).mean()) if valid.any() else None,
        velocity_m_s=summary(vv[vm]),direction_reversals=int(((dot<0)&rev).sum()),
        descending_command_fraction=float((actions[valid,2]<-.05).mean()) if valid.any() else None,
        opening_command_fraction=float((actions[valid,-1]<0).mean()) if valid.any() else None)
