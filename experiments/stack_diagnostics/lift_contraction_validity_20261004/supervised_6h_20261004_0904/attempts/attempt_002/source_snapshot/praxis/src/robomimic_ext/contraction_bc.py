"""Finite-difference contraction regularization for robomimic BC.

The local model is x[t+1] ~= x[t] + action_translation @ K. This is an
empirical approximation for the Lift OSC_POSE controller, not a guarantee for
contact-rich dynamics. See praxis/README.md for the experiment protocol.
"""

from collections import OrderedDict

import torch
import torch.nn.functional as F

from robomimic.algo import register_algo_factory_func
from robomimic.algo.bc import BC
from robomimic.config.bc_config import BCConfig


def one_step_contraction_loss(delta, action_difference, dynamics_matrix, target_ratio):
    """Penalize a one-step error ratio above the requested contraction ratio."""
    next_error = delta + action_difference @ dynamics_matrix
    squared_ratio = next_error.square().sum(dim=-1) / delta.square().sum(dim=-1)
    return F.relu(squared_ratio - target_ratio**2).mean()


def perturb_lift_observation(obs, eef_key, object_key, delta):
    """Shift the EEF and keep Lift's cube-minus-EEF feature consistent."""
    perturbed_obs = dict(obs)
    perturbed_obs[eef_key] = obs[eef_key] + delta
    object_obs = obs[object_key].clone()
    object_obs[..., -3:] -= delta
    perturbed_obs[object_key] = object_obs
    return perturbed_obs


class BCContractionConfig(BCConfig):
    ALGO_NAME = "bc_contraction"

    def algo_config(self):
        super().algo_config()
        self.algo.contraction.weight = 0.01
        self.algo.contraction.radius = 0.005  # metres
        self.algo.contraction.target_ratio = 0.99
        self.algo.contraction.eef_key = "robot0_eef_pos"
        self.algo.contraction.object_key = "object"
        self.algo.contraction.dynamics_matrix = [
            [0.01, 0.0, 0.0],
            [0.0, 0.01, 0.0],
            [0.0, 0.0, 0.01],
        ]


@register_algo_factory_func("bc_contraction")
def algo_config_to_class(algo_config):
    if algo_config.rnn.enabled or algo_config.transformer.enabled:
        raise ValueError("bc_contraction currently supports feedforward BC only")
    if algo_config.gaussian.enabled or algo_config.gmm.enabled or algo_config.vae.enabled:
        raise ValueError("bc_contraction currently supports deterministic BC only")
    return BCContraction, {}


class BCContraction(BC):
    """BC with a local one-step error-contraction penalty.

    For a sampled end-effector displacement delta, compare the actions at the
    demonstrated observation and a position-consistent perturbed observation.
    The penalty is positive if the estimated next-step displacement exceeds
    target_ratio times the starting displacement.
    """

    def _compute_losses(self, predictions, batch):
        losses = OrderedDict(super()._compute_losses(predictions, batch))
        cfg = self.algo_config.contraction
        weight = float(cfg.weight)
        if weight < 0:
            raise ValueError("contraction.weight must be nonnegative")
        if weight == 0:
            losses["contraction_loss"] = losses["action_loss"].new_zeros(())
            return losses

        radius = float(cfg.radius)
        ratio = float(cfg.target_ratio)
        if radius <= 0 or not 0 <= ratio < 1:
            raise ValueError("radius must be positive and target_ratio in [0, 1)")

        eef_key = str(cfg.eef_key)
        object_key = str(cfg.object_key)
        obs = batch["obs"]
        if eef_key not in obs or object_key not in obs:
            raise KeyError("contraction BC requires end-effector and object observations")
        if obs[eef_key].shape[-1] != 3 or obs[object_key].shape[-1] != 10:
            raise ValueError("expected Lift eef position (3) and object vector (10)")
        if predictions["actions"].shape[-1] < 3:
            raise ValueError("action needs 3 translation components")

        delta = torch.randn_like(obs[eef_key])
        delta = radius * F.normalize(delta, dim=-1, eps=1e-12)
        perturbed_obs = perturb_lift_observation(obs, eef_key, object_key, delta)

        perturbed_action = self.nets["policy"](
            obs_dict=perturbed_obs, goal_dict=batch["goal_obs"]
        )
        K = torch.as_tensor(
            cfg.dynamics_matrix,
            dtype=predictions["actions"].dtype,
            device=predictions["actions"].device,
        )
        if K.shape != (3, 3):
            raise ValueError("dynamics_matrix must have shape (3, 3)")

        action_difference = perturbed_action[..., :3] - predictions["actions"][..., :3]
        losses["contraction_loss"] = one_step_contraction_loss(delta, action_difference, K, ratio)
        losses["action_loss"] = losses["action_loss"] + weight * losses["contraction_loss"]
        return losses

    def log_info(self, info):
        log = super().log_info(info)
        log["Contraction_Loss"] = info["losses"]["contraction_loss"].item()
        return log
