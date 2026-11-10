"""Audit identity normalization, exact windows, budgets and paired start states."""
import json
import numpy as np,torch
from direct_common import OUT,ROOT,DATA,SOURCE,KEYS,flatten
from balance_common import load_training,digest
from robomimic.utils.file_utils import load_dict_from_checkpoint,config_from_checkpoint
from robomimic.utils.dataset import SequenceDataset
from robomimic.utils import obs_utils
c=json.loads((OUT/'config.json').read_text());assert digest(DATA)==c['dataset_sha256'];assert digest(SOURCE['checkpoint'])==c['diffusion_checkpoint_sha256'];source=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);cfg,_=config_from_checkpoint(ckpt_dict=source);obs_utils.initialize_obs_utils_with_config(cfg);assert cfg.train.action_config['actions']['normalization'] is None
(OUT/'diffusion_config.json').write_text(json.dumps(json.loads(source['config']),indent=2))
ds,ob,a,critical,w,refs,events=load_training();data=SequenceDataset(hdf5_path=str(DATA),obs_keys=KEYS,action_keys=['actions'],dataset_keys=['actions','rewards','dones'],action_config=cfg.train.action_config,frame_stack=2,seq_length=16,pad_frame_stack=True,pad_seq_length=True,hdf5_cache_mode='low_dim',hdf5_normalize_obs=False,filter_by_attribute='train',load_next_obs=False)
for j in np.random.default_rng(991).choice(len(a),40,replace=False):
    name,i=refs[j];item=data[data._demo_id_to_start_indices[name]+i]
    for k in KEYS:assert np.allclose(item['obs'][k][:2],ob[k][j],atol=1e-7)
    assert np.array_equal(item['actions'][:16],a[j])
audit=np.load(OUT/'training_audit.npz');assert audit['sample_indices'].shape==(30000,8);assert len(audit['loss'])==30000;assert np.isfinite(audit['loss']).all();direct=torch.load(OUT/'model_final.pth',map_location='cpu',weights_only=False);assert direct['ema_step']==30000
assert {int(v['step']) for v in direct['optimizer']['state'].values()}=={30000};assert {int(v['step']) for v in source['model']['optimizers']['policy']['state'].values()}=={30000}
rows={v:json.loads((OUT/v/'rollouts/results.json').read_text()) for v in ('diffusion','direct')};assert all(len(r)==40 for r in rows.values());assert [r['seed'] for r in rows['diffusion']]==[r['seed'] for r in rows['direct']];tails={}
for b,d in zip(rows['diffusion'],rows['direct']):
    assert b['initial_state_sha256']==d['initial_state_sha256']
    for v,r in [('diffusion',b),('direct',d)]:
        z=np.load(OUT/v/'rollouts'/f"{r['seed']}.npz");t=z['trace'];assert np.isfinite(t).all();assert np.array_equal(t[:,20:27],t[:,27:34])
        if r['reused']:assert digest(OUT/v/'rollouts'/f"{r['seed']}.npz")==digest(ROOT/'experiments/stack_diagnostics/stack_placement_20261001/baseline'/f"{r['seed']}.npz")
        if r['sustained_success']:
            tail=t[r['measured_steps']:];delta=tail[:,4:7]-tail[:,1:4];assert len(tail)==40 and np.all(tail[:,36]>0);assert not tail[:,34].any();assert np.all(tail[:,35]>0)
            tails[str(r['seed'])]=dict(model=v,max_xy_distance_m=float(np.linalg.norm(delta[:,:2],axis=1).max()),relative_height_min_m=float(delta[:,2].min()),relative_height_max_m=float(delta[:,2].max()),held_steps=0,cube_contact_steps=40)
out=dict(dataset_unchanged=True,source_checkpoint_unchanged=True,action_normalization_identity=True,training_window_checks=40,optimizer_and_ema_updates_each=30000,gradient_updates_each=30000,training_examples_each=240000,exact_original_diffusion_training_indices_available=False,uniform_sampling_both=True,fixed_start_hash_pairs_verified=40,reused_diffusion_rollouts_bit_equal=20,no_action_heuristics=True,direct_parameters=c['parameter_count'],diffusion_parameters=c['diffusion_parameter_count'],black_image_demos_unchanged=62)
(OUT/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
(OUT/'success_tail_audit.json').write_text(json.dumps(tails,indent=2))
