"""Scientific invariants and a real, bounded process-tree deadline test."""
from datetime import datetime
from pathlib import Path
import copy
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


p = module('matched_budget_test_subject', 'pipeline.py')
m = module('matched_budget_monitor_test_subject', 'monitor.py')


class ContractTests(unittest.TestCase):
    def test_process_identity_checks_creation_time_and_unknown_pid(self):
        import psutil
        created = psutil.Process().create_time()
        self.assertTrue(m.identity(os.getpid(), created))
        self.assertFalse(m.identity(os.getpid(), created-100))
        self.assertIsNone(m.identity(-1, 0))

    def test_absolute_deadline_cannot_be_extended_by_late_start(self):
        plan = p.read(p.HERE/'config.json')
        hard = datetime.fromisoformat(plan['absolute_deadline']).timestamp()
        self.assertEqual(p.deadline_for(plan, hard-1000), hard-plan['exit_reserve_seconds'])
        self.assertLess(p.deadline_for(plan, hard+1), hard+1)

    def test_every_new_split_and_confirmation_is_disjoint(self):
        plan = p.read(p.HERE/'config.json')
        p.validate(plan)
        plan['blocks'][1]['train_seeds'] = plan['blocks'][0]['validation_seeds']
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            p.validate(plan)

    def test_unique_label_budget_preserves_terminal_and_family_alignment(self):
        for left in range(2, 45):
            for right in range(2, 45):
                a, b = p.matched_indices(left, right, 32)
                self.assertEqual(len(a), len(b))
                self.assertEqual(len(set(a)), len(a))
                self.assertEqual(len(set(b)), len(b))
                self.assertEqual((a[-1], b[-1]), (left-1, right-1))
                self.assertTrue(all(i < left-1 for i in a[:-1]))
                self.assertTrue(all(i < right-1 for i in b[:-1]))

    def test_paired_outcomes_keep_all_starts_in_denominator(self):
        plan = p.read(p.HERE/'config.json')
        plan.update(blocks=plan['blocks'][:1], models=plan['models'][:1], development_seeds=[1, 2], confirmation_seeds=[3, 4])
        rows = [dict(panel=panel, block=plan['blocks'][0]['id'], model=plan['models'][0], policy=policy, seed=seed,
                     initial_sha256=str(seed), success=policy == 'targeted' and seed % 2 == 0)
                for panel, starts in (('development', [1, 2]), ('confirmation', [3, 4])) for policy in plan['policies'] for seed in starts]
        summary = p.paired_summary(rows, plan)
        result = summary['confirmation'][plan['blocks'][0]['id']][plan['models'][0]]['targeted']
        self.assertEqual(result['n'], 2)
        self.assertEqual(result['versus_standard'], dict(gains=1, losses=0))

    def test_collector_heldout_parent_cannot_supply_labels(self):
        plan = p.read(p.HERE/'config.json')
        plan['blocks'][0]['collector_models'][0] = plan['blocks'][0]['heldout_model']
        with self.assertRaisesRegex(ValueError, 'Collector-heldout'):
            p.validate(plan)

    def test_collector_assignment_is_balanced_and_prespecified(self):
        import numpy as np
        plan = p.read(p.HERE/'config.json')
        for block in plan['blocks']:
            for split in ('train', 'validation'):
                allocation = p.assignments(block, split, plan, np)
                self.assertEqual(allocation, p.assignments(block, split, plan, np))
                counts = [sum(v['model'] == model for v in allocation.values()) for model in block['collector_models']]
                self.assertLessEqual(max(counts)-min(counts), 1)
                self.assertNotIn(block['heldout_model'], {v['model'] for v in allocation.values()})

    def test_long_trajectories_do_not_gain_sampling_mass(self):
        import numpy as np
        families = np.array([1]*3+[2]*40)
        selected = p.family_uniform_indices(families, (10000, 2), np.random.default_rng(21), np)
        self.assertLess(abs(float((families[selected] == 1).mean())-.5), .02)

    def primary_rows(self):
        plan = p.read(p.HERE/'config.json')
        plan['confirmation_seeds'] = [1, 8]
        rows = [dict(panel='confirmation', block=block['id'], model=block['heldout_model'], policy=policy, seed=seed,
                     initial_sha256=str(seed), success=policy == 'targeted' and seed % 2 == 0)
                for block in plan['blocks'] for policy in plan['policies'] for seed in p.span(plan['confirmation_seeds'])]
        return plan, rows

    def test_bootstrap_keeps_same_scene_across_all_replicates_together(self):
        plan, rows = self.primary_rows()
        repeated = p.analysis.primary_analysis(rows, plan)
        plan['blocks'] = plan['blocks'][:1]
        single = p.analysis.primary_analysis([r for r in rows if r['block'] == plan['blocks'][0]['id']], plan)
        self.assertEqual(repeated['paired_scene_bootstrap']['interval_percentage_points'], single['paired_scene_bootstrap']['interval_percentage_points'])
        self.assertEqual(repeated['unique_confirmation_scene_families'], 8)

    def test_primary_cannot_be_changed_by_strong_secondary_outcomes(self):
        plan, rows = self.primary_rows()
        before = p.analysis.primary_analysis(rows, plan)
        extras = [dict(r, model=plan['blocks'][0]['collector_models'][0], success=True) for r in rows if r['block'] == plan['blocks'][0]['id']]
        self.assertEqual(before, p.analysis.primary_analysis(rows+extras, plan))

    def test_incomplete_or_duplicate_primary_has_no_positive_claim(self):
        plan, rows = self.primary_rows()
        self.assertFalse(p.analysis.primary_analysis(rows[:-1], plan)['complete'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            p.analysis.primary_analysis(rows+[rows[0]], plan)

    def test_technical_results_never_become_scientific_evidence(self):
        plan, rows = self.primary_rows()
        plan['technical_only'] = True
        self.assertEqual(p.analysis.primary_analysis(rows, plan)['decision'], 'TECHNICAL_ONLY_NO_SCIENTIFIC_CLAIM')

    def test_changed_frozen_checkpoint_is_rejected(self):
        base, _, _ = p.h.libraries()
        with tempfile.TemporaryDirectory(dir=p.HERE) as folder:
            target = Path(folder)
            checkpoint = target/'component.pth'
            checkpoint.write_bytes(b'frozen checkpoint')
            p.write(target/'frozen_components.json', dict(components={str(checkpoint.relative_to(p.ROOT)):base.sha(checkpoint)}))
            p.verify_frozen(target)
            checkpoint.write_bytes(b'changed checkpoint')
            with self.assertRaisesRegex(ValueError, 'Component changed'):
                p.verify_frozen(target)

    def test_incremental_log_offset_partial_line_and_rotation(self):
        with tempfile.TemporaryDirectory(dir=p.HERE) as folder:
            log = Path(folder)/'worker.log'
            log.write_bytes(b'normal\nRuntimeError: one\nValueError: incom')
            state = {}
            self.assertEqual(m.new_errors(log, state), ['RuntimeError: one'])
            self.assertEqual(m.new_errors(log, state), [])
            with log.open('ab') as stream:
                stream.write(b'plete\n')
            self.assertEqual(m.new_errors(log, state), ['ValueError: incomplete'])
            log.unlink()
            log.write_bytes(b'CUDA out of memory\n')
            self.assertEqual(m.new_errors(log, state), ['CUDA out of memory'])

    def test_watchdog_kills_own_worker_and_child(self):
        import psutil
        watchdog = p.h.module('matched_deadline_test_watchdog', p.HERE.parent/'grasp_phase_ablation_v1/pipeline.py')
        with tempfile.TemporaryDirectory(dir=p.HERE) as folder:
            marker = Path(folder)/'child.pid'
            code = "import subprocess,sys,time; from pathlib import Path; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(120)"
            process = subprocess.Popen([sys.executable, '-c', code, str(marker)])
            try:
                limit = time.time()+10
                while not marker.exists() and time.time() < limit:
                    time.sleep(.05)
                self.assertTrue(marker.exists())
                child = psutil.Process(int(marker.read_text()))
                watchdog.stop_worker(process)
                self.assertIsNotNone(process.poll())
                child.wait(timeout=3)
                self.assertFalse(child.is_running())
            finally:
                if process.poll() is None:
                    watchdog.stop_worker(process)


if __name__ == '__main__':
    unittest.main()
