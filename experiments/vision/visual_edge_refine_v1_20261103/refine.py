"""Bounded cuboid refinement with held-out RGB gate; never receives GT geometry."""
import numpy as np
from scipy.optimize import least_squares
from geometry import edge_samples,visible,pixel_errors,decode_delta,surface_distance
from tracking import edges

def prepare_views(images,cameras,ids,initial,all_boxes):
    points=edge_samples(initial);result=[]
    for i in ids:
        keep=visible(points,cameras[i],all_boxes)
        if keep.sum()>=8:
            result.append((cameras[i],edges(images[i])[2],np.flatnonzero(keep)))
    return result

def data_residual(box,views,points3d):
    points=edge_samples(box);values=[pixel_errors(points[ids],camera,distance) for camera,distance,ids in views]
    if len(points3d):values.append(surface_distance(points3d,box)/.0015)
    return np.concatenate(values) if values else np.array([20.])

def score(box,views):
    if not views:return None
    # Freeze support and penalty for out-of-image projections; cannot hide edges to win.
    values=np.concatenate([pixel_errors(edge_samples(box)[ids],c,d) for c,d,ids in views])
    return float(np.mean(np.minimum(values,10.)))

def fit_one(initial,all_boxes,images,cameras,fit_ids,points3d):
    views=prepare_views(images,cameras,fit_ids,initial,all_boxes)
    if len(points3d)<6 or len(views)<3:return dict(candidate=initial,status='insufficient_geometric_support',evaluations=0,fit_views=len(views))
    scale=np.array([.008]*3+[.10]*3+[.12]*3)
    def residual(delta):
        box=decode_delta(initial,delta)
        return np.r_[data_residual(box,views,points3d),delta/scale]
    bounds=np.array([.015]*3+[np.deg2rad(10)]*3+[np.log(1.15)]*3)
    fit=least_squares(residual,np.zeros(9),bounds=(-bounds,bounds),loss='soft_l1',f_scale=2.,max_nfev=35,x_scale=scale)
    box=decode_delta(initial,fit.x)
    if not np.all(np.isfinite(fit.x)):return dict(candidate=initial,status='nonfinite',evaluations=int(fit.nfev),fit_views=len(views))
    return dict(candidate=box,status='fitted' if fit.success else 'iteration_limit',evaluations=int(fit.nfev),fit_views=len(views),fit_score_before=score(initial,views),fit_score_after=score(box,views),delta=fit.x)

def gate(initial,candidate,heldout_views,anchor_views,support):
    before=score(initial,heldout_views);after=score(candidate,heldout_views)
    anchor_before=score(initial,anchor_views);anchor_after=score(candidate,anchor_views)
    reasons=[]
    if support<6:reasons.append('insufficient_tracks')
    if len(heldout_views)<3:reasons.append('insufficient_heldout_views')
    if before is None or after is None or after>before*.95 or before-after<.05:reasons.append('heldout_not_improved')
    if anchor_before is None or anchor_after is None or anchor_after>anchor_before+.25:reasons.append('initial_views_degraded')
    if np.linalg.norm(candidate['position']-initial['position'])>.015:reasons.append('position_change_too_large')
    return dict(accepted=not reasons,reasons=reasons,heldout_before=before,heldout_after=after,anchor_before=anchor_before,anchor_after=anchor_after,tracks=support)
