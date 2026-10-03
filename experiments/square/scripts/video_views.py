"""Four synchronized views; the policy's agentview camera remains unchanged."""
import mujoco
import numpy as np
from PIL import Image, ImageDraw

VIEWS = [('agentview','Bisherige Ansicht'),('frontview','Vorne'),
         ('sideview','Rechts'),('birdview','Diagonal oben - Gesamtansicht')]

def setup_cameras(env):
    sim = env.base_env.sim
    for name, position, target in [
        ('frontview',(2.3,0,1.5),(-0.2,0,1.05)),
        ('sideview',(-0.2,-2.3,1.5),(-0.2,0,1.05)),
        ('birdview',(1.8,-1.8,2.5),(-0.15,0,0.95)),
    ]:
        index = sim.model.camera_name2id(name)
        position, target = np.array(position),np.array(target)
        z = position-target; z /= np.linalg.norm(z)
        x = np.cross([0,0,1],z); x /= np.linalg.norm(x)
        y = np.cross(z,x)
        quaternion = np.zeros(4)
        mujoco.mju_mat2Quat(quaternion,np.column_stack([x,y,z]).ravel())
        sim.model.cam_pos[index] = position
        sim.model.cam_quat[index] = quaternion
        sim.model.cam_fovy[index] = 45
    sim.forward()

def frame(env, size=384):
    panels = []
    for camera, label in VIEWS:
        array = env.render(mode='rgb_array',height=size,width=size,camera_name=camera)
        panel = Image.fromarray(array)
        draw = ImageDraw.Draw(panel)
        draw.rectangle((0,0,size,24),fill=(20,25,30))
        draw.text((8,6),label,fill='white')
        panels.append(np.asarray(panel))
    return np.concatenate([np.concatenate(panels[:2],axis=1),
                           np.concatenate(panels[2:],axis=1)],axis=0)
