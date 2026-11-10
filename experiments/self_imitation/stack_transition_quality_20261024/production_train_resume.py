"""Paired B0/B training and frozen evaluation. Default is dry-run.

Production requires a hash-bound explicit user release file. Technical mode is
limited to five updates and cannot run independent/reserved evaluations.
"""
from pathlib import Path
import argparse, copy, hashlib, json, shutil, time
import numpy as np
from transition_pilot import Pool, weighted_loss, sha, dump, ROOT, ARRAYS
from online_evaluation import selection_score, check_deadline

def release_check(plan_path,release_path):
    plan_path=Path(plan_path);release=json.loads(Path(release_path).read_text())
    assert release.get('user_approved') is True,'explicit user Go missing'
    assert release.get('plan_sha256')==sha(plan_path),'release is not bound to this plan'
    assert release.get('expires_unix',0)>time.time(),'release expired'
    return release

def _batch(original,groups,replay,new,rng):
    ids=np.array([rng.choice(groups[p]) for p in rng.integers(7,size=32)])
    rr=replay.sample(rng,16);nn=new.sample(rng,16)
    x=np.r_[original['x'][ids],np.stack([r[0] for r in rr+nn])].astype('float32')
    a=np.r_[original['a'][ids],np.stack([r[1] for r in rr+nn])].astype('float32')
    p=np.r_[original['p'][ids],[r[2] for r in rr+nn]]
    sample_hash=hashlib.sha256(ids.tobytes()+json.dumps([(r[4],r[5]) for r in rr+nn]).encode()).hexdigest()
    return x,a,p,original['y'][ids],np.array([r[3] for r in nn],np.float32),sample_hash

def actor_loss(errors,weights):
    """Unveraenderter Loss fuer die Wiederaufnahme von production_train.

    0.5 Original-BC + 0.25 Erfolgs-Replay + 0.25 gewichtete neue Frames.
    Die Gewichte kommen aus dem Dataset, nicht aus einem Critic-Netz.
    Auch beim Resume bleiben Aufteilung und Batchnormalisierung gleich.
    """
    assert len(errors)==64
    return .5*errors[:32].mean()+.25*errors[32:48].mean()+.25*weighted_loss(errors[48:],weights)

def _save(path,model,opt,update,parent,rng,arm,technical):
    import torch
    ck=dict(model=model.state_dict(),optimizer=opt.state_dict(),update=update,
            parent=str(parent),parent_sha256=sha(parent),original_and_extra_rng=rng.bit_generator.state,
            torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            arm=arm,technical_only=technical)
    tmp=path.with_suffix('.tmp');torch.save(ck,tmp);tmp.replace(path)

def train_paired(plan,manifest,output,deadline,evaluator=None,*,technical_steps=None,release=None,device='cuda',resume_from=None):
    import torch,sys
    sys.path.insert(0,str(ROOT/'experiments/self_imitation/stack_phased_8h_20261023'))
    from method import PhaseNet
    technical=technical_steps is not None
    if technical:assert 1<=technical_steps<=5,'technical update cap is5'
    else:
        assert release and release.get('user_approved') is True,'production requires release'
        assert plan.get('production_enabled') is True,'plan not activated'
        assert manifest.get('production_ready') is True and manifest.get('all_native',False),'native data gates not passed'
        assert evaluator is not None,'online evaluator required'
    for path,expected in manifest.get('source_hashes',{}).items():assert sha(path)==expected,'changed dataset source'
    new=Pool([s for s in manifest['sections'] if s['split']=='train'])
    replay_path=Path(plan['replay_manifest']['path']);assert sha(replay_path)==plan['replay_manifest']['sha256']
    replayrows=json.loads(replay_path.read_text())['rows']
    replay=Pool([dict(source=r['path'],start=0,end=r['frames'],weight=1.) for r in replayrows if r['count']==3 and r['split']=='train' and r['success']])
    with np.load(ARRAYS) as f:original={k:f['train_'+k].copy() for k in ('x','a','p','y')}
    assert sha(plan['original']['path'])==plan['original']['sha256'],'original changed'
    groups=[np.flatnonzero(original['p']==p) for p in range(7)]
    pw=torch.tensor([min(50.,max(1.,(1-original['y'][g]).sum()/max(original['y'][g].sum(),1))) for g in groups],device=device)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    cfg=plan['pilot'];steps=technical_steps if technical else int(cfg['steps']);start_update=0
    eval_updates=set() if technical else set(cfg['eval_updates']);members={};rngs={};baseline={};selections={};history=[]
    for parent in plan['parents']:
        seed=int(parent['seed']);assert sha(parent['path'])==parent['sha256'],'parent changed'
        rngs[seed]=np.random.default_rng(seed)
        for arm in ('B0','B'):
            model=PhaseNet().to(device);model.load_state_dict(torch.load(parent['path'],map_location='cpu',weights_only=False)['model']);model.train()
            opt=torch.optim.AdamW(model.parameters(),lr=cfg['lr'],weight_decay=cfg['weight_decay'])
            name=f'{arm}_seed{seed}';folder=output/name;folder.mkdir();path=folder/'update0.pth'
            _save(path,model,opt,0,parent['path'],rngs[seed],arm,technical)
            members[name]=dict(model=model,opt=opt,seed=seed,arm=arm,parent=parent['path'],folder=folder,update=0)
            selections[name]=dict(path=str(path),update=0,score=None)
    if resume_from is not None:
        resume_from=Path(resume_from)
        saved={name:torch.load(resume_from/name/'update3000.pth',map_location='cpu',weights_only=False) for name in members}
        assert {int(v['update']) for v in saved.values()}=={3000},'common update3000 required'
        for seed in rngs:
            a=saved[f'B0_seed{seed}']['original_and_extra_rng'];b=saved[f'B_seed{seed}']['original_and_extra_rng']
            assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True),'paired RNG mismatch'
            rngs[seed].bit_generator.state=a
            baseline[seed]=json.loads((resume_from/f'B0_seed{seed}'/'dev_0.json').read_text())['metrics']
        for name,m in members.items():
            ck=saved[name]
            assert not ck['technical_only'] and ck['arm']==m['arm']
            assert ck['parent_sha256']==sha(m['parent']),'parent provenance changed'
            m['model'].load_state_dict(ck['model']);m['opt'].load_state_dict(ck['optimizer']);m['update']=3000
            _save(m['folder']/'update3000.pth',m['model'],m['opt'],3000,m['parent'],rngs[m['seed']],m['arm'],technical)
        selections=json.loads((resume_from/'selected_development.json').read_text())
        assert set(selections)==set(members) and {v['update'] for v in selections.values()}=={0},'common prior selection required'
        history=json.loads((resume_from/'learning_curve.json').read_text())
        start_update=3000
        steps=start_update+technical_steps if technical else int(cfg['steps'])
        last=saved['B_seed3'];torch.set_rng_state(last['torch_rng'])
        if device.startswith('cuda') and last.get('cuda_rng'):torch.cuda.set_rng_state_all(last['cuda_rng'])
        dump(output/'resume_provenance.json',dict(source=str(resume_from.resolve()),common_update=3000,
            optimizer_and_sampler_restored=True,omitted_common_selection_panel=3000,
            remaining_eval_updates=[u for u in cfg['eval_updates'] if u>start_update],
            note='Incomplete3000 panel excluded for all arms; prior common update0 retained; never repeat interrupted starts'))
    dump(output/'config.json',dict(technical_only=technical,planned_updates=steps,models=list(members),loss='0.50 original +0.25 replay +0.25 normalized weighted new +0.1 original BCE',paired_samples=True))
    def evaluate_all(update):
        # Both arms share the same parent at0; measure it once per seed.
        pending=copy.deepcopy(selections)
        for name,m in members.items():
            path=m['folder']/f'update{update}.pth'
            if update==0 and m['seed'] in baseline:metrics=baseline[m['seed']]
            else:metrics=evaluator(path,m['seed'],update,'development',deadline)
            if update==0:baseline[m['seed']]=metrics
            score=selection_score(metrics,baseline[m['seed']],update)
            dump(m['folder']/f'dev_{update}.json',dict(metrics=metrics,selection_score=score))
            if pending[name]['score'] is None or score>tuple(pending[name]['score']):
                pending[name]=dict(path=str(path),update=update,score=list(score),metrics=metrics)
        # Commit selection only after every arm/seed has completed this panel.
        # A deadline halfway through evaluation retains the previous common panel.
        selections.clear();selections.update(pending)
        dump(output/'selected_development.json',selections)
    if 0 in eval_updates and resume_from is None:evaluate_all(0)
    state='COMPLETE';completed=start_update;failure=None
    try:
        for update in range(start_update+1,steps+1):
            check_deadline(deadline-1) # finish a complete six-model update round before stopping.
            for seed in rngs:
                batch=_batch(original,groups,replay,new,rngs[seed]);x,a,p,y,w,sample_hash=batch
                xx=torch.tensor(x,device=device);aa=torch.tensor(a,device=device);pp=torch.tensor(p,device=device)
                for arm in ('B0','B'):
                    m=members[f'{arm}_seed{seed}'];model=m['model'];opt=m['opt'];model.train()
                    pred,z=model(xx,pp);errors=(pred-aa).square().mean(-1)
                    weights=torch.tensor(np.ones(16,np.float32) if arm=='B0' else w,device=device)
                    actor=actor_loss(errors,weights);mask=pp[:32]<6
                    bce=torch.nn.functional.binary_cross_entropy_with_logits(z[:32][mask],torch.tensor(y,device=device)[mask],pos_weight=pw[pp[:32]][mask])
                    loss=actor+cfg.get('completion_coefficient',.1)*bce
                    assert torch.isfinite(loss),'nonfinite loss'
                    opt.zero_grad(set_to_none=True);loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['gradient_clip']);assert torch.isfinite(norm)
                    opt.step();m['update']=update
                    if update%1000==0 or update in eval_updates or update==steps or technical:
                        history.append(dict(model=f'{arm}_seed{seed}',update=update,actor_loss=float(actor.detach()),completion_loss=float(bce.detach()),gradient_norm=float(norm),sample_sha256=sample_hash))
            completed=update
            if update%1000==0 or update in eval_updates or update==steps:
                for m in members.values():_save(m['folder']/f'update{update}.pth',m['model'],m['opt'],update,m['parent'],rngs[m['seed']],m['arm'],technical)
                dump(output/'status.json',dict(state='TRAINING',updates={name:m['update'] for name,m in members.items()},round=update))
                dump(output/'learning_curve.json',history)
            if update in eval_updates:evaluate_all(update)
    except TimeoutError:state='PARTIAL_TIME_CAP'
    except Exception as exc:
        state='FAILED';failure=exc
    # Never silently choose an unevaluated final checkpoint after a time cap.
    for name,m in members.items():
        _save(m['folder']/'latest.pth',m['model'],m['opt'],m['update'],m['parent'],rngs[m['seed']],m['arm'],technical)
    dump(output/'learning_curve.json',history)
    dump(output/'selected_development.json',selections)
    dump(output/'status.json',dict(state=state,completed_round=completed,updates={name:m['update'] for name,m in members.items()},technical_only=technical))
    if failure is not None:
        dump(output/'failure.json',dict(error=repr(failure),updates={name:m['update'] for name,m in members.items()},budget_fairness='Failure can interrupt a round; actual per-model updates are reported, never silently equated'))
        raise failure
    return dict(state=state,selections=selections,updates={name:m['update'] for name,m in members.items()},technical_only=technical)

def freeze_and_test(result,output,evaluator,deadline):
    """All checkpoints frozen before any confirmation or reserved test is read."""
    assert not result['technical_only'],'technical outputs cannot run endtests'
    output=Path(output);output.mkdir(parents=True,exist_ok=False);frozen={}
    for name,s in result['selections'].items():
        assert s['score'] is not None,'no complete development selection'
        path=output/(name+'.pth');shutil.copy2(s['path'],path)
        frozen[name]=dict(path=str(path),sha256=sha(path),source=s['path'],update=s['update'])
    dump(output/'selection.json',frozen)
    results={}
    for split in ('confirmation','reserved_final'):
        for name,f in frozen.items():
            check_deadline(deadline);assert sha(f['path'])==f['sha256'],'frozen model mutated'
            marker=output/f'{name}_{split}.started.json'
            with marker.open('x',encoding='utf-8') as stream:json.dump(dict(started_unix=time.time()),stream)
            # Existing marker forbids accidental repeat of reserved starts.
            metrics=evaluator(f['path'],int(name.rsplit('seed',1)[1]),f['update'],split,deadline)
            results[f'{name}_{split}']=metrics;dump(output/f'{name}_{split}.json',metrics)
    dump(output/'results.json',results);return results

def main():
    p=argparse.ArgumentParser();p.add_argument('--train',action='store_true');p.add_argument('--plan',type=Path);p.add_argument('--release',type=Path)
    args=p.parse_args()
    if not args.train:print(json.dumps(dict(mode='DRY_RUN',training_started=False)));return
    assert args.plan and args.release,'plan and explicit user release required'
    release_check(args.plan,args.release)
    raise SystemExit('Use the single session orchestrator to pass frozen data/evaluator/deadline; standalone launch is prohibited.')

if __name__=='__main__':main()
