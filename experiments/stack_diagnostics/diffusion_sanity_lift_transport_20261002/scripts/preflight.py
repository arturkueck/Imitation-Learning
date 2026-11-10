"""Short local checks only: no optimizer updates, rollouts, or checkpoint inference."""
import ast,copy,torch
from types import SimpleNamespace
import numpy as np,h5py
from common import *
from sanity_metrics import metrics
from robomimic.config import config_factory
from robomimic.utils import obs_utils
from robomimic.utils import train_utils
from robomimic.utils.dataset import SequenceDataset
from robomimic.algo.algo import Algo
def main():
    assert not (OUT/'worker_started.json').exists()
    config=read(OUT/'config.json');old=read(ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/C/diffusion/seed_1/config.json')
    clone=copy.deepcopy(config)
    for k in ('data','output_dir'):clone['train'][k]=old['train'][k]
    clone['experiment']['name']=old['experiment']['name'];assert clone==old
    assert config['train']['seed']==1 and config['train']['num_epochs']*config['experiment']['epoch_every_n_steps']==30000
    n=Normalizer('C');assert digest(OUT/'normalization_stats.json')==digest(ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/normalization_stats.json')
    SequenceDataset.normalize_obs=lambda self:n.obs
    cfg=config_factory(config['algo_name'],dic=config);cfg.lock();obs_utils.initialize_obs_utils_with_config(cfg)
    train,valid=train_utils.load_data_for_training(cfg,obs_keys=KEYS)
    assert len(train.demos)==180 and len(valid.demos)==20
    errors=[]
    with h5py.File(DATA,'r') as f:
        for ds in (train,valid):
            for k in KEYS:
                for s in ('offset','scale'):assert np.array_equal(ds.get_obs_normalization_stats()[k][s],n.obs[k][s])
            for index in (0,len(ds)//2,len(ds)-1):
                batch=ds[index];name=ds._index_to_demo_id[index];frame=index-ds._demo_id_to_start_indices[name];d=f['data'][name];length=len(d['actions'])
                ids=np.clip([frame-1,frame],0,length-1)
                processed=Algo.postprocess_batch_for_training(SimpleNamespace(device=torch.device('cpu')),{'obs':{k:torch.tensor(batch['obs'][k][:2][None],dtype=torch.float32) for k in KEYS}},n.obs)['obs']
                for k in KEYS:errors.append(float(abs(processed[k][0].numpy()-n.observations({k:d['obs'][k][:][ids]})[k]).max()))
                a=d['actions'][:][np.clip(np.arange(frame-1,frame+15),0,length-1)]
                errors.append(float(abs(batch['actions'][:16]-a).max()))
                assert batch['actions'][:16].shape==(16,7)
    assert max(errors)<1e-6
    # Successful held lift then 3 cm toward stationary target; reject backward motion and drops.
    t=np.zeros((20,37));t[:,1]=.1;t[:,6]=.82;t[:,34]=1;t[3:6,6]=.9;t[6:,6]=1.02
    t[9:,4]=np.arange(11)*.003;t[:,20]=.5
    assert metrics(t)['simplified_success']
    backward=t.copy();backward[:,4]*=-1;assert not metrics(backward)['simplified_success']
    dropped=t.copy();dropped[13,34]=0;assert not metrics(dropped)['simplified_success']
    lift_only=t.copy();lift_only[:,4]=0;assert not metrics(lift_only)['simplified_success']
    for p in (OUT/'scripts').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    write(OUT/'preflight.json',dict(passed=True,no_training_or_rollout_performed=True,configuration_only_data_and_output_changed=True,train_demos=180,valid_demos=20,train_frames=len(train),valid_frames=len(valid),actual_dataset_transform_max_error=max(errors),metric_positive_negative_checks_passed=True,observation_statistics_exact_C=True,seed=1))
    print('PREFLIGHT PASSED',len(train),len(valid),max(errors))
if __name__=='__main__':main()
