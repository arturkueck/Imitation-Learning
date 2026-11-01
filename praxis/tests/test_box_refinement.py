"""Geometric optimizer regressions; neural weights are never loaded."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/visual_scene_v2_20261101'))
import box_refinement as module
from test_image_consistency import camera,box


def test_parameter_bounds_are_geometric_not_neural():
    base=[box()];p=np.ones(9);result=module.decode(base,p)[0]
    assert np.allclose(result['position']-base[0]['position'],.02)
    assert np.allclose(result['size']/base[0]['size'],np.exp(.18))
    assert np.allclose(result['rotation'].T@result['rotation'],np.eye(3))
    assert np.array_equal(base[0]['position'],box()['position'])


def test_nearer_box_hides_edge_samples():
    cam=camera();back=box((.2,-.1,1.8));front=box()
    points=np.array([[.2,-.1,1.7]])
    assert not module.visible_samples(cam,points,[front,back],1).any()


def test_exact_soft_silhouette_better_than_shifted():
    cam=camera();truth=box();owner,_,_,_=module.geometry.rasterize(cam,[truth])
    reference=np.full((160,160,3),255,np.uint8);rgb=reference.copy();rgb[owner==0]=[200,30,60]
    robot=np.zeros((160,160),bool)
    objective=module.Objective([rgb,rgb],[reference,reference],[robot,robot],[cam,cam],[truth])
    shifted=np.zeros(9);shifted[0]=1
    assert objective(np.zeros(9))<objective(shifted)


def test_small_translation_refines_without_truth_input():
    cam=camera();truth=box();owner,_,_,_=module.geometry.rasterize(cam,[truth])
    reference=np.full((160,160,3),255,np.uint8);rgb=reference.copy();rgb[owner==0]=[200,30,60]
    robot=np.zeros((160,160),bool);initial=box((.215,-.1,1.3))
    config=dict(module.CONFIG,pixel_stride=4,stage_maxfun=80,stage_maxiter=5)
    output,report=module.refine([rgb,rgb],[reference,reference],[robot,robot],[cam,cam],[initial],config)
    assert report['updated'] and report['objective_after']<report['objective_before']
    assert np.linalg.norm(output[0]['position']-truth['position'])<np.linalg.norm(initial['position']-truth['position'])


def test_empty_prediction_stays_empty():
    output,report=module.refine([],[],[],[],[])
    assert output==[] and report['reason']=='empty_prediction' and report['objective_calls']==0
