"""Bounded closed-loop active camera pilot, frozen vision models, no training.

Target/acceptance use predictions only. Collision checking explicitly uses
simulator reference geometry. Ground truth is consumed only by evaluation.
"""
from pathlib import Path
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
os.environ.setdefault('OMP_NUM_THREADS','4')
import argparse,json,time,shutil,sys
import numpy as np
from PIL import Image
import ensemble_uncertainty as ensemble
import image_consistency as geometry

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'praxis/src'))

PLAN=dict(scene_seed=9841101,max_screened_scenes=80,target_triggered_scenes=8,min_objects=2,
          trigger='support<3 OR spread>15.5mm; threshold frozen from uncertainty_001 fixed_wrist',
          spread_threshold_mm=15.5,max_candidates=18,paths_tried=3,path_seconds=4.,path_nodes=150,
          acceptance='match within 50mm; support=3; previously full-support: spread decreases >=20%; previously missing support: spread<=15.5mm; no truth use',
          acceptance_ratio=.8,association_gate_m=.05,
          model_seeds=[1,2,3],camera_variants=['fixed','fixed_wrist'],
          execution='kinematic simulation only; native robot-world contact audit',
          collision_backend='explicit simulator-reference geometry, not camera-only free space',
          optimizer_updates=0)


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def select_target(groups,threshold=15.5):
    eligible=[i for i,g in enumerate(groups) if g['support']<3 or g['spread_mm']>threshold]
    if not eligible:return None
    return max(eligible,key=lambda i:(3-groups[i]['support'],groups[i]['spread_mm']))


def match_target(before,after,gate=.05):
    if not after:return None
    distances=np.array([np.linalg.norm(g['position']-before['position']) for g in after])
    candidate=int(distances.argmin())
    return candidate if distances[candidate]<=gate else None


def accept_update(before,after,ratio=.8):
    # Missing support is already uncertainty; zero numerical spread for a single
    # seed must not prevent improvement when all three subsequently agree.
    if after is None or after['support']!=3:return False
    if before['support']<3:return after['spread_mm']<=15.5
    return after['spread_mm']<=ratio*before['spread_mm']


def observe(generator):
    """Public observation adapter: RGB and existing camera calibration only."""
    g=generator;g.env.sim.forward();images=[];rays=[];poses=[]
    for name in ['agentview','frontview','robot0_eye_in_hand']:
        images.append(g.env.sim.render(width=160,height=160,camera_name=name)[::-1].copy())
        cid=g.m.camera(name).id;R=g.d.cam_xmat[cid].reshape(3,3).copy();origin=g.d.cam_xpos[cid].copy()
        focal=80/np.tan(np.deg2rad(g.m.cam_fovy[cid]/2));u,v=np.meshgrid(np.arange(20)*8+.5,np.arange(20)*8+.5)
        local=np.stack([(u-80)/focal,-(v-80)/focal,-np.ones_like(u)],axis=-1)
        directions=local@R.T;directions/=np.linalg.norm(directions,axis=-1,keepdims=True)
        rays.append(np.concatenate([directions,np.broadcast_to((origin-np.array([0.,0.,.8]))/.1,directions.shape)],axis=-1))
        poses.append(dict(position=origin.tolist(),rotation=R.tolist()))
    rgb=np.asarray(images,dtype=np.uint8)
    if any(image.max()<20 or image.mean()<1 for image in rgb):raise RuntimeError('Invalid camera RGB')
    return dict(images=rgb,rays=np.asarray(rays,dtype=np.float32)),poses


def serialize(groups):
    return [{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in g.items()} for g in groups]


def target_error(group,truth,index):
    if group is None or index<0:return None
    return float(np.linalg.norm(group['position']-truth['positions'][index])*1000)


def scene_metrics(groups,truth):
    data={k:np.asarray([v]) for k,v in truth.items()}
    rows,counts=ensemble.score_scene(groups,data,0,'fixed_wrist')
    errors=[r['position_error_mm'] for r in rows if r['gt_index']>=0]
    return dict(observed_gt=counts['observable_gt'],predicted_groups=len(groups),unmatched_gt=counts['unmatched_gt'],
                false_positives=counts['false_positive_groups'],matched_mean_position_mm=float(np.mean(errors)) if errors else None,
                recall10=sum(r['gt_index']>=0 and r['position_error_mm']<=10 for r in rows)/max(1,counts['observable_gt']))


def summarize(cases):
    moved=[c for c in cases if c['status']=='captured'];paired=[c for c in moved if c['target_error_before_mm'] is not None and c['target_error_after_mm'] is not None]
    known=[c for c in moved if c['target_error_before_mm'] is not None]
    accepted=[c for c in paired if c['accepted']]
    return dict(triggered_cases=len(cases),captured=len(moved),not_captured=len(cases)-len(moved),
                matched_target_pairs=len(paired),accepted_updates=sum(c['accepted'] for c in moved),
                baseline_known_targets=len(known),
                before_target_mean_mm=float(np.mean([c['target_error_before_mm'] for c in known])) if known else None,
                before_target_paired_mean_mm=float(np.mean([c['target_error_before_mm'] for c in paired])) if paired else None,
                raw_after_target_mean_mm=float(np.mean([c['target_error_after_mm'] for c in paired])) if paired else None,
                policy_target_mean_mm=float(np.mean([c['target_error_policy_mm'] for c in known])) if known else None,
                raw_improved_over_1mm=sum(c['target_error_after_mm']<c['target_error_before_mm']-1 for c in paired),
                raw_worsened_over_1mm=sum(c['target_error_after_mm']>c['target_error_before_mm']+1 for c in paired),
                accepted_but_worsened_over_1mm=sum(c['target_error_after_mm']>c['target_error_before_mm']+1 for c in accepted),
                accepted_uncertainty_decreases=sum(c['accepted'] and c['spread_after_mm']<c['spread_before_mm'] for c in moved if c['spread_after_mm'] is not None),
                target_missing_after=sum(c['target_match_after'] is None for c in moved),
                initial_false_target=sum(c['target_gt_index']<0 for c in moved),
                total_motion_samples=sum(c.get('playback_samples',0) for c in moved),
                native_robot_world_penetrations=sum(c.get('native_penetrations',0) for c in moved))


def plots(out,cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pairs=[c for c in cases if c['status']=='captured' and c['target_error_before_mm'] is not None and c['target_error_after_mm'] is not None]
    fig,axes=plt.subplots(1,3,figsize=(14,4.2))
    if pairs:
        x=np.arange(len(pairs))
        for key,label in [('before','Vorher'),('after','Neue Aufnahme'),('policy','Übernahmeregel')]:
            axes[0].plot(x,[c[f'target_error_{key}_mm'] for c in pairs],'o-',label=label)
        axes[0].set(xticks=x,xticklabels=[c['scene_index'] for c in pairs],xlabel='Szene',ylabel='Zielobjekt-Positionsfehler [mm]');axes[0].legend(fontsize=8)
        axes[1].scatter([c['target_error_before_mm'] for c in pairs],[c['target_error_after_mm'] for c in pairs],c=['tab:green' if c['accepted'] else 'tab:orange' for c in pairs])
        maximum=max([c['target_error_before_mm'] for c in pairs]+[c['target_error_after_mm'] for c in pairs]+[10]);axes[1].plot([0,maximum],[0,maximum],'k--')
        axes[1].set(xlabel='Vorher [mm]',ylabel='Nach neuer Aufnahme [mm]',title='Grün: Übernahmeregel akzeptiert')
    labels=['Fest vorher','Fest nachher','Fest+Hand vorher','Fest+Hand nachher'];values=[]
    moved=[c for c in cases if c['status']=='captured']
    for arm,when in [('fixed','before'),('fixed','after'),('fixed_wrist','before'),('fixed_wrist','after')]:
        values.append(np.mean([c['scene_metrics'][arm][when]['recall10'] for c in moved])*100 if moved else 0)
    axes[2].bar(np.arange(4),values);axes[2].set(xticks=np.arange(4),xticklabels=labels,ylabel='Mittlerer Szenen-Recall ≤10 mm [%]',ylim=(0,100));axes[2].tick_params(axis='x',labelrotation=20)
    for ax in axes:ax.grid(alpha=.25)
    fig.suptitle('Aktive Handkamera · ausgelöste Fälle · Referenz-Kollisionsgeometrie · kein Training');fig.tight_layout();fig.savefig(out/'quality.png',dpi=140);plt.close(fig)


def main():
    import torch
    from scene_data import Generator
    from active_view.collision import ArmChecker,reference_world
    from active_view.planner import Planner,Focus,rank_views,execute_kinematic
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='active_camera_001');parser.add_argument('--max-scenes',type=int,default=80);parser.add_argument('--target-cases',type=int,default=8);args=parser.parse_args()
    plan=dict(PLAN,max_screened_scenes=args.max_scenes,target_triggered_scenes=args.target_cases)
    out=HERE/args.name;out.mkdir(exist_ok=False);started=time.time();save(out/'locked_plan.json',plan);plan_hash=ensemble.digest(out/'locked_plan.json');shutil.copyfile(Path(__file__),out/'source_used.py')
    torch.set_num_threads(4);torch.manual_seed(9841101);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True;torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cuda.enable_flash_sdp(False);torch.backends.cuda.enable_mem_efficient_sdp(False)
    selection=json.loads((HERE/'run_001/selection.json').read_text())['models']
    model_source=ensemble.load_source(HERE/'run_001/source/model_prototype.py','frozen_active_model');learning=ensemble.load_source(HERE/'run_001/source/learning.py','frozen_active_learning')
    device='cuda' if torch.cuda.is_available() else 'cpu';models={};hashes={}
    for arm in plan['camera_variants']:
        for seed in plan['model_seeds']:
            record=next(r for r in selection if r['arm']==arm and r['seed']==seed);path=HERE/'run_001/checkpoints'/f'{arm}_seed{seed}_best.pth'
            if ensemble.digest(path)!=record['sha256']:raise RuntimeError('Checkpoint changed')
            model=model_source.ScenePerception().to(device);model.load_state_dict(torch.load(path,map_location=device,weights_only=False)['model']);model.eval();models[(arm,seed)]=model;hashes[path.name]=record['sha256']
    @torch.inference_mode()
    def infer(observation,arm):
        batch={k:torch.as_tensor(v[None],device=device) for k,v in observation.items()}
        predictions=[]
        for seed in plan['model_seeds']:
            raw,_=learning.run_model(models[(arm,seed)],batch,arm)
            predictions.append({k:v[0].cpu().numpy() for k,v in learning.decode(raw).items()})
        return ensemble.group_predictions(predictions)
    g=Generator();cases=[];screening=[]
    try:
        for index in range(plan['max_screened_scenes']):
            if len(cases)>=plan['target_triggered_scenes']:break
            truth=g.scene(plan['scene_seed'],index)
            if int(truth['count'])<plan['min_objects']:continue
            observation,poses_before=observe(g);before=infer(observation,'fixed_wrist');target=select_target(before,plan['spread_threshold_mm'])
            screening.append(dict(scene=index,triggered=target is not None,predicted_groups=len(before),kind=int(truth['kind'])))
            if target is None:continue
            folder=out/f'case_{len(cases):02d}';folder.mkdir();initial_target=before[target]
            case=dict(scene_index=index,kind=int(truth['kind']),status='triggered',target_group=target,
                      support_before=initial_target['support'],spread_before_mm=initial_target['spread_mm'],
                      source='explicit simulator-reference collision geometry',training_started=False)
            fixed_before=infer(observation,'fixed')
            # Identical-pose repeat controls renderer/model determinism before
            # attributing prediction changes to camera movement.
            repeat,_=observe(g)
            if not np.array_equal(repeat['images'],observation['images']):raise RuntimeError('Same-pose RGB control differs')
            checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=checker.q0.copy();initial=checker.check(start)
            if not initial.valid:
                case.update(status='start_blocked',reason=initial.reason);cases.append(case);save(folder/'case.json',case);continue
            planner=Planner(checker,seed=9841101+index)
            radius=float(np.clip(np.linalg.norm(initial_target['size'])/2+initial_target['spread_mm']/1000,.04,.10))
            focus=Focus(initial_target['position'].copy(),radius=radius,uncertainty=1.)
            candidates=rank_views(planner,focus,start,max_candidates=plan['max_candidates']);route=None;selected=None
            for candidate in candidates[:plan['paths_tried']]:
                route=planner.path(start,candidate['q'],max_nodes=plan['path_nodes'],seconds=plan['path_seconds'])
                if route is not None:selected=candidate;break
            checker.set_q(start)
            if route is None:
                case.update(status='no_reachable_view',candidate_count=len(candidates));cases.append(case);save(folder/'case.json',case);print(f'Scene {index}: no reachable view',flush=True);continue
            frames=[];samples=[];penetrations=[]
            def audit(stamp,q,pose):
                for contact in g.d.contact[:g.d.ncon]:
                    a=g.m.geom(int(contact.geom1)).name or '';b=g.m.geom(int(contact.geom2)).name or ''
                    ra=a.startswith(('robot0_','gripper0_'));rb=b.startswith(('robot0_','gripper0_'));other=b if ra else a
                    if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:penetrations.append(dict(a=a,b=b,depth=float(contact.dist)))
                samples.append(dict(t=float(stamp),q=q.tolist(),camera_position=pose[0].tolist()))
                if len(cases)<2 and len(samples)%10==1:
                    image=g.env.sim.render(width=160,height=160,camera_name='robot0_eye_in_hand')[::-1].copy();frames.append(Image.fromarray(image).resize((320,320)))
            execute_kinematic(checker,route,audit)
            if penetrations:raise RuntimeError('Native robot-world penetration during playback')
            after_observation,poses_after=observe(g);after=infer(after_observation,'fixed_wrist');fixed_after=infer(after_observation,'fixed')
            matched=match_target(initial_target,after,plan['association_gate_m']);new_target=after[matched] if matched is not None else None
            accepted=accept_update(initial_target,new_target,plan['acceptance_ratio'])
            # Evaluation starts here. It cannot select views or decide acceptance.
            truth_data={k:truth[k] for k in ['positions','sizes','rotations','visibility','active','kind']}
            base_rows,_=ensemble.score_scene(before,{k:np.asarray([v]) for k,v in truth_data.items()},0,'fixed_wrist');gt_index=base_rows[target]['gt_index']
            error_before=target_error(initial_target,truth,gt_index);error_after=target_error(new_target,truth,gt_index)
            case.update(status='captured',target_match_after=matched,accepted=accepted,target_gt_index=gt_index,
                        target_error_before_mm=error_before,target_error_after_mm=error_after,
                        target_error_policy_mm=error_after if accepted else error_before,
                        support_after=new_target['support'] if new_target is not None else 0,
                        spread_after_mm=new_target['spread_mm'] if new_target is not None else None,
                        candidate_count=len(candidates),camera_distance_m=float(np.linalg.norm(np.asarray(poses_after[2]['position'])-poses_before[2]['position'])),
                        camera_before=poses_before[2],camera_after=poses_after[2],
                        playback_samples=len(samples),collision_checks=checker.checks,native_penetrations=len(penetrations),
                        scene_metrics={arm:dict(before=scene_metrics(a,truth_data),after=scene_metrics(b,truth_data)) for arm,a,b in [('fixed',fixed_before,fixed_after),('fixed_wrist',before,after)]})
            # Geometric objects are frozen during kinematic camera playback.
            actual=np.array([g.d.xpos[b].copy() for b in g.bodies])
            if not np.allclose(actual,truth['positions'],rtol=0,atol=1e-7):raise RuntimeError('Objects moved during observation')
            np.savez_compressed(folder/'observations.npz',before_images=observation['images'],before_rays=observation['rays'],after_images=after_observation['images'],after_rays=after_observation['rays'])
            np.savez_compressed(folder/'evaluation_only.npz',**truth_data)
            Image.fromarray(np.concatenate([observation['images'][2],after_observation['images'][2]],axis=1)).resize((640,320)).save(folder/'wrist_before_after.png')
            save(folder/'predictions.json',dict(before=serialize(before),after=serialize(after),fixed_before=serialize(fixed_before),fixed_after=serialize(fixed_after)))
            save(folder/'trajectory.json',samples);save(folder/'case.json',case)
            if frames:frames[0].save(folder/'motion.gif',save_all=True,append_images=frames[1:],duration=150,loop=0)
            cases.append(case);save(out/'status.json',dict(stage='active_camera_test',screened=len(screening),triggered=len(cases),training_started=False))
            print(f'Scene {index}: captured, accepted={accepted}, target mm {error_before} -> {error_after}',flush=True)
    finally:g.close()
    for name,sha in hashes.items():
        if ensemble.digest(HERE/'run_001/checkpoints'/name)!=sha:raise RuntimeError('Checkpoint changed after test')
    if ensemble.digest(out/'locked_plan.json')!=plan_hash:raise RuntimeError('Plan changed')
    plots(out,cases)
    result=dict(training_started=False,neural_optimizer_updates=0,checkpoint_sha256=hashes,plan_sha256=plan_hash,
                screened_scenes=len(screening),summary=summarize(cases),cases=cases,screening=screening,
                limitations=['small triggered-case pilot, not representative all-scene accuracy','known simulator collision geometry; camera-only world not demonstrated',
                             'new wrist poses outside tiny training jitter may cause distribution shift','all three views recaptured; fixed-only models control changed robot occlusions',
                             'target matching/acceptance heuristic can be wrong; no uncertainty correctness guarantee',
                             'scene recall uses common GT set observable in original three views, for both camera variants',
                             'raw error means condition on matched pairs; missing targets reported separately',
                             'kinematic, static scene, no real hardware/dynamic tracking'],elapsed_seconds=time.time()-started)
    save(out/'results.json',result);save(out/'status.json',dict(stage='complete',training_started=False,summary=result['summary']));print(json.dumps(result['summary']),flush=True)


if __name__=='__main__':main()
