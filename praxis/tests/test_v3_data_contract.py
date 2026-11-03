"""Prevent future-image leakage and unsafe swept-box acceptance."""
import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/visual_active_v3_20261101'))
from model_v3 import context_arrays
from data_v3 import object_path_free,assignment


def data():
    return dict(images=np.zeros((1,6,3,160,160,3),np.uint8),rays=np.zeros((1,6,3,20,20,6),np.float32),
                visibility=np.ones((1,6,5,3),np.float32),positions=np.zeros((1,5,3),np.float32),
                sizes=np.ones((1,5,3),np.float32)*.04,rotations=np.broadcast_to(np.eye(3),(1,5,3,3)).copy(),
                active=np.ones((1,5),bool),count=np.array([5]),kind=np.array([0]),family=np.array([[1,0]]))


def test_future_image_and_visibility_do_not_enter_context():
    d=data();before=context_arrays(d,[0],'M2',current=0,history=[[0]])
    d['images'][:,1:]=255;d['rays'][:,1:]=100;d['visibility'][:,1:]=0
    after=context_arrays(d,[0],'M2',current=0,history=[[0]])
    for k in before:np.testing.assert_array_equal(before[k],after[k])
    with pytest.raises(ValueError):context_arrays(d,[0],'M2',current=0,history=[[1]])


def test_no_wrist_means_no_wrist_visibility_label():
    batch=context_arrays(data(),[0],'M2',current=2,history=[[]])
    assert not batch['view_available'][0,2:].any()
    assert not batch['visibility'][0,:,2].any()
    assert batch['view_available'][0,:2].all()


def test_swept_aabb_overlap_blocks_all_object_sizes():
    lo=np.array([[0.,0.,0.]]);hi=np.array([[1.,1.,1.]])
    pos=np.array([[.5,.5,.5]]);sizes=np.array([[.05,.02,.04]]);rot=np.eye(3)[None]
    assert not object_path_free(lo,hi,pos,sizes,rot,np.array([True]))
    assert object_path_free(lo,hi,pos+2,sizes,rot,np.array([True]))
    assert object_path_free(lo,hi,pos,sizes,rot,np.array([False]))


def test_joint_layout_allocation_never_uses_invalid_fallback():
    counts=np.zeros(6,int);kinds={k:0 for k in ['scattered','mixed','tower','wall']}
    for i in range(10000):
        n,kind=assignment(9364001,i);counts[n]+=1
        if n: kinds[kind]+=1
        assert n>=2 or kind=='scattered'
        assert n>=3 or kind!='wall'
    assert abs(counts[0]/10000-.05)<.015
    fractions=np.array(list(kinds.values()))/sum(kinds.values())
    np.testing.assert_allclose(fractions,[.25,.25,.35,.15],atol=.025)
