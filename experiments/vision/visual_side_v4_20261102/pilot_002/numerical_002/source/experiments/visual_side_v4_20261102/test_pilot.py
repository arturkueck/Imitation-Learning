"""Data-contract tests for the bounded pilot, without simulator execution."""
import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pilot import get_context,ScenePerception
from pilot_bank import choose
from active_view.side_views import aimed_pose
from types import SimpleNamespace
from paired_learning import paired_criterion
from learning import criterion

def sample():
    return dict(images=np.zeros((1,3,3,160,160,3),np.uint8),rays=np.zeros((1,3,3,20,20,6),np.float32),
        visibility=np.zeros((1,3,5,3),np.float32),positions=np.zeros((1,5,3),np.float32),sizes=np.ones((1,5,3),np.float32)*.04,
        rotations=np.tile(np.eye(3),(1,5,1,1)),active=np.ones((1,5),bool),count=np.array([5]),kind=np.array([0]),family=np.array([[94140201,0]]),pose_available=np.array([[True,True,False]]))

def test_blocked_images_are_never_exposed_and_future_pixels_do_not_change_prefix():
    data=sample();data['visibility'][0,0,0]=1
    before=get_context(data,[0],(0,))
    data['images'][0,1:]=255;data['rays'][0,1:]=123
    after=get_context(data,[0],(0,))
    np.testing.assert_array_equal(before['images'],after['images']);np.testing.assert_array_equal(before['rays'],after['rays'])
    full=get_context(data,[0],(0,1,2))
    assert full['view_available'].sum()==4
    assert not full['view_available'][0,4]

def test_comparison_uses_same_union_membership_but_preserves_context_visibility():
    data=sample();data['pose_available'][:]=True
    data['visibility'][0,0,0,0]=1;data['visibility'][0,2,1,2]=1
    first=get_context(data,[0],(0,));last=get_context(data,[0],(0,1,2))
    np.testing.assert_array_equal(first['target_observable_override'],last['target_observable_override'])
    assert first['active'].sum()==2
    assert first['visibility'][0,1].max()==0
    assert last['visibility'][0,1,2]==1

def test_planned_parameter_counts():
    assert sum(p.numel() for p in ScenePerception().parameters())==904112
    head=torch.nn.Sequential(torch.nn.Linear(32,64),torch.nn.GELU(),torch.nn.Linear(64,32),torch.nn.GELU(),torch.nn.Linear(32,3))
    assert sum(p.numel() for p in head.parameters())==4291

def bank_fixture():
    focus=np.array([0.,0.,.85]);camera=np.array([0.,-.35,.96])
    entry=dict(family='right',camera=camera,rotation=aimed_pose(camera,focus),low=np.array([[-.01,-.01,.8]]),high=np.array([[.01,.01,.9]]))
    g=SimpleNamespace(m=SimpleNamespace(cam_fovy=[45]))
    checker=SimpleNamespace(camera=0,world=SimpleNamespace(boxes=[]))
    truth=dict(positions=np.array([[.15,.15,.85]]),sizes=np.array([[.04]*3]),rotations=np.array([np.eye(3)]),active=np.array([True]))
    return g,checker,[entry],truth,(focus,.04),np.array([-.6,0,.8])

def test_static_bank_still_blocks_per_scene_object_intersection():
    g,c,bank,truth,focus,base=bank_fixture()
    assert choose(g,c,bank,truth,focus,'right',base) is bank[0]
    truth['positions'][0]=[0,0,.85]
    assert choose(g,c,bank,truth,focus,'right',base) is None

def test_reference_truth_does_not_supply_missing_focus_and_wrong_view_is_blocked():
    g,c,bank,truth,focus,base=bank_fixture()
    assert choose(g,c,bank,truth,None,'right',base) is None
    assert choose(g,c,bank,truth,focus,'left',base) is None
    bank[0]['rotation']=bank[0]['rotation']@np.diag([-1,1,-1])
    assert choose(g,c,bank,truth,focus,'right',base) is None

def test_paired_loss_matches_v3_when_membership_is_unchanged_and_keeps_hidden_labels():
    data=sample();data['visibility'][0,0,0,0]=1
    a=get_context(data,[0],(0,));batch={k:torch.as_tensor(v) for k,v in a.items()}
    torch.manual_seed(14)
    raw=dict(detection_logits=torch.randn(1,5),position=torch.randn(1,5,3),dimensions_raw=torch.randn(1,5,3),rotation_6d=torch.randn(1,5,6),visibility_logits=torch.randn(1,5,3))
    av=torch.tensor([[True,True,True]])
    old,_,_=criterion(raw,batch,av);new,_,matches=paired_criterion(raw,batch,av)
    torch.testing.assert_close(new,old)
    batch['active'][0,1]=True;batch['target_observable_override'][0,1]=True
    _,_,matches=paired_criterion(raw,batch,av)
    assert set(matches[0][1])=={0,1}
