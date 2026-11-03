"""Render and independently verify every accepted guidance view; no training."""
import json,time,math,shutil
import numpy as np
from PIL import Image
import pilot as P
from data_v3 import PoseGenerator
from active_view.collision import ArmChecker,reference_world
from active_view.side_views import aimed_pose,optical_axis_error
from active_view.capture_requests import RequestJournal,CaptureRequest,pose_from_mujoco,utc_now
from dataclasses import asdict
from replay_scene import restore_scene

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',default='guidance_001');args=p.parse_args()
    out=P.HERE/args.run;folder=out/'captures';folder.mkdir(exist_ok=False);began=time.perf_counter()
    rows=[json.loads(x) for x in (out/'families.jsonl').read_text().splitlines()]
    source=P.HERE/'pilot_002';old={r['index']:r for r in [json.loads(x) for x in (source/'families.jsonl').read_text().splitlines()]}
    bank={e['id']:e for e in json.loads((out/'bank.json').read_text())['entries']}
    g=PoseGenerator();audit=[];P.settings();hashes=json.loads((source/'checkpoint_hashes.json').read_text())
    assert all(P.sha(P.ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints'/name)==value for name,value in hashes.items())
    try:
        for record in rows:
            if record['stage']!='captured':continue
            index=record['index'];prior=old[index]
            with np.load(source/'samples'/f'sample_{index:04d}.npz') as z:sample={k:np.array(z[k]) for k in z.files}
            truth={k:sample[k] for k in ['positions','sizes','rotations','active','count','kind','family']}
            replay=restore_scene(g,sample,prior)
            checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));g.qadr=checker.qadr;q=np.array(record['q'])
            if not checker.check(q).valid:raise RuntimeError('Capture goal no longer free')
            seed=np.array(bank[record['bank_id']]['q'])
            if not checker.edge(seed,q):raise RuntimeError('Exact stored-scene refinement suffix not free')
            body=g.m.body(g.env.robots[0].robot_model.root_body).id
            T=np.eye(4);T[:3,:3]=g.d.xmat[body].reshape(3,3);T[:3,3]=g.d.xpos[body]
            pc=np.array(record['actual_camera']['position']);R=np.array(record['actual_camera']['rotation'])
            seed_camera=np.array(bank[record['bank_id']]['camera']);focus=np.array(record['desired_focus'])
            upright=aimed_pose(seed_camera,focus);roll=math.atan2(float(upright[:,1]@R[:,0]),float(upright[:,0]@R[:,0]))
            requested=pose_from_mujoco(seed_camera,aimed_pose(seed_camera,focus,roll),T)
            planned=pose_from_mujoco(pc,R,T)
            episode=f'guidance-{index:04d}';journal=RequestJournal(folder/f'{index:04d}.jsonl')
            req=CaptureRequest.new(episode_id=episode,scene_revision=episode+'-static',source_observation_ids=['fixed-left-0','fixed-right-0','wrist-0'],
                desired_camera_pose=requested,reason='scheduled_guidance_replay_not_learned_policy',model_revision='frozen_V3_M2_three_seeds',calibration_id='sim-'+episode)
            journal.create(req);journal.transition(req.request_id,'planned',scene_revision=req.scene_revision,plan_id=episode+'-certified',
                planner_revision='128_piece_bank_and_certified_target_refinement',planning_backend='sim_reference',joint_positions_rad=q.tolist(),planned_camera_pose=asdict(planned))
            row=g.observation(truth,q);P.native_check(g);error=P.ray_error(g,row)
            position_difference=float(np.max(np.abs(row['camera_positions'][2]-pc)));rotation_difference=float(np.max(np.abs(row['camera_rotations'][2]-R)))
            if position_difference>1e-6 or rotation_difference>1e-6 or error>.001:raise RuntimeError('Actual capture/calibration disagrees with plan')
            actual=pose_from_mujoco(row['camera_positions'][2],row['camera_rotations'][2],T)
            image_name=f'{index:04d}_wrist.png';Image.fromarray(row['images'][2]).save(folder/image_name)
            np.savez_compressed(folder/f'{index:04d}.npz',**row)
            journal.transition(req.request_id,'captured',scene_revision=req.scene_revision,observation_id=episode+'-wrist',calibration_id=req.calibration_id,
                image_uri=image_name,actual_camera_pose=asdict(actual),captured_at=utc_now())
            journal.transition(req.request_id,'evaluated',scene_revision=req.scene_revision,evaluation_id=episode+'-diagnostic',decision='hold')
            audit.append(dict(index=index,replay=replay,projection_max_px=error,position_max_difference_m=position_difference,rotation_max_difference=rotation_difference,
                optical_axis_error_deg=optical_axis_error(row['camera_positions'][2],row['camera_rotations'][2],focus),image_sha256=P.sha(folder/image_name),array_sha256=P.sha(folder/f'{index:04d}.npz')))
    finally:g.close()
    assert len(audit)==sum(r['stage']=='captured' for r in rows)
    assert all(P.sha(P.ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints'/name)==value for name,value in hashes.items())
    report=dict(passed=True,captured_images=len(audit),captures=audit,maximum_projection_error_px=max([r['projection_max_px'] for r in audit],default=None),
        maximum_position_difference_m=max([r['position_max_difference_m'] for r in audit],default=None),
        actual_maximum_axis_error_deg=max([r['optical_axis_error_deg'] for r in audit],default=None),
        seconds=time.perf_counter()-began,optimizer_updates=0,original_checkpoint_hashes_unchanged=True,
        requested_pose_note='Fresh replay request: bank camera position and target-centred direction with closest certified roll; not reconstructed original IK intent',
        production_update_adopted=False)
    P.save(out/'capture_audit.json',report);print(json.dumps({k:v for k,v in report.items() if k!='captures'}),flush=True)

if __name__=='__main__':main()
