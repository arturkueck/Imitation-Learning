"""Conservative oriented-box envelopes and separating-axis clearance bounds."""
from dataclasses import dataclass
import itertools
import numpy as np
from scipy.spatial import ConvexHull


@dataclass
class Box:
    center: np.ndarray
    half: np.ndarray
    rotation: np.ndarray
    name: str='box'
    body: int=-1
    geom: int=-1

    def corners(self):
        return np.array(list(itertools.product((-1,1),repeat=3)))*self.half@self.rotation.T+self.center


@dataclass
class Hull(Box):
    vertices: np.ndarray|None=None
    normals: np.ndarray|None=None
    edges: np.ndarray|None=None


def directions_unique(directions):
    a=np.asarray(directions,dtype=float);n=np.linalg.norm(a,axis=1);a=a[n>1e-10]/n[n>1e-10,None]
    for row in a:
        first=np.flatnonzero(np.abs(row)>1e-8)
        if len(first) and row[first[0]]<0:row*=-1
    a=np.unique(np.round(a,8),axis=0)
    return a/np.linalg.norm(a,axis=1,keepdims=True)


def hull_data(vertices):
    v=np.asarray(vertices,dtype=float);hull=ConvexHull(v);vtx=v[hull.vertices]
    normals=directions_unique(hull.equations[:,:3]);edges=[]
    for face in hull.simplices:
        for i,j in [(0,1),(1,2),(2,0)]:edges.append(v[face[j]]-v[face[i]])
    center=vtx.mean(0);_,_,vt=np.linalg.svd(vtx-center,full_matrices=False);R=vt.T
    if np.linalg.det(R)<0:R[:,-1]*=-1
    local=(vtx-center)@R;lo=local.min(0);hi=local.max(0)
    return dict(vertices=vtx,normals=normals,edges=directions_unique(edges),
                center=center+(lo+hi)/2@R.T,half=(hi-lo)/2+1e-7,rotation=R)


def convex_gap(a,b,refine_distance=.035):
    """Conservative separating-plane gap for convex collision hulls.

    A positive gap certifies separation. Face and edge-cross axes refine close
    outer boxes. Numerical ambiguity is rejected, never interpreted as free.
    """
    broad=sat_gap(a,b)
    if broad>refine_distance:return broad
    va=a.vertices if isinstance(a,Hull) else a.corners()
    vb=b.vertices if isinstance(b,Hull) else b.corners()
    na=a.normals if isinstance(a,Hull) else a.rotation.T
    nb=b.normals if isinstance(b,Hull) else b.rotation.T
    def gap(axes):
        norms=np.linalg.norm(axes,axis=1);axes=axes[norms>1e-10]/norms[norms>1e-10,None]
        if not len(axes):return -np.inf
        pa=axes@va.T;pb=axes@vb.T
        return float(np.max(np.maximum(pb.min(1)-pa.max(1),pa.min(1)-pb.max(1))))-1e-7
    best=gap(np.concatenate([na,nb,a.rotation.T,b.rotation.T]))
    if best>refine_distance:return best
    ea=a.edges if isinstance(a,Hull) else a.rotation.T
    eb=b.edges if isinstance(b,Hull) else b.rotation.T
    crosses=np.cross(ea[:,None,:],eb[None,:,:]).reshape(-1,3)
    # Early out on face separation; cross axes needed only near contact.
    if best>.004:return best
    for chunk in np.array_split(crosses,max(1,len(crosses)//1024)):
        best=max(best,gap(chunk))
        if best>.004:break
    return best


def sat_gap(a,b):
    """Lower bound on Euclidean surface distance if positive; <=0 means overlap.

    All 15 OBB separating axes are checked. This deliberately is not presented
    as an exact closest-point distance. Positive gaps are usable as conservative
    motion certificates; negative gaps reject the outer boxes.
    """
    axes=np.concatenate([a.rotation.T,b.rotation.T,
        np.cross(a.rotation.T[:,None,:],b.rotation.T[None,:,:]).reshape(-1,3)])
    norms=np.linalg.norm(axes,axis=1);axes=axes[norms>1e-10]/norms[norms>1e-10,None]
    ra=np.abs(axes@a.rotation)@a.half;rb=np.abs(axes@b.rotation)@b.half
    return float(np.max(np.abs(axes@(b.center-a.center))-ra-rb))


def segment_aabb_intersection(start,end,box,padding=0.):
    """Segment / oriented box intersection (closed interval)."""
    p=(np.asarray(start)-box.center)@box.rotation;v=(np.asarray(end)-np.asarray(start))@box.rotation
    half=box.half+padding;low=0.;high=1.
    for j in range(3):
        if abs(v[j])<1e-12:
            if abs(p[j])>half[j]:return False
            continue
        t0=(-half[j]-p[j])/v[j];t1=(half[j]-p[j])/v[j]
        low=max(low,min(t0,t1));high=min(high,max(t0,t1))
        if low>high:return False
    return True
