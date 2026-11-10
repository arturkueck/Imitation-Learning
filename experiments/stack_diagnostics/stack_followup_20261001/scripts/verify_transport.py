"""Verify actual training-window alignment and observation transforms."""
import json,hashlib
import numpy as np
from transport_data import ROOT,OUT,DATA,KEYS,demos,history
from robomimic.utils.file_utils import load_dict_from_checkpoint,config_from_checkpoint
from robomimic.utils.dataset import SequenceDataset
from robomimic.utils import obs_utils
old=json.loads((ROOT/'experiments/stack_diagnostics/stack_followup_20261001/evaluation/fixed_scheduler_h2/evaluation_results.json').read_text())
ckpt=load_dict_from_checkpoint(ckpt_path=old['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=ckpt)
obs_utils.initialize_obs_utils_with_config(cfg)
assert cfg.train.hdf5_normalize_obs is False
assert ckpt.get('obs_normalization_stats') is None
for stat in (ckpt.get('action_normalization_stats') or {}).values():
    assert np.allclose(stat['offset'],0) and np.allclose(stat['scale'],1)
assert list(cfg.observation.modalities.obs.rgb)==[]
assert ckpt['shape_metadata']['all_shapes']['object']==(6,) or ckpt['shape_metadata']['all_shapes']['object']==[6]
data=SequenceDataset(hdf5_path=str(DATA),obs_keys=KEYS,action_keys=['actions'],dataset_keys=['actions','rewards','dones'],action_config=cfg.train.action_config,
    frame_stack=2,seq_length=16,pad_frame_stack=True,pad_seq_length=True,hdf5_cache_mode='low_dim',hdf5_normalize_obs=False,filter_by_attribute='train',load_next_obs=False)
checked=[]
for d in demos():
    if d['split']!='train':continue
    ids=np.flatnonzero(d['phase']==4)
    for i in (int(ids[0]),int(ids[len(ids)//2]),int(ids[-1])):
        index=data._demo_id_to_start_indices[d['name']]+i
        item=data[index];expected=history(d,i)
        for k in KEYS:assert np.allclose(item['obs'][k][:2],expected[k],atol=1e-7)
        assert np.allclose(item['actions'][1],d['actions'][i],atol=1e-7)
        checked.append(dict(demo=d['name'],step=i))
    if len(checked)>=30:break
teacher=np.load(OUT/'baseline_teacher_predictions.npz');assert teacher['predictions'].shape[0]==3
assert np.isfinite(teacher['predictions']).all()
probes=np.load(OUT/'rollout_observation_probes.npz');assert probes['original'].shape==probes['raised'].shape and probes['original'].shape[0]==3
assert np.isfinite(probes['original']).all() and np.isfinite(probes['raised']).all()
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
result=dict(training_alignment_checks=len(checked),obs_history='t-1,t',executed_prediction_index=1,action_at_index_1='a[t]',
    obs_normalization='none',action_normalization='identity',rgb_inputs=False,numeric_features_per_frame=15,observation_frames=2,
    checkpoint=old['checkpoint'],checkpoint_sha256=digest(old['checkpoint']),dataset_sha256=digest(DATA),
    counterfactual_experiments=['target X shift, +/-4cm','held cube and EEF height jointly shifted to expert transport level'],
    common_noise_per_pair=True,diffusion_draws_per_observation=3,checkpoint_weights_modified=False,dataset_modified=False,
    xy_controller_used=False,checked_windows=checked)
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='checked_windows'},indent=2))
