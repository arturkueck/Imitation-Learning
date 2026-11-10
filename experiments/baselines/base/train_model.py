"""Baseline-Training aus einer explizit angegebenen robomimic-Konfiguration.

Arbeitskopie von square/scripts/train_model.py. Die Modell- und Losswahl
bleibt in der Konfiguration; --help startet weder Simulation noch Training.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()

    import runtime  # Registers local tasks and configures the Windows renderer.
    import torch
    from robomimic.config import config_factory
    from robomimic.utils.torch_utils import get_torch_device
    from robomimic.scripts.train import train

    torch.set_num_threads(4)
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    config = config_factory(cfg['algo_name'], dic=cfg)
    config.lock()
    # Preserve the original RNN-GMM validation correction: supervised NLL
    # must use the learned variance, while rollout configs retain low noise.
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
        print('GMM_VALIDATION_USES_LEARNED_VARIANCE', flush=True)
    # The upstream CLI can catch errors and still return exit code zero.
    train(config, device=get_torch_device(try_to_use_cuda=config.train.cuda), resume=args.resume)


if __name__ == '__main__':
    main()
