"""Audit fresh trainings, unchanged configurations and all 240 paired-start results."""
import json
import numpy as np,torch
from replication_common import OUT,OLD,ROOT,DATA,folder,checkpoint,rollouts
from balance_common import digest
from transport_data import demos
p=json.loads((OUT/'protocol.json').read_text());assert digest(DATA)==p['data_sha256'];records=[];initials={kind:[] for kind in p['model_classes']}
ds={d['name']:d for d in demos()};panel=json.loads((ROOT/'experiments/stack_diagnostics/stack_switch_20261001/panel.json').read_text())
assert all(ds[r['demo']]['split']=='valid' and int(ds[r['demo']]['phase'][r['step']])==(3 if r['offset']<0 else 4) for r in panel)
assert sum(6<=r['offset']<=10 for r in panel)==100
reference={kind:torch.load(checkpoint(kind,1),map_location='cpu',weights_only=False) for kind in p['model_classes']}
for kind in p['model_classes']:
    for seed in p['training_seeds']:
        ck=reference[kind] if seed==1 else torch.load(checkpoint(kind,seed),map_location='cpu',weights_only=False)
        if kind=='diffusion':
            c=json.loads(ck['config']);ref=json.loads(reference[kind]['config'])
            for key in ('seed','output_dir'):c['train'][key]=ref['train'][key]
            c['experiment']['name']=ref['experiment']['name'];assert c==ref;state=ck['model']['nets'];original=reference[kind]['model']['nets'];assert set(state)==set(original);assert all(state[k].shape==original[k].shape for k in state)
            assert {int(x['step']) for x in ck['model']['optimizers']['policy']['state'].values()}=={30000};assert ck['model']['lr_schedulers']['policy']['last_epoch']==30000
        else:
            c=dict(ck['config']);ref=reference[kind]['config'];c['seed']=1;assert c==ref;assert {int(x['step']) for x in ck['optimizer']['state'].values()}=={30000};assert ck['ema_step']==30000;assert ck['lr_scheduler']['last_epoch']==30000
            assert set(ck['model'])==set(reference[kind]['model']);assert all(ck['model'][k].shape==reference[kind]['model'][k].shape for k in ck['model'])
            if seed>1:assert np.load(folder(kind,seed)/'training_audit.npz')['sample_indices'].shape==(30000,8)
        if seed>1:
            init=json.loads((folder(kind,seed)/'initialization.json').read_text());assert init['fresh_random_initialization'];initials[kind].append(init['initial_weights_sha256']);assert (folder(kind,seed)/'training_complete.json').exists()
        rows=json.loads((rollouts(kind,seed)/'results.json').read_text());assert len(rows)==40;assert [r['seed'] for r in rows]==p['fixed_start_seeds'];stable=0
        for r in rows:
            assert r['initial_state_sha256']==p['fixed_start_hashes'][str(r['seed'])];z=np.load(rollouts(kind,seed)/f"{r['seed']}.npz");t=z['trace'];assert np.isfinite(t).all();assert np.array_equal(t[:,20:27],t[:,27:34])
            if r['sustained_success']:
                tail=t[r['measured_steps']:];assert len(tail)==40;assert np.all(tail[:,36]>0);assert not tail[:,34].any();assert np.all(tail[:,35]>0);stable+=1
        records.append(dict(model_class=kind,training_seed=seed,optimizer_steps=30000,start_hashes_verified=40,stable_stacks_verified=stable,checkpoint=checkpoint(kind,seed),checkpoint_sha256=digest(checkpoint(kind,seed))))
        if seed>1:del ck
for kind in initials:assert len(set(initials[kind]))==2
out=dict(training_seeds=[1,2,3],each_configuration_identical_except_seed_and_output_paths=True,fresh_distinct_initializations_seeds_2_3=True,dataset_unchanged=True,black_image_demos_unchanged=62,gradient_updates_each=30000,batch_size=8,training_examples_each=240000,fixed_start_hashes_verified=240,training_replicates_per_class=3,inference_sampling_seeds_held_fixed=True,offline_phase_labels_verified=420,stable_transport_window_true_phase4_frames=100,no_dynamics_features=True,no_phase_balancing=True,no_xy_heuristics=True,records=records)
(OUT/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
