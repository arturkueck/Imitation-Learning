"""Reference subtraction and explicit simulator-label separation."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/vision/visual_scene_v2_20261101'))
import reference_evidence as evidence
from reference_capture import segmentation_labels,mask_metric,verify_scene,verify_rgb_pair


def test_unchanged_rgb_has_no_foreground():
    rgb=np.full((40,40,3),240,np.uint8)
    assert not evidence.foreground(rgb,rgb,np.zeros((40,40),bool))['mask'].any()


def test_gray_object_detected_against_its_actual_reference():
    empty=np.full((40,40,3),240,np.uint8);rgb=empty.copy();rgb[10:25,12:27]=100
    result=evidence.foreground(rgb,empty,np.zeros((40,40),bool))
    assert result['mask'][12:23,14:25].all()


def test_robot_mask_excludes_changes_and_filled_holes():
    empty=np.full((40,40,3),240,np.uint8);rgb=empty.copy();rgb[8:30,8:30]=80
    robot=np.zeros((40,40),bool);robot[15:23,15:23]=True
    result=evidence.foreground(rgb,empty,robot)
    assert not (result['mask']&robot).any() and not result['valid'][15:23,15:23].any()


def test_identical_white_object_interior_is_not_invented_without_outline():
    rgb=np.full((40,40,3),255,np.uint8)
    result=evidence.foreground(rgb,rgb,np.zeros((40,40),bool))
    assert not result['mask'].any()


def test_segmentation_requires_geometry_type_not_only_id():
    segmentation=np.array([[[5,10],[4,10],[5,20]]])
    robot,objects=segmentation_labels(segmentation,[[20]],[10],5)
    assert robot.tolist()==[[True,False,False]] and objects.tolist()==[[0,0,1]]


def test_robot_mask_independent_of_unknown_object_list():
    seg=np.array([[[5,10],[5,20]]])
    a,_=segmentation_labels(seg,[],[10],5)
    b,_=segmentation_labels(seg,[[20]],[10],5)
    assert np.array_equal(a,b)


def test_oracle_only_changes_evaluation_not_predicted_mask():
    empty=np.full((40,40,3),240,np.uint8);rgb=empty.copy();rgb[10:25,10:25]=100
    mask=evidence.foreground(rgb,empty,np.zeros((40,40),bool))['mask']
    good=mask_metric(mask,mask,np.ones_like(mask));bad=mask_metric(mask,~mask,np.ones_like(mask))
    assert good['iou']==1 and bad['iou']==0
    assert np.array_equal(mask,evidence.foreground(rgb,empty,np.zeros((40,40),bool))['mask'])


def test_shape_and_threshold_validation():
    rgb=np.zeros((40,40,3),np.uint8)
    with pytest.raises(ValueError):evidence.foreground(rgb,rgb,np.zeros((20,20),bool))
    with pytest.raises(ValueError):evidence.foreground(rgb,rgb,np.zeros((40,40),bool),threshold=0)


def test_scene_pairing_allows_roundoff_but_rejects_geometry_change():
    keys=['positions','sizes','rotations','rays','active','count','kind','family']
    original={key:np.zeros(3) for key in keys};new={key:np.zeros(3) for key in keys}
    new['rotations'][0]=1e-14
    assert verify_scene(new,original)['rotations']==1e-14
    new['positions'][0]=.001
    with pytest.raises(RuntimeError,match='positions'):verify_scene(new,original)


def test_rgb_pairing_allows_only_sparse_one_bit_roundoff():
    original=np.zeros((3,10,10,3),np.uint8);new=original.copy();new[0,0,0,0]=1
    assert verify_rgb_pair(new,original)['changed_channels']==1
    new[0,0,0,0]=2
    with pytest.raises(RuntimeError):verify_rgb_pair(new,original)
    new[:]=1
    with pytest.raises(RuntimeError):verify_rgb_pair(new,original)
