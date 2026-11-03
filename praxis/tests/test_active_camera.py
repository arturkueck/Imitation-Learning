"""Closed-loop decision and observation tests without fitting model weights."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/visual_scene_v2_20261101'))
import active_camera_test as pilot


def group(support=3,spread=2.,position=(0,0,.85)):
    return dict(support=support,spread_mm=spread,position=np.asarray(position,dtype=float))


def test_trigger_marks_missing_support_and_high_spread_only():
    assert pilot.select_target([group()]) is None
    assert pilot.select_target([group(),group(spread=16)])==1
    assert pilot.select_target([group(spread=30),group(support=1,spread=0)])==1


def test_shared_wrong_prediction_can_remain_unflagged():
    assert pilot.select_target([group(position=(.2,.2,1.2))]) is None


def test_target_association_has_distance_gate():
    assert pilot.match_target(group(),[group(position=(.01,0,.85))])==0
    assert pilot.match_target(group(),[group(position=(.3,0,.85))]) is None
    assert pilot.match_target(group(),[]) is None


def test_acceptance_requires_all_seeds_and_better_predicted_evidence():
    assert not pilot.accept_update(group(spread=20),group(support=1,spread=0))
    assert not pilot.accept_update(group(spread=20),group(spread=19))
    assert pilot.accept_update(group(spread=20),group(spread=10))
    assert pilot.accept_update(group(support=1,spread=0),group(spread=3))
    assert not pilot.accept_update(group(),None)


def test_missing_after_prediction_does_not_improve_policy_denominator():
    case=dict(status='captured',target_error_before_mm=20.,target_error_after_mm=None,target_error_policy_mm=20.,accepted=False,
              spread_before_mm=20.,spread_after_mm=None,target_match_after=None,target_gt_index=0,
              playback_samples=4,native_penetrations=0)
    report=pilot.summarize([case])
    assert report['baseline_known_targets']==1 and report['matched_target_pairs']==0
    assert report['policy_target_mean_mm']==20 and report['target_missing_after']==1


def test_observation_recomputes_wrist_extrinsics_after_joint_change():
    from scene_data import Generator
    g=Generator()
    try:
        g.scene(9841101,1,force_count=2)
        before,poses=pilot.observe(g)
        g.d.qpos[g.robot_joints[0]]+=.01
        after,new_poses=pilot.observe(g)
        assert before['images'].shape==(3,160,160,3)
        assert np.allclose(np.linalg.norm(after['rays'][...,:3],axis=-1),1,atol=1e-6)
        assert np.array_equal(before['rays'][:2],after['rays'][:2])
        assert not np.allclose(before['rays'][2],after['rays'][2])
        assert not np.allclose(poses[2]['position'],new_poses[2]['position'])
    finally:g.close()
