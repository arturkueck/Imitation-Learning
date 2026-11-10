"""Bounded reference-simulator active-view demonstration; no training."""
from pathlib import Path
import sys,json,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'praxis/src'));sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
from scene_data import Generator
from active_view.collision import ArmChecker,reference_world,World
from active_view.planner import Planner,Focus,rank_views,execute_kinematic


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='reference_demo_002');args=parser.parse_args()
    out=Path(__file__).resolve().parent/args.name;out.mkdir(exist_ok=False)
    started=time.time();g=Generator()
    try:
        g.scene(301,3,force_count=3)
        checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=checker.q0.copy()
        initial=checker.check(start)
        if not initial.valid:raise RuntimeError(f'Initial state blocked: {initial}')
        unknown=ArmChecker(g.m,g.d,World([],source='visual',complete=False,max_age=None))
        unknown_result=unknown.check(start)
        if unknown_result.valid:raise RuntimeError('Unknown world incorrectly accepted')
        from visual_capture import capture as capture_visual
        grid,rgb,empty=capture_visual(g)
        Image.fromarray(rgb).save(out/'visual_observation.png');Image.fromarray(empty).save(out/'empty_reference.png')
        # No simulator object boxes are smuggled into the visual planner.
        visual_checker=ArmChecker(g.m,g.d,grid.as_world(max_age=60.))
        visual_result=visual_checker.check(start)
        np.savez_compressed(out/'visual_map.npz',centers=grid.centers,labels=grid.labels,bounds=[grid.low,grid.high],resolution=grid.resolution)
        planner=Planner(checker);focus=Focus(np.array([0.,.03,.88]),radius=.08)
        def images():
            g.env.sim.forward()
            return np.concatenate([g.env.sim.render(width=320,height=320,camera_name=name)[::-1].copy() for name in ['agentview','frontview','robot0_eye_in_hand']],axis=1)
        checker.set_q(start);Image.fromarray(images()).save(out/'before.png')
        candidates=rank_views(planner,focus,start)
        proposals=[];selected=None;plan=None
        for candidate in candidates[:6]:
            route=planner.path(start,candidate['q'],max_nodes=250,seconds=12.)
            proposals.append(dict(score=candidate['score'],clearance_lower_bound_m=candidate['clearance'],reachable=route is not None,camera=candidate['camera'].tolist()))
            if route is not None:selected=candidate;plan=route;break
        if plan is None:raise RuntimeError(f'No certified view trajectory among {len(candidates)} candidates')
        frames=[];trajectory=[];native_penetrations=[]
        def capture(stamp,q,pose):
            for contact in g.d.contact[:g.d.ncon]:
                a=g.m.geom(int(contact.geom1)).name or '';b=g.m.geom(int(contact.geom2)).name or ''
                robot_a=a.startswith(('robot0_','gripper0_'));robot_b=b.startswith(('robot0_','gripper0_'))
                other=b if robot_a else a
                if robot_a!=robot_b and not other.startswith('fixed_mount0_') and contact.dist<-.000001:
                    native_penetrations.append(dict(time=stamp,a=a,b=b,distance=float(contact.dist)))
            trajectory.append(dict(time=stamp,q=q.tolist(),camera_position=pose[0].tolist(),camera_rotation=pose[1].tolist()))
            if len(trajectory)%4==1:frames.append(images())
        execute_kinematic(checker,plan,capture)
        if native_penetrations:raise RuntimeError(f'Independent native collision audit failed: {native_penetrations[:1]}')
        Image.fromarray(images()).save(out/'after.png')
        frames.append(images());pil=[Image.fromarray(x).resize((720,240)) for x in frames]
        pil[0].save(out/'motion.gif',save_all=True,append_images=pil[1:],duration=120,loop=0)
        np.savez_compressed(out/'path.npz',waypoints=np.asarray(plan.waypoints))
        (out/'trajectory.json').write_text(json.dumps(trajectory,indent=2))
        report=dict(training_started=False,optimizer_updates=0,backend='explicit simulator-reference geometry',
            camera_housing='configured proxy; not a measured real mount',camera_mount_included=True,
            collision_shapes=len(checker.local),self_collision_pairs=len(checker.self_pairs),
            initial_clearance_lower_bound_m=initial.clearance,world_margin_m=checker.world_margin,self_margin_m=checker.self_margin,
            locked_gripper_positions=checker.frozen[7:9].tolist(),unknown_map_rejected=not unknown_result.valid,
            visual_map=dict(free_cells=int((grid.labels==0).sum()),possible_occupied_cells=int((grid.labels==1).sum()),unknown_cells=int((grid.labels==2).sum()),
                start_valid=visual_result.valid,rejection_reason=visual_result.reason,blocked_pair=visual_result.pair,
                calibration='simulator-known static background depth and known robot mask; foreground from RGB differences'),
            native_robot_world_penetrations=len(native_penetrations),
            candidate_count=len(candidates),tested_candidates=proposals,selected_score=selected['score'],
            waypoints=len(plan.waypoints),playback_samples=len(trajectory),collision_checks=checker.checks,
            elapsed_seconds=time.time()-started,execution='kinematic simulation, no hardware or torque controller',
            active_view_gain='heuristic prediction, not measured neural-model improvement')
        (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    finally:g.close()


if __name__=='__main__':main()
