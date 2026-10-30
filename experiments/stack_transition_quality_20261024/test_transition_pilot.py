"""Technical invariants; synthetic data does not demonstrate policy efficacy."""
import unittest
import numpy as np
import transition_pilot as t

class Invariants(unittest.TestCase):
    def fixture(self):
        n=120;count=3;post=np.zeros((n,18));post[:,2]=.82;post[:,5]=.86;post[:,8]=.82
        post[30:,8]=.86
        pre=post.copy();pre[1:]=post[:-1]
        a=dict(x=np.zeros((n,10),np.float32),a=np.zeros((n,7)),p=np.zeros(n,int),
            phase_steps=np.zeros(n),anchor=np.zeros((n,3)),pre_obs=pre,post_obs=post,
            controller_event=np.zeros(n,int),prefix_valid=np.ones((n,2),bool),
            stage=np.ones(n,int),fingers=np.zeros((n,3),bool))
        a['controller_event'][10]=1;a['controller_event'][20]=2
        a['stage'][21:]=2;a['p'][30:]=3
        a['p'][10]=6;a['fingers'][30:35,2]=True
        a['x'][:,:3]=(pre[:,9:12]-a['anchor'])/.1
        a['x'][:,3:7]=pre[:,12:16];a['x'][:,7:9]=pre[:,16:18]/.04
        row=dict(count=3,path=__file__,initial_sha256='family',split='train',
            teacher=__file__,teacher_sha256=t.sha(__file__),seed=9)
        return a,row
    def test_alignment_negative(self):
        a,r=self.fixture();t.audit_arrays(a,3);a['post_obs'][0,0]+=.01
        with self.assertRaisesRegex(AssertionError,'temporal'):t.audit_arrays(a,3)
    def test_future_input_negative(self):
        a,r=self.fixture();a['x'][0,0]=1
        with self.assertRaisesRegex(AssertionError,'pre-action'):t.audit_arrays(a,3)
    def test_bad_action(self):
        a,r=self.fixture();a['a'][0,3]=.1
        with self.assertRaisesRegex(AssertionError,'rotation'):t.audit_arrays(a,3)
    def test_family_leakage(self):
        a,r=self.fixture()
        with self.assertRaisesRegex(AssertionError,'family'):t.split_audit([r,dict(r,split='valid')])
    def test_heldout_split(self):
        a,r=self.fixture()
        with self.assertRaisesRegex(AssertionError,'reserved'):t.split_audit([dict(r,split='test')])
    def test_proxy_and_missing_tail(self):
        a,r=self.fixture();s=t.extract(a,r)
        self.assertEqual(len(s),1);self.assertFalse(s[0]['verified_grasp'])
        a['prefix_valid'][60,0]=False;self.assertEqual(t.extract(a,r),[])
    def test_tower_contact_negative(self):
        a,r=self.fixture();a['fingers'][35,0]=True;self.assertEqual(t.extract(a,r),[])
    def test_source_contact_allowed(self):
        a,r=self.fixture();a['fingers'][35,2]=True;self.assertEqual(len(t.extract(a,r)),1)
    def test_contact_lift_five_frames(self):
        a,r=self.fixture();a['fingers'][32,2]=False
        self.assertEqual(t.extract(a,r),[])
    def test_action_window_excludes_confirmation_tail(self):
        a,r=self.fixture();s=t.extract(a,r)[0]
        self.assertEqual(s['start'],11);self.assertEqual(s['next_pair_post_frame'],20)
        self.assertEqual(s['end'],35);self.assertEqual(s['confirmed_post_frame'],84)
    def test_native_grasp_negative(self):
        a,r=self.fixture();grasp=dict(held_post=np.zeros((120,3),bool),held_known=np.ones(120,bool))
        self.assertEqual(t.extract(a,dict(r,native_collector=True),grasp=grasp),[])
        with self.assertRaisesRegex(AssertionError,'lower-contact'):t.extract(a,r,grasp=grasp)
    def test_weight_mass(self):
        x=np.array([1.,3.]);w=np.array([.5,2.])
        self.assertAlmostEqual(t.weighted_loss(x,w),2.6)
        self.assertAlmostEqual(t.weighted_loss(np.ones(2),w),1.)
        # Fixed source mixture stays one under arbitrary new-quality weights.
        self.assertAlmostEqual(.5+.25+.25*t.weighted_loss(np.ones(2),w),1.)
        self.assertAlmostEqual(t.weighted_loss(x,w),t.weighted_loss(x,100*w))
    def test_invalid_weighted_loss_inputs(self):
        bad=[(np.ones(2),np.array([0.,1.])),(np.ones(2),np.array([-1.,2.])),
             (np.ones(2),np.array([np.nan,1.])),(np.array([np.inf,1.]),np.ones(2)),
             (np.array([]),np.array([])),(np.ones(2),np.ones(3)),
             (np.ones((2,1)),np.ones((2,1)))]
        for values,weights in bad:
            with self.subTest(shape=values.shape,weights=weights):
                with self.assertRaises(AssertionError):t.weighted_loss(values,weights)
        import torch
        for values,weights in bad:
            with self.assertRaises(AssertionError):t.weighted_loss(torch.tensor(values),torch.tensor(weights))
    def test_native_gripper_dict_geometry(self):
        from types import SimpleNamespace as NS
        from native_collector import finger_contact
        seen=[]
        def contact(a,b):seen.append((a,b));return a==['right_finger']
        env=NS(robots=[NS(gripper={'right':NS(contact_geoms=['right_finger'])})],check_contact=contact)
        self.assertTrue(finger_contact(env,NS(contact_geoms=['cube'])))
        self.assertEqual(seen,[(['right_finger'],['cube'])])
    def test_equal_weight_gradients_and_completion_drift(self):
        import torch
        torch.manual_seed(31)
        net=torch.nn.Sequential(torch.nn.Linear(10,16),torch.nn.Tanh(),torch.nn.Linear(16,5))
        x=torch.randn(8,10);target=torch.randn(8,4)
        logits_before=net(x)[:,4].detach().clone()
        errors=(net(x)[:,:4]-target).square().mean(-1)
        g1=torch.autograd.grad(errors.mean(),tuple(net.parameters()),retain_graph=True)
        g2=torch.autograd.grad(t.weighted_loss(errors,torch.ones(8)),tuple(net.parameters()))
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(g1,g2)))
        opt=torch.optim.SGD(net.parameters(),lr=.01)
        opt.zero_grad();(net(x)[:,:4]-target).square().mean().backward();opt.step()
        self.assertFalse(torch.equal(logits_before,net(x)[:,4].detach()))
    def test_teacher_action_corruption(self):
        import torch
        class Zero(torch.nn.Module):
            def forward(self,x,p):return torch.zeros((len(x),4)),torch.zeros(len(x))
        a,r=self.fixture();t.audit_teacher(a,Zero(),'cpu')
        a['a'][15,0]=.1
        with self.assertRaisesRegex(AssertionError,'teacher action'):t.audit_teacher(a,Zero(),'cpu')
    def test_paired_sampler_available_phases(self):
        # No absent-phase assumption: transition windows can contain only phase0.
        pool=t.Pool.__new__(t.Pool)
        pool.data={'e':dict(x=np.zeros((4,10)),a=np.zeros((4,7)),p=np.zeros(4,int))}
        pool.groups={0:{'e':[(dict(weight=2.),np.arange(4))]}}
        a=pool.sample(np.random.default_rng(12),16);b=pool.sample(np.random.default_rng(12),16)
        self.assertEqual([(r[4],r[5]) for r in a],[(r[4],r[5]) for r in b])
        self.assertTrue(all(r[2]==0 for r in a))

if __name__=='__main__':unittest.main()
