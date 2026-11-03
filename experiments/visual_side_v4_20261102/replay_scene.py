"""Restore immutable settled pilot geometry; do not settle a comparison anew."""
import numpy as np
import mujoco

def restore_scene(g,sample,record):
    rng=np.random.default_rng(np.random.SeedSequence([94140202,record['index']]))
    last_error=None
    for attempt in range(40):
        last_error=None
        try:g._setup(rng,record['count'],record['kind'],record['shape']=='long_thin')
        except ValueError as error:
            last_error=str(error)
            if last_error=='placement':continue
        configured=np.array([g.m.geom_size[ids[0]]*2 for ids in g.geoms])
        if np.max(np.abs(configured-sample['sizes']))<1e-7:break
    else:raise RuntimeError('Cannot reconstruct stored object geometry/material seed')
    resettled=np.array([g.d.xpos[b].copy() for b in g.bodies])
    for i,cube in enumerate(g.env.cubes):
        q=np.zeros(4);mujoco.mju_mat2Quat(q,np.asarray(sample['rotations'][i],float).ravel());q/=np.linalg.norm(q)
        g.env.sim.data.set_joint_qpos(cube.joints[0],np.r_[sample['positions'][i],q])
    # Fixed-camera calibration is available in the original immutable sample.
    if 'camera_positions' in sample:
        for j,name in enumerate(['agentview','frontview']):
            cid=g.m.camera(name).id
            if g.m.cam_bodyid[cid]!=0:raise RuntimeError('Fixed camera unexpectedly parented')
            q=np.zeros(4);mujoco.mju_mat2Quat(q,np.asarray(sample['camera_rotations'][0,j],float).ravel());q/=np.linalg.norm(q)
            g.m.cam_pos[cid]=sample['camera_positions'][0,j];g.m.cam_quat[cid]=q
    g.d.qvel[:]=0;g.env.sim.forward()
    restored=np.array([g.d.xpos[b].copy() for b in g.bodies])
    difference=float(np.max(np.abs(restored-sample['positions'])))
    if difference>1e-7:raise RuntimeError('Stored geometry restore disagrees')
    return dict(geometry_attempt=attempt+1,resettling_error=last_error,
        discarded_resettling_difference_m=float(np.max(np.abs(resettled-sample['positions']))),restored_difference_m=difference,
        appearance='same seed and matched dimensions/material configuration; illumination state was not serialized in original sample')
