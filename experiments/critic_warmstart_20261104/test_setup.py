from pathlib import Path
import copy
import json
import numpy as np
import pytest
import torch
from torch import nn
from core import Learner,returns


class Actor(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.Linear(2,8),nn.SiLU(),nn.Linear(8,5))
    def forward(self,x,phase):
        v=self.net(x);return v[:,:4].tanh(),v[:,4]


def setup():
    torch.manual_seed(9)
    cfg=json.loads((Path(__file__).parent/'config.json').read_text());cfg['critic_width']=16
    agent=Learner(Actor(),np.zeros(3),np.ones(3),cfg,device='cpu')
    rng=np.random.default_rng(2);n=16
    batch=dict(state=rng.normal(size=(n,3)).astype('float32'),next_state=rng.normal(size=(n,3)).astype('float32'),
        x=rng.normal(size=(n,2)).astype('float32'),next_x=rng.normal(size=(n,2)).astype('float32'),
        phase=np.zeros(n,int),next_phase=np.zeros(n,int),action=rng.uniform(-1,1,size=(n,4)).astype('float32'),
        reward=np.zeros(n,np.float32),terminal=np.ones(n,np.float32),**{'return':np.ones(n,np.float32)})
    return agent,batch


def test_returns_do_not_cross_terminal_or_failed_episode():
    assert np.array_equal(returns([0,1,0,0],[0,1,0,1],.5),[.5,1,0,0])
    with pytest.raises(AssertionError):returns([0,0],[0,0],.5)


def test_critic_warmup_never_changes_actor_or_completion_reference():
    a,b=setup();before=copy.deepcopy(a.actor.state_dict());ref=copy.deepcopy(a.reference.state_dict())
    for _ in range(3):a.warm(b)
    assert all(torch.equal(before[k],a.actor.state_dict()[k]) for k in before)
    assert all(torch.equal(ref[k],a.reference.state_dict()[k]) for k in ref)


def test_pure_rl_actor_updates_through_critic_without_bc():
    a,b=setup();before=copy.deepcopy(a.actor.state_dict())
    assert not a.update(b)['actor_updated']
    assert all(torch.equal(before[k],a.actor.state_dict()[k]) for k in before)
    m=a.update(b)
    assert m['actor_updated'] and m['bc_coefficient']==0
    assert any(not torch.equal(before[k],a.actor.state_dict()[k]) for k in before)


def test_completion_outputs_remain_identical_after_actor_updates():
    a,b=setup();x=torch.tensor(b['x']);p=torch.tensor(b['phase'])
    expected=a.policy()(x,p)[1].clone()
    for _ in range(6):a.update(b)
    assert torch.equal(expected,a.policy()(x,p)[1])


def test_terminal_transition_never_bootstraps():
    a,b=setup()
    with torch.no_grad():
        for net in (a.target_critic.q1,a.target_critic.q2):
            for p in net.parameters():p.zero_()
            net[-1].bias.fill_(1)
    assert a.update(b)['target_mean']==0
    b['terminal'][:]=0
    assert a.update(b)['target_mean']==pytest.approx(a.cfg['gamma'])


def test_bc_is_explicit_and_uses_action_targets():
    a,b=setup();bc=dict(x=b['x'],phase=b['phase'],action=b['action'])
    a.update(b,bc,.01);m=a.update(b,bc,.01)
    assert m['bc_loss']>0 and m['actor_loss']==pytest.approx(m['rl_loss']+.01*m['bc_loss'],abs=1e-6)


def test_scientific_training_defaults_disabled_and_seeds_disjoint():
    cfg=json.loads((Path(__file__).parent/'config.json').read_text())
    assert cfg['training_enabled'] is False
    ranges=[set(range(cfg['collection']['train_seed_start'],cfg['collection']['train_seed_start']+120)),
            set(range(cfg['collection']['valid_seed_start'],cfg['collection']['valid_seed_start']+40)),
            set(range(cfg['evaluation']['development_seed_start'],cfg['evaluation']['development_seed_start']+20)),
            set(range(cfg['evaluation']['reserved_final_seeds'][0],cfg['evaluation']['reserved_final_seeds'][1]+1)),
            set(cfg['technical_seeds'])]
    assert sum(map(len,ranges))==len(set.union(*ranges))
