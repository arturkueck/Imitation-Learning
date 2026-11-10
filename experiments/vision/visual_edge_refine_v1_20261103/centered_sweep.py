"""Camera-centred joint trajectories. Existing checker is reused unchanged."""
import numpy as np
from scipy.spatial.transform import Rotation
from geometry import corners,project

def transport_rotation(position,target,previous):
    z=np.asarray(position)-target;z/=np.linalg.norm(z)
    x=previous[:,0]-z*(previous[:,0]@z)
    if np.linalg.norm(x)<1e-8:x=np.cross([0.,1.,0.],z)
    x/=np.linalg.norm(x);return np.column_stack([x,np.cross(z,x),z])

def orbit_positions(start,target,base,side,angle_deg,count):
    delta=np.asarray(start)-target;r=np.linalg.norm(delta);forward=delta/r
    lateral=np.cross([0.,0.,1.],target-base)
    lateral=lateral-forward*(lateral@forward)
    if np.linalg.norm(lateral)<1e-7:lateral=np.cross(forward,[1.,0.,0.])
    if np.linalg.norm(lateral)<1e-7:lateral=np.cross(forward,[0.,1.,0.])
    lateral/=np.linalg.norm(lateral);sign=1 if side=='left' else -1
    a=np.linspace(0,np.deg2rad(angle_deg)*sign,count)
    return target+r*(np.cos(a)[:,None]*forward+np.sin(a)[:,None]*lateral)

def aim_metrics(checker,q,target,boxes,width=320):
    p,R=checker.camera_pose(q);delta=target-p;delta/=np.linalg.norm(delta)
    axis=float(np.degrees(np.arccos(np.clip((-R[:,2])@delta,-1,1))))
    f=width/2/np.tan(np.deg2rad(checker.m.cam_fovy[checker.camera]/2))
    camera=dict(position=p,rotation=R,f=f,cx=width/2,cy=width/2,width=width,height=width)
    uv,z=project(np.concatenate([corners(b) for b in boxes]),camera)
    margin=width*.035;inside=(z>.02)&(uv[:,0]>=margin)&(uv[:,0]<=width-margin)&(uv[:,1]>=margin)&(uv[:,1]<=width-margin)
    return dict(axis_error_deg=axis,group_in_frame=bool(inside.all()),position=p,rotation=R)

def aimed_ik(checker,position,rotation,start):
    import mujoco
    q=np.array(start,copy=True)
    for _ in range(160):
        p,R=checker.camera_pose(q);translation=position-p;rot=Rotation.from_matrix(rotation@R.T).as_rotvec()
        if np.linalg.norm(translation)<.001 and np.linalg.norm(rot)<.015:return q if checker.check(q).valid else None
        jp=np.zeros((3,checker.m.nv));jr=jp.copy();mujoco.mj_jac(checker.m,checker.d,jp,jr,p,checker.camera_body)
        J=np.r_[jp[:,checker.dadr],jr[:,checker.dadr]*.35];error=np.r_[translation,rot*.35]
        step=J.T@np.linalg.solve(J@J.T+np.eye(6)*.003**2,error)
        q=np.clip(q+np.clip(step,-.08,.08),checker.limits[:,0]+.002,checker.limits[:,1]-.002)
    return None

def centered_start(checker,start,focus,boxes):
    p,R=checker.camera_pose(start);delta=p-focus['center'];distance=np.linalg.norm(delta)
    minimum=focus['radius']/np.sin(np.deg2rad(checker.m.cam_fovy[checker.camera]/2)*.85)
    wanted=focus['center']+delta/distance*max(distance,minimum)
    desired=transport_rotation(wanted,focus['center'],R);q=aimed_ik(checker,wanted,desired,start)
    if q is None:return dict(status='blocked',reason='initial_centering_ik_failed')
    metrics=aim_metrics(checker,q,focus['center'],boxes)
    if metrics['axis_error_deg']>1.5 or not metrics['group_in_frame']:return dict(status='blocked',reason='initial_group_not_framed')
    # Existing path planner/edge checker, no new collision backend.
    from active_view.planner import Planner
    plan=Planner(checker).path(start,q,max_nodes=80,seconds=3.)
    if plan is None:return dict(status='blocked',reason='initial_centering_path_unavailable')
    return dict(status='centered',start=q,alignment=plan.waypoints,metrics=metrics)

def plan_sweep(checker,start,focus,boxes,base,side,frames):
    p,R=checker.camera_pose(start);attempts=[]
    for angle in [28.,20.,14.]:
        positions=orbit_positions(p,focus['center'],base,side,angle,frames);route=[np.array(start,copy=True)];metrics=[aim_metrics(checker,start,focus['center'],boxes)];previous=R.copy();reason=None
        for position in positions[1:]:
            if position[2]<focus['table_height']+.10:reason='camera_below_workspace_margin';break
            desired=transport_rotation(position,focus['center'],previous);q=aimed_ik(checker,position,desired,route[-1])
            if q is None:reason='aimed_ik_failed';break
            check=aim_metrics(checker,q,focus['center'],boxes)
            if check['axis_error_deg']>1.5 or not check['group_in_frame']:reason='group_framing_failed';break
            if not checker.edge(route[-1],q):reason='existing_edge_checker_rejected';break
            route.append(q);metrics.append(check);previous=check['rotation']
        attempts.append(dict(angle_deg=angle,reason=reason,solved_points=len(route)))
        if reason is None:
            actual=metrics[-1]['position'];baseline=float(np.linalg.norm(actual-p))
            if baseline<.08:attempts[-1]['reason']='insufficient_baseline';continue
            return dict(status='planned',side=side,angle_deg=angle,outbound=np.array(route),return_path=np.array(route[::-1]),metrics=metrics,baseline_m=baseline,attempts=attempts)
    checker.set_q(start);return dict(status='blocked',side=side,attempts=attempts,reason='no_complete_centered_sweep')
