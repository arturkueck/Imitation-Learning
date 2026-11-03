"""V2 physical settlement copied for V3; held-out thin/long cuboids and grey colors.
Original: experiments/visual_scene_v2_20261101/scene_data.py, Generator._setup.
Original V2 file remains unchanged. No training logic in this module.
"""
import numpy as np
import mujoco
from scene_data import camera_aim

def physical_setup(self,rng,n,kind,ood=False):
        self.d.qpos[:]=self.base_qpos;self.d.qvel[:]=0
        # Small real robot-joint changes vary the hand camera; reject contacts below.
        for adr in self.robot_joints:self.d.qpos[adr]+=rng.uniform(-.035,.035)
        sizes=rng.uniform(.028,.065,(5,3))
        for i in range(5):
            if rng.random()<.5:sizes[i]=rng.uniform(.03,.065)
        if ood:
            sizes[:,0]=rng.uniform(.13,.16,5);sizes[:,1]=rng.uniform(.018,.024,5);sizes[:,2]=rng.uniform(.028,.065,5)
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
        if rng.random()<.25:colors[:]=rng.uniform(.2,.98,(5,1))  # Grey/bright geometry is not identified by hue.
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

