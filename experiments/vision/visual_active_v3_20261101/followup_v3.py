"""One bounded V3 Anschlussphase. Offline supervised heads + simulation replay.

All files are new followup artifacts; frozen perception and original evidence
remain untouched. There is no real robot driver in this program.
"""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys,json,time,hashlib,traceback,itertools,copy
from datetime import datetime,timezone
from dataclasses import asdict
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
import site
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
sys.path.insert(0,str(ROOT/'praxis/src'))
import numpy as np,torch
from torch.nn import functional as F
from night import save,atomic_checkpoint,independence
from train_v3 import sha,load_data
from preflight import settings
from data_v3 import PoseGenerator,object_path_free
from model_v3 import ScenePerception
from request_heads import RequestHeads,OBSERVATION_FEATURES,CANDIDATE_FEATURES
from followup_core import (infer,observed,candidate_features,observable,errors,mean_error,
                           robot_projection,permitted_histories,summarize_binary)
from active_view.capture_requests import RequestJournal,CaptureRequest,pose_from_mujoco,utc_now,pose_error
from PIL import Image

RUN=HERE/'run_001';SMOKE='--smoke' in sys.argv
OUT=RUN/(('followup_smoke_repair001' if '--repair' in sys.argv else 'followup_smoke_002' if '--second' in sys.argv else 'followup_smoke_001') if SMOKE else 'followup_001')
PHASE=json.loads((RUN/'followup_001/phase.json').read_text())
CFG=json.loads((RUN/'config.json').read_text())
END=min(PHASE['head_phase_deadline_unix'],CFG['deadline_unix'])


def status(stage,**values):
    save(OUT/'status.json',dict(stage=stage,time=datetime.now(timezone.utc).isoformat(),
                              heartbeat_unix=time.time(),pid=os.getpid(),**values))
    print(json.dumps(dict(stage=stage,**values)),flush=True)


def stop(reserve=120):
    if time.time()>=END-reserve or (RUN/'STOP_REQUESTED').exists() or (OUT/'STOP_REQUESTED').exists():
        raise TimeoutError('Bounded followup deadline or STOP_REQUESTED')


def audit():
    checks=json.loads((RUN/'checkpoint_hashes.json').read_text())
    hashes={n:sha(RUN/'checkpoints'/n)==v for n,v in checks.items()}
    if not all(hashes.values()):raise RuntimeError('Checkpoint hash mismatch')
    source_checks={name:sha(ROOT/name)==expected for name,expected in CFG['source_hashes'].items()}
    if not all(source_checks.values()):raise RuntimeError('Frozen perception source provenance changed')
    manifests={}; families=[]
    for split in ['train','validation']:
        m=json.loads((RUN/'data'/split/'manifest.json').read_text())
        verification={n:sha(RUN/'data'/split/n)==v for n,v in m['files'].items()}
        if not all(verification.values()):raise RuntimeError('Data hash mismatch '+split)
        a=np.load(RUN/'data'/split/'family.npy',mmap_mode='r');families.append(set(map(tuple,a)))
        manifests[split]=dict(families=len(a),seed=m['seed'],hashes=verification)
    if families[0]&families[1]:raise RuntimeError('Perception family leakage')
    curves=json.loads((RUN/'curves.json').read_text());res=json.loads((RUN/'results.json').read_text())
    means={a:float(np.mean([res['validation'][f'{s}/{a}']['robust']['balanced_loss'] for s in [1,2,3]])) for a in ['M1','M2']}
    selected=min(means,key=means.get)
    if selected!='M2':raise RuntimeError('Predeclared validation selection disagrees')
    latest=torch.load(RUN/'checkpoints/latest.pth',map_location='cpu',weights_only=False)
    resume=dict(epoch=latest['epoch'],sampler_position=latest['sampler_position'],
                steps={k:v['step'] for k,v in latest['models'].items()},
                optimizer_states={k:len(v['optimizer']['state']) for k,v in latest['models'].items()},
                rng_present=all(k in latest for k in ['numpy_rng','torch_rng','cuda_rng']),
                verified_full_sampler_resume=False,
                reason='Partial epoch checkpoint was overwritten by validate(...), which defaults sampler_position=0. No validated high-level resume entrypoint; do not pretend exact continuation.')
    decision=dict(checkpoint_hashes=hashes,frozen_source_hashes=source_checks,data=manifests,family_overlap=0,variant_means=means,selected=selected,
                  seeds=[1,2,3],resume=resume,continuation=False,perception_frozen=True,
                  explanation='Late M2 validation remains nonconverged in seeds1/2, but seed3 regresses at 33/33.717 while probe stays near .10; M1 seed3 also regresses. This is mixed residual learning/instability, not proof that all seeds merely need longer. Full sampler resume is unverified. Freeze validation-selected checkpoints for separate head phase.',
                  tests_before_decision=res['final_tests_evaluated'])
    save(OUT/'decision.json',decision)
    if res['final_tests_evaluated']:raise RuntimeError('Tests already accessed before decision')
    return decision


def collect(g,split,count,seed):
    folder=OUT/'data'/split;folder.mkdir(parents=True,exist_ok=False)
    arrays={};start=time.time();blocked=0
    for i in range(count):
        stop(600)
        truth,_=g.setup_family(seed,i,ood=split=='test_geometry_ood',camera_ood=split=='test_camera_ood')
        # Candidate identities depend on seed/index/known camera band only,
        # never object positions or future images. Safety filters are separate.
        rng=np.random.default_rng(np.random.SeedSequence([seed,i,4151]));selected=[]
        for band,n in [('original',1),('near',2),('medium',2),('oblique',1)]:
            ids=[j for j,b in enumerate(g.bank) if b['band']==band and
                 (band=='original' or ((j in g.camera_holdout)==(split=='test_camera_ood')))]
            selected.extend(rng.choice(ids,n,replace=False).tolist())
        valid=[object_path_free(g.bank[j]['low'],g.bank[j]['high'],truth['positions'],truth['sizes'],truth['rotations'],truth['active']) for j in selected]
        if not valid[0]:raise RuntimeError('Initial pose unexpectedly unsafe')
        episode=f'{seed}-{i}';revision=episode+'-static';dest=OUT/'observations'/split/f'{i:06d}';dest.mkdir(parents=True)
        journal=RequestJournal(dest/'coverage.jsonl');rows=[]
        for p,j in enumerate(selected):
            entry=g.bank[j];pose=pose_from_mujoco(entry['position'],entry['rotation'],g.T_world_base)
            req=None
            if p:
                req=CaptureRequest.new(episode_id=episode,scene_revision=revision,source_observation_ids=['initial-fixed0','initial-fixed1','initial-wrist'],
                    desired_camera_pose=pose,reason='offline_supervised_candidate_coverage',model_revision='frozen_M2_three_seed_label_generation',calibration_id='sim-'+episode)
                journal.create(req)
                if not valid[p]:journal.transition(req.request_id,'blocked',scene_revision=revision,reason='sim_reference swept arm/gripper/camera envelope intersects object AABB; no image')
                else:journal.transition(req.request_id,'planned',scene_revision=revision,plan_id=f'base-bank-{j}',planner_revision='static_self_edge_plus_swept_object_aabb_v1',planning_backend='sim_reference',joint_positions_rad=entry['q'].tolist(),planned_camera_pose=asdict(pose))
            if valid[p]:
                row=g.observation(truth,entry['q'])
                Image.fromarray(row['images'][2]).save(dest/f'wrist_{p}.png')
                if req:
                    actual=pose_from_mujoco(row['camera_positions'][2],row['camera_rotations'][2],g.T_world_base)
                    journal.transition(req.request_id,'captured',scene_revision=revision,observation_id=f'wrist-{p}',calibration_id=req.calibration_id,image_uri=f'wrist_{p}.png',actual_camera_pose=asdict(actual),captured_at=utc_now())
            else:
                row={k:np.zeros_like(v) for k,v in rows[0].items()};row['camera_positions'][:2]=rows[0]['camera_positions'][:2]
                row['camera_rotations'][:2]=rows[0]['camera_rotations'][:2]
                row['camera_positions'][2]=entry['position'];row['camera_rotations'][2]=entry['rotation'];blocked+=1
            rows.append(row)
        result={k:np.stack([r[k] for r in rows]) for k in rows[0]}
        result.update(truth);result['valid']=np.asarray(valid,bool);result['pose_ids']=np.asarray(selected,np.int64)
        result['joint_positions']=np.stack([g.bank[j]['q'] for j in selected]).astype(np.float32)
        result['expected_robot_occlusion']=np.stack([robot_projection(g.robot_vertices[j],rows[0]['camera_positions'],rows[0]['camera_rotations']) for j in selected])
        if not arrays:
            for k,v in result.items():arrays[k]=np.lib.format.open_memmap(folder/f'{k}.npy',mode='w+',dtype=v.dtype,shape=(count,)+np.asarray(v).shape)
        for k,v in result.items():arrays[k][i]=v
        if i%25==0:status('render',split=split,families=i+1,total=count,blocked=blocked,seconds_per_family=(time.time()-start)/(i+1))
    for v in arrays.values():v.flush()
    save(folder/'manifest.json',dict(seed=seed,count=count,split=split,elapsed_seconds=time.time()-start,blocked=blocked,
             candidate_identity='object-independent seeded camera bank; sim_reference validity separate',
             files={p.name:sha(p) for p in folder.glob('*.npy')}))
    return arrays


def labels(models,data,split,T):
    rows=[];n=len(data['family']);histories=permitted_histories();panel=[]
    for start in range(0,n,8):
        stop(300);ids=np.arange(start,min(n,start+8));cache={}
        for hist in histories:
            subset=np.asarray([i for i in ids if all(data['valid'][i,p] for p in hist)],int)
            if len(subset):
                preds=infer(models,data,subset,hist)
                for i,pred in zip(subset,preds):cache[(int(i),hist)]=pred
        for i in ids:
            for hist in [(0,)]+[(0,p) for p in range(1,6) if data['valid'][i,p]]:
                pred=cache[(int(i),hist)];x=observed(pred,len(hist));cf=candidate_features(x,data,i,hist,T)
                gain=np.zeros(6,np.float32);mask=cf[:,-1].astype(bool);before=[]
                for q in np.flatnonzero(mask):
                    after_hist=hist+(int(q),);union=observable(data,i,hist)|observable(data,i,after_hist)
                    e0=mean_error(pred,data,i,union);e1=mean_error(cache[(int(i),after_hist)],data,i,union)
                    gain[q]=e0-e1-cf[q,-2];before.append(e0)
                need=bool(before and max(before)>5 and np.any(gain[mask]>=2))
                rows.append(dict(x=x,c=cf,gain=gain,mask=mask,need=float(need),family=data['family'][i],history=hist))
                if i<6:panel.append(dict(family=int(i),history=list(hist),observed=x.tolist(),gains=gain.tolist(),mask=mask.tolist()))
            if split=='request_validation' and i<16:
                save(OUT/'geometry_panel'/f'family_{i}.json',dict(family=int(i),histories={','.join(map(str,h)): [{k:v.tolist() for k,v in p.items()} for p in cache[(int(i),h)]] for h in histories if (int(i),h) in cache}))
        if start%64==0:status('label',split=split,families=min(start+8,n),total=n,states=len(rows))
    arrays={k:np.asarray([r[k] for r in rows]) for k in ['x','c','gain','mask','need','family']}
    np.savez_compressed(OUT/f'{split}_labels.npz',**arrays)
    save(OUT/f'{split}_label_summary.json',dict(families=n,states=len(rows),need_positive=int(arrays['need'].sum()),
        candidates=int(arrays['mask'].sum()),helpful=int(((arrays['gain']>=2)&arrays['mask']).sum()),negative_gain=int(((arrays['gain']<0)&arrays['mask']).sum()),
        mean_gain_mm=float(arrays['gain'][arrays['mask']].mean()),panel=panel))
    return arrays


def normalized(data,norm):
    return dict(x=torch.tensor((data['x']-norm['xm'])/norm['xs'],dtype=torch.float32,device='cuda'),
                c=torch.tensor((data['c']-norm['cm'])/norm['cs'],dtype=torch.float32,device='cuda'),
                gain=torch.tensor(data['gain']/20,dtype=torch.float32,device='cuda'),
                mask=torch.tensor(data['mask'],dtype=torch.bool,device='cuda'),need=torch.tensor(data['need'],dtype=torch.float32,device='cuda'))


def head_loss(model,data,ids):
    out=model(data['x'][ids],data['c'][ids]);mask=data['mask'][ids]
    need=F.binary_cross_entropy_with_logits(out['need_image_logit'],data['need'][ids])
    gain=F.smooth_l1_loss(out['gain'],data['gain'][ids],beta=.1,reduction='none')
    helpful=F.binary_cross_entropy_with_logits(out['helpful_logit'],(data['gain'][ids]>=.1).float(),reduction='none')
    loss=need+(gain*mask).sum()/mask.sum().clamp_min(1)+.5*(helpful*mask).sum()/mask.sum().clamp_min(1)
    return loss,out


def head_predictions(models,data,norm):
    d=normalized(data,norm);results=[]
    with torch.inference_mode():
        for model in models:
            model.eval();out=model(d['x'],d['c'])
            results.append(dict(need=out['need_image_logit'].sigmoid().cpu().numpy(),gain=20*out['gain'].cpu().numpy(),helpful=out['helpful_logit'].sigmoid().cpu().numpy()))
    return {k:np.mean([r[k] for r in results],axis=0) for k in results[0]},results


def train_heads(train,valid):
    mask=train['mask'];flat=train['c'][mask]
    norm={k:v for k,v in dict(xm=train['x'].mean(0),xs=np.maximum(train['x'].std(0),1e-3),cm=flat.mean(0),cs=np.maximum(flat.std(0),1e-3)).items()}
    np.savez(OUT/'normalization.npz',**norm);save(OUT/'normalization.json',{k:v.tolist() for k,v in norm.items()})
    tr=normalized(train,norm);va=normalized(valid,norm);models=[];curves=[]
    for seed in [1,2,3]:
        torch.manual_seed(seed);model=RequestHeads().cuda();opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
        best=float('inf');stale=0;updates=0
        def validate(epoch):
            nonlocal best,stale
            model.eval()
            with torch.inference_mode():
                vl=float(head_loss(model,va,slice(None))[0]);tl=float(head_loss(model,tr,slice(None))[0])
            row=dict(seed=seed,epoch=epoch,updates=updates,train_loss=tl,validation_loss=vl);curves.append(row)
            if vl<best:
                best=vl;stale=0;atomic_checkpoint(OUT/'checkpoints'/f'heads_seed{seed}_best.pth',dict(model=model.state_dict(),epoch=epoch,updates=updates,validation_loss=vl),torch)
            else:stale+=1
            save(OUT/'head_curves.json',curves);status('head_train',**row)
            if epoch%5==0:geometry_panel([model],norm,epoch,seed)
        validate(0)
        for epoch in range(1,3 if SMOKE else 31):
            stop(300);model.train();order=np.random.default_rng(953000+seed*100+epoch).permutation(len(train['x']))
            for start in range(0,len(order),256):
                ids=order[start:start+256];opt.zero_grad(set_to_none=True);loss,_=head_loss(model,tr,ids)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite head loss')
                loss.backward();opt.step();updates+=1
            validate(epoch)
            atomic_checkpoint(OUT/'checkpoints'/f'heads_seed{seed}_latest.pth',dict(model=model.state_dict(),optimizer=opt.state_dict(),epoch=epoch,sampler_position=0,updates=updates,torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),numpy_rng=np.random.get_state(),normalization=norm),torch)
            if stale>=5:break
        selected=torch.load(OUT/'checkpoints'/f'heads_seed{seed}_best.pth',weights_only=False,map_location='cuda')
        geometry_panel([model],norm,epoch,seed,tag='final')
        model.load_state_dict(selected['model']);model.eval();models.append(model)
        geometry_panel([model],norm,selected['epoch'],seed,tag='best')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,3))
    for seed,ax in zip([1,2,3],axes):
        r=[x for x in curves if x['seed']==seed]
        for key in ['train_loss','validation_loss']:ax.plot([x['epoch'] for x in r],[x[key] for x in r],label=key)
        ax.set(title=f'Heads seed {seed}',xlabel='Epoch',ylabel='Frozen protocol head loss');ax.legend()
    fig.tight_layout();fig.savefig(OUT/'head_loss.png',dpi=150);plt.close(fig)
    return models,norm


def geometry_panel(heads,norm,epoch,seed,tag='epoch'):
    # Same six validation families across head epochs; perception stays frozen.
    from compare_geometry import render
    data=load_data(OUT,'request_validation');T=np.asarray(json.loads((OUT/'pose_bank.json').read_text())['T_world_base'])
    for file in sorted((OUT/'geometry_panel').glob('family_*.json'))[:16]:
        panel=json.loads(file.read_text());i=panel['family'];preds=[{k:np.asarray(v) for k,v in p.items()} for p in panel['histories']['0']]
        x=observed(preds,1);c=candidate_features(x,data,i,(0,),T)
        d=dict(x=x[None],c=c[None],gain=np.zeros((1,6)),mask=c[None,:,-1].astype(bool),need=np.zeros(1))
        score,_=head_predictions(heads,d,norm);q=int(np.argmax(np.where(c[:,-1]>0,score['gain'][0],-1e9)))
        # Fixed .5 / 2mm are illustrative before calibration, never used to select checkpoints.
        hist=(0,q) if score['need'][0]>=.5 and score['gain'][0,q]>=2 and c[q,-1] else (0,)
        key=','.join(map(str,hist));chosen=[{k:np.asarray(v) for k,v in p.items()} for p in panel['histories'][key]]
        from ensemble_uncertainty import group_predictions
        groups=group_predictions(chosen);mask=observable(data,i,hist)
        gt=[dict(center=data['positions'][i,j].tolist(),size=data['sizes'][i,j].tolist(),rotation=data['rotations'][i,j].tolist(),observable=bool(mask[j])) for j in np.flatnonzero(data['active'][i])]
        pp=[dict(center=v['position'].tolist(),size=v['size'].tolist(),rotation=v['rotation'].tolist()) for v in groups]
        render(dict(label=f'V3 frozen M2 | head {seed} {tag} {epoch} | val {i} | acquired {hist}',ground_truth=gt,predictions=pp),OUT/'geometry'/f'{tag}_{epoch:02d}_seed{seed}_family{i}')


def calibrate(heads,data,norm):
    pred,seeds=head_predictions(heads,data,norm);candidates=[];mask=data['mask']
    # Finite grid fixed before reading calibration labels; optimize net utility
    # under <=5% observed degradation, at least 20 accepted calibration states.
    for need in [.1,.25,.5,.75,.9]:
        for gain in [0.,1.,2.,4.,8.,16.]:
            for helpful in [.25,.5,.75]:
                scores=np.where(mask&(pred['helpful']>=helpful),pred['gain'],-1e9);q=scores.argmax(-1)
                at=np.arange(len(q));accepted=(pred['need']>=need)&(scores[at,q]>=gain);actual=data['gain'][at,q]
                n=int(accepted.sum());harm=int(((actual<0)&accepted).sum());utility=float(actual[accepted].sum())
                candidates.append(dict(need=need,gain=gain,helpful=helpful,n=n,harm=harm,utility=utility,
                                       eligible=n>=20 and harm/max(1,n)<=.05 and utility>0))
    eligible=[x for x in candidates if x['eligible']]
    chosen=max(eligible,key=lambda x:x['utility']) if eligible else dict(need=1.01,gain=1e9,helpful=1.01,n=0,harm=0,utility=0.,eligible=False)
    save(OUT/'calibration.json',dict(selected=chosen,sweep=candidates,
         need_metrics=summarize_binary(pred['need'],data['need'],min(1,chosen['need'])),
         note='Calibration states share family; utility selection exploratory. No final test influenced thresholds. Disable policy if no eligible positive calibration support.'))
    return chosen


def score_heads(heads,data,norm,split,threshold):
    pred,seeds=head_predictions(heads,data,norm);mask=data['mask'];gain=data['gain'][mask];expected=pred['gain'][mask]
    valid=np.asarray(data['mask'],bool)
    metric=dict(need=summarize_binary(pred['need'],data['need'],min(1.,threshold['need'])),
        helpful=summarize_binary(pred['helpful'][mask],(data['gain'][mask]>=2).astype(float),min(1.,threshold['helpful'])),
        gain_mae_mm=float(np.mean(np.abs(expected-gain))),gain_rmse_mm=float(np.sqrt(np.mean((expected-gain)**2))),
        gain_negative_candidates=int((gain<0).sum()),gain_positive_candidates=int((gain>=2).sum()),
        per_seed={str(i+1):dict(need=summarize_binary(s['need'],data['need'],min(1.,threshold['need'])),
                 gain_mae_mm=float(np.mean(np.abs(s['gain'][mask]-gain)))) for i,s in enumerate(seeds)})
    save(OUT/f'{split}_head_metrics.json',metric)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    bins=metric['need']['reliability'];b=[r for r in bins if r['n']]
    axes[0].plot([0,1],[0,1],color='gray',linestyle='--');axes[0].plot([r['probability'] for r in b],[r['positive_fraction'] for r in b],marker='o');axes[0].set(xlabel='Predicted need',ylabel='Observed need frequency',title=split)
    take=np.random.default_rng(95411).choice(len(gain),min(3000,len(gain)),replace=False)
    axes[1].scatter(expected[take],gain[take],s=3,alpha=.3);axes[1].axhline(0,color='gray');axes[1].axvline(0,color='gray');axes[1].set(xlabel='Predicted net gain (mm eq.)',ylabel='Actual net gain (mm eq.)')
    fig.tight_layout();fig.savefig(OUT/f'{split}_head_reliability_gain.png',dpi=150);plt.close(fig)
    return metric


def evaluate_policy(g,perception,heads,norm,data,split,threshold,T):
    cases=[];rows=[];start=time.time();worldbase=T
    journal_root=OUT/'policy'/split;journal_root.mkdir(parents=True)
    for i in range(len(data['family'])):
        stop(120);hist=(0,);live={k:np.array(v[i:i+1],copy=True) for k,v in data.items()}
        initial=infer(perception,live,[0],hist)[0];pred=initial;source=['initial-fixed0','initial-fixed1','initial-wrist']
        family=tuple(map(int,data['family'][i]));episode=f'{family[0]}-{family[1]}';revision=episode+'-static'
        dest=journal_root/f'{i:06d}';dest.mkdir();journal=RequestJournal(dest/'capture_requests.jsonl');captures=[];seconds=0.;motion=0.;blocked=0
        for attempt in range(2):
            x=observed(pred,len(hist));c=candidate_features(x,live,0,hist,T)
            d=dict(x=x[None],c=c[None],gain=np.zeros((1,6)),mask=c[None,:,-1].astype(bool),need=np.zeros(1))
            score,_=head_predictions(heads,d,norm);need=float(score['need'][0]);scores=np.where((c[:,-1]>0)&(score['helpful'][0]>=threshold['helpful']),score['gain'][0],-1e9)
            q=int(scores.argmax());want=need>=threshold['need'];request=want and scores[q]>=threshold['gain'] and scores[q]>-1e8
            if not request:
                journal.decision(decision_id=f'{episode}-decision-{attempt}',episode_id=episode,scene_revision=revision,source_observation_ids=source,needs_reobserve=bool(want),request_image=False,reason='no_valid_helpful_candidate_or_calibrated_no_need',need_probability=need)
                break
            desired=pose_from_mujoco(data['camera_positions'][i,q,2],data['camera_rotations'][i,q,2],worldbase)
            req=CaptureRequest.new(episode_id=episode,scene_revision=revision,source_observation_ids=source,desired_camera_pose=desired,reason='learned_need_and_candidate_gain',model_revision='frozen_M2_3seeds_heads_3seeds',calibration_id='sim-'+episode)
            journal.create(req);journal.decision(decision_id=f'{episode}-decision-{attempt}',episode_id=episode,scene_revision=revision,source_observation_ids=source,needs_reobserve=True,request_image=True,reason='calibrated_head_thresholds',request_id=req.request_id,need_probability=need,expected_net_gain_mm=float(scores[q]),candidate_id=str(q))
            # Independently re-establish same static scene and recertify both
            # complete path legs. Never infer safety from the score / endpoint.
            truth,_=g.setup_family(family[0],family[1],ood=split=='test_geometry_ood',camera_ood=split=='test_camera_ood')
            if not np.allclose(truth['positions'],data['positions'][i],atol=1e-6):
                journal.transition(req.request_id,'blocked',scene_revision=revision,reason='scene regeneration differs; unknown/fail closed');blocked+=1;break
            js=[int(data['pose_ids'][i,p]) for p in [hist[-1],q]]
            path_ok=all(object_path_free(g.bank[j]['low'],g.bank[j]['high'],truth['positions'],truth['sizes'],truth['rotations'],truth['active']) for j in js)
            # Robot-only checker resets qpos: preserve settled object state.
            saved=g.d.qpos.copy();static_ok=all(g.checker.check(g.bank[j]['q']).valid and g.checker.edge(g.base_q,g.bank[j]['q']) for j in js)
            g.d.qpos[:]=saved;g.d.qvel[:]=0;g.env.sim.forward()
            if not (path_ok and static_ok):
                journal.transition(req.request_id,'blocked',scene_revision=revision,reason='independent whole path/limits/self/world/camera/gripper validation failed');blocked+=1;break
            planned=pose_from_mujoco(g.bank[js[1]]['position'],g.bank[js[1]]['rotation'],worldbase)
            journal.transition(req.request_id,'planned',scene_revision=revision,plan_id=f'{episode}-base-{q}',planner_revision='independent_edge_and_swept_object_envelope_v1',planning_backend='sim_reference',joint_positions_rad=g.bank[js[1]]['q'].tolist(),planned_camera_pose=asdict(planned))
            # Actual simulator acquisition after decision, separate from cached
            # offline candidate labels. No physics time advancement / hardware.
            actual_row=g.observation(truth,g.bank[js[1]]['q']);Image.fromarray(actual_row['images'][2]).save(dest/f'wrist_{attempt}.png')
            actual=pose_from_mujoco(actual_row['camera_positions'][2],actual_row['camera_rotations'][2],worldbase)
            journal.transition(req.request_id,'captured',scene_revision=revision,observation_id=f'extra-{attempt}',calibration_id=req.calibration_id,image_uri=f'wrist_{attempt}.png',actual_camera_pose=asdict(actual),captured_at=utc_now())
            difference=np.abs(actual_row['images'].astype(np.int16)-data['images'][i,q].astype(np.int16))
            replay_difference=dict(max_channel_difference=int(difference.max()),changed_channel_fraction=float((difference>0).mean()))
            # Verified OpenGL rerender: one fixed-camera channel at one pixel
            # can round by 1/255 despite identical scene/calibration. Preserve
            # and feed the ACTUAL acquisition, with a strict tiny-drift gate.
            if difference.max()>1 or (difference>0).mean()>.001:
                save(dest/f'image_mismatch_{attempt}.json',replay_difference)
                raise RuntimeError('Actual acquisition has substantive replay mismatch; fail closed')
            for key,value in actual_row.items():live[key][0,q]=value
            old=hist;hist=hist+(q,);post=infer(perception,live,[0],hist)[0]
            # A separate control refreshes fixed cameras while retaining the
            # previous wrist history. This isolates robot-motion image effects.
            from model_v3 import context_arrays,tensor_context,predict
            from learning import decode
            control_arrays=context_arrays(live,[0],'M2',current=q,history=[list(reversed(old))]);control=[]
            with torch.inference_mode():
                for model in perception:
                    raw,_=predict(model,tensor_context(control_arrays));control.append({k:v[0].cpu().numpy() for k,v in decode(raw).items()})
            union=observable(data,i,old)|observable(data,i,hist);before=errors(pred,data,i,union);after=errors(post,data,i,union);fixed=errors(control,data,i,union)
            pe=pose_error(desired,actual);accepted=pe['position_m']<=.003 and pe['angle_rad']<=.035
            journal.transition(req.request_id,'evaluated',scene_revision=revision,evaluation_id=req.request_id+'-eval',decision='accept' if accepted else 'hold')
            captures.append(dict(candidate=q,history=list(hist),request_id=req.request_id,predicted_gain_mm=float(scores[q]),actual_net_gain_mm=float(np.mean([a['error_mm']-b['error_mm'] for a,b in zip(before,after)])-c[q,-2]),
                before=before,after=after,fixed_motion_control=fixed,accepted=accepted,pose_error=pe,expected_robot_occlusion=c[q,14:16].tolist(),robot_fraction_diagnostic=data['robot_fraction'][i,q,:2].tolist(),
                replay_difference=replay_difference,path_checks='known_q forward pose (IK witness), limits+gripper limits, whole-arm self+static world edge, swept camera/gripper/arm object AABBs; both legs via base',planning_backend='sim_reference'))
            seconds+=(float(c[q,-2])-1)/.2;motion+=float(c[q,13]);source=source+[f'extra-{attempt}']
            if not accepted:hist=old;break
            pred=post
        union=observable(data,i,(0,))|observable(data,i,hist)
        baseline=errors(initial,data,i,union);final=errors(pred,data,i,union)
        case=dict(family=list(family),split=split,kind=int(data['kind'][i]),initial=baseline,final=final,captures=captures,extra_images=len(captures),blocked=blocked,planned_motion_seconds=seconds,joint_path_length=motion)
        if i<6:
            from compare_geometry import render
            from ensemble_uncertainty import group_predictions
            gt=[dict(center=data['positions'][i,j].tolist(),size=data['sizes'][i,j].tolist(),rotation=data['rotations'][i,j].tolist(),observable=bool(union[j])) for j in np.flatnonzero(data['active'][i])]
            for name,pp in [('initial',initial),('final',pred)]:
                groups=group_predictions(pp);boxes=[dict(center=v['position'].tolist(),size=v['size'].tolist(),rotation=v['rotation'].tolist()) for v in groups]
                render(dict(label=f'V3 frozen M2 active | {split} family {i} {name}',ground_truth=gt,predictions=boxes),dest/name)
        save(dest/'evaluation.json',case);cases.append(case)
        if i%25==0:status('policy_test',split=split,families=i+1,total=len(data['family']),captures=sum(c['extra_images'] for c in cases),elapsed_seconds=time.time()-start)
    save(OUT/f'{split}_cases.json',cases);summary=summarize_cases(cases);save(OUT/f'{split}_summary.json',summary)
    return summary


def summarize_cases(cases):
    gain=np.array([np.mean([a['error_mm']-b['error_mm'] for a,b in zip(c['initial'],c['final'])]) for c in cases])
    captures=[a for c in cases for a in c['captures']];accepted=[a for a in captures if a['accepted']]
    rng=np.random.default_rng(9814201);boots=np.asarray([gain[rng.integers(0,len(gain),len(gain))].mean() for _ in range(1000)])
    harm=sum(np.mean([b['error_mm']-a['error_mm'] for a,b in zip(v['before'],v['after'])])>0 for v in accepted)
    from ensemble_uncertainty import wilson_upper
    return dict(families=len(cases),mean_error_reduction_mm=float(gain.mean()),paired_family_bootstrap95=np.quantile(boots,[.025,.975]).tolist(),
        seed_metrics={str(s+1):dict(initial_mm=float(np.mean([c['initial'][s]['error_mm'] for c in cases])),final_mm=float(np.mean([c['final'][s]['error_mm'] for c in cases])),missing_before=sum(c['initial'][s]['missing'] for c in cases),missing_after=sum(c['final'][s]['missing'] for c in cases),extra_before=sum(c['initial'][s]['extra'] for c in cases),extra_after=sum(c['final'][s]['extra'] for c in cases)) for s in range(3)},
        captures=len(captures),accepted=len(accepted),harmful_accepted=int(harm),harmful_upper95=wilson_upper(harm,len(accepted)),
        blocked=sum(c['blocked'] for c in cases),mean_extra=float(np.mean([c['extra_images'] for c in cases])),max_extra=max(c['extra_images'] for c in cases),
        mean_planned_seconds=float(np.mean([c['planned_motion_seconds'] for c in cases])),
        fixed_motion_only_reduction_mm=float(np.mean([np.mean([a['error_mm']-b['error_mm'] for a,b in zip(v['before'],v['fixed_motion_control'])]) for v in captures])) if captures else None,
        additional_wrist_beyond_fixed_reduction_mm=float(np.mean([np.mean([a['error_mm']-b['error_mm'] for a,b in zip(v['fixed_motion_control'],v['after'])]) for v in captures])) if captures else None,
        note='Kinematic simulation, simulator-reference geometry safety; no real visual free-space guarantee; ordered reserved grid candidates, not arbitrary new camera domain.')


def frozen_benchmark(models,data,split):
    """Final-only M0/M1/M2, each seed and pose, plus pure fixed-camera control.

    All variants score the SAME observable GT mask at each candidate pose.
    This benchmark never trains heads or selects any threshold/checkpoint.
    """
    from model_v3 import context_arrays,tensor_context,predict
    from learning import decode
    records=[]
    for start in range(0,len(data['family']),8):
        stop(120)
        for p in range(6):
            ids=np.array([i for i in range(start,min(start+8,len(data['family']))) if data['valid'][i,p]],int)
            if not len(ids):continue
            for name,modelset in models.items():
                variant='M2' if name in ['M2','fixed_only_M2'] else 'M1'
                history=[] if name=='fixed_only_M2' else [p]
                arrays=context_arrays(data,ids,variant,current=p,history=[history for _ in ids]);batch=tensor_context(arrays)
                for seed,model in enumerate(modelset,1):
                    with torch.inference_mode():raw,_=predict(model,batch);pred={k:v.cpu().numpy() for k,v in decode(raw).items()}
                    for at,i in enumerate(ids):
                        pp={k:v[at] for k,v in pred.items()};mask=observable(data,i,(p,))
                        result=errors([pp],data,i,mask)[0]
                        records.append(dict(family=int(i),kind=int(data['kind'][i]),pose=p,variant=name,seed=seed,**result))
        if start%64==0:status('frozen_benchmark',split=split,families=min(start+8,len(data['family'])),total=len(data['family']))
    save(OUT/f'{split}_frozen_benchmark_rows.json',records)
    summaries={}
    for variant in models:
        summaries[variant]={}
        for seed in [1,2,3]:
            for p in range(6):
                rows=[r for r in records if r['variant']==variant and r['seed']==seed and r['pose']==p]
                for arrangement in ['all','scattered']:
                    subset=rows if arrangement=='all' else [r for r in rows if r['kind']==0]
                    if not subset:continue
                    pe=[e for r in subset for e in r['position_mm']];ce=[e for r in subset for e in r['corner_rmse_mm']]
                    summaries[variant][f'seed{seed}/pose{p}/{arrangement}']=dict(families=len(subset),set_error_mm=float(np.mean([r['error_mm'] for r in subset])),
                        observable=sum(r['observable'] for r in subset),missing=sum(r['missing'] for r in subset),extra=sum(r['extra'] for r in subset),
                        assignment_position_mm=float(np.mean(pe)) if pe else None,corner_rmse_mm=float(np.mean(ce)) if ce else None,
                        recall_10mm=sum(e<=10 for e in pe)/max(1,sum(r['observable'] for r in subset)))
    save(OUT/f'{split}_frozen_benchmark.json',summaries)
    return summaries


def run():
    proof=independence();save(OUT/'independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Followup worker must be independent')
    from deadline_guard import register
    register(os.getpid(),'followup_heads_and_simulation_worker',RUN)
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    OUT.mkdir(exist_ok=True)
    status('audit');settings();decision=audit()
    protocol=dict(perception_variant='M2',perception_seeds=[1,2,3],head_seeds=[1,2,3],head_epochs_maximum=30,
        request_counts=dict(request_train=4000,request_validation=500,request_calibration=500),
        test_counts=dict(test_iid=2000,test_camera_ood=1000,test_geometry_ood=1000),
        need_threshold_error_mm=5.,helpful_gain_mm=2.,gain_normalizer_mm=20.,capture_cost_mm=1.,time_cost_mm_per_second=.2,
        assumed_joint_speed_rad_per_second=.5,normalization='request_train only',maximum_extra_images=2,
        observation_features=OBSERVATION_FEATURES,candidate_features=CANDIDATE_FEATURES,
        future_image_nn_inputs=False,oracle_robot_fraction_nn_input=False,oracle_geometry_nn_input=False,
        planner='sim_reference conservative whole path',candidate_proposal='object-independent seeded pose bands',
        blocked_candidate_gain='masked, no invented label',bootstrap_seed=9814201,hardware=False,
        start_unix=PHASE['start_unix'],deadline_unix=END,source_hashes={p.name:sha(p) for p in [HERE/'followup_core.py',HERE/'followup_v3.py',HERE/'request_heads.py']})
    if SMOKE:
        protocol['request_counts']=dict(request_train=32,request_validation=16,request_calibration=16)
        protocol['test_counts']=dict(test_iid=8,test_camera_ood=8,test_geometry_ood=8)
        protocol['technical_smoke_only']=True
    save(OUT/'protocol.json',protocol);(OUT/'checkpoints').mkdir();(OUT/'geometry_panel').mkdir()
    perception=[]
    for seed in [1,2,3]:
        m=ScenePerception().cuda();m.load_state_dict(torch.load(RUN/'checkpoints'/f'M2_seed{seed}_best.pth',map_location='cuda',weights_only=False)['model']);m.eval()
        for p in m.parameters():p.requires_grad_(False)
        perception.append(m)
    g=PoseGenerator()
    try:
        bank=g.make_bank();save(OUT/'pose_bank.json',bank);T=np.asarray(bank['T_world_base'])
        g.robot_vertices=[[b.vertices.copy() for b in g.checker.robot_boxes(e['q'])] for e in g.bank]
        datasets={};labeldata={};familysets=[set(map(tuple,np.load(RUN/'data'/s/'family.npy',mmap_mode='r'))) for s in ['train','validation']]
        for split,count in protocol['request_counts'].items():
            seed=9500001+1000*list(protocol['request_counts']).index(split) if SMOKE else CFG['reserved_seeds'][split]
            datasets[split]=collect(g,split,count,seed)
            fs=set(map(tuple,datasets[split]['family']));familysets.append(fs)
            if any(fs&other for other in familysets[:-1]):raise RuntimeError('Request family leakage')
            labeldata[split]=labels(perception,datasets[split],split,T)
        heads,norm=train_heads(labeldata['request_train'],labeldata['request_validation'])
        threshold=calibrate(heads,labeldata['request_calibration'],norm)
        if SMOKE:
            threshold=dict(need=0.,gain=-1000000.,helpful=0.,technical_force_capture=True)
        for split in protocol['request_counts']:
            score_heads(heads,labeldata[split],norm,split,threshold)
        # Freeze all heads and calibration before any final family is generated.
        freeze=dict(time=datetime.now(timezone.utc).isoformat(),threshold=threshold,
                    perception_parent_hashes={n:v for n,v in json.loads((RUN/'checkpoint_hashes.json').read_text()).items() if n.startswith('M2')},
                    head_hashes={p.name:sha(p) for p in (OUT/'checkpoints').glob('*best.pth')})
        save(OUT/'policy_freeze.json',freeze)
        controls={'M2':perception,'fixed_only_M2':perception,'M1':[],'M0':[]}
        for seed in [1,2,3]:
            for name,path in [('M1',RUN/'checkpoints'/f'M1_seed{seed}_best.pth'),
                              ('M0',ROOT/'experiments/vision/visual_scene_v2_20261101/run_001/checkpoints'/f'fixed_wrist_seed{seed}_best.pth')]:
                model=ScenePerception().cuda();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);model.eval()
                for param in model.parameters():param.requires_grad_(False)
                controls[name].append(model)
        summaries={}
        for split,count in protocol['test_counts'].items():
            seed=9510001+1000*list(protocol['test_counts']).index(split) if SMOKE else CFG['reserved_seeds'][split]
            data=collect(g,split,count,seed);fs=set(map(tuple,data['family']))
            if any(fs&other for other in familysets):raise RuntimeError('Final family leakage')
            familysets.append(fs);summaries[split]=evaluate_policy(g,perception,heads,norm,data,split,threshold,T)
            frozen_benchmark(controls,data,split)
            final_labels=labels(perception,data,split,T)
            score_heads(heads,final_labels,norm,split,threshold)
        save(OUT/'results.json',dict(status='completed',scientific_success=False,perception_frozen=True,continuation=False,
            summaries=summaries,threshold=threshold,head_updates=json.loads((OUT/'head_curves.json').read_text())[-1]['updates'],
            elapsed_seconds=time.time()-PHASE['start_unix'],deadline_unix=END,
            limitations=['scientific gates must be assessed from actual results; completion is not an improvement claim','sim_reference is not visual safety','geometry OOD scattered only; compare scattered IID separately']))
        status('complete',summaries=summaries)
    finally:g.close();ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':
    try:run()
    except Exception as error:
        status('partial_deadline' if isinstance(error,TimeoutError) else 'error',error=repr(error));traceback.print_exc();raise
