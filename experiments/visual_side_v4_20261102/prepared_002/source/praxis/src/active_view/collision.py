"""Whole-arm state/edge checking with explicit world provenance and no fallback."""
from dataclasses import dataclass,field
import math,time
import numpy as np
import mujoco
from .geometry import Box,Hull,hull_data,convex_gap


@dataclass
class World:
    boxes: list
    planes: list=field(default_factory=list)
    bounds: np.ndarray|None=None
    version: int=1
    source: str='visual'
    complete: bool=False
    timestamp: float=field(default_factory=time.monotonic)
    max_age: float|None=2.
    # For visual maps, this callback checks occupied AND unknown volume.
    coverage: object=None


@dataclass
class Check:
    valid: bool
    clearance: float
    reason: str
    pair: tuple=()


class ArmChecker:
    def __init__(self,model,data,world,*,world_margin=.010,self_margin=.002,slabs=4,camera_half=(.018,.013,.013)):
        self.m=model;self.d=data;self.world=world;self.world_margin=world_margin;self.self_margin=self_margin
        self.joints=[i for i in range(model.njnt) if (self.name(mujoco.mjtObj.mjOBJ_JOINT,i)).startswith('robot0_joint')]
        if len(self.joints)!=7:raise ValueError('This adapter requires the 7-DoF Panda arm')
        self.qadr=np.array([model.jnt_qposadr[i] for i in self.joints]);self.dadr=np.array([model.jnt_dofadr[i] for i in self.joints])
        self.limits=model.jnt_range[self.joints].copy();self.frozen=data.qpos.copy();self.q0=data.qpos[self.qadr].copy()
        locked=[i for i in range(model.njnt) if self.name(mujoco.mjtObj.mjOBJ_JOINT,i).startswith('gripper0_')]
        self.locked_limits_ok=all(model.jnt_range[i,0]-1e-8<=self.frozen[model.jnt_qposadr[i]]<=model.jnt_range[i,1]+1e-8 for i in locked)
        self.camera=model.camera('robot0_eye_in_hand').id;self.camera_body=int(model.cam_bodyid[self.camera])
        self.local=[];self.geom_ids=[]
        for gid in range(model.ngeom):
            name=self.name(mujoco.mjtObj.mjOBJ_GEOM,gid)
            if not name.startswith(('robot0_','gripper0_')) or not (model.geom_contype[gid] or model.geom_conaffinity[gid]):continue
            self.geom_ids.append(gid);body=int(model.geom_bodyid[gid]);kind=int(model.geom_type[gid])
            if kind==int(mujoco.mjtGeom.mjGEOM_MESH):
                mid=model.geom_dataid[gid];v=model.mesh_vert[model.mesh_vertadr[mid]:model.mesh_vertadr[mid]+model.mesh_vertnum[mid]]
                shape=hull_data(v)
            elif kind==int(mujoco.mjtGeom.mjGEOM_BOX):shape=hull_data(Box(np.zeros(3),model.geom_size[gid].copy(),np.eye(3)).corners())
            else:raise ValueError(f'Unsupported robot collision geometry: {name}/{kind}')
            self.local.append(dict(**shape,name=name,body=body,geom=gid))
        # Physical camera housing proxy, not a zero-volume camera point.
        q=model.cam_quat[self.camera];cameraR=np.empty(9);mujoco.mju_quat2Mat(cameraR,q)
        self.local.append(dict(center=model.cam_pos[self.camera]+cameraR.reshape(3,3)@np.array([0.,0.,.012]),half=np.array(camera_half),rotation=cameraR.reshape(3,3),name='camera_housing_proxy',body=self.camera_body,geom=-1))
        # Conservative mounting bracket from flange frame to optical camera frame.
        p=model.cam_pos[self.camera];length=np.linalg.norm(p)
        if length>1e-6:
            z=p/length;helper=np.array([0.,0.,1.]) if abs(z[2])<.8 else np.array([0.,1.,0.]);x=np.cross(helper,z);x/=np.linalg.norm(x);y=np.cross(z,x)
            self.local.append(dict(center=p/2,half=np.array([.006,.006,length/2]),rotation=np.column_stack([x,y,z]),name='camera_mount_proxy',body=self.camera_body,geom=-1))
        for item in self.local:
            if 'vertices' not in item:
                shape=hull_data(Box(item['center'],item['half'],item['rotation']).corners())
                item.update(shape)
        self.self_pairs=[];self.exclusions=[]
        for i in range(len(self.local)):
            for j in range(i):
                a=self.local[i];b=self.local[j]
                if a['geom']==b['geom'] and a['geom']>=0:continue
                wa=int(model.body_weldid[a['body']]);wb=int(model.body_weldid[b['body']])
                pa=self.weld_parent(wa);pb=self.weld_parent(wb)
                adjacent=(pa==wb or pb==wa) and a['geom']>=0 and b['geom']>=0
                if wa==wb or adjacent:
                    self.exclusions.append((a['name'],b['name'],'same rigid assembly / adjacent joint attachment'));continue
                self.self_pairs.append((i,j))
        self.radii=np.zeros((len(self.local),7))
        for i,box in enumerate(self.local):
            # Global displacement bound for every point in this envelope.
            extent=np.linalg.norm(box['center'])+np.linalg.norm(box['half'])
            if box['geom']>=0:extent+=np.linalg.norm(model.geom_pos[box['geom']])
            for k,jid in enumerate(self.joints):
                jointbody=int(model.jnt_bodyid[jid]);body=box['body'];distance=extent
                while body!=jointbody and body!=0:
                    distance+=np.linalg.norm(model.body_pos[body])
                    for ji in range(model.body_jntadr[body],model.body_jntadr[body]+model.body_jntnum[body]):
                        if ji>=0 and model.jnt_type[ji]==mujoco.mjtJoint.mjJNT_SLIDE:distance+=max(abs(model.jnt_range[ji]))
                    body=int(model.body_parentid[body])
                if body==jointbody:self.radii[i,k]=distance+np.linalg.norm(model.jnt_pos[jid])
        self.checks=0;self.last_boxes=[]

    def name(self,kind,index):return mujoco.mj_id2name(self.m,kind,index) or ''
    def weld_parent(self,weld):
        if weld==0:return -1
        p=int(self.m.body_parentid[weld]);return int(self.m.body_weldid[p])
    def set_q(self,q):
        self.d.qpos[:]=self.frozen;self.d.qpos[self.qadr]=q;self.d.qvel[:]=0;mujoco.mj_forward(self.m,self.d)
    def robot_boxes(self,q):
        self.set_q(q);out=[]
        for b in self.local:
            if b['geom']>=0:R=self.d.geom_xmat[b['geom']].reshape(3,3);c=self.d.geom_xpos[b['geom']]
            else:R=self.d.xmat[b['body']].reshape(3,3);c=self.d.xpos[b['body']]
            out.append(Hull(c+R@b['center'],b['half'],R@b['rotation'],b['name'],b['body'],b['geom'],
                            b['vertices']@R.T+c,b['normals']@R.T,b['edges']@R.T))
        self.last_boxes=out;return out
    def check(self,q):
        self.checks+=1;q=np.asarray(q,dtype=float)
        if not self.locked_limits_ok:return Check(False,-math.inf,'locked_gripper_joint_limit')
        if q.shape!=(7,) or not np.isfinite(q).all():return Check(False,-math.inf,'invalid_joint_vector')
        if (q<self.limits[:,0]+1e-5).any() or (q>self.limits[:,1]-1e-5).any():return Check(False,-math.inf,'joint_limit')
        if self.world.source!='reference' and self.world.coverage is None:return Check(False,-math.inf,'unknown_world_coverage')
        owner=getattr(self.world.coverage,'__self__',None)
        if owner is not None and getattr(owner,'version',self.world.version)!=self.world.version:return Check(False,-math.inf,'map_revision_changed')
        if self.world.source!='reference' and (self.world.max_age is None or self.world.max_age<=0):return Check(False,-math.inf,'invalid_map_freshness_policy')
        if self.world.max_age is not None and time.monotonic()-self.world.timestamp>self.world.max_age:return Check(False,-math.inf,'stale_world_map')
        boxes=self.robot_boxes(q);minimum=math.inf;pair=()
        for i,j in self.self_pairs:
            gap=convex_gap(boxes[i],boxes[j])-self.self_margin
            if gap<minimum:minimum=gap;pair=(boxes[i].name,boxes[j].name)
            if gap<=0:return Check(False,gap,'self_collision_or_margin',pair)
        for a in boxes:
            for b in self.world.boxes:
                # Fixed mounting contacts are an explicit mechanical allowance,
                # never an allowance for table, obstacles or unknown cells.
                if b.name.startswith('fixed_mount0_') and a.name.startswith('robot0_link0_'):continue
                gap=convex_gap(a,b)-self.world_margin
                if gap<minimum:minimum=gap;pair=(a.name,b.name)
                if gap<=0:return Check(False,gap,'world_collision_or_margin',pair)
            for normal,offset,name in self.world.planes:
                gap=float(np.dot(a.center,normal)-np.abs(normal@a.rotation)@a.half-offset)-self.world_margin
                if gap<minimum:minimum=gap;pair=(a.name,name)
                if gap<=0:return Check(False,gap,'plane_collision_or_margin',pair)
            if self.world.bounds is not None:
                low,high=self.world.bounds;extent=np.abs(a.rotation)@a.half
                gap=float(min(np.min(a.center-extent-low),np.min(high-a.center-extent)))-self.world_margin
                if gap<minimum:minimum=gap;pair=(a.name,'map_boundary')
                if gap<=0:return Check(False,gap,'outside_verified_map',pair)
            if self.world.coverage is not None:
                gap,why=self.world.coverage(a,self.world_margin)
                if gap<minimum:minimum=gap;pair=(a.name,why)
                if gap<=0:return Check(False,gap,why,pair)
        return Check(True,minimum,'free',pair)

    def motion_bound(self,a,b):return float(np.max(self.radii@np.abs(np.asarray(b)-a)))

    def edge(self,start,end,max_depth=18):
        """Certify the entire linear joint segment by clearance / motion bounds.

        Both moving bodies of a self-collision pair can move, hence factor 2.
        Refuse uncertified segments; do not accept a fixed sparse sample grid.
        """
        version=self.world.version
        if not self.check(start).valid or not self.check(end).valid:return False
        def recurse(a,b,depth):
            if self.world.version!=version:return False
            mid=(a+b)/2;check=self.check(mid)
            if not check.valid:return False
            if check.clearance>2*self.motion_bound(mid,b)+1e-8:return True
            if depth>=max_depth:return False
            return recurse(a,mid,depth+1) and recurse(mid,b,depth+1)
        result=recurse(np.asarray(start),np.asarray(end),0)
        return result and self.world.version==version

    def camera_pose(self,q):
        self.set_q(q);return self.d.cam_xpos[self.camera].copy(),self.d.cam_xmat[self.camera].reshape(3,3).copy()


def reference_world(model,data,*,version=1):
    """Explicit simulator ground-truth backend, for audit / baseline tests only."""
    boxes=[];planes=[]
    for gid in range(model.ngeom):
        name=mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,gid) or ''
        if name.startswith(('robot0_','gripper0_')) or not(model.geom_contype[gid] or model.geom_conaffinity[gid]):continue
        R=data.geom_xmat[gid].reshape(3,3).copy();c=data.geom_xpos[gid].copy();kind=int(model.geom_type[gid])
        if kind==mujoco.mjtGeom.mjGEOM_PLANE:planes.append((R[:,2],float(c@R[:,2]),name));continue
        half=model.geom_size[gid].copy()
        if kind==mujoco.mjtGeom.mjGEOM_CYLINDER:half=np.array([half[0],half[0],half[1]])
        elif kind!=mujoco.mjtGeom.mjGEOM_BOX:raise ValueError(f'Unsupported world geom {name}')
        boxes.append(Box(c,half,R,name,int(model.geom_bodyid[gid]),gid))
    return World(boxes,planes,version=version,source='reference',complete=True,max_age=None)
