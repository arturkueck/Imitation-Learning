from pathlib import Path
import copy
import importlib.util
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('selective_test_subject',Path(__file__).with_name('pipeline.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class SelectiveTests(unittest.TestCase):
    def setUp(self):
        self.plan = p.read(p.HERE/'config.json')

    def test_fixed_families_and_success_controls(self):
        cases = p.cases_for(self.plan)
        self.assertEqual(len(cases),52)
        self.assertEqual(sum(len(c['arms']) for c in cases),354)
        self.assertEqual(sum(c['stratum']=='grasp_failure' for c in cases),6)
        self.assertEqual(sum(c['stratum']=='grasp_success_control' for c in cases),4)
        self.assertEqual(sum(c['stratum']=='release_failure' for c in cases),3)
        self.assertEqual(sum(c['stratum']=='release_success_control' for c in cases),3)
        self.assertEqual(len({c['seed'] for c in cases if c['panel']=='calibration'}),12)
        self.assertEqual(sum(len(c['arms']) for c in p.cases_for(self.plan,True)),21)

    def test_never_undo_early_or_existing_bc_completion(self):
        cfg = self.plan['grasp']
        for arm in ('grasp_timeout','grasp_ready'):
            self.assertFalse(p.grasp_decision(arm,99,False,99,cfg))
            self.assertFalse(p.grasp_decision(arm,200,True,99,cfg))
        self.assertFalse(p.grasp_decision('grasp_ready',100,False,19,cfg))
        self.assertTrue(p.grasp_decision('grasp_ready',100,False,20,cfg))
        self.assertTrue(p.grasp_decision('grasp_timeout',100,False,0,cfg))

    def test_factorial_profile_is_independent(self):
        self.assertEqual(p.release_profile('control'),(False,'bc'))
        self.assertEqual(p.release_profile('release_hold'),(False,'hold'))
        self.assertEqual(p.release_profile('release_feedback'),(False,'feedback'))
        for motion in ('bc','hold','feedback'):
            self.assertEqual(p.release_profile('guarded_'+motion),(True,motion))
        self.assertEqual(p.release_profile('grasp_ready'),(False,'bc'))

    def test_hold_opens_without_invented_motion_at_goal(self):
        eef = np.array([.1,.2,1.])
        c = p.ReleaseController('hold',eef,self.plan['release'])
        a = c.action(eef,np.zeros(3),np.ones(3),np)
        self.assertTrue(np.array_equal(a[:6],np.zeros(6)))
        self.assertEqual(a[6],-1.)

    def test_feedback_sign_duration_and_shared_height(self):
        eef = np.array([.1,.2,1.])
        c = p.ReleaseController('feedback',eef,self.plan['release'])
        source,target = np.array([.01,0.,.9]),np.array([0.,0.,.86])
        a = c.action(eef,source,target,np)
        self.assertLess(a[0],0)
        self.assertEqual(a[2],0)
        for _ in range(19):
            c.action(eef,source,target,np)
        moved = eef+np.array([.02,.01,.005])
        a = c.action(moved,source,target,np)
        self.assertTrue(c.locked)
        self.assertTrue(np.array_equal(a[:2],np.zeros(2)))
        self.assertLess(a[2],0)
        self.assertEqual(c.goal[2],eef[2])

    def test_actual_intervention_prefix_not_just_phase_entry(self):
        entry = dict(frame=10,history_sha256='h',state_sha256='s')
        ctrl = dict(initial_sha256='i',entries={'2/1':entry},trajectory_sha256='t',verification_prefixes={'100':dict(frame=100,history_sha256='a',state_sha256='b')})
        row = dict(initial_sha256='i',entries={'2/1':entry},trajectory_sha256='new',first_intervention=dict(frame=100,history_sha256='a',state_sha256='b',phase=1))
        p.check_group({},dict(control=ctrl,grasp_ready=row))
        row['first_intervention']['history_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'Actual intervention prefix'):
            p.check_group({},dict(control=ctrl,grasp_ready=row))

    def test_unexposed_controller_cannot_change_trajectory(self):
        ctrl = dict(initial_sha256='i',entries={},trajectory_sha256='same')
        row = dict(initial_sha256='i',entries={},trajectory_sha256='wrong',first_intervention=None)
        with self.assertRaisesRegex(ValueError,'Unexposed'):
            p.check_group({},dict(control=ctrl,grasp_ready=row))

    def test_release_entry_matched_within_same_guard(self):
        e = dict(frame=20,history_sha256='h',state_sha256='s')
        ctrl = dict(initial_sha256='i',entries={'2/6':e},trajectory_sha256='same')
        row = dict(ctrl,first_intervention=None)
        p.check_group({},dict(control=ctrl,release_hold=row,release_feedback=row))
        bad = copy.deepcopy(row)
        bad['entries']['2/6']['frame']=21
        with self.assertRaisesRegex(ValueError,'entry mismatch'):
            p.check_group({},dict(control=ctrl,release_hold=bad))

    def test_no_training_or_endpoint_relaxation(self):
        for key,value in (('optimizer_updates',1),('success_frames',10),('automatic_restart',True)):
            plan = copy.deepcopy(self.plan)
            plan[key]=value
            with self.assertRaisesRegex(ValueError,'frozen policies'):
                p.validate(plan)

    def test_dynamic_helpers_are_in_frozen_provenance_scope(self):
        files = p.dependency_files()
        self.assertIn(p.ENGINE_PATH,files)
        self.assertIn(Path(p.res.__file__).resolve(),files)
        self.assertIn(Path(p.h.__file__).resolve(),files)
        self.assertIn(Path(p.prior.__file__).resolve(),files)

    def test_input_similarity_rejects_same_family_and_large_input_difference(self):
        a = p.h.module('selective_analysis_test',p.HERE/'analyze.py')
        sample = dict(parent='p',seed=1,placement=2,phase=6,frame=1,x=[0.]*10,xy_m=.002,ready=True)
        other = dict(sample,seed=2,xy_m=.012,ready=False)
        report = a.similarity([sample,other],self.plan['input_similarity'])
        self.assertEqual(report['exact_cross_family_feature_pairs'],1)
        self.assertEqual(report['near_frame_pairs_readiness_disagrees_xy_diff_ge_5mm'],1)
        self.assertEqual(a.similarity([sample,dict(other,seed=1)],self.plan['input_similarity'])['near_frame_pairs'],0)
        other['x']=[1.]*10
        self.assertEqual(a.similarity([sample,other],self.plan['input_similarity'])['near_frame_pairs'],0)


if __name__=='__main__':
    unittest.main()
