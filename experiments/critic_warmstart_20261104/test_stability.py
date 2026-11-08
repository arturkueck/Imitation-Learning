import copy
import torch
import numpy as np
import pytest
from test_setup import Actor, setup
from stability import BoundedMovement, constrain, drift, protocol, gate
from stability import run


def test_runner_import_keeps_native_controller_module_separate():
    assert callable(run.native.historical.old.prefix_valid)
    assert run.native.historical.old is not run


def test_constraint_bounds_unseen_inputs_and_keeps_gradients():
    torch.manual_seed(41)
    actor = Actor()
    parent = copy.deepcopy(actor)
    bounded = BoundedMovement(actor, parent, .02)
    x = torch.randn(100, 2)*10
    phase = torch.zeros(100, dtype=torch.long)
    expected = parent(x, phase)[0].detach()
    assert torch.equal(bounded(x, phase)[0], expected)
    with torch.no_grad():
        actor.net[-1].bias[:4].add_(.001)
    action, _ = bounded(x, phase)
    assert (action-expected).abs().max() <= .020001
    action.sum().backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in actor.parameters())
    assert all(p.grad is None for p in bounded.parent.parameters())
    with torch.no_grad():
        actor.net[-1].bias[:4].add_(100)
    assert (bounded(x, phase)[0]-expected).abs().max() <= .020001


def test_constrained_update_changes_actor_but_never_parent_or_completion():
    learner, batch = setup()
    cfg = learner.cfg
    reference = copy.deepcopy(learner.reference.state_dict())
    expected_done = learner.policy()(torch.tensor(batch['x']), torch.tensor(batch['phase']))[1].detach()
    constrain(learner, .02)
    start = copy.deepcopy(learner.actor.actor.state_dict())
    for _ in range(20):
        learner.update(batch, dict(x=batch['x'], phase=batch['phase'], action=batch['action']), .01)
    assert any(not torch.equal(start[k], learner.actor.actor.state_dict()[k]) for k in start)
    assert all(torch.equal(reference[k], learner.reference.state_dict()[k]) for k in reference)
    assert torch.equal(learner.policy()(torch.tensor(batch['x']), torch.tensor(batch['phase']))[1], expected_done)
    assert drift(learner, batch)['max_abs_action_delta'] <= .020001


def test_stability_gate_rejects_drift_failure_and_nonfinite():
    good = dict(finite=True, action_mse=.0001, max_abs_action_delta=.019)
    assert gate(good, 0, protocol(), True)
    assert not gate({**good, 'max_abs_action_delta': .03}, 0, protocol(), True)
    assert not gate(good, 2, protocol(), True)
    assert not gate({**good, 'finite': False}, 0, protocol(), True)
