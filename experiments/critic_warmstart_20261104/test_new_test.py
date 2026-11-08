import copy
import torch
import pytest
from test_setup import Actor
from new_test import ExploringBoundedPolicy, performance_gate, settings, prepare


def test_exploration_preserves_action_bound_and_completion_on_unseen_inputs():
    torch.manual_seed(3)
    parent=Actor().eval()
    actor=copy.deepcopy(parent)
    with torch.no_grad():
        actor.net[-1].bias[:4].add_(10)
    noisy=ExploringBoundedPolicy(actor,parent,42,.02)
    x=torch.randn(500,2)*3
    phase=torch.zeros(500,dtype=torch.long)
    action,done=noisy(x,phase)
    expected=parent(x,phase)[0]
    assert (action-expected).abs().max()<=.020001
    assert action.abs().max()<=1
    assert torch.equal(done,actor(x,phase)[1])


def test_paired_loss_gate_does_not_hide_regressions_with_new_wins():
    cfg=settings();cfg['development_seeds']=list(range(4))
    baseline={'1':[{'success':v} for v in [True,True,True,False]]}
    current={'1':[{'success':v} for v in [False,False,False,True]]}
    passed,losses=performance_gate(baseline,current,cfg)
    assert not passed and losses['1']==3
    with pytest.raises(AssertionError):
        performance_gate(baseline,{'1':current['1'][:2]},cfg)


def test_prepare_refuses_failed_stability_proof_before_creating_output(tmp_path):
    proof=tmp_path/'stability';proof.mkdir()
    (proof/'decision.json').write_text('{"candidate_passed_stability":false}')
    output=tmp_path/'pilot'
    with pytest.raises(AssertionError,match='failed stability gate'):
        prepare(tmp_path/'source',proof,output)
    assert not output.exists()
