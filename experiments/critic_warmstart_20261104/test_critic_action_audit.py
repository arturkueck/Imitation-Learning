import numpy as np
import torch
import pytest
from critic_action_audit import discounted_return,preference,gradient_action


def test_probe_return_uses_original_horizon_and_single_terminal_reward():
    assert discounted_return(True,10,10,.5)==1
    assert discounted_return(True,10,12,.5)==.25
    assert discounted_return(False,10,12,.5)==0
    with pytest.raises(AssertionError):discounted_return(True,12,10,.5)


def test_no_outcome_difference_is_not_called_wrong_ranking():
    assert preference(100,0)=='outcome_tie'
    assert preference(0,.1)=='prediction_tie'
    assert preference(.01,.1)=='correct'
    assert preference(.01,-.1)=='wrong'


def test_q_action_gradient_changes_only_xyz_and_never_parameters():
    class LinearQ(torch.nn.Module):
        def __init__(self):
            super().__init__();self.coeff=torch.nn.Parameter(torch.tensor([2.,-1.,0.,4.],device='cuda'),requires_grad=False)
        def forward(self,state,action):
            q=(action*self.coeff).sum(-1);return q,q
    critic=LinearQ();before=critic.coeff.detach().clone();a=np.zeros(4,np.float32)
    up=gradient_action(critic,np.zeros(3,np.float32),a,.1)
    down=gradient_action(critic,np.zeros(3,np.float32),a,-.1)
    assert np.isclose(np.linalg.norm(up[:3]),.1)
    assert up[3]==down[3]==0 and np.array_equal(a,np.zeros(4))
    assert (up[:3]*np.array([2.,-1.,0.])).sum()>0
    assert (down[:3]*np.array([2.,-1.,0.])).sum()<0
    assert torch.equal(before,critic.coeff) and critic.coeff.grad is None


def test_alias_actions_do_not_create_additional_pairwise_evidence():
    from critic_action_report import unique_actions
    row=dict(action=[0,0,0,-1],category='near_policy')
    groups=unique_actions(dict(policy=row,open_gripper=dict(row,category='stress'),different=dict(row,action=[1,0,0,-1])))
    assert len(groups)==2 and groups[0]['near']
    assert groups[0]['names']==['policy','open_gripper']


def test_discounted_advantages_equal_return_change_for_an_exact_value_function():
    from critic_pulse_audit import advantage_sum
    gamma=.9;values=np.array([.2,.7,0.]);rewards=np.array([0.,1.])
    advantages=rewards+gamma*values[1:]-values[:-1]
    assert advantage_sum(advantages,gamma)==pytest.approx(gamma-.2)
    assert advantage_sum([0.,0.],gamma)==0


def test_feasible_comparison_respects_relative_actor_mapping():
    from critic_action_report import actor_feasible
    record=dict(context='final',variants=dict(other_actor=dict(action=[.8,-.1,0.,-1.])))
    assert actor_feasible(record,[.6,-.05,0.,-.98])
    assert not actor_feasible(record,[.6,.01,0.,-.98])
    assert not actor_feasible(record,[.6,-.05,.001,-.98])
