from pathlib import Path
from dataclasses import asdict
import sys,json
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'praxis/src'))
from active_view.capture_requests import CameraPose,CaptureRequest,RequestJournal,pose_from_mujoco,pose_error


def request():
    return CaptureRequest.new(episode_id='episode-1',scene_revision='revision-1',source_observation_ids=('rgb-before',),
                              desired_camera_pose=CameraPose((.3,0,.4),(0,1,0,0)),reason='occluded',
                              target_scope='objects',target_track_ids=('predicted-track-1',),
                              model_revision='model-hash',calibration_id='calibration-1',
                              created_at='2026-11-01T00:00:00+00:00',example_only=True)


def planned(journal,r):
    return journal.transition(r.request_id,'planned',scene_revision=r.scene_revision,plan_id='validated-plan-reference',
                              planner_revision='planner-hash',planning_backend='sim_reference',joint_positions_rad=[0]*7,
                              planned_camera_pose=asdict(r.desired_camera_pose))


def test_desired_pose_survives_restart_and_blocked_request(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r)
    journal.transition(r.request_id,'blocked',scene_revision=r.scene_revision,reason='no free path')
    restored=RequestJournal(journal.path)
    assert restored.state(r.request_id)=='blocked'
    assert restored.records()[0]['payload']['desired_camera_pose']['position_m']==[.3,0,.4]


def test_actual_pose_is_separate_and_error_is_saved(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r);planned(journal,r)
    actual=CameraPose((.304,0,.4),(0,1,0,0))
    row=journal.transition(r.request_id,'captured',scene_revision=r.scene_revision,observation_id='rgb-after',
                           calibration_id=r.calibration_id,image_uri='observations/rgb-after.png',
                           actual_camera_pose=asdict(actual),captured_at='2026-11-01T00:00:01+00:00')
    assert row['payload']['pose_error']['position_m']==pytest.approx(.004)
    assert journal.records()[0]['payload']['desired_camera_pose']['position_m'][0]==.3
    assert journal.records()[-1]['payload']['actual_camera_pose']['position_m'][0]==.304
    journal.transition(r.request_id,'evaluated',scene_revision=r.scene_revision,evaluation_id='quality-report-1',decision='hold')
    assert journal.state(r.request_id)=='evaluated'


def test_changed_scene_or_calibration_cannot_fulfill_old_request(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r)
    with pytest.raises(ValueError,match='Scene changed'):journal.transition(r.request_id,'blocked',scene_revision='changed',reason='changed')
    planned(journal,r)
    with pytest.raises(ValueError,match='Calibration changed'):
        journal.transition(r.request_id,'captured',scene_revision=r.scene_revision,observation_id='rgb',calibration_id='other',
                           image_uri='rgb.png',actual_camera_pose=asdict(r.desired_camera_pose),captured_at='2026-11-01T00:00:01+00:00')
    assert journal.state(r.request_id)=='planned'


def test_capture_without_plan_and_duplicate_request_rejected(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r)
    with pytest.raises(ValueError,match='Duplicate'):journal.create(r)
    with pytest.raises(ValueError,match='state transition'):journal.transition(r.request_id,'captured',scene_revision=r.scene_revision)
    assert len(journal.records())==1


def test_incomplete_or_modified_log_fails_closed(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r)
    original=journal.path.read_text(encoding='utf-8')
    journal.path.write_text(original.replace('occluded','altered'),encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):journal.records()
    journal.path.write_text(original.rstrip('\n'),encoding='utf-8')
    with pytest.raises(ValueError,match='Incomplete'):journal.records()


def test_existing_writer_lock_is_not_silently_deleted(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl');journal.lock.write_text('another writer')
    with pytest.raises(FileExistsError):journal.create(request())
    assert journal.lock.read_text()=='another writer'


def test_camera_frame_conversion_uses_explicit_base_transform():
    T=np.eye(4);T[:3,3]=[1,2,3]
    pose=pose_from_mujoco([1.2,2.3,3.4],np.eye(3),T)
    assert np.allclose(pose.position_m,[.2,.3,.4])
    assert np.allclose(pose.rotation(),np.diag([1,-1,-1]))
    assert pose_error(pose,pose)==dict(position_m=0.,angle_rad=0.)


def test_invalid_frames_nonfinite_quaternion_and_unknown_payload_rejected(tmp_path):
    with pytest.raises(ValueError):CameraPose((0,0,0),(2,0,0,0))
    with pytest.raises(ValueError):CameraPose((np.nan,0,0),(1,0,0,0))
    with pytest.raises(ValueError):CameraPose((0,0,0),(1,0,0,0),frame_id='world')
    journal=RequestJournal(tmp_path/'requests.jsonl');r=request();journal.create(r)
    with pytest.raises(ValueError,match='Unexpected'):journal.transition(r.request_id,'blocked',scene_revision=r.scene_revision,reason='blocked',ground_truth_position=[0,0,0])


def test_no_request_and_positive_decision_are_logged_without_breaking_lifecycle(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl')
    journal.decision(decision_id='decision-no',episode_id='episode-1',scene_revision='revision-1',source_observation_ids=['rgb-before'],
                     needs_reobserve=True,request_image=False,reason='no feasible candidate')
    assert journal.records()[0]['request_id'] is None
    r=request();journal.create(r)
    journal.decision(decision_id='decision-yes',episode_id=r.episode_id,scene_revision=r.scene_revision,source_observation_ids=r.source_observation_ids,
                     needs_reobserve=True,request_image=True,request_id=r.request_id,reason='candidate selected')
    assert journal.state(r.request_id)=='requested'
    planned(journal,r);assert journal.state(r.request_id)=='planned'


def test_decision_scores_are_preserved_and_invalid_probability_rejected(tmp_path):
    journal=RequestJournal(tmp_path/'requests.jsonl')
    kwargs=dict(decision_id='decision',episode_id='episode',scene_revision='scene',source_observation_ids=['rgb'],
                needs_reobserve=False,request_image=False,reason='expected benefit too small')
    row=journal.decision(**kwargs,need_probability=.2,expected_net_gain_mm=-3.,candidate_id='candidate-7')
    assert row['payload']['expected_net_gain_mm']==-3. and row['payload']['need_probability']==.2
    with pytest.raises(ValueError,match='probability'):journal.decision(**dict(kwargs,decision_id='other'),need_probability=2)


def test_request_head_shapes_and_parameter_counts():
    sys.path.insert(0,str(ROOT/'experiments/vision/visual_active_v3_20261101'))
    import torch
    from request_heads import RequestHeads,OBSERVATION_FEATURES,CANDIDATE_FEATURES
    model=RequestHeads().eval()
    with torch.inference_mode():out=model(torch.zeros(2,23),torch.zeros(2,6,19))
    assert len(OBSERVATION_FEATURES)==23 and len(CANDIDATE_FEATURES)==19
    assert out['gain'].shape==(2,6) and out['need_image_logit'].shape==(2,)
    assert sum(p.numel() for p in model.parameters())==17539
