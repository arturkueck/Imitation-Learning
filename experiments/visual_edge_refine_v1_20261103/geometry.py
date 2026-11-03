"""RGB/camera-only cuboid geometry. MuJoCo camera axes: +x right,+y up,-z forward."""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import map_coordinates

SIGNS=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]],float)
EDGES=np.array([(i,j) for i in range(8) for j in range(i+1,8) if np.sum(SIGNS[i]!=SIGNS[j])==1])

def corners(box):return (SIGNS*np.asarray(box['size'])/2)@np.asarray(box['rotation']).T+box['position']

def project(points,camera):
    local=(np.asarray(points)-camera['position'])@camera['rotation'];depth=-local[...,2]
    uv=np.stack([camera['cx']+camera['f']*local[...,0]/np.maximum(depth,1e-9),camera['cy']-camera['f']*local[...,1]/np.maximum(depth,1e-9)],axis=-1)
    return uv,depth

def rays(pixels,camera):
    uv=np.asarray(pixels);d=np.stack([(uv[...,0]-camera['cx'])/camera['f'],-(uv[...,1]-camera['cy'])/camera['f'],-np.ones(uv.shape[:-1])],axis=-1)@camera['rotation'].T
    return d/np.linalg.norm(d,axis=-1,keepdims=True)

def triangulate(observations,cameras,min_parallax_deg=1.5):
    """Least-squares ray intersection; independent of object geometry/GT."""
    if len(observations)<3:return None
    origins=np.array([cameras[i]['position'] for i,_ in observations]);dirs=np.array([rays(p,cameras[i]) for i,p in observations])
    angles=np.degrees(np.arccos(np.clip(dirs@dirs.T,-1,1)));parallax=float(angles.max())
    if parallax<min_parallax_deg:return None
    A=np.eye(3)[None]-dirs[:,:,None]*dirs[:,None,:]
    if np.linalg.cond(A.sum(0))>1e5:return None
    point=np.linalg.solve(A.sum(0),np.einsum('nij,nj->i',A,origins))
    errors=[]
    for i,p in observations:
        uv,z=project(point,cameras[i])
        if z<=.02:return None
        errors.append(np.linalg.norm(uv-p))
    rms=float(np.sqrt(np.mean(np.square(errors))))
    if rms>2.:return None
    return dict(point=point,reprojection_px=rms,parallax_deg=parallax)

def edge_samples(box,samples=7):
    c=corners(box);a=np.linspace(.08,.92,samples)
    return np.concatenate([c[i,None]*(1-a[:,None])+c[j,None]*a[:,None] for i,j in EDGES])

def visible(points,camera,boxes):
    """Occlusion approximation from predicted cuboids only, no simulator masks."""
    points=np.asarray(points);origin=np.asarray(camera['position']);direction=points-origin;result=np.ones(len(points),bool)
    for box in boxes:
        R=np.asarray(box['rotation']);o=(origin-box['position'])@R;d=direction@R;size=np.asarray(box['size'])/2
        safe=np.where(np.abs(d)>1e-10,d,np.where(d>=0,1e-10,-1e-10))
        a=(-size-o)/safe;b=(size-o)/safe
        near=np.minimum(a,b).max(-1);far=np.maximum(a,b).min(-1)
        result&=~((far>=np.maximum(near,0))&(near>0)&(near<.995))
    uv,z=project(points,camera)
    return result&(z>.02)&(uv[:,0]>=2)&(uv[:,0]<camera['width']-2)&(uv[:,1]>=2)&(uv[:,1]<camera['height']-2)

def pixel_errors(points,camera,distance):
    uv,z=project(points,camera);h,w=distance.shape
    inside=(z>.02)&(uv[:,0]>=0)&(uv[:,0]<w-1)&(uv[:,1]>=0)&(uv[:,1]<h-1)
    values=np.full(len(points),20.,float)
    values[inside]=map_coordinates(distance,[uv[inside,1],uv[inside,0]],order=1,mode='nearest')
    return np.minimum(values,20.)

def decode_delta(initial,delta):
    return dict(position=initial['position']+delta[:3],size=initial['size']*np.exp(delta[6:9]),rotation=Rotation.from_rotvec(delta[3:6]).as_matrix()@initial['rotation'])

def surface_distance(points,box):
    local=np.abs((points-box['position'])@box['rotation'])-box['size']/2
    return np.linalg.norm(np.maximum(local,0),axis=-1)+np.minimum(np.max(local,axis=-1),0)
