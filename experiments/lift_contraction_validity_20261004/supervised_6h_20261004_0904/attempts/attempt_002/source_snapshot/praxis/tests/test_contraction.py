"""Geometry and differentiation checks for the new training objective."""

import torch

from robomimic_ext.contraction_bc import (
    one_step_contraction_loss,
    perturb_lift_observation,
)


def test_contraction_loss_distinguishes_recovery_from_divergence():
    delta = torch.tensor([[0.005, 0.0, 0.0]])
    K = torch.eye(3) * 0.01
    recover = torch.tensor([[-0.5, 0.0, 0.0]], requires_grad=True)
    diverge = torch.tensor([[0.5, 0.0, 0.0]], requires_grad=True)
    good_loss = one_step_contraction_loss(delta, recover, K, target_ratio=0.99)
    bad_loss = one_step_contraction_loss(delta, diverge, K, target_ratio=0.99)
    assert good_loss.item() == 0.0
    assert bad_loss.item() > 0.0
    bad_loss.backward()
    assert diverge.grad is not None
    assert diverge.grad[0, 0] > 0


def test_lift_relative_position_stays_consistent():
    eef = torch.tensor([[0.1, 0.2, 0.3]])
    cube = torch.tensor([[0.4, 0.5, 0.6]])
    obj = torch.cat([cube, torch.tensor([[1.0, 0.0, 0.0, 0.0]]), cube - eef], dim=-1)
    obs = {"robot0_eef_pos": eef, "object": obj}
    delta = torch.tensor([[0.005, -0.002, 0.001]])
    perturbed = perturb_lift_observation(obs, "robot0_eef_pos", "object", delta)
    assert torch.allclose(perturbed["object"][:, :3], cube)
    assert torch.allclose(
        perturbed["object"][:, -3:], cube - perturbed["robot0_eef_pos"]
    )
    assert torch.allclose(obs["object"], obj)
