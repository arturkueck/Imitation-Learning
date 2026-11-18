"""Guard the causal isolation, frozen endpoints, and diagnostic selection."""
from pathlib import Path
from types import SimpleNamespace
import copy
import importlib.util
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('placement_test_subject',Path(__file__).with_name('pipeline.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.plan = p.read(p.HERE/'config.json')

    def test_fixed_families_and_denominators(self):
        cases = p.cases_for(self.plan)
        new = [c for c in cases if c['panel']=='calibration']
        known = [c for c in cases if c['panel']=='known']
        self.assertEqual(len(new),54)
        self.assertEqual(len({c['seed'] for c in new}),18)
        self.assertEqual(len(known),6)
        self.assertEqual(sum(len(c['arms']) for c in cases),354)
        self.assertEqual(sum(len(c['arms']) for c in p.cases_for(self.plan,True)),23)
        self.assertFalse({c['seed'] for c in new}&{c['seed'] for c in known})
        self.assertTrue(all(not c['archived']['success'] for c in known))

    def test_never_intervene_in_release_or_retreat_phase(self):
        for arm in p.ARMS:
            self.assertEqual(p.profile(arm,6),'control')
            self.assertEqual(p.profile(arm,0),'control')
        self.assertEqual(p.profile('grasp_completion',5),'control')
        self.assertEqual(p.profile('place_completion',1),'control')

    def test_guard_cannot_force_classifier_false_negative(self):
        policy = SimpleNamespace(phase=5,steps=10,anchor=np.zeros(3))
        blocked = p.guard(policy,5,9,np.zeros(3),False,99,self.plan['placement_readiness'])
        self.assertFalse(blocked)
        self.assertEqual(policy.phase,5)

    def test_veto_restores_counter_and_anchor(self):
        anchor = np.array([.1,.2,.3])
        policy = SimpleNamespace(phase=6,steps=0,anchor=None)
        self.assertTrue(p.guard(policy,5,7,anchor,True,2,self.plan['placement_readiness']))
        self.assertEqual((policy.phase,policy.steps),(5,8))
        self.assertTrue(np.array_equal(policy.anchor,anchor))
        policy.phase,policy.steps,policy.anchor = 6,0,None
        self.assertFalse(p.guard(policy,5,7,anchor,True,3,self.plan['placement_readiness']))
        self.assertEqual((policy.phase,policy.steps,policy.anchor),(6,0,None))

    def test_contact_speed_and_lower_prefix_are_separate_conditions(self):
        good = [.002,.04,True,.001,.02,True]
        self.assertTrue(p.readiness(good,self.plan['placement_readiness']))
        for index,bad in enumerate((.025,.09,False,.04,.4,False)):
            features = good.copy()
            features[index] = bad
            self.assertFalse(p.readiness(features,self.plan['placement_readiness']))

    def test_phase_five_oracle_keeps_gripper_closed_and_goal_fixed(self):
        cls = p.h.module('placement_real_expert',p.ROOT/'praxis/src/task_extensions/stack_expert.py').StackExpert
        env = SimpleNamespace(cubes=[0,1,2],cube_ids=[0,1,2],sim=SimpleNamespace(data=SimpleNamespace(
            body_xpos=np.array([[0.,0.,.82],[0.,0.,.86],[.1,.1,.82]]))))
        teacher = p.res.FixedPhaseExpert(cls,env,2,5)
        obs = dict(robot0_eef_pos=np.array([0.,0.,1.]))
        teacher.action(obs)
        goal = teacher.goal.copy()
        obs['robot0_eef_pos'] = goal.copy()
        for _ in range(25):
            action,ready = teacher.action(obs)
            self.assertEqual(action[6],1.)
            self.assertTrue(np.array_equal(teacher.goal,goal))
            self.assertEqual(teacher.expert.phase,5)
        self.assertTrue(ready)

    def test_preintervention_and_unexposed_divergence_rejected(self):
        case = dict(intervention_placement=2)
        row = dict(initial_sha256='a',entries={},trajectory_sha256='t')
        altered = copy.deepcopy(row)
        altered['trajectory_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError,'Unexposed'):
            p.check_group(case,dict(control=row,place_guard=altered))
        altered = copy.deepcopy(row)
        altered['entries']['2/5'] = dict(frame=2)
        with self.assertRaisesRegex(ValueError,'Pre-intervention'):
            p.check_group(case,dict(control=row,place_action=altered))

    def test_no_training_or_endpoint_change(self):
        for name,value in (('optimizer_updates',1),('automatic_restart',True),('success_frames',10)):
            plan = copy.deepcopy(self.plan)
            plan[name] = value
            with self.assertRaisesRegex(ValueError,'frozen policies'):
                p.validate(plan)


if __name__=='__main__':
    unittest.main()
