import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('approach_bc_test_subject',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


class TrainingTests(unittest.TestCase):
    def test_scene_family_overlap_rejected(self):
        cfg=p.read(p.HERE/'config.json');cfg['validation_seeds']=cfg['train_seeds']
        with self.assertRaisesRegex(ValueError,'Overlapping'):p.validate(cfg)

    def test_only_approach_parameters_trainable(self):
        _,torch,_=p.h.libraries();model=torch.nn.Module()
        model.heads=torch.nn.ModuleList([torch.nn.Linear(2,5),torch.nn.Linear(2,5)])
        p.frozen_except_approach(model)
        for name,value in model.named_parameters():self.assertEqual(value.requires_grad,name.startswith('heads.0.'))

    def test_output_composition_preserves_unselected_component_and_phase(self):
        _,torch,_=p.h.libraries()
        class Constant(torch.nn.Module):
            def __init__(self,value):super().__init__();self.value=torch.nn.Parameter(torch.tensor(float(value)))
            def forward(self,x,phase):return self.value.expand(len(x),4),self.value.expand(len(x))
        reference=Constant(1);actor=Constant(2);completion=Constant(3)
        x=torch.zeros(2,10);phase=torch.tensor([0,1])
        a,z=p.compose(reference,actor=actor,active=True)(x,phase)
        self.assertEqual(a[:,0].tolist(),[2,1]);self.assertEqual(z.tolist(),[1,1])
        a,z=p.compose(reference,completion=completion,active=True)(x,phase)
        self.assertEqual(a[:,0].tolist(),[1,1]);self.assertEqual(z.tolist(),[3,1])
        a,z=p.compose(reference,actor,completion,active=True)(x,phase)
        self.assertEqual(a[:,0].tolist(),[2,1]);self.assertEqual(z.tolist(),[3,1])
        a,z=p.compose(reference,actor,completion)(x,phase)
        self.assertEqual(a[:,0].tolist(),[1,1]);self.assertEqual(z.tolist(),[1,1])


if __name__=='__main__':unittest.main()
