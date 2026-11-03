"""Bounded RGB/known-camera diagnostic. No training, no test-set access, no real robot."""
from pathlib import Path
import os,sys,json,time,argparse,copy
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];V4=ROOT/'experiments/visual_side_v4_20261102'
sys.path.insert(0,str(V4))
from pipeline.common import read,save,sha,now
from pipeline.lineage import inventory,connect,assert_fresh_seed,assert_new_family,historical_duplicate
from pipeline.claims import claim
from pipeline.locking import exclusive
sys.path.insert(0,str(HERE))
from geometry import edge_samples
from tracking import track
from refine import fit_one,gate,prepare_views
from reporting import render,summary_plot

def jsonable(v):
    import numpy as np
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    raise TypeError(type(v).__name__)

def write(path,value):save(path,json.loads(json.dumps(value,default=jsonable)))

def predict(models,row,history,device='cuda'):
    import numpy as np
    import torch
    from learning import decode
    from ensemble_uncertainty import group_predictions
    images=np.zeros((1,5,3,160,160),np.float32);rays=np.zeros((1,5,20,20,6),np.float32);mask=np.zeros((1,5),bool)
    current=history[-1];images[0,:2]=row['images'][current,:2].transpose(0,3,1,2)/255.;rays[0,:2]=row['rays'][current,:2];mask[0,:2]=True
    for slot,index in enumerate(reversed(history),2):
        images[0,slot]=row['images'][index,2].transpose(2,0,1)/255.;rays[0,slot]=row['rays'][index,2];mask[0,slot]=True
    preds=[]
    with torch.inference_mode():
        for model in models:
            raw=model(torch.as_tensor(images,device=device),torch.as_tensor(rays,device=device),torch.as_tensor(mask,device=device))
            preds.append({k:v[0].cpu().numpy() for k,v in decode(raw).items()})
    groups=group_predictions(preds)
    # Detection consensus is frozen before any geometric refinement; no GT count.
    groups=sorted([g for g in groups if g['support']>=2],key=lambda g:(g['support'],g['min_detection_score']),reverse=True)[:5]
    return [dict(position=g['position'],size=g['size'],rotation=g['rotation']) for g in groups]

def camera(g,width,cam='robot0_eye_in_hand'):
    import numpy as np
    cid=g.m.camera(cam).id
    return dict(position=g.d.cam_xpos[cid].copy(),rotation=g.d.cam_xmat[cid].reshape(3,3).copy(),f=width/2/np.tan(np.deg2rad(g.m.cam_fovy[cid]/2)),cx=width/2,cy=width/2,width=width,height=width)

def route_samples(route,count):
    import numpy as np
    route=np.asarray(route,float);length=np.linalg.norm(np.diff(route,axis=0),axis=1);cum=np.r_[0,np.cumsum(length)]
    if cum[-1]<1e-8:raise ValueError('No camera motion')
    result=[]
    for value in np.linspace(0,cum[-1],count):
        i=min(int(np.searchsorted(cum,value,side='right')-1),len(route)-2)
        a=(value-cum[i])/max(length[i],1e-12);result.append(route[i]*(1-a)+route[i+1]*a)
    return np.asarray(result)

def evaluate(boxes,truth):
    import numpy as np
    from followup_core import scene_error
    pred=dict(position=np.array([b['position'] for b in boxes]).reshape(-1,3),size=np.array([b['size'] for b in boxes]).reshape(-1,3),rotation=np.array([b['rotation'] for b in boxes]).reshape(-1,3,3),probability=np.ones(len(boxes)))
    data={k:np.asarray(truth[k])[None] for k in ['positions','sizes','rotations','active']}
    return scene_error(pred,data,0,np.asarray(truth['active'],bool))

def prepare(run,scenes,frames):
    import shutil
    from pipeline.protocol import verify_protocol
    if run.exists():raise FileExistsError('Preserve old diagnostic runs; choose a new --run')
    run.mkdir(parents=True);inventory(run/'history.sqlite');db=connect(run/'history.sqlite',readonly=True)
    try:
        seed=95341000+1
        while db.execute('SELECT 1 FROM seeds WHERE seed=?',(seed,)).fetchone():seed+=1000
        assert_fresh_seed(db,seed)
    finally:db.close()
    source=V4/'pilot_001';cfg=verify_protocol(source,full_sources=True);frozen=read(source/'perception_freeze.json')
    if not frozen['side_gate_passed']:raise RuntimeError('Frozen perception gate missing')
    for row in frozen['models']:
        if sha(ROOT/row['file'])!=row['sha256']:raise RuntimeError('Frozen B checkpoint changed')
    protocol=dict(created=now(),purpose='development_only_geometry_diagnostic',family_seed=seed,scenes=scenes,frames=frames,width=320,
        fitting_frame_rule='indices>0 with index modulo3 !=0',heldout_frame_rule='indices>0 with index modulo3 ==0',anchor_views='initial three images',
        perception='frozen B three-seed consensus; majority detections capped5',parents=frozen['models'],perception_freeze_sha256=sha(source/'perception_freeze.json'),
        training_started=False,optimizer_updates=0,geometry_optimizer='bounded scipy least_squares, soft_l1,9 parameters per cuboid',
        camera_pose_source='exact simulated kinematics; no pose noise in this diagnostic',collision_scope='existing reference-certified route; no collision development or real robot control',
        history_sha256=sha(run/'history.sqlite'),source_hashes={p.name:sha(p) for p in HERE.glob('*.py')})
    save(run/'config.json',protocol);save(run/'protocol_seal.json',dict(config_sha256=sha(run/'config.json')))
    for p in HERE.glob('*.py'):
        dest=run/'source'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
    save(run/'status.json',dict(stage='prepared',time=now(),training_started=False))
    return cfg,protocol

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',default='smoke_001');parser.add_argument('--scenes',type=int,default=4);parser.add_argument('--frames',type=int,default=40)
    args=parser.parse_args()
    if not 1<=args.scenes<=16 or not 16<=args.frames<=80:raise ValueError('Bounded diagnostic:1..16 scenes,16..80 frames')
    run=(HERE/args.run).resolve()
    if not run.is_relative_to(HERE) or run==HERE:raise ValueError('Invalid output path')
    with exclusive(ROOT/'monitor/vision-namespace'):cfg,protocol=prepare(run,args.scenes,args.frames)
    import numpy as np
    import torch
    import mujoco
    from pipeline.generate import imports,load_bank,make_sample
    P=imports();P.settings()
    from pipeline.physical_setup import physical_setup
    from data_v3 import PoseGenerator
    models=[]
    for parent in protocol['parents']:
        m=P.ScenePerception().cuda().eval();m.load_state_dict(torch.load(ROOT/parent['file'],map_location='cuda',weights_only=False)['model']);models.append(m)
    g=PoseGenerator();history=connect(run/'history.sqlite',readonly=True);results=[]
    def setup(rng,n,kind,long,bounds):
        mujoco.mj_resetData(g.m,g.d);return physical_setup(g,rng,n,kind,long,bounds)
    g.setup_v4=setup
    try:
        bank,start,signature=load_bank(g,run,cfg)
        folder=run/'development';folder.mkdir();np.save(folder/'family.npy',np.array([[protocol['family_seed'],i] for i in range(args.scenes)]))
        for index in range(args.scenes):
            save(run/'status.json',dict(stage='acquiring',index=index,time=now(),training_started=False));begin=time.perf_counter()
            output=folder/f'scene_{index:04d}';output.mkdir();family=[protocol['family_seed'],index];assert_new_family(history,family)
            row,metadata=make_sample(g,models,bank,start,signature,cfg,'development',*family)
            metadata['focus_source']='frozen_V4_B_three_seed_ensemble'
            if historical_duplicate(history,row):raise RuntimeError('Historical RGB/geometry duplication')
            claim(row,'development',sha(run/'config.json'))
            np.savez_compressed(output/'sample.npz',**row);write(output/'capture_metadata.json',metadata)
            initial=predict(models,row,[0]);captures=[c for c in metadata['captures'] if c['state']=='captured' and c['family'] in ['right','left','base','elevated']]
            if not initial or not captures:
                result=dict(index=index,family=family,status='blocked',reason='no_consensus_objects' if not initial else 'no_existing_certified_side_route');write(output/'result.json',result);results.append(result);continue
            capture=captures[0];qpath=route_samples(capture['waypoints'],args.frames);images=[];cameras=[];width=protocol['width']
            for q in qpath:
                g.d.qpos[g.qadr]=q;g.d.qvel[:]=0;g.env.sim.forward();P.native_check(g)
                images.append(g.env.sim.render(width=width,height=width,camera_name='robot0_eye_in_hand')[::-1].copy());cameras.append(camera(g,width))
            np.savez_compressed(output/'sequence.npz',images=np.asarray(images),joint_positions=qpath,camera_positions=np.array([c['position'] for c in cameras]),camera_rotations=np.array([c['rotation'] for c in cameras]))
            write(output/'cameras.json',cameras)
            fit_ids=[i for i in range(1,args.frames) if i%3!=0];heldout_ids=[i for i in range(1,args.frames) if i%3==0]
            anchors=[dict(position=row['camera_positions'][0,i],rotation=row['camera_rotations'][0,i],f=80/np.tan(np.deg2rad(g.m.cam_fovy[g.m.camera(cam).id]/2)),cx=80,cy=80,width=160,height=160) for i,cam in enumerate(['agentview','frontview','robot0_eye_in_hand'])]
            tracks,points,track_stats=track(images,cameras,fit_ids,initial);raw=[];adopted=[];objects=[]
            for obj,box in enumerate(initial):
                cloud=np.array([p['point'] for p in points if p['object_index']==obj]).reshape(-1,3)
                fit=fit_one(box,initial,images,cameras,fit_ids,cloud)
                heldout=prepare_views(images,cameras,heldout_ids,box,initial);anchor=prepare_views(row['images'][0],anchors,[0,1,2],box,initial)
                decision=gate(box,fit['candidate'],heldout,anchor,len(cloud))
                if fit['status']!='fitted':decision['accepted']=False;decision['reasons'].append(fit['status'])
                raw.append(fit['candidate']);adopted.append(fit['candidate'] if decision['accepted'] else box);objects.append(dict(object_index=obj,fit=fit,gate=decision))
            neural=predict(models,row,[0,capture['slot']])
            # GT enters only after all predictions and gate decisions have been finalized.
            truth={k:row[k] for k in ['positions','sizes','rotations','active']}
            metrics={label:evaluate(boxes,truth) for label,boxes in [('initial',initial),('neural_extra',neural),('geometry_raw',raw),('geometry_adopted',adopted)]}
            truth_boxes=[dict(position=row['positions'][i],size=row['sizes'][i],rotation=row['rotations'][i]) for i in np.flatnonzero(row['active'])]
            result=dict(index=index,family=family,status='evaluated',initial=initial,neural_extra=neural,geometry_raw=raw,geometry_adopted=adopted,objects=objects,metrics=metrics,
                fit_frames=fit_ids,heldout_frames=heldout_ids,tracks=len(tracks),triangulated_points=len(points),tracking_rejections=track_stats,route_family=capture['family'],seconds=time.perf_counter()-begin)
            write(output/'tracks.json',dict(tracks=tracks,triangulated_points=points));write(output/'result.json',result)
            display=lambda boxes:[dict(center=b['position'],size=b['size'],rotation=b['rotation']) for b in boxes]
            write(output/'scene.json',dict(ground_truth=display(truth_boxes),initial_prediction=display(initial),updated_predictions=[display(adopted)],frame='world_meters',geometry_source='RGB plus camera poses; ground_truth only for display'))
            render(output,images,cameras,tracks,initial,adopted,truth_boxes);results.append(result)
            save(run/'status.json',dict(stage='evaluated',index=index,time=now(),training_started=False));print(json.dumps(dict(index=index,tracks=len(tracks),triangulated=len(points),accepted=sum(o['gate']['accepted'] for o in objects),errors={k:round(v['error_mm'],3) for k,v in metrics.items()})),flush=True)
        write(run/'results.json',dict(development_only=True,optimizer_updates=0,scenes=results));summary_plot(run,results)
        files={p.relative_to(run).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
        save(run/'artifacts.json',dict(files=files,config_sha256=sha(run/'config.json')));save(run/'status.json',dict(stage='complete',time=now(),training_started=False,optimizer_updates=0,scenes=len(results)))
    except BaseException as error:
        save(run/'status.json',dict(stage='error',time=now(),error=repr(error),training_started=False));raise
    finally:g.close();history.close()

if __name__=='__main__':main()
