"""Q1 immutable plans: fresh families, frozen vision/proposal engine, no launch."""
from pathlib import Path
import sys,shutil
HERE=Path(__file__).resolve().parent;LEGACY=Path(__file__).resolve().parents[2]/'vision/visual_edge_refine_v1_20261103'
sys.path.insert(0,str(LEGACY))
from run import ROOT,read,save,sha,now
from pipeline.lineage import inventory,connect,assert_fresh_seed
from pipeline.locking import exclusive
from q_features import NAMES

SPLITS={'request_train':(2000,'request_train'),'request_validation':(400,'request_validation'),
    'calibration/temperature':(200,'calibration'),'calibration/policy':(200,'calibration'),'calibration/audit':(200,'calibration'),
    'reserved_test':(400,'test'),'development':(4,'development')}

def prepare(run):
    run=Path(run)
    if run.exists():raise FileExistsError('Prepared protocols are immutable; choose another run')
    with exclusive(ROOT/'monitor/vision-namespace'):
        run.mkdir(parents=True);inventory(run/'history.sqlite');db=connect(run/'history.sqlite',readonly=True)
        base=97140000
        try:
            while any(db.execute('SELECT 1 FROM seeds WHERE seed=?',(base+i,)).fetchone() for i in range(1,len(SPLITS)+1)):base+=1000
            for i in range(1,len(SPLITS)+1):assert_fresh_seed(db,base+i)
        finally:db.close()
        baseline=read(LEGACY/'benchmark_001/config.json')
        critical=['active_policy.py','active_analysis.py','centered_sweep.py','geometry.py','tracking.py','refine.py']
        if any(sha(LEGACY/n)!=baseline['source_hashes'][n] for n in critical):raise RuntimeError('Proposal engine changed from benchmark')
        parents=read(ROOT/'experiments/vision/visual_side_v4_20261102/pilot_001/perception_freeze.json')['models']
        for p in parents:
            if sha(ROOT/p['file'])!=p['sha256']:raise RuntimeError('Frozen perception checkpoint changed')
        sources=list(HERE.glob('*.py'))+[HERE/'launch.ps1']+list(LEGACY.glob('*.py'))
        hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
        cfg=dict(schema=1,status='prepared',created=now(),objective='select safe existing cuboid proposals; preserve initial/better earlier hypothesis',
            training_started=False,optimizer_updates=0,seeds=[1,2,3],feature_names=NAMES,parents=parents,
            splits={name:dict(count=count,role=role,seed=base+i) for i,(name,(count,role)) in enumerate(SPLITS.items(),1)},
            model=dict(input=48,hidden=[128,64],output=4,activation='GELU',dropout=.1,parameters=14788,outputs=['harmful_logit','neutral_logit','helpful_logit','gain_mm_equivalent']),
            optimization=dict(optimizer='AdamW',lr=.001,weight_decay=.0001,batch=256,max_epochs=80,patience=10,clip=1.,device='cpu',
                loss='family-balanced CE weights[3,1,1] +0.5*Huber(gain/10,clipped_target/10,delta0.5)',selection='lowest validation loss; never calibration/test',gain_clip=25),
            labels=dict(reference='fixed initial matched object',metric='center_mm +0.25*corner_RMSE_mm',harmful_below=-1.,helpful_above=1.,unmatched='exclude local head label; retain full scene evaluation'),
            calibration=dict(temperature_families=200,policy_families=200,audit_families=200,risk_grid=[.01,.02,.03,.05,.075,.1,.15,.2],minimum_gain_mm=1.,
                max_family_harm_rate=.05,min_family_update_coverage=.2,min_updated_audit_families=30,harm_margin_mm=1.,
                audit='fixed policy; report family-level Wilson interval; empirical gate is not a real-world guarantee'),
            scope=dict(vision_frozen=True,proposal_engine_frozen=True,camera_policy_frozen=True,learned_camera_choice=False,proposal_bank='initial +raw stage1 +raw stage2; selector does not feed back into proposal generation',
                history_role='development benchmark families excluded from all new training/validation/calibration/test splits'),
            collection=dict(workers=2,frames=28,table_height=.8,blind_test_after_policy_freeze=True),planned_hours=12.,
            history_sha256=sha(run/'history.sqlite'),source_hashes=hashes)
        save(run/'config.json',cfg);save(run/'protocol_seal.json',dict(sha256=sha(run/'config.json')))
        for path in sources:
            target=run/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        for name,s in cfg['splits'].items():
            raw=run/'raw'/name;raw.mkdir(parents=True)
            raw_cfg=dict(scenes=s['count'],frames=28,family_seed=s['seed'],parents=parents,data_role=s['role'],history_path=(run/'history.sqlite').relative_to(ROOT).as_posix(),
                source_hashes={p.name:sha(p) for p in LEGACY.glob('*.py')},main_protocol_sha256=sha(run/'config.json'))
            save(raw/'config.json',raw_cfg);save(raw/'active_config.json',dict(table_height_m=.8));save(raw/'active_seal.json',dict(sha256=sha(raw/'config.json')))
        save(run/'status.json',dict(stage='prepared',training_started=False,optimizer_updates=0))
    return cfg

def verify(run):
    run=Path(run);cfg=read(run/'config.json')
    if sha(run/'config.json')!=read(run/'protocol_seal.json')['sha256'] or sha(run/'history.sqlite')!=cfg['history_sha256']:raise RuntimeError('Prepared plan/history changed')
    if any(sha(ROOT/name)!=h for name,h in cfg['source_hashes'].items()):raise RuntimeError('Frozen implementation changed; prepare a new run')
    if any(sha(ROOT/p['file'])!=p['sha256'] for p in cfg['parents']):raise RuntimeError('Frozen vision weights changed')
    return cfg
