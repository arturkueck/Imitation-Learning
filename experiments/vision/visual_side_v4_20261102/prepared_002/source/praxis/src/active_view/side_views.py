"""Requested lateral/back inspection poses; translation and optical aim are coupled."""
from dataclasses import dataclass,asdict
import time,math
import numpy as np
from .planner import look_at
from .view_sweep import view_change
from .geometry import segment_aabb_intersection


@dataclass(frozen=True)
class SideSettings:
    distances_m:tuple=(.22,.28,.35,.42)
    heights_above_focus_m:tuple=(.07,.11,.15)
    minimum_camera_world_z:float=.92
    maximum_elevation_deg:float=25.
    maximum_axis_error_deg:float=3.
    maximum_seconds:float=90.
    maximum_path_attempts:int=4
    ik_seed_attempts:int=6


def side_frame(base,focus):
    forward=np.asarray(focus,float)-np.asarray(base,float);forward[2]=0
    if np.linalg.norm(forward)<1e-6:raise ValueError('Base and focus need distinct horizontal positions')
    forward/=np.linalg.norm(forward);right=np.cross(forward,[0.,0.,1.])
    return {'right':right,'left':-right,'base':-forward}


def aimed_pose(position,focus,roll=0.):
    R=look_at(np.asarray(position,float),np.asarray(focus,float))
    c,s=math.cos(roll),math.sin(roll)
    # Roll changes hand posture while preserving the optical axis (-Z).
    return R@np.array([[c,-s,0],[s,c,0],[0,0,1.]])


def optical_axis_error(position,rotation,focus):
    direction=np.asarray(focus)-position;direction=direction/np.linalg.norm(direction)
    return float(np.degrees(np.arccos(np.clip((-rotation[:,2])@direction,-1,1))))


def side_view(planner,focus,start,base_position,direction,settings=None):
    settings=settings or SideSettings();c=planner.checker;start=np.asarray(start,float);began=time.monotonic()
    axes=side_frame(base_position,focus.center)
    if direction not in axes:raise ValueError('direction must be right, left or base')
    axis=axes[direction];audit=dict(direction=direction,settings=asdict(settings),proposed=0,ik_valid=0,path_attempts=0,rejections={},source=c.world.source)
    def reject(reason):audit['rejections'][reason]=audit['rejections'].get(reason,0)+1
    try:
        valid=c.check(start)
        if not valid.valid:return dict(stage='blocked',reason=valid.reason,audit=audit)
        initial,R0=c.camera_pose(start);positions=[]
        seeds=[start.copy()];rng=np.random.default_rng(9642211)
        for attempt in range(36):
            if len(seeds)>=settings.ik_seed_attempts:break
            q=np.clip(start+rng.normal(0,.25+.02*attempt,7),c.limits[:,0]+.02,c.limits[:,1]-.02)
            if c.check(q).valid:seeds.append(q)
        audit['ik_seed_count']=len(seeds)
        for radius in settings.distances_m:
            for height in settings.heights_above_focus_m:
                p=focus.center+axis*radius;p[2]=max(settings.minimum_camera_world_z,focus.center[2]+height)
                elevation=float(np.degrees(np.arctan2(p[2]-focus.center[2],np.linalg.norm((p-focus.center)[:2]))))
                distance=np.linalg.norm(p-focus.center)
                if elevation>settings.maximum_elevation_deg:continue
                if np.arcsin(min(.999,focus.radius/distance))>np.deg2rad(c.m.cam_fovy[c.camera])*.45:continue
                positions.append((elevation,radius,p))
        candidates=[]
        # Low, close, target-centred views are the objective, not largest travel.
        for elevation,radius,p in sorted(positions,key=lambda v:v[0]*.6+v[1]*30):
            for roll in [0.,math.pi/2,-math.pi/2,math.pi]:
                if time.monotonic()-began>settings.maximum_seconds*.65:break
                audit['proposed']+=1;R=aimed_pose(p,focus.center,roll)
                q=None
                for seed in seeds:
                    q=planner.ik(p,R,seed,iterations=160)
                    if q is not None:break
                if q is None:reject('ik_limits_self_or_environment');continue
                camera,actualR=c.camera_pose(q);error=optical_axis_error(camera,actualR,focus.center)
                delta=focus.center-camera;distance=np.linalg.norm(delta)
                actual_elevation=float(np.degrees(np.arctan2(camera[2]-focus.center[2],np.linalg.norm((camera-focus.center)[:2]))))
                if error>settings.maximum_axis_error_deg:reject('actual_optical_axis_misses_focus');continue
                if actual_elevation>settings.maximum_elevation_deg+1:reject('actual_view_too_high');continue
                if (camera-focus.center)@axis<.15:reject('actual_camera_not_on_requested_side');continue
                end=focus.center-delta/distance*focus.radius
                if any(segment_aabb_intersection(camera,end,b,padding=.002) for b in c.world.boxes):reject('focus_occluded_before_target_region');continue
                if np.arcsin(min(.999,focus.radius/distance))+np.deg2rad(error)>np.deg2rad(c.m.cam_fovy[c.camera])*.48:reject('actual_fov_does_not_fit_focus');continue
                audit['ik_valid']+=1
                score=-actual_elevation*.8-distance*25-.05*np.linalg.norm(q-start)+min(.05,c.check(q).clearance)
                candidates.append(dict(q=q.copy(),camera=camera,rotation=actualR,direction=direction,
                    elevation_deg=actual_elevation,optical_axis_error_deg=error,distance_to_focus_m=float(distance),
                    optical_axis=(-actualR[:,2]).copy(),focus=focus.center.copy(),roll_rad=roll,score=float(score),
                    change=view_change(initial,camera,focus.center)))
        for candidate in sorted(candidates,key=lambda v:v['score'],reverse=True)[:settings.maximum_path_attempts]:
            remaining=settings.maximum_seconds-(time.monotonic()-began)
            if remaining<.5:break
            audit['path_attempts']+=1;plan=planner.path(start,candidate['q'],max_nodes=350,seconds=min(15.,remaining))
            if plan is not None:
                audit['elapsed_seconds']=time.monotonic()-began
                return dict(stage='target_view',reason='side_translation_and_counter_aim_validated',candidate=candidate,plan=plan,audit=audit)
            reject('whole_path_not_certified')
        audit['elapsed_seconds']=time.monotonic()-began
        return dict(stage='blocked',reason='requested_side_view_unreachable_or_uncertified',audit=audit)
    finally:c.set_q(start)
