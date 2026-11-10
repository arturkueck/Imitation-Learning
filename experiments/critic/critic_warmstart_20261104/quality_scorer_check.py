"""Supervised, family-held-out section-quality check; never loads an IL actor."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import time
import traceback
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import numpy as np
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]
OLD=ROOT/'experiments/self_imitation/partial_self_imitation_20261104/run_001'
NATIVE=ROOT/'experiments/self_imitation/stack_transition_quality_20261024/native_data_v1/manifest.json'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2),encoding='utf-8');tmp.replace(path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def settings():
    return dict(schema='section-quality-predictor-v1',history=5,outcome_frames=50,stride=2,max_examples_per_episode=32,
        target='Next50 post-action frames keep the already formed lower pair valid and free of finger contact',
        eligible='Stage2/phase0 approach, pair currently valid at previous post-state, confirmed past first release, complete50-frame future',
        inputs='Past/current5 actor inputs, executed actions, phases, current relative geometry, stage and retreat; no future, outcomes, IDs or validity labels',
        scope='Historical baseline controller only; no transfer claim to the current guarded controller',
        models=['linear','mlp'],primary_model='mlp',width=64,updates=1000,batch_size=128,lr=.001,weight_decay=.0001,
        crossfit_folds=3,fold_rule='int(initial_sha256[:8],16) modulo3',ensemble_seeds=[35001,35002,35003],
        weighting='Each start family contributes equal total mass',
        gate=dict(min_train_families=40,min_valid_families=20,min_class_families=10,
            min_auc=.75,auc_lower_ci_above=.5,max_brier_fraction_of_constant=.9,
            top_fraction=.25,min_top_precision=.9,min_precision_lift=.05,min_top_precision_lower_ci=.8,
            min_selected_families=20),
        bootstrap_replicates=500,bootstrap_seed=35090,wall_clock_cap_seconds=1800,
        checkpoint_selection='Fixed update1000, no validation-based checkpoint or model selection',
        actor_updates=0,endtest_access=False,new_simulator_rollouts=0)


def features(a,t,history):
    ids=np.arange(t-history+1,t+1)
    pre=a['pre_obs'][ids];pos=pre[:,:9].reshape(len(ids),3,3)
    geometry=np.concatenate([(pos[:,1]-pos[:,0])/.04,(pos[:,2]-pos[:,0])/.1,(pre[:,9:12]-pos[:,1])/.1],axis=1)
    frame=np.concatenate([a['x'][ids],a['a'][ids][:,[0,1,2,6]],np.eye(7)[a['p'][ids].astype(int)],geometry,
                          a['stage'][ids,None]/2,a['retreat'][ids,None].astype(float)],axis=1)
    return frame.astype('float32').ravel()


def extract(a,plan):
    n=len(a['x']);h=plan['history'];future=plan['outcome_frames']
    intact=a['prefix_valid'][:,0].astype(bool)&~a['fingers'][:,:2].any(axis=1)
    releases=[int(r) for r in np.flatnonzero(a['controller_event']==1)
              if r>=9 and a['stage'][r]==1 and intact[r-9:r+1].all()]
    if not releases:return [],dict(reason='no_confirmed_first_release',eligible=0,sampled=0)
    release=releases[0]
    ids=[t for t in range(max(h-1,release+1),n-future+1)
         if a['stage'][t]==2 and a['p'][t]==0 and not a['retreat'][t] and intact[t-1]]
    selected=ids[::plan['stride']]
    if len(selected)>plan['max_examples_per_episode']:
        selected=np.asarray(selected)[np.linspace(0,len(selected)-1,plan['max_examples_per_episode'],dtype=int)].tolist()
    rows=[]
    for t in selected:
        label=float(intact[t:t+future].all())
        pos=a['pre_obs'][t,:9].reshape(3,3)
        distance=float(np.linalg.norm(pos[:2]-a['pre_obs'][t,9:12],axis=1).min())
        rows.append(dict(frame=t,x=features(a,t,h),y=label,distance=distance))
    return rows,dict(reason='eligible' if rows else 'no_uncensored_currently_valid_approach',eligible=len(ids),sampled=len(rows))


def family_weights(family,multiplicity=None):
    unique,inv,counts=np.unique(family,return_inverse=True,return_counts=True)
    mass=np.ones(len(unique)) if multiplicity is None else np.asarray(multiplicity)
    weights=mass[inv]/counts[inv]
    return weights/weights.sum()


def auc(y,p,w):
    order=np.argsort(p,kind='stable');s=np.asarray(p)[order];y=np.asarray(y)[order];w=np.asarray(w)[order]
    starts=np.r_[0,np.flatnonzero(np.diff(s)!=0)+1]
    pos=np.add.reduceat(w*y,starts);neg=np.add.reduceat(w*(1-y),starts)
    if pos.sum()==0 or neg.sum()==0:return None
    return float(np.sum(pos*(np.cumsum(neg)-.5*neg))/(pos.sum()*neg.sum()))


def top_weights(p,w,fraction):
    order=np.argsort(-p,kind='stable');s=np.asarray(p)[order];w=np.asarray(w)
    starts=np.r_[0,np.flatnonzero(np.diff(s)!=0)+1]
    mass=np.add.reduceat(w[order],starts);before=np.cumsum(mass)-mass
    portions=np.clip((fraction-before)/np.maximum(mass,1e-30),0,1)
    allocation=np.repeat(portions,np.diff(np.r_[starts,len(order)]))
    result=np.zeros(len(p));result[order]=w[order]*allocation
    return result


def metrics(y,p,family,multiplicity=None):
    w=family_weights(family,multiplicity);chosen=top_weights(p,w,.25)
    within=[]
    for fam in np.unique(family):
        ids=family==fam
        if np.unique(y[ids]).size==2:within.append(auc(y[ids],p[ids],np.ones(ids.sum())/ids.sum()))
    return dict(auc=auc(y,p,w),brier=float(np.sum(w*(p-y)**2)),prevalence=float(np.sum(w*y)),
        top_precision=float(np.sum(chosen*y)/chosen.sum()),top_mass=float(chosen.sum()),
        selected_families=len(np.unique(family[chosen>0])),
        mixed_outcome_families=len(within),within_family_auc=float(np.mean(within)) if within else None)


class Scorer(nn.Module):
    def __init__(self,mean,std,kind,width):
        super().__init__();self.register_buffer('mean',torch.tensor(mean,dtype=torch.float32))
        self.register_buffer('scale',torch.tensor(std,dtype=torch.float32).clamp_min(.001))
        n=len(mean)
        self.net=nn.Linear(n,1) if kind=='linear' else nn.Sequential(nn.Linear(n,width),nn.SiLU(),nn.Linear(width,width),nn.SiLU(),nn.Linear(width,1))
    def forward(self,x):return self.net(((x-self.mean)/self.scale).clamp(-10,10)).squeeze(-1)


def fit(train,kind,seed,plan,out,label,deadline):
    torch.manual_seed(seed);x=train['x'];y=train['y'];w=family_weights(train['family'])
    mean=np.sum(w[:,None]*x,axis=0);std=np.sqrt(np.sum(w[:,None]*(x-mean)**2,axis=0))
    model=Scorer(mean,std,kind,plan['width']).cuda()
    tx=torch.tensor(x,device='cuda');ty=torch.tensor(y,device='cuda');tw=torch.tensor(w,device='cuda')
    opt=torch.optim.AdamW(model.parameters(),lr=plan['lr'],weight_decay=plan['weight_decay'])
    generator=torch.Generator(device='cuda').manual_seed(seed+1000)
    for step in range(1,plan['updates']+1):
        if time.time()>=deadline or (out/'STOP').exists():raise TimeoutError('Scorer check budget or STOP')
        ids=torch.multinomial(tw,plan['batch_size'],replacement=True,generator=generator)
        loss=nn.functional.binary_cross_entropy_with_logits(model(tx[ids]),ty[ids]);assert torch.isfinite(loss)
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);opt.step()
        if step==1 or step%200==0:
            write(out/'status.json',dict(state='SCORER_TRAINING',model=label,step=step,loss=float(loss.detach()),updated_unix=time.time()))
    folder=out/'models';folder.mkdir(exist_ok=True)
    torch.save(dict(model=model.state_dict(),kind=kind,seed=seed,updates=step,training_families=np.unique(train['family']).tolist(),
                    actor_updates=0,normalization='Training families of this fit only'),folder/f'{label}.pth')
    model.eval().requires_grad_(False)
    return model


@torch.no_grad()
def predict(model,x):
    return np.concatenate([model(torch.tensor(x[i:i+1024],device='cuda')).sigmoid().cpu().numpy() for i in range(0,len(x),1024)])


def subset(data,mask):return {k:v[mask] for k,v in data.items()}


def main(out):
    plan=settings();audit=read(OLD/'dataset_audit.json');native=read(NATIVE);extra=read(OLD/'input/manifest.json')
    rows=[r for r in native['rows'] if r['count']==3]+extra['rows']
    assert len(rows)==340 and {r['path'] for r in rows}==set(audit['sources'])
    families={}
    for row in rows:
        assert row['split'] in ('train','valid')
        assert families.setdefault(row['initial_sha256'],row['split'])==row['split'],'Family leakage'
        assert row['collector_schema']=='native_v2_forward_synchronized'
        assert row['native_grasp_measured'] and row['restored_contacts_and_grasp_verified']
    inputs=dict(audit['sources'])
    for path in (Path(__file__),OLD/'dataset_audit.json',NATIVE,OLD/'input/manifest.json'):
        inputs[str(path.resolve())]=sha(path)
    for r in rows:inputs[r['teacher']]=r['teacher_sha256']
    assert not out.exists();out.mkdir()
    write(out/'protocol.json',dict(**plan,prepared_unix=time.time(),input_hashes=inputs))
    snap=out/'source_snapshot';snap.mkdir();shutil.copy2(Path(__file__),snap/'quality_scorer_check.py')
    deadline=time.time()+plan['wall_clock_cap_seconds'];records=[];inventory=[]
    for index,row in enumerate(rows):
        assert sha(row['path'])==inputs[row['path']]
        with np.load(row['path'],allow_pickle=False) as f:
            needed=('x','a','p','stage','retreat','pre_obs','prefix_valid','fingers','controller_event','initial')
            a={k:f[k].copy() for k in needed}
        assert hashlib.sha256(a['initial'].tobytes()).hexdigest()==row['initial_sha256']
        selected,info=extract(a,plan)
        inventory.append(dict(source=row['path'],family=row['initial_sha256'],split=row['split'],**info))
        for record in selected:
            records.append(dict(**record,family=row['initial_sha256'],split=row['split'],source=row['path']))
        if index%25==0:write(out/'status.json',dict(state='EXTRACTING',episode=index+1,total=len(rows),updated_unix=time.time()))
    data={}
    for split in ('train','valid'):
        selected=[r for r in records if r['split']==split]
        data[split]=dict(x=np.stack([r['x'] for r in selected]),y=np.asarray([r['y'] for r in selected],dtype='float32'),
            family=np.asarray([r['family'] for r in selected]),frame=np.asarray([r['frame'] for r in selected]),
            source=np.asarray([r['source'] for r in selected]),distance=np.asarray([r['distance'] for r in selected]))
        assert np.isfinite(data[split]['x']).all()
    assert not set(data['train']['family'])&set(data['valid']['family'])
    counts={split:dict(examples=len(d['y']),families=len(np.unique(d['family'])),
        positive_families=len(np.unique(d['family'][d['y']==1])),negative_families=len(np.unique(d['family'][d['y']==0])),
        safe_examples=int(d['y'].sum())) for split,d in data.items()}
    write(out/'dataset_audit.json',dict(counts=counts,inventory=inventory,feature_dimensions=data['train']['x'].shape[1],
         label_input_separation='Features at t-history+1..t; labels from post-action t..t+49',endtest_files_read=0))
    evaluate(out,plan,data,counts,inputs)


def evaluate(out,plan,data,counts,inputs):
    """Fixed-budget scorer fits on an already audited, family-separated dataset."""
    deadline=time.time()+plan['wall_clock_cap_seconds']
    assert counts['train']['families']>=40 and min(counts['train']['positive_families'],counts['train']['negative_families'])>=10,'Insufficient scorer training support'
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
    train=data['train'];valid=data['valid'];fold=np.asarray([int(f[:8],16)%3 for f in train['family']])
    predictions={};oof={};train_fit={};fold_proof=[]
    for kind in plan['models']:
        oof[kind]=np.zeros(len(train['y']))
        for k in range(3):
            mask=fold!=k;held=fold==k
            assert held.any() and mask.any()
            assert not set(train['family'][mask])&set(train['family'][held])
            model=fit(subset(train,mask),kind,35100+k,plan,out,f'{kind}_fold{k}',deadline)
            oof[kind][held]=predict(model,train['x'][held])
            fold_proof.append(dict(kind=kind,fold=k,train_families=len(np.unique(train['family'][mask])),
                                   predicted_families=len(np.unique(train['family'][held])),disjoint=True))
        held_predictions=[];fitted=[]
        for seed in plan['ensemble_seeds']:
            model=fit(train,kind,seed,plan,out,f'{kind}_seed{seed}',deadline)
            held_predictions.append(predict(model,valid['x']));fitted.append(predict(model,train['x']))
        predictions[kind]=np.mean(held_predictions,axis=0);train_fit[kind]=np.mean(fitted,axis=0)
    # All final models are frozen before the first held-out quality evaluation.
    w=family_weights(train['family']);prior=float(np.sum(w*train['y']))
    predictions['constant']=np.full(len(valid['y']),prior)
    held_metrics={kind:metrics(valid['y'],p,valid['family']) for kind,p in predictions.items()}
    held_metrics['current_distance_rank_only']=metrics(valid['y'],valid['distance'],valid['family'])
    held_metrics['current_distance_rank_only']['brier']=None
    learning={kind:dict(fitted_train=metrics(train['y'],train_fit[kind],train['family']),
                        out_of_fold_train=metrics(train['y'],oof[kind],train['family'])) for kind in plan['models']}
    np.savez_compressed(out/'scores.npz',train_family=train['family'],train_frame=train['frame'],train_source=train['source'],train_y=train['y'],
        train_oof_mlp=oof['mlp'],train_oof_linear=oof['linear'],valid_family=valid['family'],valid_frame=valid['frame'],valid_source=valid['source'],
        valid_y=valid['y'],valid_mlp=predictions['mlp'],valid_linear=predictions['linear'])
    write(out/'crossfit_audit.json',dict(folds=fold_proof,validation_families_never_trained=True,actor_weights_exported=False))
    rng=np.random.default_rng(plan['bootstrap_seed']);nf=len(np.unique(valid['family']));boot=[]
    for _ in range(plan['bootstrap_replicates']):
        multiplicity=np.bincount(rng.integers(nf,size=nf),minlength=nf)
        m=metrics(valid['y'],predictions['mlp'],valid['family'],multiplicity)
        if m['auc'] is not None:boot.append([m['auc'],m['top_precision']])
    boot=np.asarray(boot);ci=dict(auc=np.quantile(boot[:,0],[.025,.975]).tolist(),top_precision=np.quantile(boot[:,1],[.025,.975]).tolist())
    m=held_metrics['mlp'];g=plan['gate']
    gates=dict(valid_support=counts['valid']['families']>=g['min_valid_families'] and min(counts['valid']['positive_families'],counts['valid']['negative_families'])>=g['min_class_families'],
        discrimination=m['auc'] is not None and m['auc']>=g['min_auc'] and ci['auc'][0]>g['auc_lower_ci_above'],
        calibration=m['brier']<=g['max_brier_fraction_of_constant']*held_metrics['constant']['brier'],
        selection_precision=m['top_precision']>=g['min_top_precision'] and m['top_precision']>=m['prevalence']+g['min_precision_lift'] and ci['top_precision'][0]>=g['min_top_precision_lower_ci'],
        selected_family_support=m['selected_families']>=g['min_selected_families'])
    result=dict(validation=held_metrics,learning=learning,family_bootstrap_95ci=ci,gates=gates,scorer_test_passed=all(gates.values()),
        scope=plan['scope'],
        actor_training_started=False,current_guarded_controller_validated=False,actor_training_ready=False)
    write(out/'results.json',result)
    assert all(sha(path)==h for path,h in inputs.items()),'Inputs changed during scorer check'
    write(out/'verification.json',dict(input_hashes_unchanged=True,crossfit_family_disjoint=True,validation_families_never_trained=True,
        actor_weights_loaded=False,actor_updates=0,scorer_fits=12,scorer_updates=12000,source_rows=sum(len(np.unique(d['source'])) for d in data.values()),heldout_families=counts['valid']['families']))
    write(out/'status.json',dict(state='COMPLETED',scorer_test_passed=result['scorer_test_passed'],updated_unix=time.time()))
    print(json.dumps(dict(state='COMPLETED',counts=counts,validation_mlp=m,gates=gates,scorer_test_passed=result['scorer_test_passed'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:main(a.output.resolve())
    except Exception:
        if a.output.exists():write(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
