"""Versioned, hash-checked BC checkpoint bundles; original run files stay intact."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STORE = ROOT/'praxis/results/models/bc_curriculum'


def libraries():
    sys.path.insert(0, str(HERE/'axis_bc_20261110'))
    import core
    import torch
    return core, torch


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def tensor_digest(state):
    h = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        h.update(name.encode())
        h.update(str(tuple(tensor.shape)).encode())
        h.update(str(tensor.dtype).encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def copy_verified(source, target):
    base, _ = libraries()
    digest = base.sha(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if base.sha(target) != digest:
            raise ValueError('Refusing to overwrite a different bundle: '+str(target))
    else:
        shutil.copy2(source, target)
    if base.sha(target) != digest:
        raise ValueError('Copy hash mismatch')
    return digest


def build():
    base, torch = libraries()
    original = HERE/'axis_bc_20261110/ready_001'
    extension = HERE/'axis_bc_extension_20261110/ready_001'
    fixed = HERE/'axis_bc_completion_10h_20261111/ready_001'
    entries, audit = {}, {}
    cfg = read(original/'config.json')
    for seed in (1,2,3):
        left = torch.load(original/f'mixed_seed{seed}/initial.pth', map_location='cpu', weights_only=False)
        right = torch.load(original/f'curriculum_seed{seed}/initial.pth', map_location='cpu', weights_only=False)
        if left['update'] != 0 or tensor_digest(left['model']) != tensor_digest(right['model']):
            raise ValueError('B/C initialization mismatch')
        audit[seed] = dict(initial_model_sha256=tensor_digest(left['model']), initialization_equal=True)
        sources = [('initial', 0, original/f'mixed_seed{seed}/initial.pth', None)]
        for history in ('mixed','curriculum'):
            sources += [(history, 30000, original/f'{history}_seed{seed}/latest.pth', original/f'schedule_seed{seed}.npz'),
                        (history, 60000, extension/f'{history}_seed{seed}/latest.pth', extension/f'schedule_seed{seed}.npz'),
                        (history+'_fixed_completion', 60000, fixed/f'{history}_seed{seed}/latest.pth', fixed/f'schedule_seed{seed}.npz')]
        for history, update, source, sampler in sources:
            ck = torch.load(source, map_location='cpu', weights_only=False)
            if ck['technical_only'] or ck['update'] != update or ck['seed'] != seed or ck['config'] != cfg:
                raise ValueError('Checkpoint settings incompatible: '+str(source))
            if 'optimizer' not in ck or (update > 0 and not ck['optimizer']['state']):
                raise ValueError('Optimizer missing')
            model_id = f'{history}_s{seed}_u{update}'
            folder = STORE/history/f'seed_{seed}'/f'update_{update}'
            digest = copy_verified(source, folder/'checkpoint.pth')
            sampler_path = None
            if sampler:
                sampler_path = STORE/'sampling'/sampler.parent.parent.name/f'seed_{seed}.npz'
                copy_verified(sampler, sampler_path)
            metadata = dict(id=model_id, seed=seed, history=history, update=update,
                checkpoint=str((folder/'checkpoint.pth').relative_to(ROOT)), sha256=digest,
                source_checkpoint=str(source.resolve().relative_to(ROOT)),
                model_tensor_sha256=tensor_digest(ck['model']),
                config_sha256=hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
                optimizer_present=True, torch_rng_present='torch_rng' in ck,
                cuda_rng_present='cuda_rng' in ck, frozen_completion='completion_reference' in ck,
                sampler_plan=str(sampler_path.relative_to(ROOT)) if sampler_path else None,
                input_contract=dict(features=10, phases=7, actions=['x','y','z','gripper'], rotation='fixed zero',
                    completion_threshold=.8, dataset_arrays_sha256=base.sha(base.ARRAYS)),
                continuation='Restore model + AdamW. Saved plans reproduce prior sampling; new continuation needs an explicit new sampling budget. No automatic overwrite.')
            base.dump(folder/'metadata.json', metadata)
            (folder/'README.md').write_text(f'# {model_id}\n\nUpdate {update}; seed {seed}; history `{history}`.\n\n'
                'checkpoint.pth preserves the model, full AdamW state and saved RNG state. '
                'metadata.json records source hashes, data contract and sampling reference. '
                'Fixed-completion bundles also preserve the entire completion reference.\n\n'
                'Use experiments/curriculum/registry.py restore() or the new A/B/C runner. '
                'Write continuations to a new run; never replace this immutable model version.\n', encoding='utf-8')
            entries[model_id] = metadata
    inventory = dict(schema='bc-model-registry-v1', models=entries, initialization_audit=audit,
                     dataset='existing two-cube demonstrations; privileged state features', optimizer='AdamW')
    base.dump(HERE/'models.json', inventory)
    STORE.mkdir(parents=True, exist_ok=True)
    (STORE/'README.md').write_text('# BC model store\n\nImmutable versioned checkpoint bundles. '
        'Canonical index: experiments/curriculum/models.json. See experiments/curriculum/README.md for lineage, '
        'resume instructions and execution contracts. Original run checkpoints remain intact.\n', encoding='utf-8')
    print(json.dumps(dict(models=len(entries), initialization_pairs_verified=len(audit), store=str(STORE))))
    return inventory


def restore(model_id, device='cpu', restore_rng=False):
    base, torch = libraries()
    entry = read(HERE/'models.json')['models'][model_id]
    path = ROOT/entry['checkpoint']
    if base.sha(path) != entry['sha256']:
        raise ValueError('Model bundle changed')
    ck = torch.load(path, map_location='cpu', weights_only=False)
    model = base.backend().native.historical.PhaseNet(ck['config']['width']).to(device)
    model.load_state_dict(ck['model'])
    optimizer = torch.optim.AdamW(model.parameters(), lr=ck['config']['lr'], weight_decay=ck['config']['weight_decay'])
    optimizer.load_state_dict(ck['optimizer'])
    if entry['frozen_completion']:
        spec = importlib.util.spec_from_file_location('registry_fixed_completion', HERE/'axis_bc_completion_10h_20261111/policy.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import copy
        reference = copy.deepcopy(model)
        reference.load_state_dict(ck['completion_reference'])
        model = module.FixedCompletion(model, reference)
    if restore_rng and 'torch_rng' in ck:
        torch.set_rng_state(ck['torch_rng'])
        if device == 'cuda' and ck.get('cuda_rng'):
            torch.cuda.set_rng_state_all(ck['cuda_rng'])
    return model, optimizer, ck


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('build','inspect'))
    args = p.parse_args()
    if args.command == 'build':
        build()
    else:
        print(json.dumps({k: {f: v[f] for f in ('update','optimizer_present','frozen_completion','checkpoint')}
                          for k,v in read(HERE/'models.json')['models'].items()}, indent=2))
