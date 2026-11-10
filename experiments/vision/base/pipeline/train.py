"""Six paired tracks, fixed epochs/budget, validation-only checkpoint selection."""
import os,sys,time,math,copy,traceback
from pathlib import Path
import numpy as np
import torch
from .common import ROOT,EXPERIMENT,read,save,sha,event,check_stop,now
from .protocol import verify_protocol
from .audit import audit
from .samples import Store,batch_pairs
from .engine import forward,tensors,checkpoint,restore,learning_rate,saved_rng,put_rng
from .evaluate import evaluate
from .reporting import plots,geometry
sys.path.insert(0,str(EXPERIMENT));sys.path.insert(0,str(ROOT/'experiments/vision/visual_active_v3_20261101'))
from paired_learning import paired_criterion
from model_v3 import ScenePerception

def save_best(path,track,epoch,metrics,protocol_hash):
    temp=path.with_suffix('.pth.tmp');torch.save(dict(model=track['model'].state_dict(),epoch=epoch,step=track['step'],validation=metrics,protocol_sha256=protocol_hash),temp);temp.replace(path)
    save(path.with_suffix('.sha256.json'),dict(sha256=sha(path),step=track['step'],epoch=epoch))

def train(run,resume=False):
    from preflight import settings
    run=Path(run);settings();cfg=verify_protocol(run,full_sources=True);check_stop(run,60)
    if (run/'perception_freeze.json').exists():raise RuntimeError('Perception already frozen; no further optimizer updates after downstream use')
    if not (run/'budget.json').exists():raise RuntimeError('Explicit fixed launch budget required')
    event(run,'initializing',training_started=False,reason='independent data/lineage audit')
    audit(run,main=True);store=Store(run,'train',verify=False);valid=Store(run,'validation',verify=False)
    for split in ['train','validation']:
        if sha(run/'data'/split/'seal.json')!=read(run/'dataset_freeze.json')['dataset_seals'][split]:raise RuntimeError('Dataset seal changed after audit')
    device='cuda'
    if not torch.cuda.is_available():raise RuntimeError('CUDA required for main run')
    tracks={};keys=[];checkpoints=run/'checkpoints';checkpoints.mkdir(exist_ok=True)
    save(run/'runtime.json',dict(torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name(),parameters=904112))
    for seed in [1,2,3]:
        parent=next(p for p in cfg['parents'] if p['seed']==seed)
        for arm in ['A','B']:
            torch.manual_seed(seed);model=ScenePerception().to(device);model.load_state_dict(torch.load(ROOT/parent['file'],map_location=device,weights_only=False)['model'])
            key=f'{arm}{seed}';keys.append(key);tracks[key]=dict(seed=seed,arm=arm,model=model,optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4),step=0,best=float('inf'),best_epoch=0)
    cursor=dict(epoch=0,batch=0,track=0,micro=0,track_loss=0.,epoch_losses={k:0. for k in keys},epoch_seen=0,phase='initial_validation')
    curves=[];extras=dict(protocol_sha256=sha(run/'config.json'),dataset_sha256=sha(run/'dataset_freeze.json'),best_pair=float('inf'),stale=0)
    latest=checkpoints/'latest.pth'
    if resume:
        cursor,curves,extras=restore(latest,tracks,device)
        if extras['protocol_sha256']!=sha(run/'config.json') or extras['dataset_sha256']!=sha(run/'dataset_freeze.json'):raise RuntimeError('Resume provenance changed')
    elif latest.exists():raise RuntimeError('Existing checkpoint: use explicit --resume')
    steps_per_epoch=math.ceil(len(store)/32);epochs=cfg['optimization']['maximum_epochs']
    def snapshot():checkpoint(latest,tracks,cursor,curves,extras)
    def validation(epoch,train_losses=None):
        rng=saved_rng();before=copy.deepcopy(cursor)
        try:
            for key,t in tracks.items():
                event(run,'validation',epoch=epoch,step=t['step'],model=key,training_started=any(v['step']>0 for v in tracks.values()))
                v=evaluate(t['model'],valid,run);probe_ids=list(range(min(96,len(store.records))))+list(range(len(store.records),min(len(store),len(store.records)+32)))
                probe=evaluate(t['model'],store,run,probe_ids)
                row=dict(seed=t['seed'],arm=t['arm'],epoch=epoch,updates=t['step'],train_loss=None if train_losses is None else train_losses[key],
                    validation_loss=v['loss'],probe_loss=probe['loss'],selection_loss=v['balanced_loss'],
                    validation_mm=v['contexts']['side']['assignment_position_mm'],validation_count_accuracy=v['contexts']['side']['count_accuracy'],validation_recall_10mm=v['contexts']['side']['recall_at_10mm'],
                    side_set_error_mm=v['contexts']['side']['after_set_error_mm'],old_set_error_mm=v['contexts']['old']['after_set_error_mm'],validation_components=v['contexts']['side']['components'],
                    contexts=v['contexts'],learning_rate=t['optimizer'].param_groups[0]['lr'],time=now())
                curves[:]=[r for r in curves if not(r['seed']==t['seed'] and r['arm']==t['arm'] and r['epoch']==epoch)];curves.append(row)
                if v['balanced_loss']<t['best']:
                    t['best']=v['balanced_loss'];t['best_epoch']=epoch;save_best(checkpoints/f'{key}_best.pth',t,epoch,v,extras['protocol_sha256'])
                save(run/'curves.json',curves)
            plots(run,curves)
            if epoch==0 or epoch%5==0:
                for key,t in tracks.items():
                    event(run,'geometry',epoch=epoch,step=t['step'],model=key,training_started=epoch>0);geometry(run,t['model'],valid,epoch,t['seed'],t['arm'])
        finally:
            put_rng(rng)
            if cursor!=before:raise RuntimeError('Validation modified the sampler cursor')
    try:
        if cursor['phase']=='initial_validation':validation(0);cursor['phase']='train';snapshot()
        while cursor['epoch']<epochs:
            order=np.random.default_rng(94831211+cursor['epoch']).permutation(len(store))
            while cursor['batch']<len(order):
                check_stop(run,60);ids=order[cursor['batch']:cursor['batch']+32];rows=[store[int(i)] for i in ids]
                while cursor['track']<len(keys):
                    key=keys[cursor['track']];t=tracks[key];t['model'].train();opt=t['optimizer']
                    if cursor['micro']==0:
                        opt.zero_grad(set_to_none=True);opt.param_groups[0]['lr']=learning_rate(t['step'],steps_per_epoch,epochs)
                    while cursor['micro']<len(rows):
                        check_stop(run,30);offset=cursor['micro'];sub=rows[offset:offset+4]
                        torch.manual_seed(t['seed']*100000000+cursor['epoch']*100000+cursor['batch']+offset)
                        arrays=batch_pairs(sub,t['arm'],cursor['epoch'],t['seed']);loss_total=0
                        for a in arrays:
                            batch=tensors(a,device);raw,av=forward(t['model'],batch);loss,_,_=paired_criterion(raw,batch,av)
                            if not torch.isfinite(loss):raise RuntimeError('Nonfinite training loss')
                            (loss*.5*len(sub)/len(rows)).backward();loss_total+=float(loss.detach())/2
                        cursor['track_loss']+=loss_total*len(sub);cursor['micro']+=len(sub)
                    check_stop(run,15);torch.nn.utils.clip_grad_norm_(t['model'].parameters(),1.,error_if_nonfinite=True);opt.step();t['step']+=1
                    cursor['epoch_losses'][key]+=cursor['track_loss'];cursor.update(track=cursor['track']+1,micro=0,track_loss=0.)
                cursor['epoch_seen']+=len(rows);cursor.update(batch=cursor['batch']+len(rows),track=0)
                if tracks[keys[0]]['step']%10==0:event(run,'train',epoch=cursor['epoch']+cursor['batch']/len(order),step=tracks[keys[0]]['step'],loss=cursor['epoch_losses'][keys[0]]/cursor['epoch_seen'],training_started=True)
                if tracks[keys[0]]['step']%100==0:snapshot()
            cursor['phase']='epoch_validation';snapshot();epoch=cursor['epoch']+1
            validation(epoch,{key:cursor['epoch_losses'][key]/cursor['epoch_seen'] for key in keys})
            pair_loss=float(np.mean([r['selection_loss'] for r in curves if r['epoch']==epoch]))
            if pair_loss<extras['best_pair']*.995:extras.update(best_pair=pair_loss,stale=0)
            else:extras['stale']+=1
            cursor=dict(epoch=epoch,batch=0,track=0,micro=0,track_loss=0.,epoch_losses={k:0. for k in keys},epoch_seen=0,phase='train');snapshot()
            if extras['stale']>=cfg['optimization']['early_stop_pair_patience']:break
        selected=[]
        for key,t in tracks.items():
            path=checkpoints/f'{key}_best.pth'
            if sha(path)!=read(path.with_suffix('.sha256.json'))['sha256']:raise RuntimeError('Best checkpoint changed')
            value=torch.load(path,map_location=device,weights_only=False);t['model'].load_state_dict(value['model']);v=evaluate(t['model'],valid,run)
            selected.append(dict(seed=t['seed'],variant=t['arm'],file=path.relative_to(ROOT).as_posix(),sha256=sha(path),epoch=value['epoch'],updates=value['step'],validation=v))
            geometry(run,t['model'],valid,value['epoch'],t['seed'],t['arm'],tag='best')
        means={arm:float(np.mean([r['validation']['balanced_loss'] for r in selected if r['variant']==arm])) for arm in ['A','B']};winner=min(means,key=means.get)
        side={arm:float(np.mean([r['validation']['contexts']['side']['after_set_error_mm'] for r in selected if r['variant']==arm])) for arm in ['A','B']}
        old={arm:float(np.mean([r['validation']['contexts']['old']['after_set_error_mm'] for r in selected if r['variant']==arm])) for arm in ['A','B']}
        improved=sum(next(r for r in selected if r['variant']=='B' and r['seed']==s)['validation']['contexts']['side']['after_set_error_mm']<next(r for r in selected if r['variant']=='A' and r['seed']==s)['validation']['contexts']['side']['after_set_error_mm'] for s in [1,2,3])
        gate=winner=='B' and side['B']<=.9*side['A'] and old['B']<=old['A']+1 and improved>=2
        save(run/'selection.json',dict(models=selected,variant_means=means,selected_variant=winner,selection_split='validation',side_gate_passed=gate))
        save(run/'perception_freeze.json',dict(selected_variant=winner,side_gate_passed=gate,models=[dict(seed=r['seed'],file=r['file'],sha256=r['sha256']) for r in selected if r['variant']==winner],selection_sha256=sha(run/'selection.json'),protocol_sha256=sha(run/'config.json')))
        save(run/'results.json',dict(training_complete=True,variants=means,side_errors=side,old_errors=old,side_gate_passed=gate,heldout_tests_used=False,optimizer_updates={k:t['step'] for k,t in tracks.items()}))
        event(run,'complete',training_started=True,step=tracks[keys[0]]['step'],reason='paired perception phase complete; no claim about active policy')
    except (InterruptedError,TimeoutError) as error:
        snapshot();event(run,'budget_exhausted' if isinstance(error,TimeoutError) else 'cancelled_by_user',reason=str(error),training_started=any(t['step'] for t in tracks.values()),resume_cursor=cursor);return
    except Exception as error:
        event(run,'error',error=str(error),training_started=any(t['step'] for t in tracks.values()));raise
