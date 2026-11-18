"""Restore versioned BC weights/AdamW after checking model and sampling files."""
from pathlib import Path
import argparse
import json
import registry


def load(model_id, device='cpu', restore_rng=True):
    base, _ = registry.libraries()
    sampling = registry.read(registry.HERE/'model_sampling_hashes.json')
    if model_id in sampling:
        record = sampling[model_id]
        if base.sha(registry.ROOT/record['path']) != record['sha256']:
            raise ValueError('Saved sampling reference changed: '+model_id)
    return registry.restore(model_id, device=device, restore_rng=restore_rng)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model_id')
    parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    args=parser.parse_args()
    model,optimizer,checkpoint=load(args.model_id,args.device)
    print(json.dumps(dict(model_id=args.model_id,update=checkpoint['update'],optimizer_restored=True,
                          parameters=sum(p.numel() for p in model.parameters()),training_started=False)))
