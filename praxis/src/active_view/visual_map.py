"""Fail-closed visual free-space interface; unknown cells remain forbidden.

RGB subtraction is an evidence producer, NOT a safety-rated obstacle detector.
Known robot/fixture pixels and missing depth limits must be masked unknown.
No simulator object positions or collision labels enter this module.
"""
from dataclasses import dataclass
import time
import itertools
import numpy as np
from scipy.ndimage import binary_erosion,binary_dilation
from scipy.spatial import cKDTree
from .geometry import Box,convex_gap,segment_aabb_intersection
from .collision import World

FREE=0;POSSIBLE_OCCUPIED=1;UNKNOWN=2


@dataclass
class Observation:
    background: np.ndarray
    foreground: np.ndarray
    valid: np.ndarray
    # Metric distance along camera -Z to a known opaque background surface.
    # Must come from calibrated static geometry/stereo, never unknown-object GT.
    free_depth_limit: np.ndarray
    K: np.ndarray
    world_rotation: np.ndarray
    world_position: np.ndarray


def reference_difference(rgb,empty_reference,valid_mask,*,background_threshold=8,foreground_threshold=25):
    if rgb.shape!=empty_reference.shape or rgb.ndim!=3 or rgb.shape[2]!=3:raise ValueError('RGB reference mismatch')
    delta=np.linalg.norm(rgb.astype(float)-empty_reference.astype(float),axis=-1)
    background=binary_erosion((delta<=background_threshold)&valid_mask,iterations=2,border_value=0)
    foreground=binary_dilation((delta>=foreground_threshold)&valid_mask,iterations=2)
    return background,foreground


class VoxelMap:
    def __init__(self,low,high,resolution=.03):
        self.low=np.asarray(low,dtype=float);self.resolution=float(resolution)
        self.shape=np.ceil((np.asarray(high)-self.low)/self.resolution).astype(int)
        self.high=self.low+self.shape*self.resolution
        self.centers=np.indices(self.shape).reshape(3,-1).T*self.resolution+self.low+self.resolution/2
        self.labels=np.full(len(self.centers),UNKNOWN,dtype=np.uint8);self.version=0;self.timestamp=time.monotonic();self.tree=None

    def integrate(self,observations):
        if not observations:raise ValueError('No observations: refusing to invent free space')
        free=np.zeros(len(self.centers),bool);votes=np.zeros(len(self.centers),int)
        offsets=np.array(list(itertools.product((-1,1),repeat=3)))*self.resolution/2
        for obs in observations:
            h,w=obs.background.shape
            if any(x.shape!=(h,w) for x in [obs.foreground,obs.valid,obs.free_depth_limit]):raise ValueError('Observation shape mismatch')
            corners=self.centers[:,None,:]+offsets
            local=(corners-obs.world_position)@obs.world_rotation
            depth=-local[:,:,2];u=obs.K[0,0]*local[:,:,0]/np.maximum(depth,1e-9)+obs.K[0,2]
            v=obs.K[1,2]-obs.K[1,1]*local[:,:,1]/np.maximum(depth,1e-9)
            x0=np.floor(u.min(1)-2).astype(int);x1=np.ceil(u.max(1)+2).astype(int)
            y0=np.floor(v.min(1)-2).astype(int);y1=np.ceil(v.max(1)+2).astype(int)
            candidates=np.where((depth.min(1)>0)&(x0>=0)&(y0>=0)&(x1<w)&(y1<h))[0]
            known_background=obs.background&obs.valid&np.isfinite(obs.free_depth_limit)&(obs.free_depth_limit>0)
            for i in candidates:
                region=np.s_[y0[i]:y1[i]+1,x0[i]:x1[i]+1]
                if known_background[region].all() and depth[i].max()+.005<float(obs.free_depth_limit[region].min()):free[i]=True
                if (obs.foreground[region]&obs.valid[region]).any():votes[i]+=1
        self.labels[:]=UNKNOWN;self.labels[votes>=2]=POSSIBLE_OCCUPIED;self.labels[free]=FREE
        self.version+=1;self.timestamp=time.monotonic()
        ids=np.flatnonzero(self.labels!=FREE);self.bad_ids=ids;self.tree=cKDTree(self.centers[ids]) if len(ids) else None

    def clearance(self,shape,margin):
        query_distance=.10;best=query_distance-margin;why='free_visual_space'
        if self.tree is None:
            if not np.all(self.labels==FREE):return -np.inf,'uninitialized_visual_map'
            return best,why
        radius=np.linalg.norm(shape.half)+np.sqrt(3)*self.resolution/2+query_distance
        for item in self.tree.query_ball_point(shape.center,radius):
            idx=self.bad_ids[item];cell=Box(self.centers[idx],np.full(3,self.resolution/2),np.eye(3),f'voxel_{idx}')
            gap=convex_gap(shape,cell)-margin
            if gap<best:best=gap;why='unknown_space' if self.labels[idx]==UNKNOWN else 'possible_occupied_space'
            if gap<=0:return gap,why
        return best,why

    def as_world(self,known_static_boxes=(),known_planes=(),max_age=2.):
        if self.version==0:raise ValueError('Map has not been observed')
        return World(list(known_static_boxes),list(known_planes),np.array([self.low,self.high]),self.version,
                     'visual',False,self.timestamp,max_age,self.clearance)

    def ray_clear(self,start,end):
        # Unknown and possible foreground are both forbidden, including FOV holes.
        start=np.asarray(start);end=np.asarray(end)
        if (np.minimum(start,end)<self.low).any() or (np.maximum(start,end)>=self.high).any():return False
        if self.tree is None:return bool(np.all(self.labels==FREE))
        middle=(start+end)/2;radius=np.linalg.norm(end-start)/2+np.sqrt(3)*self.resolution/2
        for item in self.tree.query_ball_point(middle,radius):
            idx=self.bad_ids[item]
            if segment_aabb_intersection(start,end,Box(self.centers[idx],np.full(3,self.resolution/2),np.eye(3))):return False
        return True
