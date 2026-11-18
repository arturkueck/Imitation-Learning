import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import night


class NightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.torch, cls.np = night.libraries()
        cls.cfg = night.read(night.BASE/'ready_001/config.json')
        cls.plan = night.read(night.HERE/'config.json')

    def test_namespaces_and_continuation_budget(self):
        night.validate(self.plan, self.cfg)
        plan = copy.deepcopy(self.plan)
        plan['confirmation_seeds'] = self.cfg['final_seeds']
        with self.assertRaises(ValueError):
            night.validate(plan, self.cfg)
        plan = copy.deepcopy(self.plan)
        plan['start_update'] = 0
        with self.assertRaises(ValueError):
            night.validate(plan, self.cfg)

    def test_batches_are_deterministic_and_cover_all_phases(self):
        np = self.np
        data = (np.zeros((70, 10), 'float32'), np.zeros((70, 4), 'float32'),
                np.repeat(np.arange(7), 10), np.zeros(70, 'float32'))
        a = night.common_batches(data, 100, 64, 600001)
        b = night.common_batches(data, 100, 64, 600001)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(set(data[2][a.ravel()].tolist()), set(range(7)))
        self.assertTrue((a >= 0).all() and (a < 70).all())

    def test_optimizer_restore_preserves_the_next_cpu_update(self):
        # Exercise real saved AdamW moments with a small deterministic CPU net.
        torch = self.torch
        class Tiny(torch.nn.Module):
            def __init__(self, width=128):
                super().__init__()
                self.layer = torch.nn.Linear(10, 5)
            def forward(self, x, phase):
                result = self.layer(x)
                return result[:, :4].tanh(), result[:, 4]
        from types import SimpleNamespace
        fake_backend = SimpleNamespace(native=SimpleNamespace(historical=SimpleNamespace(PhaseNet=Tiny)))
        model = Tiny()
        opt = torch.optim.AdamW(model.parameters(), lr=self.cfg['lr'], weight_decay=self.cfg['weight_decay'])
        data = (self.np.ones((7, 10), 'float32'), self.np.ones((7, 4), 'float32')*.2,
                self.np.arange(7), self.np.zeros(7, 'float32'))
        ids = self.np.arange(7)
        weights = torch.ones(7)
        self.base.step(model, opt, data, ids, weights, self.cfg, 30000, 'cpu')
        checkpoint = copy.deepcopy(dict(model=model.state_dict(), optimizer=opt.state_dict()))
        with patch.object(self.base, 'backend', return_value=fake_backend):
            restored, restored_opt = night.restore(checkpoint, self.cfg, 'cpu')
        self.base.step(model, opt, data, ids, weights, self.cfg, 30001, 'cpu')
        self.base.step(restored, restored_opt, data, ids, weights, self.cfg, 30001, 'cpu')
        for key, value in model.state_dict().items():
            torch.testing.assert_close(value, restored.state_dict()[key], rtol=0, atol=0)
        self.assertEqual(restored_opt.state_dict()['state'][0]['step'], opt.state_dict()['state'][0]['step'])

    def test_completion_diagnostics_count_false_switches(self):
        torch, np = self.torch, self.np
        class Fixed(torch.nn.Module):
            def forward(self, x, phase):
                return torch.zeros((len(x), 4)), x[:, 0]
        # In every supervised phase: one TP, FP, FN, TN.
        phase = np.repeat(np.arange(6), 4)
        x = np.zeros((24, 10), 'float32')
        x[:, 0] = np.tile([10, 10, -10, -10], 6)
        data = (x, np.zeros((24, 4), 'float32'), phase, np.tile([1, 0, 1, 0], 6).astype('float32'))
        result = night.completion_metrics(Fixed(), data, self.cfg, 'cpu', torch.ones(7))
        for metrics in result['phases'].values():
            self.assertEqual((metrics['tp'], metrics['fp'], metrics['fn']), (1, 1, 1))
            self.assertEqual(metrics['precision'], .5)
            self.assertEqual(metrics['recall'], .5)

    def test_pairing_fails_on_changed_start(self):
        hashes = {}
        night.check_pairing(hashes, 3, dict(rows=[dict(initial_sha256='same')]))
        with self.assertRaises(ValueError):
            night.check_pairing(hashes, 3, dict(rows=[dict(initial_sha256='different')]))

    def test_monitor_rotation_and_partial_append(self):
        with tempfile.TemporaryDirectory(dir=night.HERE) as directory:
            out = Path(directory)
            night.write(out/'status.json', dict(state='READY', updated_unix=0, completed_round=30000))
            log = out/'metrics.jsonl'
            log.write_text('')
            night.status(out)
            log.write_text(json.dumps(dict(loss=.1, gradient_norm=.2))+'\n'+ '{"loss":')
            night.status(out)
            offset = night.read(out/'monitor_state.json')['offset']
            self.assertEqual(offset, log.read_bytes().index(b'\n')+1)
            log.replace(out/'metrics.old.jsonl')
            log.write_text(json.dumps(dict(loss=float('nan'), gradient_norm=.2))+'\n')
            night.status(out)
            self.assertTrue(night.read(out/'monitor_state.json')['issues'])

    def test_supervisor_shares_one_deadline_and_stops_after_partial_training(self):
        from unittest.mock import MagicMock
        for training_state in ('TRAINING_COMPLETE', 'PARTIAL_TIME_CAP'):
            with self.subTest(training_state=training_state), tempfile.TemporaryDirectory(dir=night.HERE) as directory:
                out = Path(directory)
                night.write(out/'status.json', dict(state='READY'))
                night.write(out/'plan.json', dict(wall_clock_cap_seconds=28800))
                commands = []
                def spawn(command, **kwargs):
                    commands.append(command)
                    phase = command[3]
                    night.write(out/'status.json', dict(state=training_state if phase == 'run' else 'COMPLETE'))
                    worker = MagicMock(pid=123)
                    worker.wait.return_value = 0
                    worker.poll.return_value = 0
                    return worker
                with patch.object(night, 'verify'), patch.object(night.subprocess, 'Popen', side_effect=spawn):
                    night.supervise(out, 'cpu')
                supervisor = night.read(out/'supervisor_status.json')
                if training_state == 'TRAINING_COMPLETE':
                    self.assertEqual(len(commands), 2)
                    self.assertEqual(commands[0][-1], commands[1][-1])
                    self.assertEqual(supervisor['state'], 'COMPLETE')
                else:
                    self.assertEqual(len(commands), 1)
                    self.assertEqual(supervisor['state'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
