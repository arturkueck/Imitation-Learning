"""Audit real technical data pairing, immutable other heads, and exact continuation."""
from pathlib import Path
import argparse
import importlib.util
import time

spec = importlib.util.spec_from_file_location('matched_origin_smoke_subject', Path(__file__).with_name('pipeline.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def equal(a, b, torch):
    if torch.is_tensor(a):
        return torch.equal(a, b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k], torch) for k in a)
    if isinstance(a, (tuple, list)):
        return len(a) == len(b) and all(equal(x, y, torch) for x, y in zip(a, b))
    return a == b


def verify(out, target):
    plan = p.read(out/'plan.json')
    if not plan['technical_only'] or p.read(out/'status.json')['state'] != 'COMPLETE':
        raise ValueError('Require completed isolated technical run')
    if target.exists() or not target.is_relative_to(p.ROOT):
        raise ValueError('Require new workspace verification folder')
    base, torch, np = p.h.libraries()
    base.configure(1)
    p.verify(out)
    folder = out/('block_'+plan['blocks'][0]['id'])
    families = {}
    for split in ('train', 'validation'):
        with np.load(folder/f'standard_{split}.npz') as a, np.load(folder/f'targeted_{split}.npz') as b:
            assert np.array_equal(a['family'], b['family']) and np.array_equal(a['y'], b['y'])
            assert len(a['x']) == len(b['x'])
            families[split] = set(a['family'].tolist())
    assert not families['train'] & families['validation']
    previous = base.load_data()['train']
    mask = previous[2] == 0
    old = previous[0][mask], previous[1][mask], previous[3][mask]
    model_id = plan['models'][0]
    parent = p.h.registry.restore(model_id, 'cpu')[0].state_dict()
    verified = []
    target.mkdir(parents=True)
    for source in plan['sources']:
        origin = folder/'training'/source
        destination = target/source
        destination.mkdir()
        for name in ('plan.json', 'corrections_train.npz', 'corrections_validation.npz', f'schedule_{model_id}.npz'):
            (destination/name).write_bytes((origin/name).read_bytes())
        data = p.load_pair(folder, 'standard' if source == 'replay' else source, np)
        fitting_source = 'replay' if source == 'replay' else 'correction'
        for kind in ('actor', 'completion'):
            name = f'{model_id}_{fitting_source}_{kind}'
            expected = torch.load(origin/name/'latest.pth', map_location='cpu', weights_only=False)
            assert all(torch.equal(v, parent[k]) for k, v in expected['model'].items() if not k.startswith('heads.0.'))
            p.bc.fit_branch(destination, plan, model_id, kind, fitting_source, data, old, time.time()+120, resume=origin/name/'update_000002.pth')
            actual = torch.load(destination/name/'latest.pth', map_location='cpu', weights_only=False)
            assert equal(expected['model'], actual['model'], torch), (source, kind, 'model')
            assert equal(expected['optimizer'], actual['optimizer'], torch), (source, kind, 'optimizer')
            assert actual['next_batch'] == plan['updates']
            verified.append(source+'_'+kind)
    result = dict(technical_only=True, paired_label_budgets_equal=True, split_families_disjoint=True,
                  nonapproach_heads_bitwise_unchanged=True, exact_resumed_components=verified, provenance_verified=True)
    p.write(target/'verification.json', result)
    print(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verification-output', type=Path, required=True)
    args = parser.parse_args()
    verify(args.output.resolve(), args.verification_output.resolve())
