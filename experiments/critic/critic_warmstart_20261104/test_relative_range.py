import copy
import torch
from test_setup import Actor,setup
from relative_range import widths,RelativeMovement,constrain,ExploringRelativePolicy


def test_widths_allow_large_motion_but_preserve_xyz_direction_and_equilibrium():
    parent=torch.tensor([[1.,-.4,0.,-1.]])
    w=widths(parent,.2)
    assert torch.allclose(w,torch.tensor([[.2,.2,0.,.02]]))
    assert (w[:,:3]<=parent[:,:3].abs()*.5).all()


def test_relative_policy_changes_weights_and_obeys_bounds_on_unseen_inputs():
    learner,batch=setup();parent=copy.deepcopy(learner.reference)
    constrain(learner,.2)
    before=copy.deepcopy(learner.actor.actor.state_dict())
    for _ in range(20):learner.update(batch,dict(x=batch['x'],phase=batch['phase'],action=batch['action']),.01)
    assert any(not torch.equal(before[k],learner.actor.actor.state_dict()[k]) for k in before)
    x=torch.randn(400,2)*5;phase=torch.zeros(400,dtype=torch.long)
    with torch.no_grad():
        action,_=learner.actor(x,phase);base,_=parent(x,phase)
        assert ((action-base).abs()<=widths(base,.2)+1e-6).all()
        assert (action[:,:3]*base[:,:3]>=0).all()
        noisy=ExploringRelativePolicy(learner.policy(),learner.reference,42)
        action,_=noisy(x,phase)
        assert ((action-base).abs()<=widths(base,.2)+1e-6).all()
        assert (action[:,:3]*base[:,:3]>=0).all()


def test_relative_budget_really_allows_point_two_and_vanishes_at_zero():
    class Constant(torch.nn.Module):
        def __init__(self,value):
            super().__init__();self.register_buffer('value',torch.tensor(value,dtype=torch.float32))
        def forward(self,x,phase):
            return self.value.expand(len(x),-1),torch.zeros(len(x))
    parent=Constant([.8,-.8,0.,-1.])
    raw=Constant([-1.,1.,1.,1.])
    model=RelativeMovement(raw,parent,.2)
    x=torch.zeros(2,2);phase=torch.zeros(2,dtype=torch.long)
    action,_=model(x,phase);reference,_=parent(x,phase)
    assert torch.allclose((action-reference)[:,:2].abs(),torch.full((2,2),.2),atol=1e-6)
    assert (action[:,2]==0).all()
    assert torch.allclose((action-reference)[:,3].abs(),torch.full((2,),.02),atol=1e-6)
