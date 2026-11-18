import unittest
import audit


class CriteriaTests(unittest.TestCase):
    def setUp(self):
        self.plan=audit.read(audit.HERE/'config.json')
        self.m=dict(held=True,lift=.2,eef_goal_error=.005,xy_error=.005,
                    height_above_target=.04,pair_contact=True,prefix_valid=True)

    def test_lift_requires_grasp_and_goal(self):
        self.assertTrue(audit.physical_ready(3,self.m,{},self.plan))
        self.assertFalse(audit.physical_ready(3,dict(self.m,held=False),{},self.plan))
        self.assertFalse(audit.physical_ready(3,dict(self.m,eef_goal_error=.02),{},self.plan))

    def test_bad_predecessor_is_not_eligible(self):
        self.assertFalse(audit.eligible(4,dict(self.m,held=False),self.plan))
        self.assertFalse(audit.eligible(5,dict(self.m,height_above_target=.04),self.plan))
        self.assertFalse(audit.eligible(6,dict(self.m,pair_contact=False),self.plan))

    def test_failed_positive_control_excluded(self):
        plan=dict(self.plan,model_ids=['B'],placements=[1],phases=[3])
        row=dict(model='B',seed=1,placement=1,phase=3,eligible_start=True,success=True,premature_completion=False)
        ref=dict(seed=1,placement=1,phase=3,success=False)
        result=audit.aggregate([row],[],[ref],plan,True)['models']['B'][1][3]
        self.assertEqual(result['isolated_attempts'],1)
        self.assertEqual(result['valid_reference_attempts'],0)
        self.assertEqual(result['isolated_successes'],0)


if __name__=='__main__':unittest.main()
