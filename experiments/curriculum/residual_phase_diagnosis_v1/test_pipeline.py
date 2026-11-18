"""Meaningful guards for the frozen diagnostic interventions."""
from pathlib import Path
from types import SimpleNamespace
import copy
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('residual_test_subject',Path(__file__).with_name('pipeline.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class DiagnosticTests(unittest.TestCase):
    def test_cases_are_fixed_opened_failures_and_distinct_success_controls(self):
        plan = p.read(p.HERE/'config.json')
        cases = p.select_cases(plan)
        self.assertEqual(cases,p.select_cases(plan))
        self.assertEqual(len(cases),34)
        self.assertEqual(sum(len(plan['arms_by_phase'][str(c['phase'])]) for c in cases),112)
        failure = [c for c in cases if c['role'] == 'failure']
        successful = [c for c in cases if c['role'] == 'success_control']
        self.assertTrue(all(not c['archived']['success'] for c in failure))
        self.assertTrue(all(c['archived']['success'] for c in successful))
        self.assertEqual(len({c['seed'] for c in successful}),17)
        self.assertFalse({c['seed'] for c in failure} & {c['seed'] for c in successful})

    def test_phase_six_cannot_pretend_to_test_learned_completion(self):
        plan = p.read(p.HERE/'config.json')
        plan['arms_by_phase']['6'].append('completion')
        with self.assertRaisesRegex(ValueError,'Unsupported completion'):
            p.validate(plan)

    def test_scope_excludes_other_stage_phase_and_retreat(self):
        case = dict(placement=2,phase=4)
        self.assertTrue(p.targets(2,4,False,case))
        self.assertFalse(p.targets(1,4,False,case))
        self.assertFalse(p.targets(2,5,False,case))
        self.assertFalse(p.targets(2,4,True,case))

    def test_expert_remains_in_selected_phase_after_ready(self):
        import numpy as np
        expert = p.h.module('residual_real_expert',p.ROOT/'praxis/src/task_extensions/stack_expert.py').StackExpert
        env = SimpleNamespace(cubes=[0,1,2],cube_ids=[0,1,2],sim=SimpleNamespace(data=SimpleNamespace(body_xpos=np.array([[0.,0.,.82],[.1,.1,.82],[-.1,0.,.82]]))))
        for phase in (1,4,6):
            oracle = p.FixedPhaseExpert(expert,env,2,phase)
            obs = dict(robot0_eef_pos=np.array([0.,0.,1.]))
            oracle.action(obs)
            obs['robot0_eef_pos'] = oracle.goal.copy()
            for _ in range(35):
                action, ready = oracle.action(obs)
                self.assertTrue(np.array_equal(action[:3],np.zeros(3)))
                self.assertEqual(action[6],1. if phase == 4 else -1.)
                self.assertEqual(oracle.expert.phase,phase)
            self.assertTrue(ready)

    def test_completion_only_overrides_transition_not_current_action(self):
        import numpy as np
        anchor = np.array([.1,.2,.3])
        policy = SimpleNamespace(phase=2,steps=0,anchor=None)
        bc_action, teacher = np.arange(7), -np.arange(7)
        action = p.apply_intervention(policy,1,12,anchor,bc_action,teacher,False,'completion')
        self.assertIs(action,bc_action)
        self.assertEqual((policy.phase,policy.steps),(1,13))
        self.assertTrue(np.array_equal(policy.anchor,anchor))
        p.apply_intervention(policy,1,13,anchor,bc_action,teacher,True,'completion')
        self.assertEqual((policy.phase,policy.steps,policy.anchor),(2,0,None))

    def test_action_only_does_not_override_bc_transition(self):
        import numpy as np
        policy = SimpleNamespace(phase=2,steps=0,anchor=None)
        teacher = np.ones(7)
        action = p.apply_intervention(policy,1,12,np.zeros(3),np.zeros(7),teacher,False,'action')
        self.assertIs(action,teacher)
        self.assertEqual((policy.phase,policy.steps,policy.anchor),(2,0,None))

    def test_different_preintervention_history_is_rejected(self):
        case = p.select_cases(p.read(p.HERE/'config.json'))[0]
        control = dict(case['archived'],entry=dict(frame=3,history_sha256='a',state_sha256='b'))
        altered = copy.deepcopy(control)
        altered['entry']['history_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError,'Pre-intervention'):
            p.check_group(case,dict(control=control,action=altered))

    def test_archived_control_mismatch_is_rejected(self):
        case = p.select_cases(p.read(p.HERE/'config.json'))[0]
        control = dict(case['archived'],entry=None)
        control['frames'] += 1
        with self.assertRaisesRegex(ValueError,'Archived control regression'):
            p.check_group(case,dict(control=control))


if __name__ == '__main__':
    unittest.main()
