"""200-family bounded pilot using independently certified static motion banks.

This changes the offline data-generation strategy, not model architecture/loss.
Reference object geometry is confined to collision admissibility and labels.
"""
from pathlib import Path
import json,time,sys,hashlib
import numpy as np
import torch
from PIL import Image,ImageFilter,ImageDraw
from collections import Counter
import pilot as P
from data_v3 import PoseGenerator,assignment,KINDS,swept_envelopes,object_path_free
from active_view.collision import ArmChecker,reference_world
from active_view.geometry import segment_aabb_intersection
from active_view.side_views import side_frame,optical_axis_error
from active_view.view_sweep import view_change
from ensemble_uncertainty import group_predictions
import psutil

HERE=P.HERE;ROOT=P.ROOT;SEED=94140202
def static_signature(g,checker):
    objects=set(sum(g.geoms,[]));w=reference_world(g.m,g.d)
    # Actual static transforms, geometry and robot configuration contract.
    static=[dict(center=b.center,half=b.half,rotation=b.rotation,name=b.name) for b in w.boxes if b.geom not in objects]
    robot=[dict(id=i,size=g.m.geom_size[i],pos=g.m.geom_pos[i],quat=g.m.geom_quat[i],body=int(g.m.geom_bodyid[i])) for i in checker.geom_ids]
    value=dict(static=static,planes=w.planes,robot=robot,limits=checker.limits,locked_q=g.d.qpos[[g.m.jnt_qposadr[i] for i in range(g.m.njnt) if (g.m.joint(i).name or '').startswith('gripper0_')]],
        base_position=g.d.xpos[g.m.body(g.env.robots[0].robot_model.root_body).id],margin=checker.world_margin,self_margin=checker.self_margin)
    return hashlib.sha256(json.dumps(value,default=P.jsonable,sort_keys=True).encode()).hexdigest()

def make_bank(g,out,source):
    rng=np.random.default_rng(SEED);g._setup(rng,0,'scattered',False)
    checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=g.base_qpos[checker.qadr].copy();g.qadr=checker.qadr
    checker.set_q(start);signature=static_signature(g,checker)
    if not checker.check(start).valid:raise RuntimeError('Nominal bank start invalid')
    records=[json.loads(x) for x in source.read_text().splitlines()];bank=[]
    proposals=[r for r in records if r.get('stage')=='captured' and 'waypoints' in r]
    near=start+np.array([.01,-.01,.01,0,0,.01,0]);proposals=[dict(index=-1,requested_family='near',waypoints=[start,near])]+proposals
    for r in proposals:
        family=r['requested_family'];family='right' if family=='difficult' else family
        if sum(e['family']==family for e in bank)>=3:continue
        waypoints=[start]+[np.asarray(q,float) for q in r['waypoints']]
        waypoints=[q for i,q in enumerate(waypoints) if i==0 or np.max(np.abs(q-waypoints[i-1]))>1e-9]
        if not all(checker.edge(a,b) for a,b in zip(waypoints[:-1],waypoints[1:])):continue
        lows=[];highs=[]
        for a,b in zip(waypoints[:-1],waypoints[1:]):
            low,high=swept_envelopes(checker,a,b);lows.append(low);highs.append(high)
        low=np.concatenate(lows);high=np.concatenate(highs);camera,R=checker.camera_pose(waypoints[-1])
        entry=dict(id=len(bank),family=family,source_family_index=r['index'],waypoints=waypoints,q=waypoints[-1],camera=camera,rotation=R,low=low,high=high)
        bank.append(entry)
        np.savez_compressed(out/f'bank_certificate_{entry["id"]:02d}.npz',low=low,high=high,waypoints=np.array(waypoints),q=entry['q'],camera=camera,rotation=R)
        print(json.dumps(dict(stage='bank_certificate',id=entry['id'],family=family)),flush=True)
    checker.set_q(start)
    P.save(out/'bank.json',dict(static_signature=signature,source_jsonl=str(source.relative_to(ROOT)),source_sha256=P.sha(source),
        entries=[{k:v for k,v in e.items() if k not in ['low','high']} for e in bank],
        certificate='Static/self full checker edges plus conservative analytic swept AABBs; per-scene objects checked independently'))
    return checker,start,signature,bank

def choose(g,checker,bank,truth,focus,family,base):
    requested='right' if family=='difficult' else family;valid=[]
    for e in bank:
        if e['family']!=requested:continue
        if not object_path_free(e['low'],e['high'],truth['positions'],truth['sizes'],truth['rotations'],truth['active']):continue
        if family=='near':valid.append((0,e));continue
        if focus is None:continue
        center,radius=focus;camera=e['camera'];delta=center-camera;distance=np.linalg.norm(delta)
        error=optical_axis_error(camera,e['rotation'],center)
        cid=checker.camera;half_fov=np.deg2rad(g.m.cam_fovy[cid]/2)
        if distance<=radius+.05 or np.deg2rad(error)+np.arcsin(min(.999,radius/distance))>half_fov*.96:continue
        direction='left' if family=='elevated' else requested
        axis=side_frame(base,center)[direction]
        if (camera-center)@axis<.10:continue
        end=center-delta/distance*radius
        if any(segment_aabb_intersection(camera,end,b,padding=.002) for b in checker.world.boxes):continue
        valid.append((error,e))
    return min(valid,key=lambda v:v[0])[1] if valid else None

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--name',default='pilot_002');p.add_argument('--source',default='pilot_001/families.jsonl');args=p.parse_args()
    out=HERE/args.name;out.mkdir(exist_ok=False);(out/'samples').mkdir();(out/'examples').mkdir();(out/'source').mkdir()
    P.settings();started=time.perf_counter();records=[];paths=[];rss=0
    for f in [Path(__file__),HERE/'pilot.py',HERE/'PLAN.md',HERE/'report_pilot.py',ROOT/'experiments/visual_active_v3_20261101/data_v3.py',ROOT/'praxis/src/active_view/collision.py',ROOT/'praxis/src/active_view/geometry.py']:
        dest=out/'source'/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes())
    P.save(out/'manifest.json',dict(pilot_only=True,main_training_authorized=False,seed=SEED,families=200,view_strategy='frozen_predicted_focus_seeded_static_motion_bank',full_six_candidate_bank=False,
        bank_focus_tolerance='whole focus sphere within calibrated FoV; actual optical offset reported, not constrained to 3 degrees',
        source_hashes={str(f.relative_to(out/'source')):P.sha(f) for f in (out/'source').rglob('*') if f.is_file()}))
    run=ROOT/'experiments/visual_active_v3_20261101/run_001';expected=json.loads((run/'checkpoint_hashes.json').read_text());models=[]
    for seed in [1,2,3]:
        path=run/'checkpoints'/f'M2_seed{seed}_best.pth'
        if P.sha(path)!=expected[path.name]:raise RuntimeError('Original checkpoint mismatch')
        model=P.ScenePerception().cuda().eval();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);models.append(model)
    P.save(out/'checkpoint_hashes.json',{f'M2_seed{s}_best.pth':expected[f'M2_seed{s}_best.pth'] for s in [1,2,3]})
    # Independent deterministic stratification: long/thin families span all views.
    labels=np.tile(np.array(['right','left','base','elevated','difficult']),40);np.random.default_rng(SEED+1).shuffle(labels)
    thin=set()
    for family in set(labels):
        ids=np.flatnonzero(labels==family);thin.update(np.random.default_rng(SEED+2+int(ids[0])).choice(ids,4,replace=False).tolist())
    g=PoseGenerator()
    try:
        checker,start,signature,bank=make_bank(g,out,HERE/args.source);bank_seconds=time.perf_counter()-started
        for index in range(200):
            if (out/'STOP_REQUESTED').exists():raise RuntimeError('Pilot stop requested')
            t=time.perf_counter();n,kind=assignment(SEED,index);family=str(labels[index]);shape='long_thin' if index in thin and n else 'standard'
            if shape=='long_thin':kind='scattered'
            rng=np.random.default_rng(np.random.SeedSequence([SEED,index]));r=dict(index=index,seed=SEED,count=n,kind=kind,shape=shape,requested_family=family)
            for attempt in range(40):
                try:sizes,pos=g._setup(rng,n,kind,shape=='long_thin');break
                except ValueError as e:g.rejections[str(e)]=g.rejections.get(str(e),0)+1
            else:raise RuntimeError('Settlement failed')
            # Explicit fixed start for cached complete paths, not the small
            # incidental robot jitter used while settling the objects.
            checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));g.qadr=checker.qadr;checker.set_q(start)
            if static_signature(g,checker)!=signature:raise RuntimeError('Static/robot geometry certificate invalidated')
            if not checker.check(start).valid:raise RuntimeError('Per-scene initial arm invalid')
            truth=dict(positions=pos.astype('float32'),sizes=sizes.astype('float32'),rotations=np.array([g.d.xmat[b].reshape(3,3).copy() for b in g.bodies],np.float32),active=np.arange(5)<n,count=np.int64(n),kind=np.int64(KINDS.index(kind)),family=np.array([SEED,index],np.int64))
            observations=[g.observation(truth,start)];qs=[start.copy() for _ in range(3)];available=[True,False,False];P.native_check(g)
            data={key:np.stack([observations[0][key]]*3)[None] for key in observations[0]};data.update({k:np.asarray(v)[None] for k,v in truth.items()})
            groups=group_predictions(P.infer(models,data,[0],(0,))[0]);focus=None
            if groups:
                target=max(groups,key=lambda x:(3-x['support'],x['spread_mm']));focus=(target['position'].copy(),float(np.clip(np.linalg.norm(target['size'])/2+target['spread_mm']/1000,.04,.09)))
                r['focus']=focus[0];r['focus_source']='frozen_V3_M2_three_seed_predictions'
            body=g.m.body(g.env.robots[0].robot_model.root_body).id;base=g.d.xpos[body].copy()
            near=choose(g,checker,bank,truth,None,'near',base)
            if near:qs[1]=near['q'];available[1]=True
            checker.set_q(qs[1]);observations.append(g.observation(truth,qs[1]));P.native_check(g)
            entry=choose(g,checker,bank,truth,focus,family,base)
            r['bank_candidates']=sum(e['family']==('right' if family=='difficult' else family) for e in bank)
            if entry:
                states=0
                for a,b in zip(entry['waypoints'][:-1],entry['waypoints'][1:]):
                    for alpha in np.linspace(0,1,9):
                        checker.set_q(a+(b-a)*alpha);P.native_check(g);states+=1
                qs[2]=entry['q'];available[2]=True;center=focus[0];delta=entry['camera']-center
                initial_camera,_=checker.camera_pose(start)
                r.update(stage='captured',bank_id=entry['id'],waypoints=entry['waypoints'],replayed_states=states,
                    camera_change=view_change(initial_camera,entry['camera'],center),
                    elevation_deg=float(np.degrees(np.arctan2(delta[2],np.linalg.norm(delta[:2])))),
                    optical_axis_error_deg=optical_axis_error(entry['camera'],entry['rotation'],center))
            else:r.update(stage='blocked',reason='no_bank_candidate' if not r['bank_candidates'] else 'no_predicted_focus' if focus is None else 'focus_fov_or_reference_collision_gate')
            checker.set_q(qs[2]);observations.append(g.observation(truth,qs[2]));P.native_check(g)
            if family=='difficult' and available[2]:
                observations[2]['images'][2]=np.asarray(Image.fromarray(observations[2]['images'][2]).filter(ImageFilter.GaussianBlur(3))).copy();r['image_degradation']='GaussianBlur(radius=3)'
            projection=max(P.ray_error(g,v) for v in observations)
            if projection>.001:raise RuntimeError('Projection error')
            sample={k:np.stack([o[k] for o in observations]) for k in observations[0]};sample.update(truth);sample['pose_available']=np.array(available);sample['joint_positions']=np.array(qs,np.float32)
            path=out/'samples'/f'sample_{index:04d}.npz';np.savez_compressed(path,**sample);paths.append(path)
            r.update(available=available,projection_max_px=projection,compressed_bytes=path.stat().st_size,raw_array_bytes=sum(v.nbytes for v in sample.values()),sample_sha256=P.sha(path),seconds=time.perf_counter()-t)
            records.append(r)
            with (out/'families.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(r,default=P.jsonable)+'\n')
            if index<30:
                sheet=Image.new('RGB',(480,340),'#11202c');draw=ImageDraw.Draw(sheet)
                for rr,o in enumerate([observations[0],observations[2]]):
                    for col in range(3):sheet.paste(Image.fromarray(o['images'][col]),(col*160,20+rr*160))
                draw.text((5,3),f'{index}: {family} {r["stage"]}; n={n}',fill='white');sheet.save(out/'examples'/f'{index:03d}_{family}.png')
            rss=max(rss,psutil.Process().memory_info().rss)
            if (index+1)%20==0:
                status=dict(phase='bank_data_pilot',completed=index+1,total=200,stages=dict(Counter(r['stage'] for r in records)),elapsed_seconds=time.perf_counter()-started)
                P.save(out/'status.json',status);print(json.dumps(status),flush=True)
    finally:g.close()
    data_seconds=time.perf_counter()-started;del models;torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
    print('Disposable numerical benchmark: three updates and partial resume',flush=True);bench=P.numerical_pilot(out,paths)
    for name,expected_hash in json.loads((out/'checkpoint_hashes.json').read_text()).items():
        if P.sha(run/'checkpoints'/name)!=expected_hash:raise RuntimeError('Original checkpoint modified')
    captured=[r for r in records if r['stage']=='captured']
    report=dict(pilot_completed=True,main_training_started=False,promoted_model=False,families_requested=200,valid_samples=len(paths),
        stages=dict(Counter(r['stage'] for r in records)),counts=dict(Counter(r['count'] for r in records)),kinds=dict(Counter(r['kind'] for r in records)),shape_counts=dict(Counter(r['shape'] for r in records)),
        view_families={fam:dict(attempted=sum(r['requested_family']==fam for r in records),captured=sum(r['requested_family']==fam and r['stage']=='captured' for r in records)) for fam in ['right','left','base','elevated','difficult']},
        data_seconds=data_seconds,bank_seconds=bank_seconds,seconds_per_family=(data_seconds-bank_seconds)/200,
        compressed_bytes_per_family=float(np.mean([r['compressed_bytes'] for r in records])),raw_array_bytes_per_family=float(np.mean([r['raw_array_bytes'] for r in records])),peak_process_rss_gib=rss/2**30,
        calibration_max_projection_px=max(r['projection_max_px'] for r in records),maximum_axis_error_deg=max([r['optical_axis_error_deg'] for r in captured],default=None),
        data_scope='One assigned bank candidate plus near/initial; static/self paths prechecked, analytical swept per-scene object exclusion, native replay states',
        bank_entries=len(bank),static_signature=signature,source_probe='pilot_001 ended early due per-scene search throughput bottleneck; artifacts retained',
        rejected_settlements=g.rejections,numerical=bench,elapsed_seconds=time.perf_counter()-started,hardware=dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__),
        limitations=['No V4 efficacy/generalization claim','No full six-candidate bank benchmark','Reference geometry only, not visual safety','Long/thin sampled scattered only','Bank permits target offset within FoV instead of 3-degree exact aim'])
    P.save(out/'report.json',report);P.save(out/'status.json',dict(phase='completed',main_training_started=False));print(json.dumps(report,default=P.jsonable),flush=True)

if __name__=='__main__':main()
