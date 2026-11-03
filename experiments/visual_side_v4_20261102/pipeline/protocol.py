"""Frozen run protocol and explicit historical training-only replay selection."""
import json,sys,shutil
from pathlib import Path
import numpy as np
from .common import ROOT,EXPERIMENT,read,save,sha,now
from .lineage import connect,assert_fresh_seed,assert_replay,family_roles

SPLITS={
    'train':(94831001,18000),'validation':(94831002,2000),
    'request_train':(94831003,4000),'request_validation':(94831004,1000),
    'calibration':(94831005,1000),'test_iid':(94831006,2000),
    'test_camera':(94831007,1000),'test_geometry':(94831008,1000)}
CAMERA_ROI=dict(x=[.04,.07],abs_y_min=.25,z=[.90,1.14],guard=.02)
def in_roi(position,guard=False):
    a=np.asarray(position);p=CAMERA_ROI;g=p['guard'] if guard else 0.
    return (a[...,0]>=p['x'][0]-g)&(a[...,0]<=p['x'][1]+g)&(np.abs(a[...,1])>=p['abs_y_min']-g)&(a[...,2]>=p['z'][0]-g)&(a[...,2]<=p['z'][1]+g)

def prepare(run,pilot=False):
    run=Path(run);history=run/'history.sqlite'
    if (run/'config.json').exists():raise FileExistsError('Protocol already frozen')
    db=connect(history,readonly=True)
    try:
        base=94831000
        while any(db.execute('SELECT 1 FROM seeds WHERE seed=? LIMIT 1',(base+i,)).fetchone() for i in list(range(1,9))+[901]):base+=1000
        assigned={name:(base+i,count) for i,(name,(_,count)) in enumerate(SPLITS.items(),1)}
        if pilot:
            assigned['train']=(assigned['train'][0],1000);assigned['validation']=(assigned['validation'][0],256)
        replay_count=333 if pilot else 6000
        for seed,_ in assigned.values():assert_fresh_seed(db,seed)
        assert_fresh_seed(db,base+901)
        replay=ROOT/'experiments/visual_active_v3_20261101/run_001/data/train'
        families=np.load(replay/'family.npy',mmap_mode='r')
        eligible=[i for i,f in enumerate(families) if family_roles(db,f)=={'perception_train'}]
        if len(eligible)<replay_count:raise RuntimeError('Insufficient exclusively historical training families')
        indices=np.random.default_rng(94831991).choice(eligible,replay_count,replace=False).tolist()
        for i in indices:assert_replay(db,families[i])
        parents=ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints'
        expected=read(parents.parent/'checkpoint_hashes.json')
        parent_rows=[]
        for seed in [1,2,3]:
            path=parents/f'M2_seed{seed}_best.pth'
            if sha(path)!=expected[path.name]:raise RuntimeError('Warm-start checkpoint changed')
            parent_rows.append(dict(seed=seed,file=path.relative_to(ROOT).as_posix(),sha256=expected[path.name]))
        # This is a training-camera exposure check, not just a new raster-ID label.
        camera_exposure={}
        for folder in [ROOT/'experiments/visual_scene_v2_20261101/run_001/data/train',replay]:
            if (folder/'camera_positions.npy').exists():p=np.load(folder/'camera_positions.npy',mmap_mode='r')
            else:
                rays=np.load(folder/'rays.npy',mmap_mode='r');p=rays[...,0,0,3:]*.1+np.array([0,0,.8])
            camera_exposure[folder.relative_to(ROOT).as_posix()]=int(in_roi(p).sum())
        if any(camera_exposure.values()):raise RuntimeError('Proposed camera ROI already present in ancestor training')
        # All imported data are identified by source manifests and checked fully
        # before collection/training, never silently regenerated under same IDs.
        manifests={}
        for folder in [replay,ROOT/'experiments/visual_active_v3_20261101/run_001/data/validation',ROOT/'experiments/visual_scene_v2_20261101/run_001/data/train',ROOT/'experiments/visual_scene_v2_20261101/run_001/data/validation']:
            manifest=folder/'manifest.json';manifests[manifest.relative_to(ROOT).as_posix()]=sha(manifest)
        cfg=dict(schema=1,status='prepared',created=now(),training_started=False,stage_scope='paired_perception_AB',task='V4 RGB cuboid perception with inspected side views',
            paired_seeds=[1,2,3],variants=['A','B'],parameters=904112,authorized_pilot=pilot,
            data_seed_namespace_base=base,development_seed=base+901,splits={name:dict(seed=s,count=n,role=name) for name,(s,n) in assigned.items()},
            replay=dict(directory=replay.relative_to(ROOT).as_posix(),indices=indices,count=replay_count,eligible=len(eligible),excluded=len(families)-len(eligible),
                families=[list(map(int,families[i])) for i in indices],only_role='perception_train'),
            parents=parent_rows,ancestor_dataset_manifests=manifests,historical_registry_sha256=sha(history),
            geometry_holdout=dict(train_long_length=[.13,.16],train_long_width=[.018,.024],test_long_length=[.18,.21],test_long_width=[.014,.017],long_fraction=.15,long_arrangements='scattered_only'),
            camera_holdout=dict(roi=CAMERA_ROI,ancestor_training_observations_in_roi=camera_exposure,scope='new wrist views; initial/fixed context shared; every non-camera-test split excludes guarded ROI'),
            optimization=dict(optimizer='AdamW',learning_rate=1e-4,weight_decay=1e-4,effective_batch_size=32,microbatch=4,paired_contexts=2,
                maximum_epochs=10,warmup_epochs=3,gradient_clip=1.,precision='FP32',early_stop_pair_patience=8),
            selection=dict(split='validation',metric='balanced_common_context_loss',never_use_tests=True,common_update_budget=True),
            geometry_plots=dict(every_epochs=5,fixed_validation_families=16,colors=dict(truth='cyan',initial='orange',updated='green')),
            bank=dict(directory='experiments/visual_side_v4_20261102/guidance_002',manifest_sha256=sha(EXPERIMENT/'guidance_002/bank.json'),source='sim_reference',old_pose_bank_sha256=sha(ROOT/'experiments/visual_active_v3_20261101/run_001/pose_bank.json')),
            history=dict(maximum_wrist_images=3,max_extra_images=2),monitor=dict(agent_check_interval_hours_minimum=2,notify_only_changes=True),
            downstream_heads=dict(status='separate_phase_after_perception_freeze',reserved_splits=['request_train','request_validation','calibration'],endtests_not_for_training=True))
        sourcefiles=[p for p in (EXPERIMENT/'pipeline').rglob('*.py') if '__pycache__' not in p.parts]
        sourcefiles += [EXPERIMENT/'pipeline.py',EXPERIMENT/'paired_learning.py',EXPERIMENT/'replay_scene.py',EXPERIMENT/'guidance_validate.py',EXPERIMENT/'pilot.py']
        sourcefiles += [ROOT/'praxis/src/active_view'/p for p in ['camera_guidance.py','collision.py','planner.py','geometry.py','side_views.py','view_sweep.py','capture_requests.py']]
        sourcefiles += [ROOT/'experiments/visual_active_v3_20261101'/p for p in ['model_v3.py','data_v3.py','followup_core.py']]
        sourcefiles += [ROOT/'experiments/visual_scene_v2_20261101'/p for p in ['learning.py','scene_data.py','preflight.py','model_prototype.py','ensemble_uncertainty.py']]
        cfg['source_hashes']={p.relative_to(ROOT).as_posix():sha(p) for p in sourcefiles}
        for path in sourcefiles:
            dest=run/'source'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        save(run/'config.json',cfg);save(run/'protocol_seal.json',dict(config_sha256=sha(run/'config.json'),registry_sha256=sha(history)))
        save(run/'status.json',dict(stage='prepared',training_started=False,optimizer_updates=0))
        return dict(replay_eligible=len(eligible),replay_excluded=len(families)-len(eligible),reserved_splits=len(SPLITS),camera_exposure=camera_exposure)
    finally:db.close()

def verify_protocol(run,full_sources=False):
    run=Path(run);seal=read(run/'protocol_seal.json');cfg=read(run/'config.json')
    if sha(run/'config.json')!=seal['config_sha256'] or sha(run/'history.sqlite')!=seal['registry_sha256']:raise RuntimeError('Frozen protocol/lineage changed')
    if full_sources:
        for p,value in cfg['source_hashes'].items():
            if sha(ROOT/p)!=value:raise RuntimeError('Frozen implementation changed: '+p)
        for p in cfg['parents']:
            if sha(ROOT/p['file'])!=p['sha256']:raise RuntimeError('Parent weights changed')
    return cfg

def verify_imports(cfg):
    for rel,expected in cfg['ancestor_dataset_manifests'].items():
        path=ROOT/rel
        if sha(path)!=expected:raise RuntimeError('Ancestor manifest changed: '+rel)
        for name,value in read(path)['files'].items():
            if sha(path.parent/name)!=value:raise RuntimeError('Ancestor array changed: '+str(path.parent/name))
    return True
