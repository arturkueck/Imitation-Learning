"""Bounded V4 feasibility pilot. Not a production training entrypoint."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import sys,json,time,hashlib,copy,random,traceback
from collections import Counter
import numpy as np
import torch
from PIL import Image,ImageFilter,ImageDraw
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/visual_active_v3_20261101'))
sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'praxis/src'))
from data_v3 import PoseGenerator,assignment,KINDS
from model_v3 import ScenePerception,context_arrays,tensor_context,predict
from followup_core import infer
from ensemble_uncertainty import group_predictions
from preflight import settings
from learning import criterion
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Planner,Focus
from active_view.side_views import side_view,SideSettings,optical_axis_error
from active_view.view_sweep import view_change
import psutil

SEED=94140201
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def jsonable(v):
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,Path):return str(v)
    raise TypeError(type(v).__name__)
def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,default=jsonable,indent=2),encoding='utf-8');tmp.replace(path)
def ray_error(g,row):
    """Project world points lying on exported rays back to their sampled pixels."""
    errors=[]
    for cam in range(3):
        R=row['camera_rotations'][cam].astype(float);origin=row['camera_positions'][cam].astype(float)
        cid=g.m.camera(['agentview','frontview','robot0_eye_in_hand'][cam]).id
        focal=80/np.tan(np.deg2rad(g.m.cam_fovy[cid]/2))
        for y,x in [(0,0),(10,10),(19,19),(0,19)]:
            ray=row['rays'][cam,y,x];world=ray[3:]*.1+np.array([0,0,.8])+ray[:3]*.4
            local=(world-origin)@R
            pixel=np.array([80+focal*local[0]/(-local[2]),80-focal*local[1]/(-local[2])])
            errors.append(float(np.max(np.abs(pixel-np.array([x*8+.5,y*8+.5])))))
    return max(errors)
def native_check(g):
    for contact in g.d.contact[:g.d.ncon]:
        a=g.m.geom(int(contact.geom1)).name or '';b=g.m.geom(int(contact.geom2)).name or ''
        ra=a.startswith(('robot0_','gripper0_'));rb=b.startswith(('robot0_','gripper0_'))
        other=b if ra else a
        if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:
            raise RuntimeError('Native robot-world penetration')

def get_context(data,ids,history):
    histories=[];curr=[]
    for i in ids:
        valid=[p for p in history if data['pose_available'][i,p]]
        if not valid:raise ValueError('No available acquired prefix')
        curr.append(max(valid));histories.append(list(reversed(valid)))
    a=context_arrays(data,ids,'M2',current=curr,history=histories)
    # Same observable target set for both paired reconstruction losses. Role
    # visibility stays contextual; newly visible objects counted separately later.
    union=np.max(data['visibility'][ids],axis=(1,3))>=.05
    a['active']=a['active']&union
    a['target_observable_override']=a['active'].copy()
    return a

def paired_loss(model,data,ids,device='cuda'):
    losses=[]
    for history in [(0,),(0,1,2)]:
        a=get_context(data,ids,history);batch=tensor_context(a,device);raw,av=predict(model,batch)
        # criterion determines GT membership from visibility. Keep the union GT
        # membership without relabelling the per-role visibility loss.
        loss=union_criterion(raw,batch,av)
        losses.append(loss)
    return sum(losses)/2

def union_criterion(raw,batch,av):
    # Existing criterion computes both membership and role labels from visibility.
    # A first criterion call uses the unchanged contextual role labels; a second
    # with union membership is used only for geometric/detection components.
    _,role,_=criterion(raw,batch,av)
    union=batch['target_observable_override']
    surrogate={**batch,'visibility':union[:,:,None].expand(-1,-1,3).float()}
    _,parts,_=criterion(raw,surrogate,av)
    return parts['detection']+5*parts['position']+parts['size']+.5*parts['rotation']+.25*role['visibility']

def numerical_pilot(out,paths):
    rows=[]
    for path in paths[:40]:
        with np.load(path) as z:rows.append({k:z[k] for k in z.files})
    if len(rows)<32:raise RuntimeError('Need 32 valid pilot families for effective batch 32')
    data={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    model=ScenePerception().cuda();parent=ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints/M2_seed1_best.pth'
    model.load_state_dict(torch.load(parent,map_location='cuda',weights_only=False)['model']);model.train()
    opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.LambdaLR(opt,lambda step:min(1.,(step+1)/3))
    n=sum(p.numel() for p in model.parameters());assert n==904112
    initial=copy.deepcopy(model.state_dict());order=np.random.default_rng(SEED+1).permutation(32).tolist()
    timings=[];losses=[];state=None;last_diff=None
    def micro(offset):
        loss=paired_loss(model,data,order[offset:offset+4])
        if not torch.isfinite(loss):raise RuntimeError('Nonfinite paired loss')
        (loss/8).backward();return float(loss.detach())/8
    for step in range(3):
        torch.cuda.synchronize();began=time.perf_counter();opt.zero_grad(set_to_none=True);total=0.
        for offset in range(0,32,4):
            total+=micro(offset)
            if step==1 and offset==12:
                state=copy.deepcopy(dict(model=model.state_dict(),optimizer=opt.state_dict(),scheduler=scheduler.state_dict(),
                    grads={name:p.grad for name,p in model.named_parameters()},torch_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all(),numpy_rng=np.random.get_state(),python_rng=random.getstate(),
                    sampler=dict(order=order,next_offset=16,epoch=0,update=1),partial_loss=total))
                torch.save(state,out/'diagnostic_partial_resume.pth')
        torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);opt.step();scheduler.step()
        torch.cuda.synchronize();timings.append(time.perf_counter()-began);losses.append(total)
        if step==1:expected=copy.deepcopy(dict(model=model.state_dict(),optimizer=opt.state_dict(),scheduler=scheduler.state_dict(),loss=total))
    delta=max(float((model.state_dict()[k]-initial[k]).abs().max()) for k in initial)
    if delta<=0:raise RuntimeError('No actual parameter updates')
    state=torch.load(out/'diagnostic_partial_resume.pth',map_location='cuda',weights_only=False)
    model.load_state_dict(state['model']);opt.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
    for name,p in model.named_parameters():p.grad=state['grads'][name].clone()
    torch.set_rng_state(state['torch_rng'].cpu());torch.cuda.set_rng_state_all([v.cpu() for v in state['cuda_rng']])
    np.random.set_state(state['numpy_rng']);random.setstate(state['python_rng'])
    assert state['sampler']['order']==order and state['sampler']['next_offset']==16
    total=state['partial_loss']
    for offset in range(state['sampler']['next_offset'],32,4):total+=micro(offset)
    torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);opt.step();scheduler.step()
    diff=max(float((model.state_dict()[k]-expected['model'][k]).abs().max()) for k in expected['model'])
    moment_diff=0.
    actual_opt=opt.state_dict()
    for key,val in expected['optimizer']['state'].items():
        for name,x in val.items():
            y=actual_opt['state'][key][name]
            moment_diff=max(moment_diff,float((x-y).abs().max()) if torch.is_tensor(x) else float(abs(x-y)))
    if diff!=0 or moment_diff!=0 or abs(total-expected['loss'])>1e-8 or scheduler.state_dict()!=expected['scheduler']:
        raise RuntimeError(f'Partial update resume mismatch {diff}/{moment_diff}')
    # Validation-like fixed probe, used only to measure runtime, never selection.
    model.eval();began=time.perf_counter()
    with torch.inference_mode():probe=float(paired_loss(model,data,list(range(32,40)) or list(range(8))))
    torch.cuda.synchronize();probe_seconds=time.perf_counter()-began
    report=dict(parameters=n,optimizer_updates=3,replayed_resume_suffix_updates=1,trained_model_promoted=False,
        effective_scene_batch=32,microbatch=4,paired_contexts=2,fp32=True,losses=losses,parameter_max_delta=delta,
        seconds_per_update=timings,median_seconds_per_update=float(np.median(timings)),
        partial_epoch_and_accumulation_resume=dict(exact=True,weight_max_difference=diff,optimizer_max_difference=moment_diff,offset=16),
        fixed_probe_loss=probe,fixed_probe_seconds=probe_seconds,probe_families=min(8,len(rows)-32),
        peak_cuda_allocated_gib=torch.cuda.max_memory_allocated()/2**30,peak_cuda_reserved_gib=torch.cuda.max_memory_reserved()/2**30)
    save(out/'numerical.json',report)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,3));ax.plot([1,2,3],losses,'o-',label='Diagnose-Trainingsloss (32 Szenen)')
    ax.set(xlabel='Benchmark-Update',ylabel='Gepaarter Loss',title='Nur technischer Pilot – keine Lernkurve oder Overfitting-Auswertung');ax.legend();fig.tight_layout();fig.savefig(out/'diagnostic_loss.png');plt.close(fig)
    return report

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--families',type=int,default=200);p.add_argument('--name',default='pilot_001');args=p.parse_args()
    if not 40<=args.families<=200:raise ValueError('Pilot bounded to 40..200 families')
    out=HERE/args.name;out.mkdir(exist_ok=False);(out/'samples').mkdir();(out/'examples').mkdir()
    settings();random.seed(SEED);started=time.perf_counter();records=[];paths=[];rss=0
    sourcefiles=[Path(__file__),HERE/'PLAN.md',ROOT/'praxis/src/active_view/side_views.py',ROOT/'praxis/src/active_view/collision.py',ROOT/'praxis/src/active_view/planner.py',ROOT/'experiments/visual_active_v3_20261101/data_v3.py',ROOT/'experiments/visual_active_v3_20261101/model_v3.py',ROOT/'experiments/visual_active_v3_20261101/physical_setup.py',ROOT/'experiments/visual_scene_v2_20261101/learning.py']
    (out/'source').mkdir()
    for f in sourcefiles:
        dest=out/'source'/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes())
    save(out/'manifest.json',dict(pilot_only=True,main_training_authorized=False,seed=SEED,families=args.families,
        per_family_slots=['initial','near','requested'],requested_families=['right','left','base','elevated','difficult'],
        full_six_candidate_bank=False,maximum_side_search_seconds=4,simulation_reference_only=True,source_hashes={str(f.relative_to(ROOT)):sha(f) for f in sourcefiles}))
    models=[];run=ROOT/'experiments/visual_active_v3_20261101/run_001';expected=json.loads((run/'checkpoint_hashes.json').read_text())
    for seed in [1,2,3]:
        path=run/'checkpoints'/f'M2_seed{seed}_best.pth'
        if sha(path)!=expected[path.name]:raise RuntimeError('Original checkpoint hash mismatch')
        model=ScenePerception().cuda().eval();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);models.append(model)
    save(out/'checkpoint_hashes.json',{f'M2_seed{s}_best.pth':expected[f'M2_seed{s}_best.pth'] for s in [1,2,3]})
    g=PoseGenerator()
    try:
        for index in range(args.families):
            if (HERE/'STOP_REQUESTED').exists():raise RuntimeError('Pilot STOP_REQUESTED')
            t=time.perf_counter();n,kind=assignment(SEED,index);shape='long_thin' if index%10==0 and n else 'standard'
            if shape=='long_thin':kind='scattered'
            rng=np.random.default_rng(np.random.SeedSequence([SEED,index]));record=dict(index=index,count=n,kind=kind,shape=shape,seed=SEED)
            try:
                for attempt in range(40):
                    try:sizes,pos=g._setup(rng,n,kind,shape=='long_thin');break
                    except ValueError as e:g.rejections[str(e)]=g.rejections.get(str(e),0)+1
                else:raise RuntimeError('Scene settlement exhausted')
                truth=dict(positions=pos.astype('float32'),sizes=sizes.astype('float32'),rotations=np.array([g.d.xmat[b].reshape(3,3).copy() for b in g.bodies],np.float32),active=np.arange(5)<n,count=np.int64(n),kind=np.int64(KINDS.index(kind)),family=np.array([SEED,index],np.int64))
                checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=checker.q0.copy();g.qadr=checker.qadr
                if not checker.check(start).valid:raise ValueError('Initial arm invalid')
                observations=[g.observation(truth,start)];available=[True,False,False];qs=[start.copy(),start.copy(),start.copy()]
                projection=ray_error(g,observations[0]);native_check(g)
                for _ in range(4):
                    q=np.clip(start+rng.uniform(-.035,.035,7),checker.limits[:,0]+.002,checker.limits[:,1]-.002)
                    if checker.edge(start,q):qs[1]=q;available[1]=True;break
                checker.set_q(qs[1]);observations.append(g.observation(truth,qs[1]));native_check(g)
                data={key:np.stack([observations[0][key]]*3)[None] for key in observations[0]}
                data.update({k:np.asarray(truth[k])[None] for k in truth})
                predictions=infer(models,data,[0],(0,))[0];groups=group_predictions(predictions)
                family=['right','left','base','elevated','difficult'][index%5];direction='right' if family in ['right','difficult'] else 'left' if family in ['left','elevated'] else 'base'
                record['requested_family']=family;checker.set_q(start);planner=Planner(checker,seed=SEED+index)
                if groups:
                    target=max(groups,key=lambda x:(3-x['support'],x['spread_mm']));focus=Focus(target['position'].copy(),float(np.clip(np.linalg.norm(target['size'])/2+target['spread_mm']/1000,.04,.09)))
                    body=g.m.body(g.env.robots[0].robot_model.root_body).id;base=g.d.xpos[body].copy()
                    elevated=family=='elevated';cfg=SideSettings(distances_m=(.35,.42),heights_above_focus_m=(.25,.35) if elevated else (.11,.15),maximum_elevation_deg=65 if elevated else 40 if family=='base' else 35,maximum_seconds=4.,maximum_path_attempts=1,ik_seed_attempts=2)
                    bt=time.perf_counter();result=side_view(planner,focus,start,base,direction,cfg);record['search_seconds']=time.perf_counter()-bt
                    record['search_audit']=result['audit'];record['focus']=focus.center;record['focus_source']='frozen_V3_M2_three_seed_predictions'
                    if result['stage']=='target_view':
                        q=result['candidate']['q'];plan=result['plan'];checks=0
                        for a,b in zip(plan.waypoints[:-1],plan.waypoints[1:]):
                            if not checker.edge(a,b):raise RuntimeError('Independent path recheck failed')
                            for alpha in np.linspace(0,1,9):
                                checker.set_q(a+(b-a)*alpha);native_check(g);checks+=1
                        qs[2]=q;available[2]=True;record.update(stage='captured',camera_change=result['candidate']['change'],elevation_deg=result['candidate']['elevation_deg'],optical_axis_error_deg=result['candidate']['optical_axis_error_deg'],waypoints=plan.waypoints,replayed_states=checks)
                    else:record.update(stage='blocked',reason=result['reason'])
                else:record.update(stage='blocked',reason='no_predicted_focus')
                checker.set_q(qs[2]);observations.append(g.observation(truth,qs[2]));native_check(g)
                if family=='difficult' and available[2]:
                    observations[2]['images'][2]=np.asarray(Image.fromarray(observations[2]['images'][2]).filter(ImageFilter.GaussianBlur(3))).copy();record['image_degradation']='GaussianBlur(radius=3); pose unchanged'
                projection=max(projection,ray_error(g,observations[2]))
                if projection>.001:raise RuntimeError(f'Ray projection error {projection}')
                sample={k:np.stack([r[k] for r in observations]) for k in observations[0]};sample.update(truth)
                sample['pose_available']=np.array(available);sample['joint_positions']=np.array(qs,np.float32)
                path=out/'samples'/f'sample_{index:04d}.npz';np.savez_compressed(path,**sample);paths.append(path)
                record.update(available=available,projection_max_px=projection,compressed_bytes=path.stat().st_size,raw_array_bytes=sum(v.nbytes for v in sample.values()),sample_sha256=sha(path))
                if index<20:
                    sheet=Image.new('RGB',(480,340),'#11202c');draw=ImageDraw.Draw(sheet)
                    for row_idx,ob in enumerate([observations[0],observations[2]]):
                        for col in range(3):sheet.paste(Image.fromarray(ob['images'][col]),(col*160,20+row_idx*160))
                    draw.text((5,3),f'{index}: {family}, {record["stage"]}, n={n}',fill='white');sheet.save(out/'examples'/f'{index:03d}_{family}.png')
                checker.set_q(start)
            except (ValueError,RuntimeError) as e:
                # Physical sample failures remain explicit, never turn safety or
                # invariant failures into ordinary rejected training families.
                if str(e) not in ['Initial arm invalid','Scene settlement exhausted']:raise
                record.update(stage='family_rejected',reason=str(e))
            record['seconds']=time.perf_counter()-t;records.append(record);rss=max(rss,psutil.Process().memory_info().rss)
            with (out/'families.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,default=jsonable)+'\n')
            if (index+1)%10==0:
                status=dict(phase='data_pilot',completed=index+1,total=args.families,valid_samples=len(paths),stages=dict(Counter(r['stage'] for r in records)),elapsed_seconds=time.perf_counter()-started)
                save(out/'status.json',status);print(json.dumps(status),flush=True)
    finally:g.close()
    data_seconds=time.perf_counter()-started
    del models
    torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
    save(out/'status.json',dict(phase='numerical_benchmark',valid_samples=len(paths),main_training_started=False));print('Starting disposable three-update benchmark',flush=True)
    bench=numerical_pilot(out,paths)
    for name,expected_hash in json.loads((out/'checkpoint_hashes.json').read_text()).items():
        if sha(run/'checkpoints'/name)!=expected_hash:raise RuntimeError('Original weights modified')
    valid=[r for r in records if 'compressed_bytes' in r];captured=[r for r in records if r['stage']=='captured']
    summary=dict(pilot_completed=True,main_training_started=False,promoted_model=False,families_requested=args.families,valid_samples=len(paths),
        stages=dict(Counter(r['stage'] for r in records)),counts=dict(Counter(r['count'] for r in valid)),kinds=dict(Counter(r['kind'] for r in valid)),shape_counts=dict(Counter(r['shape'] for r in valid)),
        view_families={fam:dict(attempted=sum(r.get('requested_family')==fam for r in records),captured=sum(r.get('requested_family')==fam and r['stage']=='captured' for r in records)) for fam in ['right','left','base','elevated','difficult']},
        data_seconds=data_seconds,seconds_per_family=data_seconds/args.families,compressed_bytes_per_family=float(np.mean([r['compressed_bytes'] for r in valid])),
        raw_array_bytes_per_family=float(np.mean([r['raw_array_bytes'] for r in valid])),peak_process_rss_gib=rss/2**30,
        calibration_max_projection_px=max(r['projection_max_px'] for r in valid),maximum_axis_error_deg=max([r['optical_axis_error_deg'] for r in captured],default=None),
        data_scope='one assigned requested view plus near and initial per family; not the full six-candidate V4 bank',
        rejected_settlements=g.rejections,numerical=bench,elapsed_seconds=time.perf_counter()-started,
        hardware=dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__),
        limitations=['No perception efficacy or overfitting conclusion from three updates','No full six-view bank throughput measurement','Only simulation reference collisions; visual unknown space remains blocked','New long/thin shapes sampled scattered only; stacked long/thin coverage remains unimplemented'])
    save(out/'report.json',summary);save(out/'status.json',dict(phase='completed',main_training_started=False,report='report.json'));print(json.dumps(summary,default=jsonable),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();raise
