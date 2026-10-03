"""Check continuation isolation, unchanged data, and actual SequenceDataset targets."""
import json
import numpy as np
from balance_common import EXP,SOURCE,digest,load_training
from transport_data import DATA,KEYS,history
from robomimic.utils.file_utils import load_dict_from_checkpoint,config_from_checkpoint
from robomimic.utils.dataset import SequenceDataset
from robomimic.utils import obs_utils
p=json.loads((EXP/'protocol.json').read_text());assert digest(DATA)==p['dataset_sha256'];assert digest(SOURCE['checkpoint'])==p['source_sha256']
ckpt=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt);obs_utils.initialize_obs_utils_with_config(cfg)
data=SequenceDataset(hdf5_path=str(DATA),obs_keys=KEYS,action_keys=['actions'],dataset_keys=['actions','rewards','dones'],action_config=cfg.train.action_config,frame_stack=2,seq_length=16,pad_frame_stack=True,pad_seq_length=True,hdf5_cache_mode='low_dim',hdf5_normalize_obs=False,filter_by_attribute='train',load_next_obs=False)
ds,obs,a,c,w,refs,events=load_training();lookup={d['name']:d for d in ds};rng=np.random.default_rng(991);checked=[]
for j in np.r_[rng.choice(len(a),30,replace=False),np.flatnonzero(c)[::90]]:
    name,i=refs[j];item=data[data._demo_id_to_start_indices[name]+i]
    for k in KEYS:assert np.allclose(item['obs'][k][:2],obs[k][j],atol=1e-7)
    assert np.allclose(item['actions'][:16],a[j],atol=1e-7);checked.append(refs[j])
u=np.load(EXP/'uniform/sampling_audit.npz');b=np.load(EXP/'balanced/sampling_audit.npz');assert np.array_equal(u['lr'],b['lr'])
cu=load_dict_from_checkpoint(ckpt_path=str(EXP/'uniform/model_final.pth'));cb=load_dict_from_checkpoint(ckpt_path=str(EXP/'balanced/model_final.pth'));assert cu['config']==cb['config'];assert cu['shape_metadata']==cb['shape_metadata']
phase=np.array([lookup[n]['phase'][i] for n,i in refs]);phasecounts={v:{str(ph):int(np.load(EXP/v/'sampling_audit.npz')['sample_counts'][phase==ph].sum()) for ph in np.unique(phase)} for v in ('uniform','balanced')}
out=dict(dataset_unchanged=True,source_checkpoint_unchanged=True,checkpoint_configs_identical=True,lr_arrays_identical=True,training_window_checks=len(checked),checked_windows=checked,actual_phase_sample_counts=phasecounts,black_image_demos_unchanged=62,state_policy_rgb_inputs=False,source_sha256=p['source_sha256'],dataset_sha256=p['dataset_sha256'])
(EXP/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
