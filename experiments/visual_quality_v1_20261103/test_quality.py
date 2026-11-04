import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import torch
import pytest
from q_model import QualityModel,loss
from q_features import extract,NAMES
from q_policy import choose,probabilities
from q_calibration import wilson
import q_data

def fixture():
    b=dict(position=[0.,0.,.83],size=[.04,.04,.06],rotation=np.eye(3).tolist());candidate={**b,'position':[.002,0.,.83]}
    group=dict(support=3,spread_mm=2.,size_spread_mm=1.,corner_disagreement_mm=3.,min_detection_score=.9)
    cloud=[dict(object_index=0,track=i,point=[i*.002,0.,.86],reprojection_px=.5,parallax_deg=5.) for i in range(6)]
    snapshot=dict(triangulated_points=cloud,tracks=[dict(observations=[(j,[1.,1.]) for j in range(10)]) for _ in range(6)],heldout_frames=[3,6,9],rejections=dict(photometric_rejected=2,forward_backward_rejected=1))
    obj=dict(gate=dict(reasons=[],tracks=6,heldout_before=1.,heldout_after=.7,anchor_before=1.,anchor_after=.8),fit=dict(status='fitted',fit_views=9,evaluations=20))
    return b,candidate,group,snapshot,obj

def test_architecture_and_asymmetric_loss_without_optimizer():
    model=QualityModel().eval();assert sum(p.numel() for p in model.parameters())==14788
    for p in model.parameters():p.data.zero_()
    x=torch.zeros(2,48);out=model(x);assert out['logits'].shape==(2,3) and out['gain'].shape==(2,)
    a=loss(model,x,torch.zeros(2,dtype=torch.long),torch.zeros(2),torch.ones(2));b=loss(model,x,torch.ones(2,dtype=torch.long),torch.zeros(2),torch.ones(2))
    assert torch.isfinite(a) and float((a/b).detach())==pytest.approx(3.)

def test_features_ignore_gt_and_future_camera_fields():
    b,c,g,s,o=fixture();cams=[dict(position=[0.,0.,1.2]),dict(position=[.1,0.,1.2])]
    x,ok=extract(b,c,g,1,0,s,o,cams,1,.8);assert len(NAMES)==48 and x.shape==(48,) and np.isfinite(x).all() and ok
    s['ground_truth']='forbidden';s['future_rgb']='poison';s['labels']=[12345]
    y,_=extract(b,c,g,1,0,s,o,cams,1,.8);np.testing.assert_array_equal(x,y)

def test_best_earlier_proposal_retained_and_labels_not_selection_input():
    d=dict(family=np.array([[10,0],[10,0],[10,0]]),object_index=np.array([0,0,1]),stage=np.array([1,2,2]),eligible=np.array([True,True,False]),classes=np.array([0,2,2]),gains=np.array([-50,50,99]))
    p=np.array([[.01,.09,.9],[.01,.09,.9],[.01,.09,.9]]);g=np.array([5.,3.,99.]);chosen=choose(d,p,g,.05)
    assert chosen=={(10,0,0):0}
    d['classes'][:]=-1;d['gains']=np.full(3,np.nan);assert choose(d,p,g,.05)==chosen
    p[0,0]=.2;assert choose(d,p,g,.05)=={(10,0,0):1}

def test_probability_normalization_and_family_interval():
    p=probabilities(np.array([[1000.,999.,998.]]),dict(temperature=2.,bias=[0.,0.,0.]));assert np.isfinite(p).all() and p.sum()==pytest.approx(1.)
    assert wilson(0,200)[1]<.02 and wilson(200,200)[0]>.98

def test_public_start_requires_approval_before_any_budget(tmp_path,monkeypatch):
    import quality
    monkeypatch.setattr(quality,'HERE',tmp_path);monkeypatch.setattr(quality,'verify',lambda r:dict(planned_hours=12))
    monkeypatch.setattr(sys,'argv',['quality.py','start','--run','r'])
    with pytest.raises(ValueError,match='not authorized'):quality.main()
    assert not (tmp_path/'r/budget.json').exists()

def test_blind_test_collection_blocked_without_policy_and_audit(tmp_path,monkeypatch):
    from q_protocol import save,sha
    raw=tmp_path/'raw/reserved_test';raw.mkdir(parents=True);save(raw/'config.json',dict(family_seed=9000001,data_role='test',scenes=4));save(raw/'active_seal.json',dict(sha256=sha(raw/'config.json')))
    cfg=dict(splits=dict(reserved_test=dict(seed=9000001,role='test',count=4)));monkeypatch.setattr(q_data,'verify',lambda r:cfg)
    with pytest.raises(RuntimeError,match='Blind test blocked'):q_data.collect(tmp_path,'reserved_test')

def test_training_subset_excludes_unmatched_and_ineligible_examples():
    from q_train import subset,weights
    d=dict(x=np.zeros((3,48)),family=np.array([[1,0],[1,0],[1,1]]),eligible=np.array([True,False,True]),labelled=np.array([True,True,False]),classes=np.array([0,2,-1]))
    out=subset(d);assert len(out['x'])==1 and out['classes'].tolist()==[0]
    np.testing.assert_allclose(weights(d['family']),[.5,.5,1.])

def test_renamed_foreign_feature_family_is_rejected(tmp_path,monkeypatch):
    from q_protocol import save,sha
    split='request_train';folder=tmp_path/'features'/split;folder.mkdir(parents=True);raw=tmp_path/'raw'/split;raw.mkdir(parents=True)
    save(tmp_path/'config.json',{});save(raw/'seal.json',{})
    np.savez_compressed(folder/'dataset.npz',x=np.zeros((1,48)),family=np.array([[9999999,0]]))
    save(folder/'manifest.json',dict(split=split,role=split,family_seed=9000001,dataset_sha256=sha(folder/'dataset.npz'),raw_seal_sha256=sha(raw/'seal.json'),main_protocol_sha256=sha(tmp_path/'config.json')))
    monkeypatch.setattr(q_data,'verify',lambda r:dict(splits={split:dict(seed=9000001,role=split,count=10)}))
    with pytest.raises(RuntimeError,match='Foreign family'):q_data.load(tmp_path,split)
