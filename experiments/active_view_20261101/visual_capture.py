"""Acquire RGB free-space evidence from a simulator empty-workspace reference.

Unknown objects are parked ONLY to emulate a prior empty-reference capture.
Their positions/geometries are not passed to the RGB-to-map implementation.
Metric background-depth limits and robot masking are simulator-derived known
calibration in this diagnostic; a real installation must supply these inputs.
"""
import numpy as np
import mujoco
from active_view.visual_map import Observation,reference_difference,VoxelMap
from robosuite.utils.camera_utils import get_real_depth_map


def capture(generator):
    g=generator;model=g.m;data=g.d;env=g.env
    cameras=['agentview','frontview','robot0_eye_in_hand']
    actual=[env.sim.render(width=160,height=160,camera_name=c)[::-1].copy() for c in cameras]
    original=data.qpos.copy();observations=[];references=[]
    try:
        for i,obj in enumerate(env.cubes):env.sim.data.set_joint_qpos(obj.joints[0],np.r_[4+i,4.,-.5,1.,0.,0.,0.])
        env.sim.forward()
        robot_ids=[i for i in range(model.ngeom) if (mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,i) or '').startswith(('robot0_','gripper0_'))]
        for rgb,name in zip(actual,cameras):
            empty,depth=env.sim.render(width=160,height=160,camera_name=name,depth=True)
            empty=empty[::-1].copy();depth=get_real_depth_map(env.sim,depth[::-1].copy())
            segmentation=env.sim.render(width=160,height=160,camera_name=name,segmentation=True)[::-1]
            valid=~np.isin(segmentation[:,:,1],robot_ids)
            background,foreground=reference_difference(rgb,empty,valid)
            cid=model.camera(name).id;f=80/np.tan(np.deg2rad(model.cam_fovy[cid]/2));K=np.array([[f,0,80],[0,f,80],[0,0,1]])
            observations.append(Observation(background,foreground,valid,depth,K,data.cam_xmat[cid].reshape(3,3).copy(),data.cam_xpos[cid].copy()))
            references.append(empty)
    finally:data.qpos[:]=original;env.sim.forward()
    grid=VoxelMap([-.9,-.7,.5],[.6,.7,1.6],resolution=.04);grid.integrate(observations)
    return grid,np.concatenate(actual,axis=1),np.concatenate(references,axis=1)
