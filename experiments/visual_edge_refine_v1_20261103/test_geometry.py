import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import cv2
from geometry import project,rays,triangulate,corners,EDGES
from refine import fit_one,prepare_views,gate
from tracking import track

def cam(x=0.):return dict(position=np.array([x,0.,0.]),rotation=np.eye(3),f=260.,cx=160.,cy=160.,width=320,height=320)
def box(x=0.):return dict(position=np.array([x,0.,-.8]),size=np.array([.08,.06,.05]),rotation=np.eye(3))
def image(b,c):
    out=np.full((320,320,3),220,np.uint8);uv,z=project(corners(b),c)
    for a,d in EDGES:cv2.line(out,tuple(np.rint(uv[a]).astype(int)),tuple(np.rint(uv[d]).astype(int)),(20,20,20),2)
    return out

def test_projection_ray_and_metric_triangulation():
    cameras=[cam(x) for x in [-.1,0.,.1]];point=np.array([.01,.02,-.8]);obs=[(i,project(point,c)[0]) for i,c in enumerate(cameras)]
    p=triangulate(obs,cameras);np.testing.assert_allclose(p['point'],point,atol=1e-9)
    for c in cameras:
        d=rays(project(point,c)[0],c);expected=point-c['position'];expected/=np.linalg.norm(expected);np.testing.assert_allclose(d,expected)
    assert triangulate([(i,obs[1][1]) for i in range(3)],[cam()]*3) is None

def test_geometric_fit_improves_synthetic_offset_and_does_not_read_holdout():
    cameras=[cam(x) for x in np.linspace(-.12,.12,6)];truth=box();initial=box(.006)
    images=[image(truth,c) for c in cameras];fit_ids=[0,2,4];points=corners(truth)
    fitted=fit_one(initial,[initial],images,cameras,fit_ids,points)
    assert np.linalg.norm(fitted['candidate']['position']-truth['position'])<.006
    poisoned=[a if i in fit_ids else None for i,a in enumerate(images)]
    repeated=fit_one(initial,[initial],poisoned,cameras,fit_ids,points)
    np.testing.assert_array_equal(fitted['candidate']['position'],repeated['candidate']['position'])

def test_gate_rejects_missing_evidence_and_unchanged_candidate():
    b=box();decision=gate(b,b,[],[],0)
    assert not decision['accepted'] and 'insufficient_tracks' in decision['reasons']

def test_tracking_never_reads_reserved_rgb_frames():
    cameras=[cam(x) for x in np.linspace(-.03,.03,8)];b=box();fit=[0,2,4,6]
    images=[image(b,c) if i in fit else None for i,c in enumerate(cameras)]
    tracks,points,stats=track(images,cameras,fit,[b]);assert len(tracks)>0
    assert all(frame in fit for t in tracks for frame,_ in t['observations'])

def test_recorded_route_interpolation_has_exact_endpoints():
    from run import route_samples
    route=np.array([[0.,0.],[1.,0.],[1.,2.]])
    q=route_samples(route,20);np.testing.assert_array_equal(q[0],route[0]);np.testing.assert_array_equal(q[-1],route[-1])
    assert q.shape==(20,2)

def test_perception_adapter_uses_dict_output_and_only_rgb_rays_mask():
    from run import predict,V4
    import torch
    sys.path.insert(0,str(V4.parent/'visual_scene_v2_20261101'))
    class Spy:
        def __call__(self,images,rays,mask):
            assert images.shape==(1,5,3,160,160) and mask.sum()==3
            return dict(detection_logits=torch.full((1,5),-10.),position=torch.zeros((1,5,3)),dimensions_raw=torch.zeros((1,5,3)),rotation_6d=torch.tensor([1.,0,0,0,1,0]).repeat(1,5,1),visibility_logits=torch.zeros((1,5,3)))
    row=dict(images=np.zeros((2,3,160,160,3),np.uint8),rays=np.zeros((2,3,20,20,6),np.float32))
    assert predict([Spy(),Spy(),Spy()],row,[0],device='cpu')==[]
