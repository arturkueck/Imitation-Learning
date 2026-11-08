import copy
import numpy as np
import pytest
import torch
from torch import nn
from test_setup import setup
from core import Learner
from relative_range import constrain,project_relative,widths


def test_legacy_target_noise_and_rng_are_bitwise_unchanged():
    learner,batch=setup()
    x=torch.tensor(batch['next_x']);phase=torch.tensor(batch['next_phase'])
    state=learner.generator.get_state().clone()
    generator=torch.Generator().set_state(state)
    with torch.no_grad():
        original=learner.target_actor(x,phase)[0]
        noise=torch.randn(original.shape,generator=generator)*torch.tensor(learner.cfg['target_noise_std'])
        expected=(original+noise.clamp(-learner.cfg['target_noise_clip'],learner.cfg['target_noise_clip'])).clamp(-1,1)
    actual,metrics=learner.target_actions(x,phase)
    assert torch.equal(actual,expected)
    assert torch.equal(learner.generator.get_state(),generator.get_state())
    assert metrics['target_action_projection']=='legacy'
    assert metrics['target_projection_changed_fraction']==0


def test_projection_covers_extreme_noise_zero_channels_and_broadcast_batches():
    parent=torch.tensor([[[.8,-.1,0.,-.99]], [[-.8,.4,0.,.99]]])
    noisy=torch.tensor([[[100.,100.,100.,100.],[-100.,-100.,-100.,-100.]]]).expand(2,-1,-1)
    actual=project_relative(noisy,parent,.2,.5,.02)
    assert ((actual-parent).abs()<=widths(parent,.2,.5,.02)+1e-6).all()
    assert (actual[...,2]==0).all()
    assert (actual[...,:3]*parent[...,:3]>=0).all()
    assert actual.abs().max()<=1


class PhaseActor(nn.Module):
    def __init__(self):
        super().__init__();self.bias=nn.Parameter(torch.zeros(4))
    def forward(self,x,phase):
        center=torch.stack([torch.where(phase==0,.8,-.8),x[:,0]*.05,torch.zeros_like(x[:,0]),
                            torch.where(phase==0,-.99,.99)],-1)
        return (center+self.bias).clamp(-1,1),torch.zeros(len(x))


def test_production_critic_receives_projected_targets_for_next_input_and_phase():
    _,batch=setup();cfg=setup()[0].cfg
    learner=Learner(PhaseActor(),np.zeros(3),np.ones(3),cfg,device='cpu')
    constrain(learner,.2)
    batch['next_phase'][:]=1;batch['phase'][:]=0
    captured=[]
    handle=learner.target_critic.register_forward_pre_hook(lambda module,args:captured.append(args[1].clone()))
    reference=copy.deepcopy(learner.reference.state_dict())
    metrics=learner.update(batch)
    handle.remove()
    parent=learner.reference(torch.tensor(batch['next_x']),torch.tensor(batch['next_phase']))[0]
    assert len(captured)==1
    assert ((captured[0]-parent).abs()<=widths(parent,.2,.5,.02)+1e-6).all()
    assert (captured[0][:,0]<0).all() # Current-phase center is +.8, NEXT is -.8.
    assert not captured[0].requires_grad
    assert metrics['target_action_projection']=='actor_bounds_v1'
    assert metrics['target_projection_changed_fraction']>0
    assert all(torch.equal(reference[k],learner.reference.state_dict()[k]) for k in reference)
    assert all(p.grad is None for p in learner.target_actor.parameters())


def test_projection_mode_is_explicit_and_missing_actor_contract_fails():
    learner,batch=setup()
    learner.cfg['target_action_projection']='actor_bounds_v1'
    with pytest.raises(ValueError,match='project_action'):learner.update(batch)
    assert learner.updates==0
    learner.cfg['target_action_projection']='typo'
    with pytest.raises(ValueError,match='Unknown target action projection'):learner.update(batch)
    assert learner.updates==0


def test_relative_checkpoint_records_projection_mode_and_allows_explicit_legacy(tmp_path):
    learner,_=setup();constrain(learner,.2)
    path=tmp_path/'projected.pth';learner.save(path)
    assert torch.load(path,weights_only=False)['config']['target_action_projection']=='actor_bounds_v1'
    previous,_=setup();constrain(previous,.2,project_targets=False)
    assert previous.cfg['target_action_projection']=='legacy'
