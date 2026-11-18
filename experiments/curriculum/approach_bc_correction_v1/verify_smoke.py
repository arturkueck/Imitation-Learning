"""Verify split isolation, composed policy checkpoints, and exact resumed updates."""
from pathlib import Path
import argparse
import importlib.util
import time

spec=importlib.util.spec_from_file_location('approach_bc_resume_test_subject',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def equal(left,right,torch):
    if torch.is_tensor(left):return torch.equal(left,right)
    if isinstance(left,dict):return left.keys()==right.keys() and all(equal(left[k],right[k],torch) for k in left)
    if isinstance(left,(list,tuple)):return len(left)==len(right) and all(equal(a,b,torch) for a,b in zip(left,right))
    return left==right


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--verification-output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();target=args.verification_output.resolve();plan=p.read(out/'plan.json')
    if not plan['technical_only'] or p.read(out/'status.json')['state']!='COMPLETE':raise ValueError('Require completed technical run')
    if target.exists() or not target.is_relative_to(p.ROOT):raise ValueError('Require new workspace verification output')
    base,torch,np=p.h.libraries();base.configure(1);p.verify(out);data={};families={}
    for split in ('train','validation'):
        with np.load(out/f'corrections_{split}.npz') as archive:
            data[split]=tuple(archive[k].copy() for k in ('x','a','y'));families[split]=set(archive['family'].tolist())
        assert data[split][2].sum()>0
    assert not families['train']&families['validation']
    target.mkdir(parents=True)
    model_id=plan['models'][0]
    for name in ('plan.json','corrections_train.npz','corrections_validation.npz',f'schedule_{model_id}.npz'):(target/name).write_bytes((out/name).read_bytes())
    olddata=base.load_data()['train'];mask=olddata[2]==0;old=(olddata[0][mask],olddata[1][mask],olddata[3][mask])
    verified=[]
    for source in ('replay','correction'):
        for kind in ('actor','completion'):
            folder=out/f'{model_id}_{source}_{kind}'
            parent=folder/'update_000002.pth';expected=torch.load(folder/'latest.pth',map_location='cpu',weights_only=False)
            p.fit_branch(target,plan,model_id,kind,source,data,old,time.time()+120,resume=parent)
            actual=torch.load(target/f'{model_id}_{source}_{kind}'/'latest.pth',map_location='cpu',weights_only=False)
            assert equal(expected['model'],actual['model'],torch),(source,kind,'weights')
            assert equal(expected['optimizer'],actual['optimizer'],torch),(source,kind,'optimizer')
            assert expected['next_batch']==actual['next_batch']==4
            verified.append(source+'_'+kind)
    result=dict(exact_resumed_components=verified,next_batch=4,train_validation_families_disjoint=True,
        source_provenance_verified=True,technical_only=True)
    p.write(target/'verification.json',result);print(result)


if __name__=='__main__':main()
