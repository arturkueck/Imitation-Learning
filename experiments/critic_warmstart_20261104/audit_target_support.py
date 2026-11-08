"""Frozen target-noise support check at already observed counterfactual probes."""
from pathlib import Path
import argparse
import copy
import json
import numpy as np
import torch
from relative_range import RelativeMovement,widths,project_relative,run

HERE=Path(__file__).resolve().parent


def main(primary,source,output=None,compare_projection=False):
    rows=json.loads((primary/'counterfactuals.json').read_text())
    inputs={}
    result={}
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.use_deterministic_algorithms(True)
    with torch.no_grad():
        for seed in (1,2,3):
            selected=[r for r in rows if r['model_seed']==seed and r['context']=='final']
            ck_path=source/f'seed{seed}/round4.pth';inputs[str(ck_path)]=run.sha(ck_path)
            ck=torch.load(ck_path,map_location='cuda',weights_only=False)
            parent=run.native.historical.load(run.parent(seed)['path']).eval().requires_grad_(False)
            parent.load_state_dict(ck['reference'])
            target=RelativeMovement(copy.deepcopy(parent),parent,.2,.5,.02).cuda().eval().requires_grad_(False)
            target.load_state_dict(ck['target_actor'])
            x=torch.tensor(np.array([r['probe']['x'] for r in selected],dtype='float32'),device='cuda')
            p=torch.tensor([r['probe']['phase'] for r in selected],device='cuda')
            original=parent(x,p)[0];action=target(x,p)[0];limit=widths(original,.2,.5,.02)
            assert ((action-original).abs()<=limit+1e-6).all(),'Noiseless target violates its own mapping'
            generator=torch.Generator(device='cuda').manual_seed(2026113500+seed)
            noise=torch.randn((len(selected),1000,4),device='cuda',generator=generator)*torch.tensor(ck['config']['target_noise_std'],device='cuda')
            noisy=(action[:,None,:]+noise.clamp(-ck['config']['target_noise_clip'],ck['config']['target_noise_clip'])).clamp(-1,1)
            violation=((noisy-original[:,None,:]).abs()>limit[:,None,:]+1e-6).any(-1)
            flip=(noisy[:,:,:3]*original[:,None,:3]<0).any(-1)
            result[str(seed)]=dict(probes=len(selected),draws=violation.numel(),
                outside_actor_bounds=int(violation.sum()),xyz_sign_reversals=int(flip.sum()),
                outside_actor_bounds_fraction=violation.float().mean().item(),
                noiseless_targets_within_bounds=True)
            if compare_projection:
                projected=project_relative(noisy,original[:,None,:],.2,.5,.02)
                outside=((projected-original[:,None,:]).abs()>limit[:,None,:]+1e-6).any(-1)
                reversed_xyz=(projected[:,:,:3]*original[:,None,:3]<0).any(-1)
                assert not outside.any() and not reversed_xyz.any()
                result[str(seed)].update(projected_outside_actor_bounds=int(outside.sum()),
                    projected_xyz_sign_reversals=int(reversed_xyz.sum()),
                    projected_changed_fraction=float(((projected-noisy).abs().amax(-1)>1e-7).float().mean()))
    assert all(run.sha(path)==h for path,h in inputs.items())
    report=dict(schema='target-support-probe-v1',rows=result,input_hashes=inputs,
        seed_rule='2026113500 + parentseed',draws_per_probe=1000,
        interpretation='Synthetic draws from the saved target-noise rule at existing final-policy probes; not a reconstruction of all historical training batches',
        caveat='All tested actions remain legal environment actions in [-1,1]; outside means outside the relative actor constraint, not outside simulator limits',
        optimizer_updates=0,projection_comparison=compare_projection)
    if compare_projection:
        report['projection_source_hashes']={str(p):run.sha(p) for p in (Path(__file__),Path(__file__).with_name('relative_range.py'),Path(__file__).with_name('core.py'))}
    out=output if output is not None else primary/'target_support.json'
    assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);run.dump(out,report)
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--primary',type=Path,default=HERE/'critic_audit_001')
    p.add_argument('--source',type=Path,default=HERE/'pilot_002');p.add_argument('--output',type=Path)
    p.add_argument('--compare-projection',action='store_true');a=p.parse_args()
    if a.compare_projection:assert a.output is not None,'Use a new output path; preserve historical audit results'
    main(a.primary.resolve(),a.source.resolve(),a.output.resolve() if a.output else None,a.compare_projection)
