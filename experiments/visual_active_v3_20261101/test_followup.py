"""Focused scientific boundary checks for the new V3 head pipeline."""
import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from followup_core import contexts,candidate_features,scene_error,observed,robot_projection


def data():
    n=2
    return dict(images=np.zeros((n,6,3,160,160,3),np.uint8),rays=np.zeros((n,6,3,20,20,6),np.float32),
      visibility=np.ones((n,6,5,3),np.float32),positions=np.zeros((n,5,3),np.float32),sizes=np.ones((n,5,3),np.float32)*.04,
      rotations=np.broadcast_to(np.eye(3),(n,5,3,3)).copy(),active=np.ones((n,5),bool),count=np.ones(n,int)*5,
      kind=np.zeros(n,int),family=np.array([[11,0],[11,1]]),joint_positions=np.zeros((n,6,7)),
      camera_positions=np.zeros((n,6,3,3)),camera_rotations=np.broadcast_to(np.eye(3),(n,6,3,3,3)).copy(),
      valid=np.ones((n,6),bool),expected_robot_occlusion=np.zeros((n,6,2)),robot_fraction=np.zeros((n,6,3)))


def test_future_pixels_do_not_change_prefix():
    d=data();before=contexts(d,[0],(0,))
    d['images'][:,1:]=255;d['rays'][:,1:]=42
    after=contexts(d,[0],(0,))
    assert np.array_equal(before['images'],after['images'])
    assert np.array_equal(before['rays'],after['rays'])


def test_oracle_diagnostics_and_geometry_not_candidate_input():
    d=data();x=np.zeros(23);x[21]=-1
    a=candidate_features(x,d,0,(0,),np.eye(4))
    for k in ['images','robot_fraction','positions','sizes','rotations','visibility']:d[k][...]=17
    b=candidate_features(x,d,0,(0,),np.eye(4))
    assert np.array_equal(a,b)
    assert a.shape==(6,19)


def test_future_history_rejected():
    from model_v3 import context_arrays
    with pytest.raises(ValueError):context_arrays(data(),[0],'M2',current=0,history=[[1]])


def test_missing_and_extra_objects_are_penalized():
    d=data();d['active'][0,1:]=False
    p=dict(probability=np.zeros(5),position=np.zeros((5,3)),size=np.ones((5,3))*.04,rotation=np.broadcast_to(np.eye(3),(5,3,3)))
    missing=scene_error(p,d,0,d['active'][0]);assert missing['error_mm']==62.5 and missing['missing']==1
    p['probability'][0]=1
    assert scene_error(p,d,0,d['active'][0])['error_mm']<1e-5
    assert scene_error(p,d,0,np.zeros(5,bool))['error_mm']==50


def test_empty_focus_is_scene_without_invented_target():
    p=dict(probability=np.zeros(5),position=np.zeros((5,3)),size=np.ones((5,3))*.04,
           rotation=np.broadcast_to(np.eye(3),(5,3,3)),visibility=np.zeros((5,3)))
    x=observed([p,p,p],1)
    assert x[22]==0 and x[21]==-1 and (x[:20]==0).all()


def test_robot_occlusion_uses_known_projection_only():
    vertices=np.array([[-.1,-.1,-1],[.1,.1,-1]])
    result=robot_projection([vertices],np.zeros((3,3)),np.array([np.eye(3)]*3))
    assert result.shape==(2,) and (result>0).all() and (result<1).all()
