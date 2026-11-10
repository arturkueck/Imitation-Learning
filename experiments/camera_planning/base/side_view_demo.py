"""New bounded broad-view illustration, frozen V3 models, no training/hardware."""
from pathlib import Path
import sys,json,time,itertools,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'praxis/src'));sys.path.insert(0,str(ROOT/'experiments/vision/visual_active_v3_20261101'))
from data_v3 import PoseGenerator
from model_v3 import ScenePerception
from followup_core import infer,errors,observable
from make_comparison_gifs import Panel,groups,corners,jsonable
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Planner,Focus,timed_samples
from active_view.view_sweep import inspect_or_probe,SweepSettings
from active_view.side_views import side_view,SideSettings
from ensemble_uncertainty import group_predictions
from active_view.capture_requests import RequestJournal,CaptureRequest,pose_from_mujoco,utc_now
from dataclasses import asdict
import torch
from preflight import settings


def save(path,value):path.write_text(json.dumps(jsonable(value),indent=2,ensure_ascii=False),encoding='utf-8')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--name');p.add_argument('--direction',choices=['right','left','base'],required=True);a=p.parse_args();a.name=a.name or ('side_view_'+a.direction+'_001')
    out=HERE/a.name;out.mkdir(exist_ok=False);settings();g=PoseGenerator();began=time.time()
    try:
        truth=g.scene(9642101,0,force_count=3)
        checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=checker.q0.copy();g.qadr=checker.qadr
        row=g.observation(truth,start);models=[];hashes={}
        run=ROOT/'experiments/vision/visual_active_v3_20261101/run_001';expected=json.loads((run/'checkpoint_hashes.json').read_text())
        for seed in [1,2,3]:
            path=run/'checkpoints'/f'M2_seed{seed}_best.pth';sha=hashlib.sha256(path.read_bytes()).hexdigest()
            if sha!=expected[path.name]:raise RuntimeError('Frozen checkpoint changed')
            model=ScenePerception().cuda();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);model.eval();models.append(model);hashes[path.name]=sha
        data={k:np.stack([v,v])[None] for k,v in row.items()}
        data.update({k:np.asarray(truth[k])[None] for k in ['positions','sizes','rotations','active','count','kind','family']})
        before=infer(models,data,[0],(0,))[0];first=groups(before)
        if not first:raise RuntimeError('No predicted focus; do not substitute true object positions')
        predicted=group_predictions(before);target=max(predicted,key=lambda v:(3-v['support'],v['spread_mm']))
        center=target['position'].copy()
        radius=float(np.clip(np.linalg.norm(target['size'])/2+target['spread_mm']/1000,.04,.09))
        focus=Focus(center,radius=radius)
        planner=Planner(checker,seed=9642110)
        root_body=g.m.body(g.env.robots[0].robot_model.root_body).id
        base=g.d.xpos[root_body].copy()
        cfg=SideSettings(maximum_elevation_deg=40.,heights_above_focus_m=(.11,.15,.20,.25)) if a.direction=='base' else SideSettings()
        result=side_view(planner,focus,start,base,a.direction,cfg)
        if result['stage']!='target_view':
            save(out/'report.json',dict(result=result,training_started=False,direction=a.direction));print(json.dumps(jsonable(result)),flush=True);return
        candidate=result['candidate'];plan=result['plan'];save(out/'planning.json',dict(audit=result['audit'],candidate=candidate,focus=asdict(focus),waypoints=plan.waypoints))
        # A separate visual-only gate is reported, never silently replaced by reference geometry.
        sys.path.insert(0,str(HERE));from visual_capture import capture as capture_visual
        checker.set_q(start);grid,rgb,empty=capture_visual(g)
        visual=ArmChecker(g.m,g.d,grid.as_world(max_age=120.))
        visual_decision=inspect_or_probe(Planner(visual),focus,start,require_visual=True,settings=SweepSettings(maximum_seconds=10.))
        save(out/'visual_gate.json',dict(stage=visual_decision['stage'],reason=visual_decision['reason'],detail=visual_decision.get('detail'),
            note='RGB background differences and simulator-known static depth limits; no real visual safety proof'))
        checker.set_q(candidate['q']);after_row=g.observation(truth,candidate['q'])
        for key,value in after_row.items():data[key][0,1]=value
        after=infer(models,data,[0],(0,1))[0];last=groups(after)
        mask=observable(data,0,(0,))|observable(data,0,(0,1));before_error=errors(before,data,0,mask);after_error=errors(after,data,0,mask)
        old_score=float(np.mean([v['error_mm'] for v in before_error]));new_score=float(np.mean([v['error_mm'] for v in after_error]))
        gt=[dict(center=truth['positions'][i],size=truth['sizes'][i],rotation=truth['rotations'][i]) for i in np.flatnonzero(truth['active'])]
        pts=np.concatenate([corners(b) for b in gt+first+last]);low=pts.min(0)-.025;high=np.maximum(pts.max(0)+.025,low+.10);low[2]=min(low[2],.795)
        title={'right':'Kamera rechts | Blick nach links zum Ziel','left':'Kamera links | Blick nach rechts zum Ziel','base':'Kamera zur Basis | Blick von Basis weg zum Ziel'}[a.direction]
        panel=Panel(gt,first,[last],title,(low,high),old_score)
        panel.fig.texts[1].set_text('Gezielte niedrige Seitenansicht | Richtung relativ zur Roboterbasis | eingefrorenes M2')
        panel.fig.texts[-1].set_text('Kinematische Simulation mit Referenzgeometrie. Visuelle Freigabe separat geprueft; kein Realroboter.')
        root=g.env.robots[0].robot_model.root_body;body=g.m.body(root).id;checker.set_q(start)
        T=np.eye(4);T[:3,:3]=g.d.xmat[body].reshape(3,3);T[:3,3]=g.d.xpos[body]
        desired=pose_from_mujoco(candidate['camera'],candidate['rotation'],T)
        journal=RequestJournal(out/'capture_requests.jsonl');req=CaptureRequest.new(episode_id='broad-9642101-0',scene_revision='static-0',source_observation_ids=['initial-fixed0','initial-fixed1','initial-wrist'],desired_camera_pose=desired,reason='geometric_large_baseline_demo_not_learned_policy',model_revision='frozen_M2_3seeds',calibration_id='sim-broad-0')
        journal.create(req);journal.transition(req.request_id,'planned',scene_revision=req.scene_revision,plan_id='broad-plan-0',planner_revision='broad_view_v1_complete_path',planning_backend='sim_reference',joint_positions_rad=candidate['q'].tolist(),planned_camera_pose=asdict(desired))
        frames=[];durations=[];trajectory=[];native=0
        def images():return [g.env.sim.render(width=160,height=160,camera_name=n)[::-1].copy() for n in ['agentview','frontview','robot0_eye_in_hand']]
        def frame(text,updated=None,score=None,duration=125):
            nonlocal native
            for contact in g.d.contact[:g.d.ncon]:
                aa=g.m.geom(int(contact.geom1)).name or '';bb=g.m.geom(int(contact.geom2)).name or '';ra=aa.startswith(('robot0_','gripper0_'));rb=bb.startswith(('robot0_','gripper0_'));other=bb if ra else aa
                if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:raise RuntimeError('Native robot-world penetration')
            native+=1;frames.append(panel.frame(images(),updated,text,score,int(updated is not None)));durations.append(duration)
        checker.set_q(start);frame('Ausgangsansicht: gespeicherte erste Vorhersage',duration=1200)
        # Entire segments were certified before playback; audit every rendered state too.
        for stamp,q in timed_samples(plan,dt=.125):
            if not checker.check(q).valid:raise RuntimeError('Rendered trajectory state no longer valid')
            checker.set_q(q);pose=checker.camera_pose(q);trajectory.append(dict(time=stamp,q=q.tolist(),camera_position=pose[0].tolist(),camera_rotation=pose[1].tolist()))
            frame(f'Seitenansicht: {candidate["elevation_deg"]:.0f} Grad ueber Zielhoehe | Blickfehler {candidate["optical_axis_error_deg"]:.1f} Grad')
        checker.set_q(candidate['q']);actual_row=g.observation(truth,candidate['q']);Image.fromarray(actual_row['images'][2]).save(out/'wrist_after.png')
        actual=pose_from_mujoco(actual_row['camera_positions'][2],actual_row['camera_rotations'][2],T)
        journal.transition(req.request_id,'captured',scene_revision=req.scene_revision,observation_id='broad-wrist-1',calibration_id=req.calibration_id,image_uri='wrist_after.png',actual_camera_pose=asdict(actual),captured_at=utc_now())
        frame('Neue Aufnahme: aktualisierte Vorhersage in Gruen',last,new_score,2500)
        frames[-1].save(out/'poster.png');palette=frames[-1].convert('P',palette=Image.Palette.ADAPTIVE,colors=256);encoded=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
        encoded[0].save(out/'comparison.gif',save_all=True,append_images=encoded[1:],duration=durations,loop=0,optimize=True,disposal=1)
        save(out/'scene_comparison.json',dict(ground_truth=gt,initial_prediction=first,updated_predictions=[last],inspection_camera=dict(focus=center,start=dict(position=row['camera_positions'][2],rotation=row['camera_rotations'][2]),goal=dict(position=candidate['camera'],rotation=candidate['rotation']),path=[v['camera_position'] for v in trajectory]),note='Explicit requested side view; no learned view policy or visual safety claim',source_case=dict(before=before_error,after=after_error)))
        save(out/'trajectory.json',trajectory)
        report=dict(training_started=False,optimizer_updates=0,geometry_backend='sim_reference',direction=a.direction,camera_change=candidate['change'],camera_elevation_deg=candidate['elevation_deg'],optical_axis_error_deg=candidate['optical_axis_error_deg'],distance_to_focus_m=candidate['distance_to_focus_m'],
            initial_set_error_mm=old_score,updated_set_error_mm=new_score,native_robot_world_penetrations=0,rendered_states_checked=native,
            whole_path_checks=checker.checks,visual_gate=dict(stage=visual_decision['stage'],reason=visual_decision['reason'],detail=visual_decision.get('detail')),
            focus_source='most uncertain predicted group; actual target pose not used in planning',checkpoint_hashes=hashes,planning=result['audit'],
            elapsed_seconds=time.time()-began,policy='geometric demo only; learned production policy unchanged')
        journal.transition(req.request_id,'evaluated',scene_revision=req.scene_revision,evaluation_id='diagnostic-only-'+a.direction,decision='hold')
        report['update_adopted']=False
        save(out/'report.json',report);print(json.dumps(jsonable(report)),flush=True)
    finally:g.close()
if __name__=='__main__':main()
