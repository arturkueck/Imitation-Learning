"""Centred one/two-side sweeps with exact returns, no learned controller/training."""
from pathlib import Path
import os,sys,argparse,time,json
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from run import ROOT,V4,prepare,write,camera,evaluate,route_samples
from pipeline.common import read,save,sha,now
from pipeline.lineage import connect,assert_new_family,historical_duplicate
from pipeline.claims import claim
from pipeline.locking import exclusive
from active_policy import group_focus,initial_decision,second_decision,quality,prefer_side
from centered_sweep import centered_start,plan_sweep,aim_metrics
from active_analysis import analyze
from reporting import render,summary_plot

def observed_second_decision(initial,first_quality,completed):
    if not initial['requested_sides']:return dict(required=False,reasons=['initial_policy_skip'],observed_sides=[])
    return second_decision(initial,first_quality,completed)

def consensus(models,row):
    import numpy as np
    import torch
    from learning import decode
    from ensemble_uncertainty import group_predictions
    images=np.zeros((1,5,3,160,160),np.float32);rays=np.zeros((1,5,20,20,6),np.float32);mask=np.zeros((1,5),bool)
    images[0,:3]=row['images'][0].transpose(0,3,1,2)/255.;rays[0,:3]=row['rays'][0];mask[0,:3]=True
    predictions=[]
    with torch.inference_mode():
        for model in models:
            raw=model(torch.as_tensor(images,device='cuda'),torch.as_tensor(rays,device='cuda'),torch.as_tensor(mask,device='cuda'))
            predictions.append({k:v[0].cpu().numpy() for k,v in decode(raw).items()})
    groups=sorted([g for g in group_predictions(predictions) if g['support']>=2],key=lambda g:(g['support'],g['min_detection_score']),reverse=True)[:5]
    return [dict(position=g['position'],size=g['size'],rotation=g['rotation']) for g in groups],groups

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',default='active_smoke_001');p.add_argument('--scenes',type=int,default=4);p.add_argument('--frames',type=int,default=28);p.add_argument('--table-height',type=float,default=.8)
    p.add_argument('--benchmark',action='store_true');p.add_argument('--workers',type=int,choices=[1,2,4],default=4);p.add_argument('--evaluation-worker',type=int)
    p.add_argument('--prepared-path',type=Path);p.add_argument('--data-role',choices=['development','request_train','request_validation','calibration','test'],default='development');args=p.parse_args()
    if args.benchmark and args.evaluation_worker is None:
        from benchmark import launch
        return launch(args)
    if not 1<=args.scenes<=(2000 if args.prepared_path else 100 if args.benchmark else 16) or not 16<=args.frames<=60:raise ValueError('Bounded collection run')
    run=args.prepared_path.resolve() if args.prepared_path else (HERE/args.run).resolve()
    allowed=ROOT/'experiments/vision/visual_quality_v1_20261103' if args.prepared_path else HERE
    if not run.is_relative_to(allowed) or run==allowed:raise ValueError('Invalid run')
    worker=args.evaluation_worker
    if worker is None and not args.prepared_path:
        with exclusive(ROOT/'monitor/vision-namespace'):cfg,protocol=prepare(run,args.scenes,args.frames)
    else:
        from pipeline.protocol import verify_protocol
        cfg=verify_protocol(V4/'pilot_001',full_sources=True);protocol=read(run/'config.json')
        if args.prepared_path and protocol.get('data_role')!=args.data_role:raise RuntimeError('Prepared data role changed')
        if not args.benchmark or not 0<=worker<args.workers:raise ValueError('Invalid evaluation worker')
        if any(sha(HERE/name)!=h for name,h in protocol['source_hashes'].items()):raise RuntimeError('Frozen evaluation code changed')
        if (args.scenes,args.frames)!=(protocol['scenes'],protocol['frames']):raise RuntimeError('Evaluation worker assignment changed')
    active=dict(created=now(),table_height_m=args.table_height,max_sides=2,outbound_frames=args.frames,policy='untrained deterministic RGB/prediction/observed-track rules',
        initial_thresholds=dict(two_sides_count=3,overlap=.25,spread_mm=4,min_support=3,skip_single_spread_mm=1,skip_single_edge_px=.6),
        quality=dict(distinct_points_per_object=6,merge_distance_m=.002,max_heldout_edge_px=1.5),
        focus='fixed initial predicted group center above known table; no GT object coordinates',
        start='joint pose saved after initial centering; returns exact reverse outbound path; original pose restored at end',
        planning='28/20/14 degree aimed orbits,existing edge checker unchanged; no free camera rotation',
        acquisition='initial three images then at most two outbound/return sweeps; no future candidate RGB',
        parent_protocol_sha256=sha(run/'config.json'))
    if worker is None:
        save(run/'active_config.json',active);save(run/'active_seal.json',dict(active_config_sha256=sha(run/'active_config.json'),parent_protocol_sha256=sha(run/'config.json')))
    import numpy as np
    import torch
    import mujoco
    from pipeline.generate import imports,scene
    P=imports();P.settings()
    if worker is not None:torch.set_num_threads(1)
    from pipeline.physical_setup import physical_setup
    from data_v3 import PoseGenerator
    from run import predict
    models=[]
    for parent in protocol['parents']:
        model=P.ScenePerception().cuda().eval();model.load_state_dict(torch.load(ROOT/parent['file'],map_location='cuda',weights_only=False)['model']);models.append(model)
    history_path=ROOT/protocol['history_path'] if args.prepared_path else run/'history.sqlite'
    g=PoseGenerator();history=connect(history_path,readonly=True);results=[];status_path=run/('status.json' if worker is None else f'worker_{worker}_status.json')
    def setup(rng,n,kind,long,bounds):mujoco.mj_resetData(g.m,g.d);return physical_setup(g,rng,n,kind,long,bounds)
    g.setup_v4=setup
    try:
        if abs(float(g.env.table_offset[2])-args.table_height)>1e-6:raise ValueError('Supplied known table height differs from simulated workplane')
        development=run/'development';development.mkdir(exist_ok=True)
        if worker is None:np.save(development/'family.npy',np.array([[protocol['family_seed'],i] for i in range(args.scenes)]))
        indices=range(args.scenes) if worker is None else range(worker,args.scenes,args.workers)
        for index in indices:
            if (run/'STOP_REQUESTED').exists():raise InterruptedError('STOP_REQUESTED')
            save(status_path,dict(stage='acquiring',index=index,time=now(),training_started=False));began=time.perf_counter();output=development/f'scene_{index:04d}';output.mkdir()
            family=[protocol['family_seed'],index];assert_new_family(history,family)
            truth,c,original_start,rng,meta=scene(g,cfg,'development',*family);g.qadr=c.qadr
            first=g.observation(truth,original_start);P.native_check(g)
            row={k:np.asarray([v]) for k,v in first.items()};row.update(truth)
            if historical_duplicate(history,row):raise RuntimeError('Historical content duplicate')
            claim(row,args.data_role,sha(run/'config.json'));np.savez_compressed(output/'sample.npz',**row)
            initial,groups=consensus(models,row)
            write(output/'initial_observation_summary.json',dict(initial=initial,groups=groups,table_height=args.table_height))
            anchors=[]
            for i,name in enumerate(['agentview','frontview','robot0_eye_in_hand']):
                f=80/np.tan(np.deg2rad(g.m.cam_fovy[g.m.camera(name).id]/2));anchors.append(dict(position=first['camera_positions'][i],rotation=first['camera_rotations'][i],f=f,cx=80,cy=80,width=160,height=160))
            decision=initial_decision(initial,groups,first['images'],anchors);focus=group_focus(initial,args.table_height)
            journal=[dict(stage='initial_decision',observed_contexts=[0],decision=decision,focus=focus)];images=[];cameras=[];trace=[];segments=[];completed=[];returns=[];endpoint_observations=[];latest=None
            prior=initial;state='initial_only_unverified' if initial else 'still_uncertain';failure=None;phase_boxes=[];phase_quality=[];adaptive_stage=0 if decision['requested_sides']==0 else None
            def record(q,phase):
                c.set_q(q);P.native_check(g);cam=camera(g,320)
                images.append(g.env.sim.render(width=320,height=320,camera_name='robot0_eye_in_hand')[::-1].copy());cameras.append(cam)
                metrics=aim_metrics(c,q,focus['center'],initial) if focus else None
                trace.append(dict(frame=len(images)-1,phase=phase,joints=np.asarray(q).copy(),camera=cam,aim=metrics))
                return len(images)-1
            if decision['requested_sides']>0 or (args.benchmark and initial):
                centered=centered_start(c,original_start,focus,initial);journal.append(dict(stage='initial_centering',plan=centered))
                if centered['status']=='centered':
                    saved=np.asarray(centered['start']);base=g.d.xpos[g.m.body(g.env.robots[0].robot_model.root_body).id].copy()
                    for q in route_samples(centered['alignment'],6) if np.linalg.norm(saved-original_start)>1e-9 else [saved]:record(q,'initial_alignment')
                    preferred,ranking=prefer_side(c,saved,focus,initial,base);journal.append(dict(stage='first_direction',preferred=preferred,ranking=ranking,observed_contexts=[0]))
                    candidates=[preferred,'left' if preferred=='right' else 'right'];first_plan=None
                    for side in candidates:
                        plan=plan_sweep(c,saved,focus,initial,base,side,args.frames);journal.append(dict(stage='plan_first',plan=plan))
                        if plan['status']=='planned':first_plan=plan;break
                    plan=first_plan
                    for sweep in range(2):
                        if plan is None:failure='no_complete_aimed_sweep';break
                        sweep_started=time.perf_counter()
                        ids=[record(q,f'{plan["side"]}_outbound') for q in plan['outbound']];segments.append(ids)
                        endpoint_observations.append(g.observation(truth,plan['outbound'][-1]));P.native_check(g)
                        for q in plan['return_path'][1:]:record(q,f'{plan["side"]}_return_to_start')
                        actual=g.d.qpos[c.qadr].copy();error=float(np.max(np.abs(actual-saved)));returns.append(error)
                        if error>1e-8:raise RuntimeError('Camera did not return to saved start pose')
                        completed.append(plan['side']);latest=analyze(images,cameras,segments,initial,prior,first['images'],anchors);prior=latest['adopted'];q=quality(latest['objects'])
                        phase_boxes.append(latest['adopted']);phase_quality.append(q);snapshot=f'analysis_after_sweep_{len(completed)}.json';write(output/snapshot,latest)
                        journal.append(dict(stage='after_sweep',side=plan['side'],seen_frames=len(images),quality=q,return_max_joint_error=error,analysis_snapshot=snapshot,analysis_sha256=sha(output/snapshot),elapsed_seconds=time.perf_counter()-sweep_started,
                            counterfactual_only=bool(args.benchmark and (decision['requested_sides']==0 or sweep==1 and adaptive_stage==1))))
                        if sweep==0:
                            next_decision=observed_second_decision(decision,q,completed)
                            if adaptive_stage is None:adaptive_stage=2 if next_decision['required'] else 1
                            journal.append(dict(stage='second_side_decision',decision=next_decision,seen_frames=len(images)))
                            if not next_decision['required'] and not args.benchmark:break
                            opposite='left' if completed[0]=='right' else 'right';plan=plan_sweep(c,saved,focus,initial,base,opposite,args.frames);journal.append(dict(stage='plan_second',plan=plan,seen_frames=len(images)))
                            if plan['status']!='planned':failure='opposite_side_unavailable';break
                    # Restore the original pre-centering pose over the certified alignment.
                    for q in route_samples(centered['alignment'][::-1],6) if np.linalg.norm(saved-original_start)>1e-9 else [original_start]:record(q,'restore_original_pose')
                    if np.max(np.abs(g.d.qpos[c.qadr]-original_start))>1e-8:raise RuntimeError('Original pose not restored')
                    state='supported_by_acquired_views' if latest and quality(latest['objects'])['supported'] and failure is None else 'still_uncertain'
                else:failure=centered['reason'];state='still_uncertain'
            write(output/'decisions.json',journal)
            if latest:
                raw=latest['raw'];adopted=latest['adopted'];write(output/'tracks.json',latest)
            else:raw=initial;adopted=initial
            if endpoint_observations:
                contexts={k:np.stack([first[k]]+[o[k] for o in endpoint_observations]) for k in ['images','rays']};neural=predict(models,contexts,list(range(len(endpoint_observations)+1)))
            else:neural=initial
            contexts={k:np.stack([first[k]]+[o[k] for o in endpoint_observations]) for k in ['images','rays']}
            np.savez_compressed(output/'neural_contexts.npz',**contexts)
            # Simulator GT is only used here after all acquisition/gating decisions.
            metrics={name:evaluate(boxes,truth) for name,boxes in [('initial',initial),('neural_extra',neural),('geometry_raw',raw),('geometry_adopted',adopted)]}
            chosen=min(adaptive_stage if adaptive_stage is not None else decision['requested_sides'],len(phase_boxes))
            one=phase_boxes[0] if phase_boxes else initial;two=phase_boxes[-1] if phase_boxes else initial;adaptive_boxes=phase_boxes[chosen-1] if chosen else initial
            stage_metrics={name:evaluate(boxes,truth) for name,boxes in [('initial',initial),('one_side',one),('two_sides',two),('adaptive',adaptive_boxes)]}
            active_frames=[f for f in trace if f['phase'].endswith('_outbound') or f['phase'].endswith('_return_to_start')]
            aim_summary=dict(max_axis_error_deg=max((f['aim']['axis_error_deg'] for f in active_frames),default=None),group_in_frame=all(f['aim']['group_in_frame'] for f in active_frames),checked_frames=len(active_frames))
            result=dict(index=index,family=family,state=state,initial_decision=decision,completed_sides=completed,failure=failure,return_errors=returns,aim_summary=aim_summary,
                initial=initial,geometry_raw=raw,geometry_adopted=adopted,neural_extra=neural,metrics=metrics,focus=focus,seconds=time.perf_counter()-began,
                benchmark_counterfactual=bool(args.benchmark),adaptive_chosen_stage=chosen,adaptive_requested_stage=adaptive_stage if adaptive_stage is not None else decision['requested_sides'],
                adaptive_supported=bool(chosen and phase_quality[chosen-1]['supported'] and (adaptive_stage or 0)<=len(phase_boxes)),
                stage_metrics=stage_metrics,stage_available=dict(one_side=len(phase_boxes)>=1,two_sides=len(phase_boxes)>=2),
                evaluation_stratum=dict(count=int(truth['count']),kind=meta['arrangement'],long=bool(meta['long'])))
            write(output/'result.json',result);write(output/'motion.json',dict(original_start=original_start,frames=trace,segments=segments))
            if images:
                np.savez_compressed(output/'sequence.npz',images=np.asarray(images),joint_positions=np.asarray([f['joints'] for f in trace]),camera_positions=np.asarray([cam['position'] for cam in cameras]),camera_rotations=np.asarray([cam['rotation'] for cam in cameras]))
                write(output/'cameras.json',cameras)
                truth_boxes=[dict(position=truth['positions'][i],size=truth['sizes'][i],rotation=truth['rotations'][i]) for i in np.flatnonzero(truth['active'])]
                if not args.benchmark or index<6:render(output,images,cameras,latest['tracks'] if latest else [],initial,adopted,truth_boxes)
            results.append(result);write(run/('results.json' if worker is None else f'worker_{worker}_results.json'),dict(development_only=True,policy_trained=False,optimizer_updates=0,scenes=results));print(json.dumps(dict(index=index,sides=completed,state=state,failure=failure,aim=aim_summary,errors={k:round(v['error_mm'],3) for k,v in metrics.items()})),flush=True)
        if worker is None:
            summary_plot(run,results)
            from active_reporting import annotate
            annotate(run)
            save(run/'artifacts.json',dict(files={p.relative_to(run).as_posix():sha(p) for p in development.rglob('*') if p.is_file()},active_config_sha256=sha(run/'active_config.json')))
        save(status_path,dict(stage='complete',time=now(),training_started=False,optimizer_updates=0,scenes=len(results)))
    except BaseException as e:
        save(status_path,dict(stage='error',time=now(),error=repr(e),training_started=False));raise
    finally:g.close();history.close()

if __name__=='__main__':main()
