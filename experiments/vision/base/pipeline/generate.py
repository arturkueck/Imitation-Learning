"""Explicit data generation, complete reference paths, immutable family files."""
import json,os,sys,sqlite3,time
import numpy as np
from pathlib import Path
from .common import ROOT,EXPERIMENT,read,save,sha,check_stop,event
from .protocol import verify_protocol,verify_imports,in_roi
from .lineage import connect,assert_new_family,historical_duplicate,geometry_digest,image_digest
from .samples import SLOTS
from .claims import claim

def imports():
    sys.path.insert(0,str(EXPERIMENT));sys.path.insert(0,str(ROOT/'experiments/vision/visual_active_v3_20261101'));sys.path.insert(0,str(ROOT/'praxis/src'))
    import pilot as P
    return P

def content_db(path):
    db=sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS fingerprints(kind TEXT,digest TEXT,seed INTEGER,idx INTEGER,split TEXT,PRIMARY KEY(kind,digest,seed,idx,split))')
    db.execute('CREATE INDEX IF NOT EXISTS lookup ON fingerprints(kind,digest)');return db
def register_content(db,row,split,commit=True):
    seed,index=map(int,row['family']);values=[('initial_rgb',image_digest(row['images'][0]))]
    g=geometry_digest(row)
    if g:values.append(('geometry',g))
    for kind,digest in values:
        match=db.execute('SELECT seed,idx,split FROM fingerprints WHERE kind=? AND digest=? AND NOT(seed=? AND idx=? AND split=?) LIMIT 1',(kind,digest,seed,index,split)).fetchone()
        if match:raise ValueError('Content duplicate across families/splits: '+str(match))
    if commit:
        db.executemany('INSERT OR IGNORE INTO fingerprints VALUES(?,?,?,?,?)',[(k,d,seed,index,split) for k,d in values]);db.commit()
    return dict(values)

def load_bank(g,run,cfg):
    from active_view.collision import ArmChecker,reference_world
    from active_view.camera_guidance import swept_envelopes,join_routes
    from pilot_bank import static_signature
    folder=EXPERIMENT/'guidance_002';metadata=read(folder/'bank.json')
    if sha(folder/'bank.json')!=cfg['bank']['manifest_sha256']:raise RuntimeError('Guidance bank changed')
    g._setup(np.random.default_rng(94831992),0,'scattered',False);c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=g.base_qpos[c.qadr].copy();c.set_q(start);g.qadr=c.qadr
    signature=static_signature(g,c)
    if signature!=metadata['signature']:raise RuntimeError('Static robot/environment contract changed')
    bank=[]
    for e in metadata['entries']:
        file=folder/f'certificate_{e["id"]:03d}.npz'
        if sha(file)!=e['certificate_sha256']:raise RuntimeError('Guidance certificate changed')
        with np.load(file) as z:value={**e,**{k:np.array(z[k]) for k in z.files if k!='id'}}
        value['waypoints']=[q.copy() for q in value['waypoints']];bank.append(value)
    cached=Path(run)/'old_camera_bank.json'
    certificates=Path(run)/'old_camera_certificates';certificates.mkdir(exist_ok=True)
    if cached.exists():
        old=read(cached)
        if not (Path(run)/'bank_cache_seal.json').exists() or sha(cached)!=read(Path(run)/'bank_cache_seal.json')['old_bank_sha256']:raise RuntimeError('Unsealed/changed camera cache')
        if old['signature']!=signature:raise RuntimeError('Old-bank contract changed')
        for e in old['entries']:
            path=certificates/e['file']
            if sha(path)!=e['sha256']:raise RuntimeError('Old certificate changed')
            with np.load(path) as z:value={**e,**{k:np.array(z[k]) for k in z.files}}
            value['waypoints']=[q.copy() for q in value['waypoints']];bank.append(value)
    else:
        if sha(ROOT/'experiments/vision/visual_active_v3_20261101/run_001/pose_bank.json')!=cfg['bank']['old_pose_bank_sha256']:raise RuntimeError('Old camera-bank source changed')
        raw=read(ROOT/'experiments/vision/visual_active_v3_20261101/run_001/pose_bank.json');entries=[]
        for family in ['near','medium','oblique']:
            for j,e in enumerate(raw['candidates']):
                if e['band']!=family or j in raw['camera_holdout_ids']:continue
                if sum(v['family']==family for v in entries)>=4:break
                route=[start,np.array(raw['base_q']),np.array(e['q'])]
                if not all(c.edge(a,b) for a,b in zip(route[:-1],route[1:])):continue
                low=[];high=[]
                for a,b in zip(route[:-1],route[1:]):
                    lo,hi=swept_envelopes(c,a,b);low.append(lo);high.append(hi)
                pc,R=c.camera_pose(route[-1]);name=f'old_{j:03d}.npz';path=certificates/name
                if path.exists():raise RuntimeError('Uncommitted bank artifact; inspect before recovery')
                np.savez_compressed(path,low=np.concatenate(low),high=np.concatenate(high),q=route[-1],waypoints=np.array(route),camera=pc,rotation=R)
                item=dict(id=1000+j,family=family,file=name,sha256=sha(path));entries.append(item)
                bank.append({**item,'low':np.concatenate(low),'high':np.concatenate(high),'q':route[-1],'waypoints':route,'camera':pc,'rotation':R})
        if any(not any(e['family']==f for e in entries) for f in ['near','medium','oblique']):raise RuntimeError('Insufficient old-view controls')
        save(cached,dict(signature=signature,entries=entries,source_pose_bank_sha256=sha(ROOT/'experiments/vision/visual_active_v3_20261101/run_001/pose_bank.json')))
        save(Path(run)/'bank_cache_seal.json',dict(old_bank_sha256=sha(cached)))
    c.set_q(start);return bank,start,signature

def scene(g,cfg,split,seed,index):
    from data_v3 import assignment,KINDS
    from active_view.collision import ArmChecker,reference_world
    rng=np.random.default_rng(np.random.SeedSequence([seed,index]));n,kind=assignment(seed,index)
    held=split=='test_geometry';long=held or bool(rng.random()<cfg['geometry_holdout']['long_fraction'])
    if held:n=max(n,1)
    if long:kind='scattered'
    bounds=dict(length=cfg['geometry_holdout']['test_long_length' if held else 'train_long_length'],width=cfg['geometry_holdout']['test_long_width' if held else 'train_long_width'])
    for attempt in range(80):
        try:sizes,pos=g.setup_v4(rng,n,kind,long,bounds)
        except ValueError:continue
        c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=g.base_qpos[c.qadr].copy();c.set_q(start)
        if c.check(start).valid:break
    else:raise RuntimeError('Unable to obtain physical family without changing its split')
    truth=dict(positions=pos.astype('float32'),sizes=sizes.astype('float32'),rotations=np.array([g.d.xmat[b].reshape(3,3).copy() for b in g.bodies],np.float32),
        active=np.arange(5)<n,count=np.int64(n),kind=np.int64(KINDS.index(kind)),family=np.array([seed,index],np.int64))
    return truth,c,start,rng,dict(long=long,physical_attempt=attempt+1,arrangement=kind)

def make_sample(g,models,bank,start,signature,cfg,split,seed,index):
    P=imports()
    from pilot_bank import static_signature
    from data_v3 import object_path_free
    from guidance_validate import candidate_order
    from active_view.planner import Planner,Focus
    from active_view.camera_guidance import refine_view,join_routes
    from active_view.geometry import segment_aabb_intersection
    from ensemble_uncertainty import group_predictions
    truth,c,actual_start,rng,meta=scene(g,cfg,split,seed,index);g.qadr=c.qadr
    if np.max(np.abs(start-actual_start))>1e-9 or static_signature(g,c)!=signature:raise RuntimeError('Bank not valid for this initial state')
    initial=g.observation(truth,start);P.native_check(g)
    row={k:np.stack([initial[k]]*len(SLOTS)) for k in initial};row.update(truth);row['pose_available']=np.zeros(len(SLOTS),bool);row['pose_available'][0]=True
    row['joint_positions']=np.tile(start,(len(SLOTS),1)).astype(np.float32)
    dummy={k:np.stack([initial[k]]*2)[None] for k in initial};dummy.update({k:np.asarray(v)[None] for k,v in truth.items()})
    predictions=group_predictions(P.infer(models,dummy,[0],(0,))[0]);focus=None
    if predictions:
        target=max(predictions,key=lambda v:(3-v['support'],v['spread_mm']));focus=Focus(target['position'].copy(),float(np.clip(np.linalg.norm(target['size'])/2+target['spread_mm']/1000,.04,.09)))
    base=g.d.xpos[g.m.body(g.env.robots[0].robot_model.root_body).id].copy();start_camera=initial['camera_positions'][2];captures=[]
    for slot,family in enumerate(SLOTS[1:],1):
        if slot<=3:
            options=[e for e in bank if e['family']==family and not in_roi(e['camera'],guard=True) and object_path_free(e['low'],e['high'],truth['positions'],truth['sizes'],truth['rotations'],truth['active'])]
            rng.shuffle(options)
        elif focus is None:captures.append(dict(slot=slot,family=family,state='blocked',reason='no_predicted_focus'));continue
        else:
            options,_=candidate_order(bank,focus,family,c,base,start_camera,{k:truth[k] for k in ['positions','sizes','rotations','active']})
            options=[e for e in options if bool(in_roi(e['camera']))==bool(split=='test_camera') and (split=='test_camera' or not in_roi(e['camera'],guard=True))]
        picked=None
        for e in options[:5]:
            if slot<=3:
                q=e['q'];route=e['waypoints'];pc,R=c.camera_pose(q);requested=dict(position=pc,rotation=R)
            else:
                result=refine_view(Planner(c,seed=seed+index+slot),focus,start_camera,base,family,e['q'])
                if result['stage']!='aimed':continue
                q=result['q'];route=join_routes(e['waypoints'],result['suffix']);pc=result['metrics']['camera'];R=result['metrics']['rotation'];requested=result['desired_pose']
                if bool(in_roi(pc))!=bool(split=='test_camera') or (split!='test_camera' and in_roi(pc,guard=True)):continue
                delta=focus.center-pc;end=focus.center-delta/np.linalg.norm(delta)*focus.radius
                if any(segment_aabb_intersection(pc,end,b,padding=.002) for b in c.world.boxes):continue
            if not c.check(q).valid:continue
            if np.max(np.abs(route[0]-start))>1e-8 or np.max(np.abs(route[-1]-q))>1e-8:raise RuntimeError('Discontinuous capture path')
            for a,b in zip(route[:-1],route[1:]):
                for alpha in np.linspace(0,1,9):c.set_q(a+(b-a)*alpha);P.native_check(g)
            actual=g.observation(truth,q);P.native_check(g)
            if P.ray_error(g,actual)>.001 or np.max(np.abs(actual['camera_positions'][2]-pc))>1e-6:raise RuntimeError('Capture/calibration disagrees')
            for k,v in actual.items():row[k][slot]=v
            row['pose_available'][slot]=True;row['joint_positions'][slot]=q
            captures.append(dict(slot=slot,family=family,state='captured',source='scheduled_coverage_not_learned_policy',bank_id=e['id'],desired=requested,
                planned=dict(position=pc,rotation=R,joints=q),actual=dict(position=actual['camera_positions'][2],rotation=actual['camera_rotations'][2]),
                pose_frame='world_mujoco_camera_minus_z',image_sha256=image_digest(actual['images'][2]),waypoints=route))
            picked=e;break
        if picked is None:captures.append(dict(slot=slot,family=family,state='blocked',reason='no_reference_certified_view'))
    c.set_q(start);meta.update(captures=captures,focus_source='frozen_V3_M2_ensemble',camera_frame='world_mujoco_minus_z',geometry_backend='sim_reference',slot_roles=SLOTS)
    return row,meta

def collect(run,split,smoke_count=None,workers=1,worker_id=None):
    if workers>1 and worker_id is None:
        from .parallel import collect_parallel
        return collect_parallel(run,split,smoke_count,workers)
    P=imports();import torch
    from .physical_setup import physical_setup
    from data_v3 import PoseGenerator
    run=Path(run);cfg=verify_protocol(run,full_sources=True)
    if split.startswith('test') and not (run/'final_policy_freeze.json').exists():raise RuntimeError('Blind RGB generation blocked until model AND policy freeze')
    if split in ['request_train','request_validation','calibration'] and not (run/'perception_freeze.json').exists():raise RuntimeError('Request data require frozen selected perception first')
    P.settings()
    if worker_id is not None:torch.set_num_threads(1)
    folder=run/'data'/split;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'seal.json').exists():
        sealed=read(folder/'seal.json');expected_count=smoke_count or cfg['splits'][split]['count']
        if sealed['count']!=expected_count:raise RuntimeError('Sealed split size cannot be changed')
        return sealed
    if smoke_count is None and worker_id is None:verify_imports(cfg)
    seed=cfg['development_seed'] if smoke_count else cfg['splits'][split]['seed'];count=smoke_count or cfg['splits'][split]['count']
    if smoke_count and split!='development':raise ValueError('Smoke can only use development role')
    history=connect(run/'history.sqlite',readonly=True);contents=content_db(run/('content.sqlite' if worker_id is None else f'content_worker_{worker_id}.sqlite'));models=[]
    parents=cfg['parents']
    if split in ['request_train','request_validation','calibration'] or split.startswith('test'):
        frozen=read(run/'perception_freeze.json')
        if not frozen['side_gate_passed']:raise RuntimeError('Perception side-view quality gate not passed')
        parents=frozen['models']
    for parent in parents:
        if sha(ROOT/parent['file'])!=parent['sha256']:raise RuntimeError('Perception parent changed')
        m=P.ScenePerception().cuda().eval();m.load_state_dict(torch.load(ROOT/parent['file'],map_location='cuda',weights_only=False)['model']);models.append(m)
    g=PoseGenerator()
    def setup_v4(rng,n,kind,long,bounds):
        import mujoco
        mujoco.mj_resetData(g.m,g.d)
        return physical_setup(g,rng,n,kind,long,bounds)
    g.setup_v4=setup_v4
    try:
        with exclusive_bank(run):bank,start,signature=load_bank(g,run,cfg)
        records=[]
        indices=range(count) if worker_id is None else range(worker_id,count,workers)
        for index in indices:
            family_started=time.perf_counter()
            check_stop(run,60)
            if worker_id is not None and (run/'PARALLEL_CANCELLED').exists():raise InterruptedError('Another worker failed/stopped')
            file=folder/f'{index:06d}.npz';meta_path=file.with_suffix('.json')
            if meta_path.exists():
                r=read(meta_path)
                if r['family']!=[seed,index] or r['split']!=split or sha(file)!=r['sha256']:raise RuntimeError('Existing family differs from frozen assignment')
                with np.load(file,allow_pickle=False) as z:existing={k:np.array(z[k]) for k in z.files}
                claim(existing,split,sha(run/'config.json'));register_content(contents,existing,split)
                records.append(r);continue
            if file.exists():raise RuntimeError('Uncommitted family file preserved; audit required before recovery')
            assert_new_family(history,[seed,index])
            sample,metadata=make_sample(g,models,bank,start,signature,cfg,split,seed,index)
            duplicate=historical_duplicate(history,sample)
            if duplicate:raise RuntimeError('Historical content duplicated; split not reassigned: '+str(duplicate))
            fingerprints=register_content(contents,sample,split,commit=False)
            temp=file.with_suffix('.npz.tmp')
            with temp.open('wb') as f:np.savez_compressed(f,**sample);f.flush();os.fsync(f.fileno())
            temp.replace(file)
            # Convert only metadata arrays, never expose them as model inputs.
            metadata=json.loads(json.dumps(metadata,default=P.jsonable));r=dict(file=file.name,sha256=sha(file),family=[seed,index],split=split,fingerprints=fingerprints,
                kind=int(sample['kind']),count=int(sample['count']),available=sample['pose_available'].tolist(),generation_seconds=time.perf_counter()-family_started,metadata=metadata)
            save(meta_path,r);claim(sample,split,sha(run/'config.json'));register_content(contents,sample,split,commit=True);records.append(r)
            if worker_id is None and ((index+1)%10==0 or index+1==count):event(run,'render',split=split,rendered=index+1,render_total=count,training_started=False)
        if worker_id is not None:return len(records)
        save(folder/'index.json',dict(split=split,seed=seed,count=len(records),records=records,purpose='development_only' if smoke_count else 'frozen_main_protocol'))
        seal=dict(split=split,count=len(records),seed=seed,index_sha256=sha(folder/'index.json'),history_sha256=cfg['historical_registry_sha256'],smoke_only=bool(smoke_count))
        save(folder/'seal.json',seal);return seal
    finally:g.close();history.close();contents.close()

def exclusive_bank(run):
    # Different workers may initialize concurrently; only cache creation is serialized.
    from contextlib import contextmanager
    from .locking import exclusive
    @contextmanager
    def locked():
        while True:
            check_stop(run,60)
            try:
                lock=exclusive(Path(run)/'bank_init');lock.__enter__();break
            except RuntimeError:time.sleep(.2)
        try:yield
        finally:lock.__exit__(None,None,None)
    return locked()
