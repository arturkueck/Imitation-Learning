import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import torch
import night
from policy import FixedCompletion
from replay import select_cases


class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(10, 8), torch.nn.SiLU(), torch.nn.Linear(8, 5))
    def forward(self, x, phase):
        y = self.net(x)
        return y[:, :4].tanh(), y[:, 4]


class CompletionTests(unittest.TestCase):
    def test_completion_function_stays_exact_despite_shared_trunk_updates(self):
        torch.manual_seed(1)
        actor = Tiny()
        model = FixedCompletion(actor, actor)
        x, phase = torch.randn(32, 10), torch.zeros(32, dtype=torch.long)
        action0, completion0 = model(x, phase)
        optimizer = torch.optim.AdamW(actor.parameters(), lr=.1)
        for _ in range(3):
            action, _ = model(x, phase)
            optimizer.zero_grad(set_to_none=True)
            action.square().mean().backward()
            optimizer.step()
        action1, completion1 = model(x, phase)
        self.assertFalse(torch.equal(action0, action1))
        torch.testing.assert_close(completion0, completion1, rtol=0, atol=0)
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in model.reference.parameters()))
        model.train()
        self.assertFalse(model.reference.training)

    def test_swapping_only_changes_requested_outputs(self):
        actor, reference = Tiny(), Tiny()
        x, phase = torch.randn(12, 10), torch.zeros(12, dtype=torch.long)
        combined = FixedCompletion(actor, reference)
        action, completion = combined(x, phase)
        torch.testing.assert_close(action, actor(x, phase)[0], rtol=0, atol=0)
        torch.testing.assert_close(completion, reference(x, phase)[1], rtol=0, atol=0)

    def test_fixed_checkpoint_restores_live_and_reference_separately(self):
        base, _, _ = night.runtime.libraries()
        actor, reference = Tiny(), Tiny()
        model = FixedCompletion(actor, reference)
        optimizer = torch.optim.AdamW(actor.parameters())
        with tempfile.TemporaryDirectory(dir=night.HERE) as directory:
            out = Path(directory)
            (out/'model').mkdir()
            member = dict(name='model', model=model, optimizer=optimizer, update=30003,
                          seed=1, arm='mixed', parent={}, sampler_sha256='sample')
            night.fixed_save(out, member, dict(start_update=30000), {}, True)
            ck = torch.load(out/'model/latest.pth', map_location='cpu', weights_only=False)
        def restore_fake(ck, cfg, device):
            live = Tiny()
            live.load_state_dict(ck['model'])
            opt = torch.optim.AdamW(live.parameters())
            opt.load_state_dict(ck['optimizer'])
            return live, opt
        with patch.object(night, 'original_restore', side_effect=restore_fake):
            restored, _ = night.fixed_restore(ck, {}, 'cpu')
        x, p = torch.randn(7, 10), torch.zeros(7, dtype=torch.long)
        for a, b in zip(model(x, p), restored(x, p)):
            torch.testing.assert_close(a, b, rtol=0, atol=0)
        self.assertTrue(ck['completion_frozen'] and ck['technical_only'])

    def test_historical_examples_have_all_outcomes_and_deterministic_selection(self):
        before = [dict(seed=i, success=v, initial_sha256=str(i)) for i, v in enumerate((False, True, False, True))]
        after = [dict(seed=i, success=v, initial_sha256=str(i)) for i, v in enumerate((True, False, False, True))]
        cases = select_cases(before, after)
        self.assertEqual({r['group'] for r in cases}, {'gain', 'loss', 'both_fail', 'both_success'})
        self.assertEqual(cases, select_cases(before, after))
        after[0]['initial_sha256'] = 'changed'
        with self.assertRaises(ValueError):
            select_cases(before, after)

    def test_control_budget_and_new_confirmation_namespace(self):
        cfg = night.read(night.EXT.with_name('axis_bc_20261110')/'ready_001/config.json')
        plan = night.read(night.HERE/'config.json')
        source = night.read(night.EXT/'ready_001/plan.json')
        night.validate(plan, cfg, source)
        changed = copy.deepcopy(plan)
        changed['sampler_seed_offset'] += 1
        with self.assertRaises(ValueError):
            night.validate(changed, cfg, source)
        changed = copy.deepcopy(plan)
        changed['confirmation_seeds'] = source['confirmation_seeds']
        with self.assertRaises(ValueError):
            night.validate(changed, cfg, source)

    def test_supervisor_uses_single_deadline_for_diagnosis_training_and_test(self):
        with tempfile.TemporaryDirectory(dir=night.HERE) as directory:
            out = Path(directory)
            night.write(out/'status.json', dict(state='READY'))
            night.write(out/'plan.json', dict(wall_clock_cap_seconds=36000, shutdown_reserve_seconds=120))
            calls = []
            def spawn(command, **kwargs):
                calls.append(command)
                if command[3] == 'diagnose':
                    night.write(out/'diagnostic_status.json', dict(state='DIAGNOSIS_COMPLETE'))
                else:
                    night.write(out/'status.json', dict(state='TRAINING_COMPLETE' if command[3] == 'run' else 'COMPLETE'))
                worker = MagicMock(pid=1)
                worker.wait.return_value = 0
                worker.poll.return_value = 0
                return worker
            with patch.object(night.runtime, 'verify'), patch.object(night.subprocess, 'Popen', side_effect=spawn), patch.object(night.time, 'time', return_value=1000):
                night.supervise(out, 'cpu')
            self.assertEqual([c[3] for c in calls], ['diagnose', 'run', 'test'])
            self.assertEqual(len({c[-1] for c in calls}), 1)
            final = night.read(out/'supervisor_status.json')
            self.assertEqual(final['state'], 'COMPLETE')
            self.assertEqual(final['hard_deadline']-final['started_unix'], 36000)
            self.assertEqual(final['hard_deadline']-final['deadline'], 120)
            self.assertEqual(float(calls[0][-1]), final['deadline'])


if __name__ == '__main__':
    unittest.main()
