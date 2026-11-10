"""Tests for association and abstention; no checkpoint/model loading."""
from pathlib import Path
import importlib.util
import numpy as np

path=Path(__file__).resolve().parents[2]/'experiments/vision/visual_scene_v2_20261101/ensemble_uncertainty.py'
spec=importlib.util.spec_from_file_location('ensemble_diagnostic',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def prediction(positions, probabilities=None):
    n=len(positions)
    return dict(position=np.asarray(positions,dtype=float).reshape(n,3),size=np.tile([.04,.05,.06],(n,1)),
                rotation=np.tile(np.eye(3),(n,1,1)),probability=np.ones(n) if probabilities is None else np.asarray(probabilities),
                visibility=np.ones((n,3)))


def test_slot_permutation_does_not_change_association():
    a=prediction([[0,0,0],[.15,0,0]])
    b=prediction([[.151,0,0],[.001,0,0]])
    groups=module.group_predictions([a,b,a])
    assert len(groups)==2 and all(g['support']==3 for g in groups)
    assert all(g['spread_mm']<1 for g in groups)


def test_low_support_not_confident_even_if_zero_spread():
    groups=module.group_predictions([prediction([[0,0,0]]),prediction([]),prediction([])])
    assert len(groups)==1 and groups[0]['spread_mm']==0 and groups[0]['support']==1
    assert module.rule_metrics([dict(groups[0],bad=True)],100)['accepted']==0


def test_large_disagreement_splits_instead_of_averaging():
    groups=module.group_predictions([prediction([[0,0,0]]),prediction([[.2,0,0]]),prediction([[0,0,0]])])
    assert len(groups)==2 and sorted(g['support'] for g in groups)==[1,2]


def test_common_wrong_prediction_is_counted_as_error():
    groups=module.group_predictions([prediction([[.02,0,0]])]*3)
    data=dict(active=np.array([[True]]),visibility=np.ones((1,1,3)),positions=np.zeros((1,1,3)),kind=np.array([0]))
    rows,scene=module.score_scene(groups,data,0,'fixed_wrist')
    assert rows[0]['bad'] and rows[0]['spread_mm']==0
    assert rows[0]['position_error_mm']==20 and scene['unmatched_gt']==0


def test_all_models_missing_target_reported_separately():
    data=dict(active=np.array([[True]]),visibility=np.ones((1,1,3)),positions=np.zeros((1,1,3)),kind=np.array([0]))
    rows,scene=module.score_scene([],data,0,'fixed')
    assert rows==[] and scene['unmatched_gt']==1 and scene['all_seed_blind_scene']


def test_box_axis_symmetry_has_zero_corner_disagreement():
    a=dict(position=np.zeros(3),size=np.array([.04,.05,.06]),rotation=np.eye(3))
    b=dict(a,rotation=np.diag([-1,-1,1]))
    assert module.corner_distance(a,b)<1e-10


def test_remote_prediction_is_false_positive_and_missed_target():
    groups=module.group_predictions([prediction([[.3,0,0]])]*3)
    data=dict(active=np.array([[True]]),visibility=np.ones((1,1,3)),positions=np.zeros((1,1,3)),kind=np.array([0]))
    rows,scene=module.score_scene(groups,data,0,'fixed')
    assert rows[0]['bad'] and scene['false_positive_groups']==1 and scene['unmatched_gt']==1
