"""Leakage and exact-resume regressions. Optimizer tests use tiny synthetic nets."""
import sys,copy,json,sqlite3
from pathlib import Path
import numpy as np
import torch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import lineage
from pipeline.lineage import connect,add,assert_replay,assert_fresh_seed,assert_new_family,geometry_digest,historical_duplicate
from pipeline.generate import content_db,register_content
from pipeline.samples import SLOTS,pair,context,Store
from pipeline.engine import checkpoint,restore,learning_rate,forward
from pipeline.common import save,sha,begin_budget,check_stop
from pipeline.protocol import in_roi
import pipeline.audit as audit_module

def sample(family=(94831001,0)):
    n=len(SLOTS);images=np.stack([np.full((3,160,160,3),i+1,np.uint8) for i in range(n)])
    rays=np.stack([np.full((3,20,20,6),i+.1,np.float32) for i in range(n)])
    vis=np.zeros((n,5,3),np.float32);vis[:,0,0]=1;vis[4:,1,2]=1
    return dict(images=images,rays=rays,visibility=vis,positions=np.array([[i*.06,0,.83] for i in range(5)],np.float32),sizes=np.ones((5,3),np.float32)*.04,
        rotations=np.tile(np.eye(3,dtype=np.float32),(5,1,1)),active=np.array([True,True,False,False,False]),count=np.int64(2),kind=np.int64(0),family=np.array(family),pose_available=np.ones(n,bool),slot_roles=SLOTS,is_replay=False)

def test_all_historical_roles_block_new_splits_and_only_train_can_replay(tmp_path):
    db=connect(tmp_path/'history.sqlite')
    for i,role in enumerate(['perception_train','model_validation','test','calibration','request_train','development']):add(db,[9000001,i],role,'old')
    assert_replay(db,[9000001,0])
    for i in range(1,6):
        with pytest.raises(ValueError):assert_replay(db,[9000001,i])
        with pytest.raises(ValueError):assert_new_family(db,[9000001,i])
    add(db,[9000001,0],'test','other_run')
    with pytest.raises(ValueError):assert_replay(db,[9000001,0])
    with pytest.raises(ValueError):assert_fresh_seed(db,9000001)
    db.close()

def test_relabelled_old_content_and_cross_split_copies_are_rejected(tmp_path):
    db=connect(tmp_path/'h.sqlite');old=sample((9000001,0));add(db,old['family'],'test','old',old)
    new=sample((94831002,0));assert historical_duplicate(db,new)
    contents=content_db(':memory:');register_content(contents,old,'train')
    with pytest.raises(ValueError,match='duplicate'):register_content(contents,new,'validation')
    register_content(contents,old,'train') # Exact same sealed record on resume is allowed.
    db.close();contents.close()

def test_geometry_fingerprint_is_slot_and_cube_symmetry_invariant():
    row=sample();digest=geometry_digest(row);permutation=[1,0,2,3,4]
    for key in ['positions','sizes','rotations','active']:row[key]=row[key][permutation]
    row['rotations'][0]=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    assert geometry_digest(row)==digest
    row['active'][:]=False;assert geometry_digest(row) is None

def test_inventory_includes_previous_v4_prepared_runs(tmp_path,monkeypatch):
    folder=tmp_path/'experiments/visual_old/prepared_001/data/train';folder.mkdir(parents=True)
    np.save(folder/'family.npy',np.array([[9000123,0]]))
    destination=tmp_path/'experiments/visual_old/prepared_002';destination.mkdir()
    monkeypatch.setattr(lineage,'ROOT',tmp_path)
    result=lineage.inventory(destination/'history.sqlite')
    db=connect(destination/'history.sqlite',readonly=True)
    assert result['unique_families']==1
    with pytest.raises(ValueError):assert_new_family(db,[9000123,0])
    db.close()

def test_inputs_never_read_future_views_and_A_never_receives_guided_RGB():
    row=sample();before=pair(row,'A',epoch=3,seed=1)
    row['images'][4:]=255;row['rays'][4:]=555
    after=pair(row,'A',epoch=3,seed=1)
    for j in [0,1]:
        for k in ['images','rays','view_available']:np.testing.assert_array_equal(before[j][k],after[j][k])
    first=context(row,[0]);row['images'][1:]=120
    np.testing.assert_array_equal(first['images'],context(row,[0])['images'])
    row['pose_available'][4]=False
    with pytest.raises(ValueError,match='Unavailable'):context(row,[0,4])

def test_paired_targets_common_but_visibility_and_observation_inputs_stay_contextual():
    row=sample();before,after,history=pair(row,'B',kind='side')
    np.testing.assert_array_equal(before['target_observable_override'],after['target_observable_override'])
    assert before['visibility'][1,2]==0 and after['visibility'][1,2]==1
    assert len(history)<=3 and len(set(history))==len(history)
    class Spy:
        def __call__(self,*args):assert len(args)==3;return dict(dummy=1)
    forward(Spy(),{k:torch.as_tensor(v[None]) for k,v in after.items()})

def test_camera_roi_has_a_real_spatial_buffer():
    assert in_roi([.05,.35,1.])
    assert not in_roi([.03,.35,1.])
    assert in_roi([.03,.35,1.],guard=True)
    assert not in_roi([-.1,.35,1.],guard=True)

def test_resume_restores_partial_gradients_optimizer_rng_and_sampler(tmp_path):
    torch.manual_seed(42)
    model=torch.nn.Sequential(torch.nn.Linear(2,4),torch.nn.ReLU(),torch.nn.Dropout(.2),torch.nn.Linear(4,1))
    opt=torch.optim.AdamW(model.parameters(),lr=.001)
    tracks={'A1':dict(model=model,optimizer=opt,step=0,best=1.,best_epoch=0)}
    x=torch.arange(8,dtype=torch.float32).reshape(4,2)/8;y=torch.ones(4,1)
    def micro(a,b):((model(x[a:b])-y[a:b]).square().mean()*.5).backward()
    opt.zero_grad();micro(0,2);cursor=dict(epoch=2,batch=32,track=0,micro=2)
    checkpoint(tmp_path/'latest.pth',tracks,cursor,[],{'protocol':'test'})
    micro(2,4);opt.step();expected=copy.deepcopy(model.state_dict());expected_opt=copy.deepcopy(opt.state_dict())
    torch.manual_seed(999);restored,_,_=restore(tmp_path/'latest.pth',tracks,'cpu');assert restored==cursor
    micro(2,4);opt.step()
    for k,v in expected.items():assert torch.equal(v,model.state_dict()[k])
    for k,v in expected_opt['state'].items():
        for n,t in v.items():assert torch.equal(t,opt.state_dict()['state'][k][n])
    with (tmp_path/'latest.pth').open('ab') as f:f.write(b'corrupt')
    with pytest.raises(RuntimeError,match='hash'):restore(tmp_path/'latest.pth',tracks,'cpu')

def test_budget_is_not_extended_on_resume(tmp_path,monkeypatch):
    import pipeline.common as common
    monkeypatch.setattr(common.time,'time',lambda:100.)
    first=begin_budget(tmp_path,2)
    assert begin_budget(tmp_path,None)==first
    with pytest.raises(ValueError,match='reset'):begin_budget(tmp_path,2)
    monkeypatch.setattr(common.time,'time',lambda:10000.)
    with pytest.raises(TimeoutError):check_stop(tmp_path)

def test_dataset_loader_rejects_development_role_disguised_as_training(tmp_path,monkeypatch):
    import pipeline.samples as samples
    folder=tmp_path/'data/train';folder.mkdir(parents=True);(tmp_path/'legacy').mkdir()
    np.savez_compressed(folder/'000000.npz',family=np.array([94831901,0]))
    save(folder/'index.json',dict(records=[dict(file='000000.npz',sha256=sha(folder/'000000.npz'),family=[94831901,0],split='development')]))
    save(folder/'seal.json',dict(index_sha256=sha(folder/'index.json')))
    save(tmp_path/'config.json',dict(replay=dict(indices=[],directory='legacy')))
    monkeypatch.setattr(samples,'ROOT',tmp_path)
    store=Store(tmp_path,'train')
    with pytest.raises(RuntimeError,match='role'):store[0]

def test_schedule_uses_frozen_total_updates():
    assert learning_rate(0,10,10)<learning_rate(29,10,10)
    assert learning_rate(100,10,10)==pytest.approx(5e-6)

def test_independent_audit_rejects_current_run_development_content(tmp_path,monkeypatch):
    db=connect(tmp_path/'history.sqlite');db.commit();db.close()
    dev=sample((94831901,0));copied=sample((94831001,0))
    for split,seed in [('development',94831901),('train',94831001),('validation',94831002)]:
        save(tmp_path/'data'/split/'seal.json',dict(seed=seed,count=1,smoke_only=split=='development'))
    class Fake:
        def __init__(self,run,split,**kw):self.records=[0];self.split=split
        def __getitem__(self,i):return dev if self.split=='development' else copied
    cfg=dict(splits=dict(train=dict(seed=94831001,count=1),validation=dict(seed=94831002,count=1)))
    monkeypatch.setattr(audit_module,'verify_protocol',lambda *a,**kw:cfg);monkeypatch.setattr(audit_module,'verify_imports',lambda *a:None)
    monkeypatch.setattr(audit_module,'Store',Fake)
    with pytest.raises(ValueError,match='duplicate'):audit_module.audit(tmp_path,main=True)
