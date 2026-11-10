"""Final data/config/checkpoint/counter/start/inversion audit and SHA-256 manifest."""
import shutil, platform
import numpy as np,torch
from common import *
from replication_common import checkpoint as baseline_checkpoint,weight_digest

def verify_config(v,kind,seed,c):
    if kind=='direct':
        ref=read(ROOT/'experiments/stack_diagnostics/stack_direct_20261001/config.json');expected=read(folder(v,kind,seed)/'config.json');assert c==expected
        for key in ('seed','action_normalization','observation_normalization'):c[key]=ref[key]
    else:
        ref=json.loads(torch.load(baseline_checkpoint(kind,1),map_location='cpu',weights_only=False)['config'])
        for key in ('seed','output_dir','hdf5_normalize_obs'):c['train'][key]=ref['train'][key]
        c['train']['action_config']=ref['train']['action_config'];c['experiment']['name']=ref['experiment']['name']
    assert c==ref, 'Undeclared configuration difference'

def main():
    protocol=read(OUT/'protocol.json');base=protocol['baseline_protocol'];assert digest(DATA)==base['data_sha256']
    assert digest(OUT/'normalization_stats.json')==protocol['normalization_stats_sha256']
    for name,h in protocol['config_sha256'].items():assert digest(OUT/name)==h
    results=read(OUT/'results_normalization.json');records=[];initials={};refshape={};samples={}
    for kind in ('direct','diffusion'):
        ck=torch.load(baseline_checkpoint(kind,1),map_location='cpu',weights_only=False);state=ck['model'] if kind=='direct' else ck['model']['nets'];refshape[kind]={k:v.shape for k,v in state.items()};del ck,state
    for cell in results['cells']:
        v=cell['variant'];kind=cell['model_class'];seed=cell['training_seed']
        if v=='A':continue
        dest=folder(v,kind,seed);cp=checkpoint(v,kind,seed);ck=torch.load(cp,map_location='cpu',weights_only=False)
        c=copy.deepcopy(ck['config']) if kind=='direct' else json.loads(ck['config']);verify_config(v,kind,seed,c)
        state=ck['model'] if kind=='direct' else ck['model']['nets'];assert {k:v.shape for k,v in state.items()}==refshape[kind]
        assert all(torch.isfinite(v).all() for v in state.values())
        ema=ck['ema'] if kind=='direct' else ck['model']['ema'];assert all(torch.isfinite(v).all() for v in ema.values())
        opt=ck['optimizer'] if kind=='direct' else ck['model']['optimizers']['policy'];sched=ck['lr_scheduler'] if kind=='direct' else ck['model']['lr_schedulers']['policy']
        assert {int(s['step']) for s in opt['state'].values()}=={30000};assert sched['last_epoch']==30000
        tc=read(dest/'training_complete.json');assert tc['optimizer_updates']==tc['scheduler_updates']==tc['ema_updates']==30000
        init=read(dest/'initialization.json');key=(kind,seed)
        assert init['fresh_random_initialization'];initials.setdefault(key,[]).append(init['initial_weights_sha256'])
        if seed>1:
            old_init=read(ROOT/f'experiments/stack_diagnostics/stack_replication_20261001/{kind}/seed_{seed}/initialization.json')
            assert init['initial_weights_sha256']==old_init['initial_weights_sha256'],'Initial weights differ from paired historical training seed'
        audit=np.load(dest/'training_audit.npz');assert audit['loss'].shape==(30000,) and np.isfinite(audit['loss']).all()
        if kind=='direct':
            assert ck['ema_step']==30000 and audit['sample_indices'].shape==(30000,8)
            baseline_dest=ROOT/'experiments/stack_diagnostics/stack_direct_20261001' if seed==1 else ROOT/f'experiments/stack_diagnostics/stack_replication_20261001/direct/seed_{seed}'
            assert np.array_equal(audit['sample_indices'],np.load(baseline_dest/'training_audit.npz')['sample_indices'])
        else:
            assert len(audit['validation'])==6000
            assert audit['sample_indices'].shape==(30000,8)
            samples.setdefault((kind,seed),[]).append(audit['sample_indices'].copy())
            tr=read(dest/'normalization_training_verified.json');assert max(tr['actual_batch_transform_max_error'].values())<1e-6
        rows=read(dest/'rollouts/results.json');assert len(rows)==40 and [r['seed'] for r in rows]==base['fixed_start_seeds']
        stable=0
        for r in rows:
            assert r['initial_state_sha256']==base['fixed_start_hashes'][str(r['seed'])]
            z=np.load(dest/'rollouts'/f"{r['seed']}.npz");t=z['trace'];assert np.isfinite(t).all();assert np.array_equal(t[:,20:27],t[:,27:34]);Normalizer(v).check_actions(t[:,20:27])
            if r['sustained_success']:
                tail=t[r['measured_steps']:];assert len(tail)==40 and np.all(tail[:,36]>0) and np.all(tail[:,35]>0) and not tail[:,34].any();stable+=1
        for filename in ('offline_verification.json','rollout_verification.json'):
            vr=read(dest/filename);assert vr['denormalization_max_error']<1e-6
        records.append(dict(variant=v,kind=kind,seed=seed,updates=30000,scheduler_steps=30000,ema_steps=30000,start_hashes_verified=40,stable_stacks_verified=stable,checkpoint=str(cp),checkpoint_sha256=digest(cp),configuration_only_normalization_changed=True))
        del ck,state,ema,opt
    for key,hashes in initials.items():assert len(set(hashes))==1, f'Initial weights differ across normalization cells: {key}'
    for key,arrays in samples.items():assert all(np.array_equal(a,arrays[0]) for a in arrays),f'Diffusion sample sequence differs across normalization cells: {key}'
    decision=read(OUT/'replication_decision.json')
    required=[(v,k,1) for v in VARIANTS for k in ('direct','diffusion')]
    for v in decision['qualified_variants']:
        for kind in ('direct','diffusion'):
            for seed in (2,3):required.append((v,kind,seed))
    for v,kind,seed in required:
        complete=any(r['variant']==v and r['kind']==kind and r['seed']==seed for r in records)
        assert complete or (folder(v,kind,seed)/'aborted.json').exists(),f'Planned run never completed or documented as aborted: {v}/{kind}/{seed}'
    snapshot=OUT/'source_snapshot';snapshot.mkdir(exist_ok=True)
    sources=[ROOT/'experiments/stack_diagnostics/stack_replication_20261001/ERGEBNISSE.md',ROOT/'experiments/stack_diagnostics/stack_replication_20261001/protocol.json',ROOT/'experiments/stack_diagnostics/stack_replication_20261001/verification.json',ROOT/'experiments/stack_diagnostics/stack_direct_20261001/config.json',ROOT/'experiments/stack_diagnostics/stack_direct_20261001/diffusion_config.json',ROOT/'experiments/stack_diagnostics/stack_followup_20261001/state_scheduler_fixed/config.json']
    sources+=list((ROOT/'experiments/stack_diagnostics/stack_replication_20261001').glob('*/seed_*/config.json'))
    sources+=[SHARED/name for name in ('train_direct.py','train_replication.py','direct_common.py','balance_common.py','dynamics_common.py','transport_data.py','evaluate_replication.py','offline_replication.py')]
    sources+=[ROOT/'experiments/baselines/square/scripts/scheduler_fix.py',ROOT/'experiments/baselines/square/scripts/runtime.py']
    sources += [ROOT/'praxis/upstream/robomimic/robomimic'/name for name in ('scripts/train.py','algo/algo.py','algo/diffusion_policy.py','utils/dataset.py','utils/obs_utils.py','utils/torch_utils.py','utils/train_utils.py','models/diffusion_policy_nets.py')]
    sources += [ROOT/'praxis/src/task_extensions'/name for name in ('__init__.py','environments.py','stack_expert.py')]
    sourcehashes={}
    for path in sources:
        rel=path.relative_to(ROOT);target=snapshot/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);sourcehashes[str(rel)]=digest(path)
    write(OUT/'verification.json',dict(passed=True,dataset_unchanged=True,no_baseline_retraining=True,stats_train_only=True,all_saved_configs_unchanged=True,all_new_model_shapes_match_baseline=True,paired_initial_weights_across_cells=True,direct_sample_indices_match_baseline=True,records=records,source_hashes=sourcehashes,system=dict(python=platform.python_version(),torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0))))
    hashes={}
    for path in OUT.rglob('*'):
        if path.is_file() and path.name not in ('hashes.json','pipeline.log','status.json','verify.log') and path.suffix not in ('.pyc','.tmp'):
            hashes[str(path.relative_to(OUT))]=dict(sha256=digest(path),bytes=path.stat().st_size)
    write(OUT/'hashes.json',dict(algorithm='SHA-256',files=hashes,baseline_checkpoints={f'{k}/seed_{s}':dict(path=baseline_checkpoint(k,s),sha256=digest(baseline_checkpoint(k,s))) for k in ('direct','diffusion') for s in (1,2,3)},dataset=dict(path=str(DATA),sha256=digest(DATA))))
    print(json.dumps(records,indent=2))
if __name__=='__main__':main()
