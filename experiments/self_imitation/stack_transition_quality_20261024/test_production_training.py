"""Mechanism tests, not evidence of policy efficacy."""
import copy,json,tempfile,time,unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import torch
import production_train as train
from online_evaluation import TransitionJudge,selection_score,rate,evaluate_prepared,prepare_reserved_panels,evaluator_from_plan,_Progress

def result(success,total=20):return dict(successes=success,attempts=total,complete=True)
def metrics(p2=10,p3=10,full2=10,full3=10,full4=10):
    return dict(prepared_prefix2=result(p2),prepared_prefix3=result(p3),full_stack2=result(full2),full_stack3=result(full3),full_stack4=result(full4))

class TrainingMechanisms(unittest.TestCase):
    def test_selection_uses_worst_primary(self):
        baseline=metrics();self.assertGreater(selection_score(metrics(12,11),baseline,3000),selection_score(metrics(20,10),baseline,10000))
    def test_selection_regression_and_earlier(self):
        base=metrics();self.assertGreater(selection_score(metrics(),base,0),selection_score(metrics(full2=9),base,0))
        self.assertGreater(selection_score(base,base,3000),selection_score(base,base,10000))
    def test_incomplete_cannot_select(self):
        m=metrics();m['full_stack2']['complete']=False
        with self.assertRaises(AssertionError):selection_score(m,metrics(),0)
    def test_actor_weight_mass_and_gradient(self):
        e=torch.arange(64,dtype=torch.float64,requires_grad=True);w=torch.linspace(.5,2,16,dtype=torch.float64)
        loss=train.actor_loss(e,w);loss.backward();self.assertTrue(torch.allclose(e.grad[:32],torch.full((32,),.5/32,dtype=torch.float64)))
        self.assertTrue(torch.allclose(e.grad[32:48],torch.full((16,),.25/16,dtype=torch.float64)))
        self.assertTrue(torch.allclose(e.grad[48:],.25*w/w.sum()))
        self.assertAlmostEqual(train.actor_loss(e.detach(),w).item(),train.actor_loss(e.detach(),w*17).item())
    def test_actor_uniform_same_mean(self):
        e=torch.randn(64);self.assertTrue(torch.allclose(train.actor_loss(e,torch.ones(16)),e.mean()))
    def test_release_plan_binding_and_expiry(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            plan=Path(d)/'plan.json';plan.write_text('{}');release=Path(d)/'release.json'
            release.write_text(json.dumps(dict(user_approved=True,plan_sha256=train.sha(plan),expires_unix=time.time()+60)))
            train.release_check(plan,release);plan.write_text('{"changed":true}')
            with self.assertRaises(AssertionError):train.release_check(plan,release)
    def test_technical_freeze_forbidden(self):
        with self.assertRaises(AssertionError):train.freeze_and_test(dict(technical_only=True),'unused',None,time.time()+1)
    def test_training_requires_explicit_release_before_loading_data(self):
        with self.assertRaisesRegex(AssertionError,'production requires release'):
            train.train_paired({}, {}, 'unused', time.time()+1,device='cpu')
    def test_technical_update_cap(self):
        with self.assertRaisesRegex(AssertionError,'technical update cap'):
            train.train_paired({}, {}, 'unused', time.time()+1,technical_steps=6,device='cpu')
    def test_freeze_all_before_first_eval_and_once(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root=Path(d);source=root/'source';source.write_bytes(b'fake-model')
            selections={f'{arm}_seed{seed}':dict(path=str(source),update=0,score=[0,0,0,0]) for seed in(1,2,3) for arm in('B0','B')}
            def evaluate(path,seed,update,split,deadline):
                frozen=json.loads((root/'frozen/selection.json').read_text());self.assertEqual(len(frozen),6)
                self.assertTrue(all(Path(v['path']).exists() for v in frozen.values()));return metrics()
            train.freeze_and_test(dict(technical_only=False,selections=selections),root/'frozen',evaluate,time.time()+10)
            self.assertEqual(len(list((root/'frozen').glob('*.started.json'))),12)
    def test_preparation_requires_all_six_frozen_models(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            p=Path(d);selection=p/'selection.json';selection.write_text('{}')
            with self.assertRaisesRegex(AssertionError,'all six'):
                prepare_reserved_panels({},p/'panel',time.time()+5,selection)
    def test_preparation_failure_retained_in_denominator(self):
        rows=[dict(seed=498004,prefix=2,prepared=False,reason='teacher never reached prefix')]
        r=evaluate_prepared(None,rows,time.time()+5)
        self.assertEqual(r['attempts'],1);self.assertEqual(r['successes'],0);self.assertTrue(r['complete'])
        self.assertIn('preparation_failure',r['rows'][0])
    def test_partial_rows_survive_timeout_before_second_start(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            rows=[dict(seed=i,prefix=2,prepared=False) for i in (498004,498005)];path=Path(d)/'progress.json'
            with patch('online_evaluation.check_deadline',side_effect=[None,TimeoutError('test cutoff')]):
                with self.assertRaises(TimeoutError):evaluate_prepared(None,rows,time.time()+5,progress_path=path)
            saved=json.loads(path.read_text());self.assertFalse(saved['complete'])
            self.assertEqual(saved['attempts'],1);self.assertEqual(saved['completed_starts'],[498004])
            self.assertEqual(saved['possibly_consumed_unfinished_starts'],[])
            with self.assertRaisesRegex(AssertionError,'automatic rerun'):
                evaluate_prepared(None,rows,time.time()+5,progress_path=path)
    def test_started_unfinished_not_invented_as_failure(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            path=Path(d)/'progress.json';p=_Progress(path,2);p.begin(498004)
            saved=json.loads(path.read_text());self.assertEqual(saved['attempts'],0)
            self.assertEqual(saved['possibly_consumed_unfinished_starts'],[498004]);self.assertFalse(saved['complete'])
    def test_progress_names_isolate_same_hash_arms(self):
        from native_collector import historical
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            p=Path(d);callback=evaluator_from_plan({}, {},progress_root=p/'progress')
            for arm in ('B0','B'):
                folder=p/f'{arm}_seed1';folder.mkdir();checkpoint=folder/'update0.pth';checkpoint.write_bytes(b'same model')
                with patch.object(historical,'load',side_effect=ValueError('stop before model load')):
                    with self.assertRaises(ValueError):callback(checkpoint,1,0,'development',time.time()+5)
            self.assertEqual(len(list((p/'progress/development').glob('*/update*/callback.json'))),2)

class TransitionMetric(unittest.TestCase):
    def test_success_requires_5_grasp_plus_50_frames(self):
        j=TransitionJudge(.82)
        for _ in range(4):self.assertFalse(j.step(valid=True,held=True,source_z=.86))
        self.assertFalse(j.step(valid=True,held=True,source_z=.86));self.assertEqual(j.pickup,5)
        for _ in range(49):self.assertFalse(j.step(valid=True,held=False,source_z=.86))
        self.assertTrue(j.step(valid=True,held=False,source_z=.86));self.assertTrue(j.success)
    def test_contact_or_prefix_failure_never_recovers(self):
        for kw in (dict(valid=False,tower_contact=False),dict(valid=True,tower_contact=True)):
            j=TransitionJudge(.82);self.assertTrue(j.step(held=True,source_z=.86,**kw))
            for _ in range(60):j.step(valid=True,held=True,source_z=.86)
            self.assertFalse(j.success)
    def test_no_grasp_no_pickup(self):
        j=TransitionJudge(.82)
        for _ in range(200):j.step(valid=True,held=False,source_z=.86)
        self.assertIsNone(j.pickup);self.assertFalse(j.success)
    def test_late_pickup_rejected(self):
        j=TransitionJudge(.82)
        for _ in range(197):j.step(valid=True,held=False,source_z=.82)
        for _ in range(60):j.step(valid=True,held=True,source_z=.86)
        self.assertIsNone(j.pickup)
    def test_unknown_initial_prefix_invalid(self):
        j=TransitionJudge(.82,initial_valid=False)
        for _ in range(60):j.step(valid=True,held=True,source_z=.86)
        self.assertFalse(j.success)

if __name__=='__main__':unittest.main()
