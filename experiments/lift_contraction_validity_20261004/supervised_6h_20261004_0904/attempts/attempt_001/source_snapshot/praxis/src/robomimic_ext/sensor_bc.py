"""Paired clean/noisy BC for a specified EEF measurement-error model.

This is a controlled augmentation baseline, not a novel stability guarantee.
The physical demonstration and its action label stay unchanged. Only the
measured EEF and the derived cube-minus-EEF measurement are perturbed.
"""
from collections import OrderedDict

import torch
import torch.nn.functional as F

from robomimic.algo import register_algo_factory_func
from robomimic.algo.bc import BC
from robomimic.config.bc_config import BCConfig

from .contraction_bc import perturb_lift_observation


class BCSensorConfig(BCConfig):
    ALGO_NAME = 'bc_sensor'

    def algo_config(self):
        super().algo_config()
        self.algo.sensor.mix = 0.5
        self.algo.sensor.radius = 0.005
        self.algo.sensor.seed = 4100401
        self.algo.sensor.eef_key = 'robot0_eef_pos'
        self.algo.sensor.object_key = 'object'


@register_algo_factory_func('bc_sensor')
def algo_config_to_class(algo_config):
    if algo_config.rnn.enabled or algo_config.transformer.enabled:
        raise ValueError('bc_sensor supports feedforward BC only')
    if algo_config.gaussian.enabled or algo_config.gmm.enabled or algo_config.vae.enabled:
        raise ValueError('bc_sensor supports deterministic BC only')
    return BCSensor, {}


class BCSensor(BC):
    def train_on_batch(self, batch, epoch, validate=False):
        self._sensor_validate = validate
        return super().train_on_batch(batch, epoch, validate=validate)

    def _compute_losses(self, predictions, batch):
        losses = OrderedDict(super()._compute_losses(predictions, batch))
        cfg = self.algo_config.sensor
        mix, radius = float(cfg.mix), float(cfg.radius)
        if not 0 <= mix <= 1 or radius < 0:
            raise ValueError('sensor.mix must be in [0,1] and radius nonnegative')
        losses['clean_action_loss'] = losses['action_loss']
        losses['noisy_action_loss'] = losses['action_loss'].new_zeros(())
        if mix == 0 or radius == 0 or getattr(self, '_sensor_validate', False):
            return losses
        eef_key, object_key = str(cfg.eef_key), str(cfg.object_key)
        obs = batch['obs']
        if obs[eef_key].shape[-1] != 3 or obs[object_key].shape[-1] != 10:
            raise ValueError('sensor augmentation requires Lift EEF (3) and object (10)')
        if self.global_config.train.hdf5_normalize_obs:
            raise ValueError('sensor radius is in metres; normalized inputs require a separate conversion')
        if not hasattr(self, '_sensor_generator'):
            self._sensor_generator = torch.Generator(device=obs[eef_key].device)
            self._sensor_generator.manual_seed(int(cfg.seed))
        delta = torch.randn(obs[eef_key].shape, device=obs[eef_key].device,
                            dtype=obs[eef_key].dtype, generator=self._sensor_generator)
        delta = radius * F.normalize(delta, dim=-1, eps=1e-12)
        noisy_obs = perturb_lift_observation(obs, eef_key, object_key, delta)
        noisy_action = self.nets['policy'](obs_dict=noisy_obs, goal_dict=batch['goal_obs'])
        noisy_losses = super()._compute_losses({'actions': noisy_action}, batch)
        losses['noisy_action_loss'] = noisy_losses['action_loss']
        losses['action_loss'] = (1-mix)*losses['clean_action_loss'] + mix*losses['noisy_action_loss']
        return losses

    def log_info(self, info):
        log = super().log_info(info)
        log['Clean_Action_Loss'] = info['losses']['clean_action_loss'].item()
        log['Noisy_Action_Loss'] = info['losses']['noisy_action_loss'].item()
        return log
