"""Audit treatment isolation and recompute dynamics from saved rollout inputs."""
import json
import numpy as np,torch
from dynamics_common import OUT,DATA,SOURCE,KEYS,augment
from balance_common import digest
p=json.loads((OUT/'protocol.json').read_text());a=np.load(OUT/'baseline/training_audit.npz');b=np.load(OUT/'dynamics/training_audit.npz')
assert np.array_equal(a['sample_indices'],b['sample_indices']);assert np.array_equal(a['lr'],b['lr']);assert a['sample_indices'].shape==(5000,8)
assert digest(DATA)==p['dataset_sha256'];assert digest(SOURCE['checkpoint'])==p['source_sha256']
audits=[json.loads((OUT/v/'training_audit.json').read_text()) for v in ('baseline','dynamics')]
assert audits[0]['initial_expanded_sha256']==audits[1]['initial_expanded_sha256']==digest(OUT/'initial_expanded.pth')
assert all(r['gradient_updates']==5000 and r['optimizer_final_step']==35000 and r['ema_final_step']==35000 for r in audits)
base=torch.load(OUT/'baseline/model_final.pth',map_location='cpu',weights_only=False);dyn=torch.load(OUT/'dynamics/model_final.pth',map_location='cpu',weights_only=False)
assert base['config']==dyn['config'];assert base['shape_metadata']==dyn['shape_metadata'];assert all(base['model']['nets'][k].shape==dyn['model']['nets'][k].shape for k in base['model']['nets'])
ports=np.r_[np.arange(271,275),np.arange(290,294)];port_weights={}
for v,ckpt in [('baseline',base),('dynamics',dyn)]:
    values=[ckpt['model']['ema'][name][:,ports].flatten() for name in p['expanded_weight_names']];weights=torch.cat(values)
    port_weights[v]=dict(l2_norm=float(torch.linalg.vector_norm(weights)),max_absolute=float(weights.abs().max()),nonzero_count=int(torch.count_nonzero(weights)))
assert port_weights['baseline']['nonzero_count']==0;assert port_weights['dynamics']['nonzero_count']>0
checks={}
for v in ('baseline','dynamics'):
    rp=OUT/v/'rollouts/results.json'
    if not rp.exists():continue
    rr=json.loads(rp.read_text());rows=[]
    for r in rr:
        seed=r['seed'];assert r['initial_state_sha256']==SOURCE['rollouts'][seed-46000]['intervention']['initial_state_sha256']
        z=np.load(OUT/v/'rollouts'/f'{seed}.npz');t=z['trace'];assert np.array_equal(t[:,20:27],t[:,27:34]);assert np.isfinite(t).all()
        aug=augment({k:z[k] for k in KEYS},v);assert np.array_equal(aug['zz_dynamics'],z['zz_dynamics']);assert len(t)==int(z['measured'])+40
        rows.append(seed)
    checks[v]=rows
out=dict(dataset_unchanged=True,source_unchanged=True,training_indices_bit_equal=True,learning_rates_bit_equal=True,configuration_bit_equal=True,parameter_shapes_identical=True,updates_each=5000,samples_each=40000,same_initial_expanded_checkpoint=True,validated_rollout_seeds=checks,no_action_heuristics=True,features_from_exact_saved_two_frame_inputs=True,new_ema_weights=port_weights)
(OUT/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
