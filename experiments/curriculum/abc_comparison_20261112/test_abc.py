from pathlib import Path
import copy
import tempfile
import unittest

import train


class ABCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.torch,cls.np=train.runtime.libraries()
        cls.base.configure(1)
        cls.cfg=train.read(train.HERE.with_name('axis_bc_20261110')/'ready_001/config.json')

    def test_fixed_budget_and_fresh_confirmation(self):
        plan=train.read(train.HERE/'config.json')
        train.validate(plan,self.cfg)
        bad=copy.deepcopy(plan);bad['updates']=60000
        with self.assertRaises(ValueError):train.validate(bad,self.cfg)
        bad=copy.deepcopy(plan);bad['confirmation_seeds']=[2026119000,2026119099]
        with self.assertRaises(ValueError):train.validate(bad,self.cfg)

    def test_standard_sampling_is_reproducible_and_full_phase_pool(self):
        np=self.np
        data=(np.zeros((70,10),'float32'),np.zeros((70,4),'float32'),np.repeat(np.arange(7),10),np.zeros(70,'float32'))
        a=train.full_schedule(data,100,64,1);b=train.full_schedule(data,100,64,1)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(set(data[2][a.ravel()].tolist()),set(range(7)))
        self.assertFalse(np.array_equal(a,train.full_schedule(data,100,64,2)))

    def test_native_checkpoint_restores_exact_next_cpu_adamw_step(self):
        model,opt,ck=train.registry.restore('mixed_s1_u30000','cpu')
        data=self.base.load_data()['train'];ids=self.np.arange(64)
        weights=self.base.positive_weights(data,'cpu')
        with tempfile.TemporaryDirectory(dir=train.HERE) as directory:
            folder=Path(directory)
            sampler=folder/'sampler.npz';self.np.savez_compressed(sampler,batches=ids[None])
            train.save(folder/'checkpoint.pth',model,opt,ck['update'],1,self.cfg,{'test':True},sampler,True)
            restored,restored_opt,saved=train.restore_training_checkpoint(folder/'checkpoint.pth','cpu')
            self.assertEqual(saved['next_batch'],30000)
            self.base.step(model,opt,data,ids,weights,self.cfg,30001,'cpu')
            self.base.step(restored,restored_opt,data,ids,weights,self.cfg,30001,'cpu')
            for key,value in model.state_dict().items():
                self.torch.testing.assert_close(value,restored.state_dict()[key],rtol=0,atol=0)
            self.assertEqual(opt.state_dict()['state'][0]['step'],restored_opt.state_dict()['state'][0]['step'])

    def test_initialization_equal_and_optimizer_available_for_all_histories(self):
        inventory=train.read(train.HERE.parent/'models.json')
        for seed in (1,2,3):
            self.assertTrue(inventory['initialization_audit'][str(seed)]['initialization_equal'])
            for history in ('mixed','curriculum'):
                entry=inventory['models'][f'{history}_s{seed}_u30000']
                self.assertTrue(entry['optimizer_present'] and entry['sampler_plan'])
                self.assertEqual(entry['update'],30000)


if __name__=='__main__':unittest.main()
