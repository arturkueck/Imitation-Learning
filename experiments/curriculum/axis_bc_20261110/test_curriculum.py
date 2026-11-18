import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

import core


class CurriculumTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((Path(__file__).with_name('config.json')).read_text())
        self.cfg.update(updates=12, batch_size=8, evaluation_updates=[12])
        for stage, end in zip(self.cfg['stages'], [4, 8, 12]):
            stage['end_update'] = end
        p = np.repeat(np.arange(7), 4)
        a = np.tile([[.8, 0, 0, -1], [.8, .8, 0, 1], [.4, .4, .8, 1], [0, 0, .8, -1]], (7, 1)).astype('float32')
        self.data = (np.zeros((28, 10), 'float32'), a, p, np.zeros(28, 'float32'))

    def test_exact_exposure_matching_and_reproducibility(self):
        batches, permutation = core.schedule(self.data, self.cfg, 1)
        again, order = core.schedule(self.data, self.cfg, 1)
        np.testing.assert_array_equal(batches, again)
        np.testing.assert_array_equal(permutation, order)
        self.assertEqual(sorted(permutation.tolist()), list(range(12)))
        np.testing.assert_array_equal(np.bincount(batches.ravel(), minlength=28),
                                      np.bincount(batches[permutation].ravel(), minlength=28))
        self.assertFalse(np.array_equal(batches, batches[permutation]))

    def test_stage_focus_and_full_actions_preserved(self):
        batches, _ = core.schedule(self.data, self.cfg, 2)
        self.assertTrue(np.isin(batches[:4, :6], core.pools(self.data, .1)['X']).all())
        self.assertTrue(np.isin(batches[4:8, :6], core.pools(self.data, .1)['XY']).all())
        # Read-only partitioning cannot replace Y/Z or gripper labels with zeros.
        original = self.data[1].copy()
        core.schedule(self.data, self.cfg, 3)
        np.testing.assert_array_equal(self.data[1], original)

    def test_empty_pool_fails_instead_of_changing_experiment(self):
        empty = list(self.data)
        empty[1] = empty[1].copy()
        empty[1][:, 2] = .8
        with self.assertRaises(ValueError):
            core.schedule(empty, self.cfg, 1)

    def test_nonfinite_loss_blocks_optimizer(self):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.layer = torch.nn.Linear(10, 5)

            def forward(self, x, p):
                out = self.layer(x)
                return out[:, :4], out[:, 4]

        model = Model()
        opt = torch.optim.AdamW(model.parameters())
        corrupt = list(self.data)
        corrupt[1] = corrupt[1].copy()
        corrupt[1][0, 0] = np.nan
        before = copy.deepcopy(model.state_dict())
        with self.assertRaises(FloatingPointError):
            core.step(model, opt, corrupt, np.array([0]), torch.ones(7), self.cfg, 1, 'cpu')
        for key, value in model.state_dict().items():
            torch.testing.assert_close(value, before[key], rtol=0, atol=0)

    def test_deadline_and_stop(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory)
            with self.assertRaises(TimeoutError):
                core.check_stop(path, 0)
            (path / 'STOP').touch()
            with self.assertRaises(InterruptedError):
                core.check_stop(path, float('inf'))

    def test_split_and_stage_validation(self):
        core.validate_config(self.cfg)
        bad = copy.deepcopy(self.cfg)
        bad['final_seeds'] = bad['development_seeds']
        with self.assertRaises(ValueError):
            core.validate_config(bad)
        bad = copy.deepcopy(self.cfg)
        bad['stages'][1]['end_update'] = bad['updates']+1
        with self.assertRaises(ValueError):
            core.validate_config(bad)


if __name__ == '__main__':
    unittest.main()
