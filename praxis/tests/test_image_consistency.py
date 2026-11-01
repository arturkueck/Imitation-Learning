"""Reprojection/occlusion/evidence tests; no renderer, weights or optimizer."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/visual_scene_v2_20261101'))
import image_consistency as module


def camera():
    y,x=np.mgrid[:20,:20]
    directions=np.stack([(x*8+.5-80)/100,(y*8+.5-80)/100,np.ones_like(x)],axis=-1)
    directions/=np.linalg.norm(directions,axis=-1,keepdims=True)
    origin=np.array([.2,-.1,.3])
    rays=np.concatenate([directions,np.broadcast_to((origin-[0,0,.8])/.1,directions.shape)],axis=-1)
    return module.camera_from_rays(rays)


def box(center=(.2,-.1,1.3)):
    return dict(position=np.array(center),size=np.array([.2,.2,.2]),rotation=np.eye(3))


def test_ray_calibration_recovers_known_camera():
    cam=camera(); assert cam['residual']<1e-8
    p=(box()['position']-cam['origin'])@cam['projection'].T
    assert np.allclose(p[:2]/p[2],[80,80])


def test_z_buffer_hides_rear_box():
    cam=camera();front=box();back=box((.2,-.1,1.8))
    owner,depth,_,_=module.rasterize(cam,[front,back])
    assert owner[80,80]==0 and np.isfinite(depth[80,80])
    assert not (owner==1).any()


def test_matching_image_better_than_shifted_box():
    cam=camera();truth=box();owner,_,_,_=module.rasterize(cam,[truth])
    rgb=np.full((160,160,3),255,dtype=np.uint8);rgb[owner==0]=[200,40,60]
    exact,_,_=module.image_features([rgb,rgb],[cam,cam],[truth])
    shifted,_,_=module.image_features([rgb,rgb],[cam,cam],[box((.35,-.1,1.3))])
    assert exact[0]['image_score']<shifted[0]['image_score']
    assert exact[0]['usable_views']==2 and not exact[0]['image_unknown']


def test_neutral_pixels_remain_unknown():
    rgb=np.full((160,160,3),100,dtype=np.uint8)
    features,_,_=module.image_features([rgb,rgb],[camera(),camera()],[box()])
    assert features[0]['image_unknown'] and features[0]['usable_views']==0


def test_empty_scene_and_parallel_rays_do_not_make_false_hits():
    owner,_,_,_=module.rasterize(camera(),[]);assert (owner==-1).all()
    cam=camera();cam['directions']=np.broadcast_to([0,0,1],(160,160,3))
    depth,_=module.ray_box(cam,box((2.,2.,1.3)));assert np.isinf(depth).all()


def test_changed_calibration_rejected():
    y,x=np.mgrid[:20,:20];rays=np.random.default_rng(1).normal(size=(20,20,6));rays[...,3:]=0
    with pytest.raises(ValueError,match='calibration'):module.camera_from_rays(rays)


def test_identical_alert_budget_and_deterministic_ties():
    rows=[dict(bad=i<3) for i in range(20)]
    result=module.top_budget(rows,np.zeros(20),.1)
    assert result['flagged']==2 and result['detected_bad']==2


def test_empty_evaluation_stratum():
    result=module.top_budget([],np.array([]),.1)
    assert result['predictions']==0 and result['flagged']==0
    assert module.bootstrap_delta([],np.array([],bool),np.array([],bool))==[None,None]
