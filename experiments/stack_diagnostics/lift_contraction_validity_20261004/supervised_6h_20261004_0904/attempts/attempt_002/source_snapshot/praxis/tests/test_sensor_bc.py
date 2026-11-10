"""BC parity, independent randomness and meaningful noisy-loss gradients."""
import torch

import robomimic_ext  # noqa: F401
from robomimic.algo import algo_factory
from robomimic.config import config_factory
from robomimic.utils import obs_utils as OU


SHAPES = {'robot0_eef_pos': (3,), 'robot0_eef_quat': (4,), 'robot0_gripper_qpos': (2,), 'object': (10,)}


def model(name, mix=.5, radius=.005):
    cfg = config_factory(name)
    with cfg.values_unlocked():
        cfg.algo.actor_layer_dims = [32,32]
        cfg.observation.modalities.obs.low_dim = list(SHAPES)
        cfg.train.hdf5_normalize_obs = False
        if name == 'bc_sensor':
            cfg.algo.sensor.mix, cfg.algo.sensor.radius = mix, radius
    OU.initialize_obs_utils_with_config(cfg)
    torch.manual_seed(53)
    return algo_factory(name, cfg, SHAPES, 7, torch.device('cpu'))


def batch():
    generator = torch.Generator().manual_seed(92)
    obs = {k: torch.randn((8,)+s,generator=generator) for k,s in SHAPES.items()}
    obs['object'][:,-3:] = obs['object'][:,:3]-obs['robot0_eef_pos']
    return {'obs':obs, 'goal_obs':None, 'actions':torch.randn(8,7,generator=generator)}


def test_zero_mix_exact_bc_parameter_updates_and_randomness():
    bc, sensor = model('bc'), model('bc_sensor', mix=0)
    b = batch()
    for epoch in range(1,4):
        before = torch.random.get_rng_state().clone()
        a = bc.train_on_batch(b,epoch)
        bc_rng = torch.random.get_rng_state().clone()
        torch.random.set_rng_state(before)
        s = sensor.train_on_batch(b,epoch)
        assert torch.equal(torch.random.get_rng_state(),bc_rng)
        assert torch.equal(a['losses']['action_loss'],s['losses']['action_loss'])
        for x,y in zip(bc.nets.parameters(),sensor.nets.parameters()):
            assert torch.equal(x,y)


def test_sensor_noise_keeps_global_rng_and_generates_finite_distinct_gradients():
    bc, sensor = model('bc'), model('bc_sensor')
    b = batch()
    original = {k:v.clone() for k,v in b['obs'].items()}
    state = torch.random.get_rng_state().clone()
    a = bc.train_on_batch(b,1)
    s = sensor.train_on_batch(b,1)
    assert torch.equal(torch.random.get_rng_state(),state)
    assert torch.isfinite(s['losses']['action_loss'])
    assert s['losses']['noisy_action_loss'] != s['losses']['clean_action_loss']
    assert any(not torch.equal(x,y) for x,y in zip(bc.nets.parameters(),sensor.nets.parameters()))
    assert all(torch.isfinite(x).all() for x in sensor.nets.parameters())
    for key in original:
        assert torch.equal(original[key],b['obs'][key])
    validation = sensor.train_on_batch(b,1,validate=True)
    assert validation['losses']['noisy_action_loss'] == 0
    assert validation['losses']['action_loss'] == validation['losses']['clean_action_loss']
