"""Physically settled 0--5 box scenes; RGB input, privileged labels only."""
from pathlib import Path
import sys, itertools, time
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
import robosuite, mujoco
from task_extensions.environments import StackFour
from robosuite.environments.manipulation.manipulation_env import ManipulationEnv
from robosuite.models.arenas import TableArena
from robosuite.models.objects import BoxObject
from robosuite.models.tasks import ManipulationTask
from robosuite.utils.placement_samplers import UniformRandomSampler

ORIGIN=np.array([0.,0.,.8],dtype=np.float32)
CAMS=['agentview','frontview','robot0_eye_in_hand']


class VisionScene(StackFour):
    cube_count=5
    def _load_model(self):
        ManipulationEnv._load_model(self)
        self.robots[0].robot_model.set_base_xpos(self.robots[0].robot_model.base_xpos_offset['table'](self.table_full_size[0]))
        arena=TableArena(table_full_size=self.table_full_size,table_friction=self.table_friction,table_offset=self.table_offset)
        self.cubes=[BoxObject(name='vision_'+str(i),size=[.025]*3,rgba=[.6,.3,.2,1],density=500,friction=[1,.005,.0001]) for i in range(5)]
        for name,cube in zip('ABCDE',self.cubes):setattr(self,'cube'+name,cube)
        self.placement_initializer=UniformRandomSampler(name='VisionSampler',mujoco_objects=self.cubes,x_range=[-.17,.17],y_range=[-.17,.17],rotation=0,ensure_valid_placement=True,reference_pos=self.table_offset,z_offset=.01)
        self.model=ManipulationTask(mujoco_arena=arena,mujoco_robots=[r.robot_model for r in self.robots],mujoco_objects=self.cubes)
    def tower_is_valid(self):return False


def camera_aim(env,name,pos,target):
    idx=env.sim.model.camera_name2id(name)
    z=pos-target;z/=np.linalg.norm(z);x=np.cross([0.,0.,1.],z);x/=np.linalg.norm(x);y=np.cross(z,x)
    q=np.zeros(4);mujoco.mju_mat2Quat(q,np.column_stack([x,y,z]).ravel())
    env.sim.model.cam_pos[idx]=pos;env.sim.model.cam_quat[idx]=q;env.sim.model.cam_fovy[idx]=45


class Generator:
    def __init__(self):
        import json
        np.random.seed(200101)
        kw=json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())['environment']['env_kwargs']
        kw.update(use_camera_obs=False,use_object_obs=False,hard_reset=False,has_renderer=False,has_offscreen_renderer=True,initialization_noise=None)
        self.env=robosuite.make('VisionScene',**kw);self.env.reset()
        self.m=self.env.sim.model._model;self.d=self.env.sim.data._data
        self.base_qpos=self.d.qpos.copy();self.base_mass=self.m.body_mass.copy()
        self.geoms=[[self.env.sim.model.geom_name2id(g) for g in c.contact_geoms+c.visual_geoms] for c in self.env.cubes]
        self.bodies=self.env.cube_ids
        self.groups=self.m.geom_group.copy()
        self.rejections={};self.audit=[]
        self.env.sim.render(width=160,height=160,camera_name=CAMS[0])
        self.context=self.env.sim._render_context_offscreen
        self.context.vopt.geomgroup[5]=0
        self.robot_joints=[self.m.jnt_qposadr[i] for i in range(self.m.njnt) if self.m.jnt_type[i]==3][:7]

    def close(self):self.env.close()

    def _setup(self,rng,n,kind,ood=False):
        self.d.qpos[:]=self.base_qpos;self.d.qvel[:]=0
        # Small real robot-joint changes vary the hand camera; reject contacts below.
        for adr in self.robot_joints:self.d.qpos[adr]+=rng.uniform(-.035,.035)
        sizes=rng.uniform(.028,.065,(5,3))
        for i in range(5):
            if rng.random()<.5:sizes[i]=rng.uniform(.03,.065)
        if ood:
            sizes[:,0]=rng.uniform(.085,.115,5);sizes[:,1]=rng.uniform(.028,.04,5);sizes[:,2]=rng.uniform(.028,.065,5)
        centers=np.zeros((5,3));angles=rng.uniform(-np.pi,np.pi,5)
        xy=[]
        for i in range(n):
            for _ in range(100):
                p=rng.uniform(-.14,.14,2)
                if all(np.linalg.norm(p-q)>.105 for q in xy):break
            else:raise ValueError('placement')
            xy.append(p);centers[i,:2]=p;centers[i,2]=.8+sizes[i,2]/2+.001
        if kind in ('tower','mixed') and n>=2:
            height=n if kind=='tower' else min(n,3)
            base=rng.uniform(-.075,.075,2);angle=rng.uniform(-np.pi,np.pi);z=.801
            sizes[0,:2]=.067
            for i in range(height):
                if i:
                    limit=min(sizes[i-1,:2])*.97
                    width=rng.uniform(.026,max(.0261,limit))
                    sizes[i,:2]=width
                    if np.ptp(sizes[i])<.005:sizes[i]=width
                centers[i,:2]=base;centers[i,2]=z+sizes[i,2]/2;z+=sizes[i,2]+.00015;angles[i]=angle
        elif kind=='wall' and n>=3:
            # Two actual supporting blocks and a spanning lintel, plus optional top blocks.
            sizes[0]=[.04,.05,.04];sizes[1]=sizes[0];sizes[2]=[.105,.045,.03]
            centers[0]=[-.032,0,.821];centers[1]=[.032,0,.821];centers[2]=[0,0,.856]
            angles[:3]=0
            z=.871
            for i in range(3,n):
                sizes[i]=[.035,.035,.03];centers[i]=[0,0,z+.015];angles[i]=0;z+=.0302
            scale=rng.uniform(.85,1.10);yaw=rng.uniform(-np.pi,np.pi)
            rotation=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
            centers[:n,:2]=centers[:n,:2]@rotation.T*scale+rng.uniform(-.055,.055,2)
            centers[:n,2]=.8+(centers[:n,2]-.8)*scale;sizes[:n]*=scale;angles[:n]=yaw
        colors=rng.uniform(.12,.9,(5,3))
        if rng.random()<.4:colors[:]=colors[0]  # Identity cannot be inferred from color.
        for i,cube in enumerate(self.env.cubes):
            for gid in self.geoms[i]:
                self.m.geom_size[gid]=sizes[i]/2
                self.m.geom_rbound[gid]=np.linalg.norm(sizes[i]/2)
                self.m.geom_aabb[gid,3:]=sizes[i]/2
                self.m.geom_rgba[gid,:3]=colors[i]
            body=self.bodies[i];mass=500*np.prod(sizes[i]);self.m.body_mass[body]=mass
            self.m.body_inertia[body]=mass/12*np.array([sizes[i,1]**2+sizes[i,2]**2,sizes[i,0]**2+sizes[i,2]**2,sizes[i,0]**2+sizes[i,1]**2])
            if i>=n:centers[i]=[3+i*.2,3,-.5]
            a=angles[i];self.env.sim.data.set_joint_qpos(cube.joints[0],np.r_[centers[i],np.cos(a/2),0,0,np.sin(a/2)])
        configured_qpos=self.d.qpos.copy()
        mujoco.mj_setConst(self.m,self.d)
        self.d.qpos[:]=configured_qpos;self.d.qvel[:]=0;self.env.sim.forward()
        for _ in range(350):
            self.d.qpos[:9]=configured_qpos[:9];self.d.qvel[:9]=0
            self.d.qfrc_applied[:9]=self.d.qfrc_bias[:9]
            mujoco.mj_step(self.m,self.d)
        self.env.sim.forward()
        pos=np.array([self.d.xpos[b].copy() for b in self.bodies])
        vel=np.array([self.env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in self.env.cubes])
        if n and (np.max(np.linalg.norm(vel[:n,:3],axis=1))>.015 or np.max(np.linalg.norm(vel[:n,3:],axis=1))>.15):raise ValueError('not_settled')
        if n and (np.min(pos[:n,2]-sizes[:n,2]/2)<.796 or np.max(np.abs(pos[:n,:2]))>.22):raise ValueError('fell_or_outside')
        if kind in ('tower','mixed','wall') and n>=2 and max(pos[:n,2])<.85:raise ValueError('stack_collapsed')
        if kind in ('tower','mixed','wall') and n>=2 and np.max(np.linalg.norm(pos[:n]-centers[:n],axis=-1))>.012:raise ValueError('layout_changed')
        for contact in self.d.contact[:self.d.ncon]:
            if contact.dist<-.003 and any(contact.geom1 in g or contact.geom2 in g for g in self.geoms[:n]):raise ValueError('penetration')
            object_geoms=set(sum(self.geoms[:n],[]))
            if (contact.geom1 in object_geoms)!=(contact.geom2 in object_geoms):
                other=contact.geom2 if contact.geom1 in object_geoms else contact.geom1
                name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,int(other)) or ''
                if name.startswith(('robot0','gripper0')):raise ValueError('robot_object_contact')
        for name,p in [('agentview',[.63,-.55,1.36]),('frontview',[.63,.55,1.36])]:
            camera_aim(self.env,name,np.array(p)+rng.uniform(-.012,.012,3),np.array([0.,0.,.91]))
        self.m.light_diffuse[:]=rng.uniform(.55,.9,self.m.light_diffuse.shape)
        self.env.sim.forward()
        return sizes,pos

    def scene(self,seed,index,force_count=None,ood=False):
        rng=np.random.default_rng(np.random.SeedSequence([seed,index]))
        n=int(rng.choice(6,p=[.05,.19,.19,.19,.19,.19])) if force_count is None else force_count
        kind=str(rng.choice(['scattered','mixed','tower','wall'],p=[.35,.30,.25,.10]))
        if n<2:kind='scattered'
        if kind=='wall' and n<3:kind='scattered'
        if ood:kind='scattered'
        for attempt in range(30):
            try:sizes,pos=self._setup(rng,n,kind,ood);break
            except ValueError as e:self.rejections[str(e)]=self.rejections.get(str(e),0)+1
        else:raise RuntimeError(f'No valid physical scene after 30 attempts: {seed}/{index}/{n}/{kind}')
        images=[];visible=np.zeros((5,3),np.float32);rays=[];rot=np.array([self.d.xmat[b].reshape(3,3).copy() for b in self.bodies])
        for view,cam in enumerate(CAMS):
            image=self.env.sim.render(width=160,height=160,camera_name=cam)[::-1].copy();images.append(image)
            segmentation=self.env.sim.render(width=160,height=160,camera_name=cam,segmentation=True)[::-1]
            cid=self.env.sim.model.camera_name2id(cam);R=self.d.cam_xmat[cid].reshape(3,3).copy();origin=self.d.cam_xpos[cid].copy()
            focal=80/np.tan(np.deg2rad(self.m.cam_fovy[cid]/2))
            u,v=np.meshgrid(np.arange(20)*8+.5,np.arange(20)*8+.5)
            local=np.stack([(u-80)/focal,-(v-80)/focal,-np.ones_like(u)],axis=-1)
            directions=local@R.T;directions/=np.linalg.norm(directions,axis=-1,keepdims=True)
            rays.append(np.concatenate([directions,np.broadcast_to((origin-ORIGIN)/.1,directions.shape)],axis=-1))
            for i in range(n):
                self.m.geom_group[:]=5;self.m.geom_group[self.geoms[i]]=self.groups[self.geoms[i]]
                isolated=self.env.sim.render(width=160,height=160,camera_name=cam,segmentation=True)[::-1]
                mask=np.isin(isolated[:,:,1],self.geoms[i])&(isolated[:,:,0]==int(mujoco.mjtObj.mjOBJ_GEOM))
                denominator=int(mask.sum());numerator=int((np.isin(segmentation[:,:,1],self.geoms[i])&(segmentation[:,:,0]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum())
                visible[i,view]=min(1.,numerator/max(1,denominator))
                if denominator:
                    corners=np.array(list(itertools.product((-1,1),repeat=3)))*sizes[i]/2
                    world=corners@rot[i].T+pos[i];camera=(world-origin)@R
                    if (camera[:,2]<0).all():
                        projected=np.c_[80+focal*camera[:,0]/(-camera[:,2]),80-focal*camera[:,1]/(-camera[:,2])]
                        yy,xx=np.where(mask)
                        if min(xx)<projected[:,0].min()-3 or max(xx)>projected[:,0].max()+3 or min(yy)<projected[:,1].min()-3 or max(yy)>projected[:,1].max()+3:raise RuntimeError('Camera projection / segmentation disagrees')
                self.m.geom_group[:]=self.groups
        active=np.arange(5)<n
        return dict(images=np.asarray(images,dtype=np.uint8),rays=np.asarray(rays,dtype=np.float32),
            positions=pos.astype('float32'),sizes=sizes.astype('float32'),rotations=rot.astype('float32'),
            visibility=visible,active=active,count=np.int64(n),kind=np.int64(['scattered','mixed','tower','wall'].index(kind)),
            family=np.array([seed,index],dtype=np.int64))


def stack(rows):return {k:np.stack([r[k] for r in rows]) for k in rows[0]}
