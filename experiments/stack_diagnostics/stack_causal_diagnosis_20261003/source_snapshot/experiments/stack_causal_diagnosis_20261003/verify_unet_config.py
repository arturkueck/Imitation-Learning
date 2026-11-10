"""Separate regression check: config forwarding, unchanged existing defaults."""
import ast, json, sys, hashlib
from pathlib import Path
import torch
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
from robomimic.models.diffusion_policy_nets import ConditionalUnet1D
from robomimic.config import config_factory
from robomimic.algo import algo_factory
from robomimic.utils import obs_utils

torch.set_num_threads(4)
source=ROOT/'praxis/upstream/robomimic/robomimic/algo/diffusion_policy.py'
cfg=json.loads((ROOT/'experiments/stack_normalization_20261001/C/diffusion/seed_1/config.json').read_text())
defaults=cfg['algo']['unet'];kwargs={k:v for k,v in defaults.items() if k!='enabled'}
torch.manual_seed(111);old=ConditionalUnet1D(7,30)
torch.manual_seed(111);new=ConditionalUnet1D(7,30,**kwargs)
assert list(old.state_dict())==list(new.state_dict())
assert all(torch.equal(v,new.state_dict()[k]) for k,v in old.state_dict().items())
del old,new
# Real algo creation with different, small dimensions verifies that the forwarding is effective.
cfg['algo']['unet'].update(diffusion_step_embed_dim=16,down_dims=[16,32,64],kernel_size=3,n_groups=4)
cfg['algo']['optim_params']['policy'].update(num_train_batches=100,num_epochs=300)
c=config_factory('diffusion_policy',dic=cfg);obs_utils.initialize_obs_utils_with_config(c)
model=algo_factory('diffusion_policy',config=c,obs_key_shapes={'object':(6,),'robot0_eef_pos':(3,),'robot0_eef_quat':(4,),'robot0_gripper_qpos':(2,)},ac_dim=7,device=torch.device('cpu'))
net=model.nets['policy']['noise_pred_net']
assert net.diffusion_step_encoder[1].in_features==16
assert net.down_modules[0][0].blocks[0].block[0].out_channels==16
assert net.down_modules[0][0].blocks[0].block[0].kernel_size==(3,)
assert net.down_modules[0][0].blocks[0].block[1].num_groups==4
result=dict(passed=True,default_initial_weights_bit_equal=True,nondefault_algo_constructor_honors_config=True,current_experiment_behavior_changed=False,modified_file=str(source.relative_to(ROOT)),modified_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(OUT/'unet_config_fix_verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
