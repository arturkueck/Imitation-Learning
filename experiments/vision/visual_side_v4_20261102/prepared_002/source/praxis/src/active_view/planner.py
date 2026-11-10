"""Bounded IK, configuration-space planning and conservative time scaling."""
from dataclasses import dataclass
import time,math
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation
from .geometry import segment_aabb_intersection


@dataclass
class Plan:
    waypoints:list
    world_version:int
    source:str
    checks:int


class Planner:
    def __init__(self,checker,seed=42):self.checker=checker;self.rng=np.random.default_rng(seed)

    def ik(self,position,rotation,start,iterations=100):
        c=self.checker;q=np.asarray(start).copy();target=np.asarray(position)
        for _ in range(iterations):
            p,R=c.camera_pose(q);error=np.r_[target-p,Rotation.from_matrix(rotation@R.T).as_rotvec()*.35]
            if np.linalg.norm(error[:3])<.006 and np.linalg.norm(error[3:])<.035:
                return q if c.check(q).valid else None
            jp=np.zeros((3,c.m.nv));jr=jp.copy();mujoco.mj_jac(c.m,c.d,jp,jr,p,c.camera_body)
            J=np.r_[jp[:,c.dadr],jr[:,c.dadr]*.35]
            step=J.T@np.linalg.solve(J@J.T+np.eye(6)*.002**2,error)
            step=np.clip(step,-.12,.12);q=np.clip(q+step,c.limits[:,0]+.002,c.limits[:,1]-.002)
        return None

    def path(self,start,goal,max_nodes=450,seconds=20.,step=.20):
        c=self.checker;start=np.asarray(start);goal=np.asarray(goal);began=time.monotonic();checks=c.checks
        if not c.check(start).valid or not c.check(goal).valid:return None
        if c.edge(start,goal):return Plan([start,goal],c.world.version,c.world.source,c.checks-checks)
        # Bounded joint-space bridges often solve small camera detours cheaply.
        # These are proposals only; all three connecting segments are certified.
        for joint in range(7):
            for offset in (-.35,.35):
                if time.monotonic()-began>min(4.,seconds*.4):break
                a=start.copy();b=goal.copy();a[joint]+=offset;b[joint]+=offset
                if c.edge(start,a) and c.edge(a,b) and c.edge(b,goal):
                    return Plan([start,a,b,goal],c.world.version,c.world.source,c.checks-checks)
        trees=[([start.copy()],[-1]),([goal.copy()],[-1])]
        def extend(tree,target):
            nodes,parents=tree;dist=np.linalg.norm(np.asarray(nodes)-target,axis=1);idx=int(dist.argmin());delta=target-nodes[idx];length=np.linalg.norm(delta)
            candidate=target.copy() if length<=step else nodes[idx]+delta/length*step
            if not c.edge(nodes[idx],candidate):return None
            nodes.append(candidate);parents.append(idx);return len(nodes)-1
        def trace(tree,i):
            result=[]
            while i>=0:result.append(tree[0][i]);i=tree[1][i]
            return result[::-1]
        swapped=False
        while sum(len(t[0]) for t in trees)<max_nodes and time.monotonic()-began<seconds:
            target=trees[1][0][0] if self.rng.random()<.2 else self.rng.uniform(c.limits[:,0]+.005,c.limits[:,1]-.005)
            ai=extend(trees[0],target)
            if ai is not None:
                target=trees[0][0][ai]
                for _ in range(30):
                    bi=extend(trees[1],target)
                    if bi is None:break
                    if np.linalg.norm(trees[1][0][bi]-target)<1e-8:
                        a=trace(trees[0],ai);b=trace(trees[1],bi)
                        route=a+b[-2::-1]
                        if swapped:route=route[::-1]
                        # Every shortcut is independently certified.
                        for _ in range(25):
                            if len(route)<3:break
                            i,j=sorted(self.rng.choice(len(route),2,replace=False))
                            if j>i+1 and c.edge(route[i],route[j]):route=route[:i+1]+route[j:]
                        return Plan(route,c.world.version,c.world.source,c.checks-checks)
            trees=trees[::-1];swapped=not swapped
        return None


def look_at(position,target):
    z=np.asarray(position)-target;z/=np.linalg.norm(z);x=np.cross([0.,0.,1.],z)
    if np.linalg.norm(x)<1e-8:x=np.cross([0.,1.,0.],z)
    x/=np.linalg.norm(x);return np.column_stack([x,np.cross(z,x),z])


@dataclass
class Focus:
    center:np.ndarray
    radius:float=.06
    uncertainty:float=1.


def rank_views(planner,focus,start,max_candidates=18):
    c=planner.checker;current,R0=c.camera_pose(start)
    offset=current-focus.center;azimuth=math.atan2(offset[1],offset[0]);distance=float(np.clip(np.linalg.norm(offset),.23,.40))
    proposals=[]
    for angle in np.linspace(-.7,.7,6):
        for elevation in (.65,.95,1.2):
            a=azimuth+angle;pos=focus.center+distance*np.array([np.cos(elevation)*np.cos(a),np.cos(elevation)*np.sin(a),np.sin(elevation)])
            proposals.append(pos)
    candidates=[]
    for pos in proposals[:max_candidates]:
        desired=look_at(pos,focus.center)
        right=R0[:,0]-desired[:,2]*np.dot(R0[:,0],desired[:,2])
        if np.linalg.norm(right)>1e-6:
            right/=np.linalg.norm(right);desired=np.column_stack([right,np.cross(desired[:,2],right),desired[:,2]])
        q=planner.ik(pos,desired,start)
        if q is None:continue
        camera,R=c.camera_pose(q);direction=focus.center-camera;length=np.linalg.norm(direction)
        if length<focus.radius+.08:continue
        fovy=np.deg2rad(c.m.cam_fovy[c.camera]);angular_radius=np.arcsin(min(.999,focus.radius/length))
        if angular_radius>fovy*.45:continue
        # Check line of sight only up to the uncertain target region, not through it.
        visible_end=focus.center-direction/length*focus.radius
        if c.world.coverage is not None:
            owner=getattr(c.world.coverage,'__self__',None)
            if owner is None or not owner.ray_clear(camera,visible_end):continue
        if any(segment_aabb_intersection(camera,visible_end,b,padding=.002) for b in c.world.boxes):continue
        novelty=1-float(np.clip(np.dot((current-focus.center)/np.linalg.norm(current-focus.center),(camera-focus.center)/length),-1,1))
        clearance=c.check(q).clearance
        score=focus.uncertainty*(.2+novelty)*min(1.,.25**2/length**2)+min(.05,clearance)-.02*np.linalg.norm(q-start)
        candidates.append(dict(q=q,score=float(score),camera=camera,clearance=clearance,
                               expected_gain_only=True))
    return sorted(candidates,key=lambda v:v['score'],reverse=True)


def timed_samples(plan,vmax=.35,amax=.5,dt=.05):
    """Rest-to-rest quintic segments; bounded joint velocity and acceleration."""
    samples=[];clock=0.
    for a,b in zip(plan.waypoints[:-1],plan.waypoints[1:]):
        maximum=float(np.max(np.abs(b-a)))
        duration=max(.1,1.875*maximum/vmax,math.sqrt(5.774*maximum/amax))
        count=max(2,math.ceil(duration/dt)+1)
        for t in np.linspace(0,duration,count):
            u=t/duration;s=10*u**3-15*u**4+6*u**5
            samples.append((clock+t,a+(b-a)*s))
        clock+=duration
    return samples


def execute_kinematic(checker,plan,capture):
    """Simulation-only playback; recheck the current map before every move.

    Not a torque controller and not a claim about real tracking error/dynamics.
    capture receives simulated time, joints and camera pose at each sample.
    """
    if plan.world_version!=checker.world.version:raise RuntimeError('Map changed: replan required')
    previous=plan.waypoints[0]
    for stamp,q in timed_samples(plan):
        if plan.world_version!=checker.world.version:raise RuntimeError('Map changed: stopped before next move')
        if not checker.edge(previous,q):raise RuntimeError('Path no longer certified: stopped')
        if plan.world_version!=checker.world.version:raise RuntimeError('Map changed during check: stopped')
        checker.set_q(q);capture(stamp,q,checker.camera_pose(q));previous=q
