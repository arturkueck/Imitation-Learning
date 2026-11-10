import runtime
import json
import sys
import torch
from robomimic.config import config_factory
from robomimic.utils.torch_utils import get_torch_device
from robomimic.scripts.train import train

torch.set_num_threads(4)
cfg = json.loads(open(sys.argv[1], encoding='utf-8').read())
config = config_factory(cfg['algo_name'], dic=cfg)
config.lock()
# robomimic's RNN-GMM also applies low-noise rollout sampling in eval mode
# during validation. NLL must use the learned variance, not fixed 1e-4 noise.
# Scope this override to supervised forward passes in this training process.
# Saved configs retain low_noise_eval=True for independent policy rollouts.
if config.algo_name == 'bc' and config.algo.gmm.enabled and config.algo.rnn.enabled:
    from robomimic.algo.bc import BC_RNN_GMM
    original_forward = BC_RNN_GMM._forward_training
    def likelihood_forward(self, batch):
        actor = self.nets['policy']
        previous = actor.low_noise_eval
        actor.low_noise_eval = False
        try:
            return original_forward(self, batch)
        finally:
            actor.low_noise_eval = previous
    BC_RNN_GMM._forward_training = likelihood_forward
    print('GMM_VALIDATION_USES_LEARNED_VARIANCE',flush=True)
# Call train directly: upstream CLI catches exceptions and can return exit code 0.
train(config, device=get_torch_device(try_to_use_cuda=config.train.cuda), resume='--resume' in sys.argv[2:])
