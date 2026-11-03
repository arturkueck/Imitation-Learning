"""Broad camera baselines and fail-closed visual map expansion proposals.

All scores are geometric heuristics, never a learned information-gain guarantee.
Reference simulation must be explicitly permitted; it is never a visual fallback.
"""
from dataclasses import dataclass,asdict
import math,time
import numpy as np
from .planner import look_at
from .geometry import segment_aabb_intersection


@dataclass(frozen=True)
class SweepSettings:
    minimum_baseline_m:float=.20
    minimum_angle_deg:float=35.
    target_angle_deg:float=70.
    radii_m:tuple=(.36,.46)
    elevations_rad:tuple=(.45,.80,1.10)
    max_proposals:int=48
    maximum_seconds:float=100.
    maximum_path_attempts:int=6


def view_change(before,after,focus):
    before=np.asarray(before,float);after=np.asarray(after,float);focus=np.asarray(focus,float)
    a=before-focus;b=after-focus
    if min(np.linalg.norm(a),np.linalg.norm(b))<1e-8:raise ValueError('Camera cannot coincide with focus')
    return dict(baseline_m=float(np.linalg.norm(after-before)),
                angle_deg=float(np.degrees(np.arccos(np.clip(a@b/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))))


def broad_view(planner,focus,start,settings=None):
    settings=settings or SweepSettings();c=planner.checker;start=np.asarray(start,float);began=time.monotonic()
    audit=dict(settings=asdict(settings),proposed=0,ik_valid=0,path_attempts=0,rejections={},planning_source=c.world.source)
    def reject(reason):audit['rejections'][reason]=audit['rejections'].get(reason,0)+1
    try:
        initial=c.check(start)
        if not initial.valid:return dict(stage='blocked',reason=initial.reason,audit=audit)
        p0,R0=c.camera_pose(start);azimuth=math.atan2(*(p0-focus.center)[1::-1]);proposals=[]
        for radius in settings.radii_m:
            for elevation in settings.elevations_rad:
                for angle in [-math.pi,-2.1,-1.4,-.8,.8,1.4,2.1,math.pi]:
                    a=azimuth+angle
                    position=focus.center+radius*np.array([math.cos(elevation)*math.cos(a),math.cos(elevation)*math.sin(a),math.sin(elevation)])
                    change=view_change(p0,position,focus.center)
                    proposals.append((change['angle_deg']+change['baseline_m']*25,position))
        candidates=[]
        for _,position in sorted(proposals,key=lambda x:x[0],reverse=True)[:settings.max_proposals]:
            if time.monotonic()-began>settings.maximum_seconds*.65:break
            audit['proposed']+=1;desired=look_at(position,focus.center)
            right=R0[:,0]-desired[:,2]*np.dot(R0[:,0],desired[:,2])
            if np.linalg.norm(right)>1e-6:
                right/=np.linalg.norm(right);desired=np.column_stack([right,np.cross(desired[:,2],right),desired[:,2]])
            q=planner.ik(position,desired,start,iterations=130)
            if q is None:reject('ik_limits_self_or_environment');continue
            camera,R=c.camera_pose(q);change=view_change(p0,camera,focus.center)
            if change['baseline_m']<settings.minimum_baseline_m or change['angle_deg']<settings.minimum_angle_deg:
                reject('insufficient_view_change');continue
            delta=focus.center-camera;distance=np.linalg.norm(delta)
            if distance<=focus.radius+.08 or math.asin(min(.999,focus.radius/distance))>np.deg2rad(c.m.cam_fovy[c.camera])*.45:
                reject('target_does_not_fit_fov');continue
            end=focus.center-delta/distance*focus.radius
            if any(segment_aabb_intersection(camera,end,b,padding=.002) for b in c.world.boxes):reject('line_of_sight_occupied');continue
            # Unknown cells can be looked at, but the arm may never enter them.
            # This is only a target-view proposal; full trajectory is checked below.
            valid=c.check(q)
            if not valid.valid:reject(valid.reason);continue
            audit['ik_valid']+=1
            score=change['angle_deg']/settings.target_angle_deg+.5*change['baseline_m']/.35+min(.05,valid.clearance)-.02*np.linalg.norm(q-start)
            candidates.append(dict(q=q.copy(),camera=camera,rotation=R,change=change,score=float(score)))
        for candidate in sorted(candidates,key=lambda v:v['score'],reverse=True)[:settings.maximum_path_attempts]:
            remaining=settings.maximum_seconds-(time.monotonic()-began)
            if remaining<.5:break
            audit['path_attempts']+=1
            plan=planner.path(start,candidate['q'],max_nodes=300,seconds=min(12.,remaining))
            if plan is None:reject('whole_path_not_certified');continue
            audit['elapsed_seconds']=time.monotonic()-began
            return dict(stage='target_view',reason='largest_scored_certified_view_among_bounded_candidates',candidate=candidate,plan=plan,audit=audit)
        audit['elapsed_seconds']=time.monotonic()-began
        return dict(stage='blocked',reason='no_certified_broad_view',audit=audit)
    finally:c.set_q(start)


def unknown_in_fov(checker,q):
    """Optimistic probe utility from unknown map voxels, no hidden geometry."""
    owner=getattr(checker.world.coverage,'__self__',None)
    if owner is None or not hasattr(owner,'centers'):return 0
    p,R=checker.camera_pose(q);local=(owner.centers-p)@R;depth=-local[:,2]
    tangent=np.tan(np.deg2rad(checker.m.cam_fovy[checker.camera]/2))
    visible=(depth>.03)&(np.abs(local[:,0])<depth*tangent)&(np.abs(local[:,1])<depth*tangent)
    return int((visible&(owner.labels==2)).sum())


def inspect_or_probe(planner,focus,start,*,require_visual=True,settings=None):
    """Return a plan only through already verified arm space.

    Caller captures from the returned pose, integrates real calibrated evidence,
    snapshots a new world revision and calls again. No cells are freed here.
    """
    c=planner.checker;start=np.asarray(start,float)
    if require_visual and c.world.source=='reference':
        return dict(stage='blocked',reason='reference_geometry_is_not_visual_clearance')
    initial=c.check(start)
    if not initial.valid:
        return dict(stage='blocked',reason='initial_arm_volume_unverified',detail=initial.reason,
                    next_action='observe_from_stationary_or_fixed_cameras; no arm motion')
    result=broad_view(planner,focus,start,settings)
    if result['stage']=='target_view' or not require_visual:return result
    try:
        baseline=unknown_in_fov(c,start);probes=[]
        for joint in range(7):
            for offset in [-.12,-.06,.06,.12]:
                q=start.copy();q[joint]+=offset
                if not c.check(q).valid:continue
                unseen=unknown_in_fov(c,q)
                if unseen<=baseline:continue
                probes.append((unseen,q))
        for unseen,q in sorted(probes,key=lambda x:x[0],reverse=True)[:4]:
            plan=planner.path(start,q,max_nodes=150,seconds=5.)
            if plan is not None:
                return dict(stage='map_probe',reason='look_at_more_unknown_voxels_from_already_verified_space',plan=plan,
                            candidate=dict(q=q.copy(),optimistic_unknown_voxels=unseen),
                            requires_capture_and_new_map=True,map_version=c.world.version)
        return dict(stage='blocked',reason='no_probe_path_inside_verified_space',target_audit=result.get('audit'))
    finally:c.set_q(start)
