"""Audit a frozen native dataset and measure information before optimization.

Does not update parameters, select test outcomes, or start production training.
"""
from pathlib import Path
import argparse
import json
import sys
import time
import numpy as np
from transition_pilot import Pool, sha, dump, split_audit, ROOT


def inspect(plan, dataset_path, *, measure_signal=True, device='cuda'):
    dataset_path=Path(dataset_path)
    data=json.loads(dataset_path.read_text());rows=data['rows'];sections=data['sections']
    checks={};g=plan['gates']
    split_audit(rows)
    family_splits={}
    row_by_path={}
    permitted_teachers={p['sha256'] for p in plan['parents']}
    for r in rows:
        path=Path(r['path']).resolve()
        if path.parent not in {dataset_path.resolve().parent/'n3',dataset_path.resolve().parent/'n4'}:
            raise ValueError('Episode outside native collection')
        if path in row_by_path:raise ValueError('Duplicate source episode')
        if r['teacher_sha256'] not in permitted_teachers:raise ValueError('Unapproved Teacher')
        row_by_path[path]=r
        family=r.get('initial_family_id',r['initial_sha256'])
        if family in family_splits and family_splits[family]!=r['split']:
            raise ValueError('Native family crosses splits')
        family_splits[family]=r['split']
        if sha(r['path'])!=r['sha256'] or sha(r['teacher'])!=r['teacher_sha256']:
            raise ValueError('Dataset/teacher mutated')
    for s in sections:
        source=Path(s['source']).resolve()
        if source not in row_by_path:raise ValueError('Section source absent from audited rows')
        r=row_by_path[source]
        expected_family=r.get('initial_family_id',r['initial_sha256'])
        if (s['source_sha256']!=r['sha256'] or s['teacher_sha256']!=r['teacher_sha256'] or
            Path(s['teacher']).resolve()!=Path(r['teacher']).resolve() or s['split']!=r['split'] or
            s['initial_family_id']!=expected_family or s['seed']!=r['seed'] or s['count']!=r['count']):
            raise ValueError('Section provenance/split mismatch')
        if not (0<=s['start']<s['end']<=r['frames'] and 2<=s['prefix']<r['count']):
            raise ValueError('Section frame/prefix bounds')
    checks['collection_complete']=bool(data.get('complete'))
    checks['original_hash']=sha(plan['original']['path'])==plan['original']['sha256']
    checks['all_native']=bool(rows and all(r.get('native_grasp_measured',False) and r.get('native_collector',False) for r in rows)
                              and all(s.get('verified_grasp',False) and s.get('historical_finger_contact_reliable',False) for s in sections))
    summary={}
    for split in ('train','valid'):
        ss=[s for s in sections if s['split']==split]
        families={s['initial_family_id'] for s in ss}
        summary[split]=dict(sections=len(ss),families=len(families),
            teacher_sources=len({s['teacher_sha256'] for s in ss}),
            prefix_counts={str(k):sum(s['prefix']==k for s in ss) for k in (2,3)})
        checks[f'{split}_sections']=len(ss)>=g[f'min_{split}_sections']
        checks[f'{split}_families']=len(families)>=g[f'min_{split}_families']
    train=[s for s in sections if s['split']=='train']
    checks['teacher_diversity']=len({s['teacher_sha256'] for s in train})>=g['min_teacher_sources']
    quality=np.array([s['quality'] for s in train],dtype=float)
    weights=np.array([s['weight'] for s in train],dtype=float)
    qstd=float(quality.std()) if len(quality) else 0.
    checks['score_dispersion']=qstd>=g['min_score_std']
    if len(train):
        assert np.isfinite(weights).all() and (weights>0).all()
        expected=np.mean([s['raw_weight'] for s in train])
        assert abs(expected-data['train_only_normalizer'])<1e-12
        for s in sections:
            assert abs(s['weight']-s['raw_weight']/expected)<1e-12
    signals={}
    if measure_signal and train:
        import torch
        sys.path.insert(0,str(ROOT/'experiments/self_imitation/stack_phased_8h_20261023'))
        from method import PhaseNet
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
        pool=Pool(train);sample=pool.sample(np.random.default_rng(731),512)
        x=torch.tensor(np.stack([r[0] for r in sample]),device=device)
        a=torch.tensor(np.stack([r[1] for r in sample]),device=device)
        p=torch.tensor([r[2] for r in sample],device=device)
        w=torch.tensor([r[3] for r in sample],device=device)
        for parent in plan['parents']:
            assert sha(parent['path'])==parent['sha256']
            model=PhaseNet().to(device)
            model.load_state_dict(torch.load(parent['path'],map_location='cpu',weights_only=False)['model'])
            pred,_=model(x,p);err=(pred-a).square().mean(-1)
            loss0=err.mean();lossw=(err*w).sum()/w.sum()
            grad0=torch.autograd.grad(loss0,tuple(model.parameters()),retain_graph=True,allow_unused=True)
            gradw=torch.autograd.grad(lossw,tuple(model.parameters()),allow_unused=True)
            norm0=float(torch.sqrt(sum(v.square().sum() for v in grad0 if v is not None)))
            normw=float(torch.sqrt(sum(v.square().sum() for v in gradw if v is not None)))
            difference=float(torch.sqrt(sum((v-u).square().sum() for u,v in zip(grad0,gradw) if u is not None and v is not None)))
            byphase={str(k):float(err[p==k].mean().detach()) for k in torch.unique(p).tolist()}
            signals[str(parent['seed'])]=dict(action_mse=float(loss0.detach()),weighted_mse=float(lossw.detach()),
                new_gradient_norm=norm0,weighted_new_gradient_norm=normw,
                weighting_gradient_difference=difference,phase_mse=byphase,sampled_frames=512,
                no_optimizer_step=True)
        checks['new_actor_signal']=all(s['new_gradient_norm']>g['min_new_actor_gradient_norm'] for s in signals.values())
        checks['weighting_not_numerically_identical']=all(s['weighting_gradient_difference']>1e-12 for s in signals.values())
    else:
        checks['new_actor_signal']=False;checks['weighting_not_numerically_identical']=False
    return dict(dataset_path=str(dataset_path.resolve()),dataset_sha256=sha(dataset_path),
        checks=checks,data_ready=all(checks.values()),summary=summary,
        score_mean=float(quality.mean()) if len(quality) else None,score_std=qstd,
        section_weight_ess=float(weights.sum()**2/(weights**2).sum()) if len(weights) else 0.,
        signals=signals,signal_scope='train data only; no parameter updates or held-out selection')


def freeze_manifest(plan,dataset_path,output,report):
    if not report['data_ready']:raise ValueError('Data readiness gates failed')
    if report['dataset_sha256']!=sha(dataset_path) or Path(report['dataset_path']).resolve()!=Path(dataset_path).resolve():
        raise ValueError('Readiness report is stale or belongs to another dataset')
    output=Path(output)
    if output.exists():raise FileExistsError('Frozen dataset manifest already exists')
    raw=json.loads(Path(dataset_path).read_text());sources={r['path']:r['sha256'] for r in raw['rows']}
    frozen=dict(schema='frozen-native-b0-b-v1',production_ready=True,all_native=True,
                source_dataset_path=str(Path(dataset_path).resolve()),source_dataset_sha256=sha(dataset_path),
                source_hashes=sources,sections=raw['sections'],data_readiness=report,
                quality_fitted_on='train only',reserved_tests_used=False)
    dump(output,frozen);return frozen


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--dataset',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--device',default='cuda');args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Readiness report must be new')
    report=inspect(json.loads(args.plan.read_text()),args.dataset,device=args.device)
    dump(args.output,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('signals',)}))


if __name__=='__main__':main()
