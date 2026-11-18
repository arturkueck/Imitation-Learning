import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

import pipeline
from policy import effective_steps, make_policy


class PipelineTests(unittest.TestCase):
    def test_adapter_changes_only_final_release_input_and_preserves_real_counter(self):
        class FakePolicy:
            def __init__(self, model, historical, threshold):
                self.phase, self.steps, self.anchor = 6, 16, None
            def action(self, obs, target, source):
                used = self.steps
                self.steps += 1
                return used, self.phase, 0
        base = SimpleNamespace(DevicePolicy=FakePolicy)
        historical = SimpleNamespace(vector=lambda o, a, steps: steps)
        stage = [2]
        policy = make_policy(base, historical, None, .8, lambda: stage[0], 17)
        self.assertEqual([policy.action(None, [], [])[0] for _ in range(5)], [16,17,17,17,17])
        self.assertEqual(policy.steps, 21)
        stage[0] = 1
        self.assertEqual(policy.action(None, [], [])[0], 21)
        self.assertFalse(policy.intervened)
        stage[0], policy.phase = 2, 5
        self.assertEqual(policy.action(None, [], [])[0], 22)
        self.assertEqual(effective_steps(6, 2, 1000, 17), 17)
        with self.assertRaises(ValueError):
            effective_steps(6, 2, -1, 17)

    def test_pairing_requires_identical_history_before_input_intervention(self):
        original = dict(initial_sha256='scene', first_intervention_frame=None, trajectory_sha256='old',
                        success=False, frames=100, _prefixes=['0','1','2'])
        bounded = dict(initial_sha256='scene', first_intervention_frame=2, history_before_intervention='2',
                       trajectory_sha256='new', success=True, frames=60)
        self.assertTrue(pipeline.compare_pair(original, bounded)['gain'])
        bounded['history_before_intervention'] = 'different'
        with self.assertRaises(ValueError):
            pipeline.compare_pair(original, bounded)

    def test_negative_control_must_be_bitwise_identical(self):
        original = dict(initial_sha256='scene', trajectory_sha256='same', success=True, frames=80, _prefixes=[])
        bounded = dict(original, first_intervention_frame=None)
        self.assertTrue(pipeline.compare_pair(original, bounded, True)['negative_identical'])
        bounded['success'] = False
        with self.assertRaises(ValueError):
            pipeline.compare_pair(original, bounded, True)

    def test_namespaces_and_no_accidental_training(self):
        plan = pipeline.read(pipeline.HERE/'config.json')
        cfg = pipeline.read(pipeline.SOURCE/'ready_001/base_config.json')
        previous = pipeline.read(pipeline.SOURCE/'ready_001/plan.json')
        pipeline.validate(plan, cfg, previous)
        changed = copy.deepcopy(plan)
        changed['confirmation_seeds'] = previous['confirmation_seeds']
        with self.assertRaises(ValueError):
            pipeline.validate(changed, cfg, previous)
        changed = copy.deepcopy(plan)
        changed['optimizer_updates'] = 1
        with self.assertRaises(ValueError):
            pipeline.validate(changed, cfg, previous)

    def test_review_gate_is_false_for_partial_data_and_has_seed_regression_limit(self):
        plan = pipeline.read(pipeline.HERE/'config.json')
        cases = {}
        for history in ('mixed','curriculum'):
            for seed in (1,2,3):
                rows = [dict(original=dict(success=i<50), bounded_clock=dict(success=i<60),
                             gain=50 <= i < 60, loss=False, negative_identical=False) for i in range(100)]
                cases[f'{history}_seed{seed}'] = {'3': rows, '2': [dict(original=dict(success=True),
                    bounded_clock=dict(success=True), gain=False, loss=False, negative_identical=True)]}
        self.assertFalse(pipeline.summarize(cases, plan, False)['candidate_for_review'])
        self.assertTrue(pipeline.summarize(cases, plan, True)['candidate_for_review'])
        self.assertFalse(pipeline.summarize({'mixed_seed1': {'3': []}}, plan, False)['candidate_for_review'])
        cases['mixed_seed1']['3'] = [dict(original=dict(success=i<50), bounded_clock=dict(success=i<40),
               gain=False, loss=40 <= i < 50, negative_identical=False) for i in range(100)]
        self.assertFalse(pipeline.summarize(cases, plan, True)['candidate_for_review'])

    def test_supervisor_keeps_shutdown_inside_ten_hours(self):
        with tempfile.TemporaryDirectory(dir=pipeline.HERE) as directory:
            out = Path(directory)
            pipeline.write(out/'status.json', dict(state='READY'))
            pipeline.write(out/'plan.json', dict(wall_clock_cap_seconds=36000, shutdown_reserve_seconds=120))
            worker = MagicMock(pid=123)
            worker.wait.return_value = 0
            worker.poll.return_value = 0
            def spawn(command, **kwargs):
                pipeline.write(out/'status.json', dict(state='COMPLETE'))
                self.assertEqual(float(command[-1]), 36880)
                return worker
            with patch.object(pipeline, 'verify'), patch.object(pipeline.subprocess, 'Popen', side_effect=spawn), patch.object(pipeline.time, 'time', return_value=1000):
                pipeline.supervise(out, 'cpu')
            worker.wait.assert_called_once_with(timeout=36000)
            result = pipeline.read(out/'supervisor_status.json')
            self.assertEqual(result['state'], 'COMPLETE')
            self.assertEqual(result['hard_deadline']-result['deadline'], 120)
            self.assertFalse(result['sleep_prevention_active'])


if __name__ == '__main__':
    unittest.main()
