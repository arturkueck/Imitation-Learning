"""Frozen V3 request features, paired labels and bounded prefix contexts.

NN features consume observations and calibrated robot planning only. GT and
future images are restricted to offline labels / post-decision evaluation.
"""
from pathlib import Path
import sys,itertools
import numpy as np
import torch
from scipy.optimize import linear_sum_assignment
HERE=Path(__file__).resolve().parent; ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
from learning import decode
from ensemble_uncertainty import group_predictions,corner_distance
from model_v3 import context_arrays,tensor_context,predict


def contexts(data,ids,history):
    # History is explicitly acquired in chronological order. Current fixed
    # cameras follow the last acquisition; M2 keeps at most three wrist images.
    current=history[-1] if history else 0
    return context_arrays(data,ids,'M2',current=current,
                          history=[list(reversed(history)) for _ in ids])


def infer(models,data,ids,history):
    a=contexts(data,ids,history); b=tensor_context(a)
    outputs=[]
    with torch.inference_mode():
        for model in models:
            raw,_=predict(model,b)
            outputs.append({k:v.detach().cpu().numpy() for k,v in decode(raw).items()})
    return [[{k:v[j] for k,v in output.items()} for output in outputs] for j in range(len(ids))]


def observed(predictions,history_length):
    groups=group_predictions(predictions)
    x=np.zeros(23,np.float32);x[20]=history_length;x[21]=-1
    if groups:
        # Fixed GT-free focus rule; no error or hidden object identity.
        g=max(groups,key=lambda v:(3-v['support'],v['spread_mm']))
        x[:3]=g['position'];x[3:6]=g['size']
        x[6:12]=g['rotation'][:,:2].T.reshape(-1)
        x[12]=g['min_detection_score'];x[13]=g['support']/3
        x[14:17]=g['axis_std_mm']/1000;x[17:20]=g['visibility'];x[22]=1
    return x


def candidate_features(observation,data,i,history,T_world_base):
    current=history[-1];q0=data['joint_positions'][i,0];q=data['joint_positions'][i,current]
    Rbw=T_world_base[:3,:3].T; origin=T_world_base[:3,3]
    rows=[]
    for p in range(6):
        pos=data['camera_positions'][i,p,2];R=data['camera_rotations'][i,p,2]@np.diag([1.,-1.,-1.])
        posbase=Rbw@(pos-origin);Rbase=Rbw@R
        direction=observation[:3]-pos if observation[22] else np.zeros(3)
        distance=np.linalg.norm(direction)
        if distance:direction=Rbw@direction/distance
        motion=float(np.linalg.norm(q-q0)+np.linalg.norm(data['joint_positions'][i,p]-q0))
        seconds=motion/.5
        valid=bool(data['valid'][i,p]) and p>current and p not in history
        rows.append(np.r_[posbase,Rbase[:,:2].T.reshape(-1),direction,distance,motion,
                          data['expected_robot_occlusion'][i,p],1.,1.+.2*seconds,float(valid)])
    return np.asarray(rows,np.float32)


def observable(data,i,history):
    p=history[-1]
    vis=data['visibility'][i,p,:,:2].max(-1)
    for h in history:vis=np.maximum(vis,data['visibility'][i,h,:,2])
    return data['active'][i]&(vis>=.05)


def scene_error(prediction,data,i,mask):
    """Frozen PLAN equivalent-mm set error, with FP/FN and physical corners."""
    ids=np.flatnonzero(mask); pi=np.flatnonzero(prediction['probability']>=.5)
    costs=np.full(len(ids),62.5); used=set();position=[];corners=[]
    if len(ids) and len(pi):
        dist=np.linalg.norm(prediction['position'][pi,None]-data['positions'][i,ids][None],axis=-1)
        aa,bb=linear_sum_assignment(dist)
        for a,b in zip(aa,bb):
            if dist[a,b]>.05:continue
            j=int(pi[a]);g=int(ids[b]);used.add(j)
            pp={k:prediction[k][j] for k in ['position','size','rotation']}
            gg=dict(position=data['positions'][i,g],size=data['sizes'][i,g],rotation=data['rotations'][i,g])
            ce=corner_distance(pp,gg)*1000;pe=dist[a,b]*1000
            costs[b]=min(50.,pe)+.25*min(50.,ce);position.append(float(pe));corners.append(float(ce))
    fp=len(pi)-len(used);fn=len(ids)-len(used)
    return dict(error_mm=float((costs.sum()+50*fp)/max(1,len(ids))),missing=fn,extra=fp,
                observable=len(ids),matched=len(used),position_mm=position,corner_rmse_mm=corners)


def errors(predictions,data,i,mask):
    return [scene_error(p,data,i,mask) for p in predictions]


def mean_error(predictions,data,i,mask):
    return float(np.mean([r['error_mm'] for r in errors(predictions,data,i,mask)]))


def robot_projection(box_vertices,positions,rotations,fovy=45.):
    """Conservative robot-only projected rectangle union; no object segmentation.

    Uses known robot collision geometry and camera calibration. This is an
    expected robot occlusion proxy, not the GT robot_fraction diagnostic.
    """
    answer=[];f=80/np.tan(np.deg2rad(fovy/2))
    for pos,R in zip(positions[:2],rotations[:2]):
        mask=np.zeros((160,160),bool)
        for vertices in box_vertices:
            local=(vertices-pos)@R;front=-local[:,2]
            if np.all(front<=.001):continue
            if np.any(front<=.001):mask[:]=True;break
            pixels=np.c_[80+f*local[:,0]/front,80-f*local[:,1]/front]
            lo=np.maximum(0,np.floor(pixels.min(0))).astype(int)
            hi=np.minimum(159,np.ceil(pixels.max(0))).astype(int)
            if np.all(hi>=lo):mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1]=True
        answer.append(mask.mean())
    return np.asarray(answer,np.float32)


def permitted_histories():
    return [(0,)]+[(0,p) for p in range(1,6)]+[(0,p,q) for p in range(1,6) for q in range(p+1,6)]


def summarize_binary(prob,y,threshold=.5):
    chosen=np.asarray(prob)>=threshold;y=np.asarray(y,dtype=bool)
    tp=int((chosen&y).sum());fp=int((chosen&~y).sum());fn=int((~chosen&y).sum())
    bins=[]
    for low in np.linspace(0,.9,10):
        at=(prob>=low)&(prob<(low+.1 if low<.9 else 1.001))
        bins.append(dict(low=float(low),n=int(at.sum()),probability=float(prob[at].mean()) if at.any() else None,
                         positive_fraction=float(y[at].mean()) if at.any() else None))
    return dict(tp=tp,fp=fp,fn=fn,positives=int(y.sum()),n=len(y),
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                brier=float(np.mean((prob-y)**2)),reliability=bins)
