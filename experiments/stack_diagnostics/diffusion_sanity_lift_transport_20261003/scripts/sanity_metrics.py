"""Predeclared short-transport criterion in original simulator units."""
import numpy as np
def first(mask,n=3):
    ids=np.flatnonzero(np.convolve(np.asarray(mask,dtype=int),np.ones(n,dtype=int),'valid')==n) if len(mask)>=n else []
    return int(ids[0]) if len(ids) else None
def metrics(t):
    held=t[:,34]>0;z=t[:,6];p=t[:,4:6];goal=t[:,1:3]-p
    vel=np.vstack([np.zeros(2),np.diff(p,axis=0)/.05]);speed=np.linalg.norm(vel,axis=1)
    cosine=(vel*goal).sum(1)/np.maximum(speed*np.linalg.norm(goal,axis=1),1e-9)
    lift=first(held&(z>.88));start=first(held&(z>.98)&(speed>.02)&(cosine>.5))
    success=False;progress=0.;fraction=None;moving=0;action_cos=None;motion_cos=None
    active=held&(z>.98)&(np.linalg.norm(t[:,20:22],axis=1)>.01)
    if active.any():
        a=t[active,20:22];v=goal[active]
        action_cos=float(np.mean((a*v).sum(1)/np.maximum(np.linalg.norm(a,axis=1)*np.linalg.norm(v,axis=1),1e-9)))
    if lift is not None and start is not None and lift<start:
        ref=max(0,start-1);unit=goal[ref]/max(float(np.linalg.norm(goal[ref])),1e-9)
        progress=float((p[-1]-p[ref])@unit);mask=speed[start:]>.005;moving=int(mask.sum())
        fraction=float((cosine[start:][mask]>.5).mean()) if moving else None
        motion_cos=float(cosine[start:][mask].mean()) if moving else None
        success=bool(progress>=.02 and held[start:].all() and (z[start:]>.98).all() and moving>=3 and fraction>=.8)
    return dict(simplified_success=success,grasp_success=bool(held.any()),lift_success=lift is not None,transport_started_sanity=start is not None,lift_frame=lift,transport_frame=start,projected_transport_m=progress,correct_motion_fraction=fraction,motion_goal_cosine_mean=motion_cos,moving_transport_frames=moving,xy_action_goal_cosine_mean=action_cos,max_object_height_m=float(z.max()))
