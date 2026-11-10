"""Tighter conservative motion envelopes and target-centred wrist refinement.

No learned perception, robot motion execution or visual safety fallback.
"""
from dataclasses import dataclass
import math
import numpy as np
from .side_views import aimed_pose,optical_axis_error,side_frame
from .view_sweep import view_change

def join_routes(prefix,suffix):
    """Copy/concatenate joint routes identically for lists and NumPy arrays."""
    first=[np.asarray(q,float).copy() for q in prefix];last=[np.asarray(q,float).copy() for q in suffix]
    if not first or not last:raise ValueError('Both route pieces require an endpoint')
    if any(q.shape!=first[0].shape or not np.isfinite(q).all() for q in first+last):raise ValueError('Invalid joint route')
    if np.max(np.abs(first[-1]-last[0]))>1e-8:raise ValueError('Route pieces are discontinuous')
    return first+last[1:]

def swept_envelopes(checker,start,end,pieces=128):
    """Enclose every robot/greifer/camera point throughout a linear joint edge.

    Same analytic displacement bound and margins as the prior 32-piece method;
    finer intervals reduce over-approximation, never the safety distances.
    This excludes object intersections only. Self/static edge certification is
    separately required and must share the exact geometry/configuration contract.
    """
    if not isinstance(pieces,int) or pieces<32:raise ValueError('At least 32 subdivisions required')
    low=[];high=[];start=np.asarray(start,float);end=np.asarray(end,float)
    for t in range(pieces):
        a=start+(end-start)*t/pieces;b=start+(end-start)*(t+1)/pieces
        shapes=checker.robot_boxes((a+b)/2)
        bounds=checker.radii@np.abs(b-a)/2+checker.world_margin+1e-8
        for shape,margin in zip(shapes,bounds):
            low.append(shape.vertices.min(0)-margin);high.append(shape.vertices.max(0)+margin)
    return np.asarray(low),np.asarray(high)

@dataclass(frozen=True)
class AimSettings:
    maximum_axis_error_deg:float=3.
    minimum_side_offset_m:float=.10
    minimum_baseline_m:float=.20
    maximum_side_elevation_deg:float=35.
    maximum_base_elevation_deg:float=40.
    maximum_elevated_elevation_deg:float=65.
    maximum_refinement_position_shift_m:float=.015

def view_metrics(checker,q,focus,start_camera,base,direction,settings=None):
    settings=settings or AimSettings();camera,R=checker.camera_pose(q)
    delta=camera-focus.center;distance=np.linalg.norm(delta)
    if distance<=focus.radius+.05:return None,'camera_too_close'
    error=optical_axis_error(camera,R,focus.center)
    if error>settings.maximum_axis_error_deg:return None,'optical_axis_misses_focus'
    fov=np.deg2rad(checker.m.cam_fovy[checker.camera]/2)
    if np.deg2rad(error)+np.arcsin(min(.999,focus.radius/distance))>fov*.96:return None,'focus_does_not_fit'
    axis=side_frame(base,focus.center)['left' if direction=='elevated' else direction]
    if delta@axis<settings.minimum_side_offset_m:return None,'wrong_requested_side'
    elevation=float(np.degrees(np.arctan2(delta[2],np.linalg.norm(delta[:2]))))
    limit=settings.maximum_elevated_elevation_deg if direction=='elevated' else settings.maximum_base_elevation_deg if direction=='base' else settings.maximum_side_elevation_deg
    if elevation>limit:return None,'requested_view_too_high'
    change=view_change(start_camera,camera,focus.center)
    if change['baseline_m']<settings.minimum_baseline_m:return None,'insufficient_translation'
    return dict(camera=camera,rotation=R,optical_axis_error_deg=error,elevation_deg=elevation,change=change),None

def refine_view(planner,focus,start_camera,base,direction,seed,settings=None):
    """Keep bank camera position; counter-aim at current predicted focus.

    Returned suffix is certified against the provided full world. Caller must
    independently certify the complete prefix from its current start state.
    No alternative direction is silently substituted.
    """
    settings=settings or AimSettings();checker=planner.checker;seed=np.asarray(seed,float)
    original=checker.q0.copy();seed_camera,seed_R=checker.camera_pose(seed)
    candidates=[];rejections=[]
    try:
        if not checker.check(seed).valid:return dict(stage='blocked',reason='bank_endpoint_not_free')
        # Already well-aimed candidates need no added motion.
        metrics,why=view_metrics(checker,seed,focus,start_camera,base,direction,settings)
        if metrics is not None:return dict(stage='aimed',q=seed,metrics=metrics,suffix=[seed],refined=False)
        desired=aimed_pose(seed_camera,focus.center)
        # Match camera roll to the current wrist before testing alternatives.
        roll=math.atan2(float(desired[:,1]@seed_R[:,0]),float(desired[:,0]@seed_R[:,0]))
        for angle in [roll,roll+.25,roll-.25]:
            q=planner.ik(seed_camera,aimed_pose(seed_camera,focus.center,angle),seed,iterations=120)
            if q is None:rejections.append('refinement_ik_or_endpoint_collision');continue
            metrics,why=view_metrics(checker,q,focus,start_camera,base,direction,settings)
            if metrics is None:rejections.append(why);continue
            if np.linalg.norm(metrics['camera']-seed_camera)>settings.maximum_refinement_position_shift_m:
                rejections.append('refinement_translation_too_large');continue
            if not checker.edge(seed,q):rejections.append('refinement_suffix_not_certified');continue
            candidates.append((metrics['optical_axis_error_deg']+.1*np.linalg.norm(q-seed),q,metrics))
        if not candidates:return dict(stage='blocked',reason='no_target_centred_refinement',rejections=rejections)
        _,q,metrics=min(candidates,key=lambda v:v[0])
        return dict(stage='aimed',q=q,metrics=metrics,suffix=[seed,q],refined=True,rejections=rejections)
    finally:checker.set_q(original)
