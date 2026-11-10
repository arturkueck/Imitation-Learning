"""Bounded joint cuboid refinement from RGB/reference evidence, never truth.

Only geometric parameters are optimized. Neural weights are not loaded here.
Silhouette union handles overlap; visible RGB edge samples are hidden by nearer
predicted cuboids. Equivalent image solutions remain possible and are reported.
"""
import itertools
import numpy as np
from scipy.ndimage import map_coordinates, distance_transform_edt, binary_erosion
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.special import expit
import image_consistency as geometry
import reference_evidence
from ensemble_uncertainty import corners

CONFIG=dict(position_bound_m=.020,log_size_bound=.18,rotation_bound_rad=.175,
            silhouette_weight=.65,edge_weight=.35,prior_weight=.02,physical_weight=.05,
            pixel_stride=2,soft_boundary_pixels=1.,stage_maxfun=240,stage_maxiter=12,
            reference_threshold=8,minimum_gain=.005,ambiguity_loss_gap=.01,ambiguity_position_m=.005)
SIGNS=np.array(list(itertools.product((-1,1),repeat=3)))
EDGES=[(a,a^bit) for a in range(8) for bit in [1,2,4] if a<(a^bit)]


def decode(base,parameters,config=CONFIG):
    p=np.asarray(parameters).reshape(len(base),9)
    return [dict(b,position=b['position']+x[:3]*config['position_bound_m'],
                 size=b['size']*np.exp(x[3:6]*config['log_size_bound']),
                 rotation=Rotation.from_rotvec(x[6:]*config['rotation_bound_rad']).as_matrix()@b['rotation'])
            for b,x in zip(base,p)]


def project(camera,points):
    p=(points-camera['origin'])@camera['projection'].T
    return p[:,:2]/np.maximum(p[:,2,None],1e-9),p[:,2]


def soft_mask(camera,box,grid,softness):
    uv,z=project(camera,corners(box))
    if (z<=0).any():return np.zeros(grid.shape[:2])
    hull=ConvexHull(uv)
    signed=np.einsum('ijk,lk->ijl',grid,hull.equations[:,:2])+hull.equations[:,2]
    return expit(-signed.max(-1)/softness)


def edge_points(box,camera):
    local_camera=(camera['origin']-box['position'])@box['rotation']
    points=[]
    for a,b in EDGES:
        shared=np.flatnonzero(SIGNS[a]==SIGNS[b])
        if any(local_camera[axis]*SIGNS[a,axis]>box['size'][axis]/2 for axis in shared):
            t=np.linspace(.04,.96,7)
            local=(SIGNS[a][None]*(1-t[:,None])+SIGNS[b][None]*t[:,None])*box['size']/2
            points.extend(local@box['rotation'].T+box['position'])
    return np.asarray(points).reshape(-1,3)


def visible_samples(camera,points,boxes,exclude):
    visible=np.ones(len(points),bool)
    vectors=points-camera['origin'];lengths=np.linalg.norm(vectors,axis=-1)
    directions=vectors/np.maximum(lengths[:,None],1e-12)
    for j,box in enumerate(boxes):
        if j==exclude:continue
        origin=(camera['origin']-box['position'])@box['rotation'];d=directions@box['rotation']
        parallel=np.abs(d)<1e-10;safe=np.where(parallel,1.,d)
        a=(-box['size']/2-origin)/safe;b=(box['size']/2-origin)/safe
        lo=np.where(parallel,-np.inf,np.minimum(a,b)).max(-1)
        hi=np.where(parallel,np.inf,np.maximum(a,b)).min(-1)
        outside=(parallel&(np.abs(origin)>box['size']/2)).any(-1)
        hidden=(hi>=np.maximum(lo,0))&~outside&(lo>0)&(lo<lengths-.001)
        visible &= ~hidden
    return visible


class Objective:
    def __init__(self,images,references,robot_masks,cameras,base,config=CONFIG,table_z=.8):
        self.base=base;self.config=dict(config);self.cameras=cameras;self.views=[];self.calls=0;self.table_z=table_z
        stride=config['pixel_stride'];yy,xx=np.mgrid[0:160:stride,0:160:stride]
        self.grid=np.stack([xx,yy],axis=-1)
        for rgb,ref,robot in zip(images,references,robot_masks):
            ev=reference_evidence.foreground(rgb,ref,robot,config['reference_threshold'])
            rgb_edges=geometry.rgb_evidence(rgb)['edges']
            # The mask's outer contour is usable even on a neutral object.
            boundary=ev['mask']&~binary_erosion(ev['mask'])
            distances=distance_transform_edt(~((rgb_edges|boundary)&ev['valid']))
            self.views.append(dict(mask=ev['mask'][::stride,::stride],valid=ev['valid'][::stride,::stride],
                                   full_valid=ev['valid'],distance=distances))

    def components(self,parameters):
        self.calls+=1;boxes=decode(self.base,parameters,self.config);silhouette=[];edges=[]
        for camera,view in zip(self.cameras,self.views):
            soft=np.asarray([soft_mask(camera,b,self.grid,self.config['soft_boundary_pixels']) for b in boxes])
            union=1-np.prod(1-soft,axis=0);fg=view['mask'];valid=view['valid']
            intersection=np.sum(union*fg*valid);area=np.sum((union+fg-union*fg)*valid)
            silhouette.append(1-intersection/max(1,area))
            distances=[]
            for index,box in enumerate(boxes):
                points=edge_points(box,camera)
                keep=visible_samples(camera,points,boxes,index)
                uv,z=project(camera,points);keep &= (z>0)&(uv[:,0]>=1)&(uv[:,0]<159)&(uv[:,1]>=1)&(uv[:,1]<159)
                uv=uv[keep]
                if len(uv):
                    known=map_coordinates(view['full_valid'].astype(float),[uv[:,1],uv[:,0]],order=0)>.5;uv=uv[known]
                    if len(uv):distances.extend(np.minimum(8,map_coordinates(view['distance'],[uv[:,1],uv[:,0]],order=1))/8)
            edges.append(float(np.mean(distances)) if distances else 1.)
        physical=0.
        for b in boxes:
            bottom=b['position'][2]-np.abs(b['rotation'][2])@(b['size']/2)
            physical+=max(0,self.table_z-bottom-.001)/.01
        # All objects are optimized together; overlapping physical volumes are
        # discouraged, but this term does not certify stability or grasp safety.
        for i,a in enumerate(boxes):
            for b in boxes[:i]:
                axes=np.concatenate([a['rotation'].T,b['rotation'].T,np.cross(a['rotation'].T[:,None],b['rotation'].T[None]).reshape(-1,3)])
                norms=np.linalg.norm(axes,axis=1);axes=axes[norms>1e-10]/norms[norms>1e-10,None]
                gap=np.max(np.abs(axes@(b['position']-a['position']))-np.abs(axes@a['rotation'])@(a['size']/2)-np.abs(axes@b['rotation'])@(b['size']/2))
                physical+=max(0,-gap-.001)/.01
        return dict(silhouette=float(np.mean(silhouette)),edge=float(np.mean(edges)),
                    prior=float(np.mean(np.asarray(parameters)**2)),physical=physical/max(1,len(boxes)))

    def __call__(self,p):
        c=self.components(p);cfg=self.config
        return cfg['silhouette_weight']*c['silhouette']+cfg['edge_weight']*c['edge']+cfg['prior_weight']*c['prior']+cfg['physical_weight']*c['physical']


def refine(images,references,robot_masks,cameras,base,config=CONFIG):
    if not base:return [],dict(updated=False,reason='empty_prediction',objective_calls=0,ambiguous=False)
    objective=Objective(images,references,robot_masks,cameras,base,config)
    initial=np.zeros(len(base)*9);initial_loss=objective(initial)
    options=dict(maxfun=config['stage_maxfun'],maxiter=config['stage_maxiter'],ftol=1e-6,eps=.005,maxls=12)
    position_ids=np.array([i*9+j for i in range(len(base)) for j in range(3)])
    def positions_only(x):
        p=initial.copy();p[position_ids]=x;return objective(p)
    first=minimize(positions_only,initial[position_ids],method='L-BFGS-B',bounds=[(-1,1)]*len(position_ids),options=options)
    translated=initial.copy();translated[position_ids]=first.x
    candidates=[(initial_loss,initial),(objective(translated),translated)]
    for start in [translated,initial]:
        result=minimize(objective,start,method='L-BFGS-B',bounds=[(-1,1)]*len(initial),options=options)
        candidates.append((objective(result.x),result.x.copy()))
    candidates.sort(key=lambda item:item[0]);loss,best=candidates[0]
    competing=candidates[1:];ambiguous=False
    for other_loss,p in competing:
        displacement=np.linalg.norm((p-best).reshape(-1,9)[:,:3]*config['position_bound_m'],axis=1).max()
        if other_loss-loss<=config['ambiguity_loss_gap'] and displacement>config['ambiguity_position_m']:ambiguous=True
    gain=initial_loss-loss;updated=bool(np.isfinite(loss) and gain>=config['minimum_gain'])
    final=decode(base,best,config) if updated else base
    return final,dict(updated=updated,ambiguous=ambiguous,objective_before=initial_loss,objective_after=loss if updated else initial_loss,
                      objective_gain=gain,objective_calls=objective.calls,
                      components_before=objective.components(initial),components_candidate=objective.components(best),
                      max_position_change_mm=float(max(np.linalg.norm(a['position']-b['position'])*1000 for a,b in zip(base,final))))
