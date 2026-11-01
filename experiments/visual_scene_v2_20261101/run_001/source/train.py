"""Bounded paired V2 training with physical data, exact state and geometry QA."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import site
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
import argparse,json,sys,time,hashlib,math,traceback,shutil
import numpy as np,torch
from PIL import Image
sys.path.insert(0,str(ROOT/'experiments/visual_overnight_20261101'))
from night import save,atomic_checkpoint,supervise
from scene_data import Generator,stack,ORIGIN
from learning import initialize,tensor_batch,run_model,criterion,decode,boxes
from model_prototype import ScenePerception
from preflight import settings
from compare_geometry import render,compare


def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())


class Session:
    def __init__(self,run):
        self.run=run;self.cfg=json.loads((run/'config.json').read_text());self.state={}
        self.deadline=self.cfg['deadline_unix'];self.stop_training=self.deadline-900
    def status(self,**values):
        self.state.update(values);self.state.update(time=now(),heartbeat_unix=time.time(),pid=os.getpid())
        save(self.run/'status.json',self.state)
    def should_stop(self):return time.time()>=self.stop_training or (self.run/'STOP_REQUESTED').exists()
    def data(self,split,count,seed,g):
        folder=self.run/'data'/split;folder.mkdir(parents=True,exist_ok=False)
        arrays={};counts=np.zeros(6,dtype=int);kinds=np.zeros(4,dtype=int);start=time.time()
        for i in range(count):
            if time.time()>self.deadline-60 or ((self.run/'STOP_REQUESTED').exists()):raise RuntimeError('Session stopped during data preparation')
            if not split.startswith('reserved') and self.should_stop():raise RuntimeError('Stop requested before dataset preparation completed')
            row=g.scene(seed,i,ood=split.endswith('_ood'))
            if not arrays:
                for k,v in row.items():arrays[k]=np.lib.format.open_memmap(folder/f'{k}.npy',mode='w+',dtype=v.dtype,shape=(count,)+v.shape)
            for k,v in row.items():arrays[k][i]=v
            counts[int(row['count'])]+=1;kinds[int(row['kind'])]+=1
            if i%32==0:self.status(stage='render',split=split,rendered=i,render_total=count)
        for a in arrays.values():a.flush()
        manifest=dict(split=split,count=count,seed=seed,count_histogram=counts.tolist(),kind_histogram=kinds.tolist(),
                      elapsed_seconds=time.time()-start,rejections=g.rejections.copy())
        # Hash all arrays once; source labels and source photos remain bound together.
        manifest['files']={}
        for p in sorted(folder.glob('*.npy')):
            h=hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
            manifest['files'][p.name]=h.hexdigest()
        save(folder/'manifest.json',manifest)
        return arrays


def gt_boxes(data,index,arm):
    views=2 if arm=='fixed' else 3
    return [dict(center=data['positions'][index,i].tolist(),size=data['sizes'][index,i].tolist(),
                 rotation=data['rotations'][index,i].tolist(),observable=bool((data['visibility'][index,i,:views]>=.05).any()))
            for i in range(5) if data['active'][index,i]]


@torch.no_grad()
def evaluate(s,model,data,arm,indices=None):
    model.eval();indices=np.arange(len(data['images'])) if indices is None else np.asarray(indices)
    total=0.;parts_total={};errors=[];counts=[];success=0;observations=0;strata={}
    for start in range(0,len(indices),16):
        ids=indices[start:start+16];batch=tensor_batch(data,ids);out,av=run_model(model,batch,arm)
        loss,parts,matches=criterion(out,batch,av);d=decode(out)
        total+=float(loss)*len(ids)
        for kind in torch.unique(batch['kind']):
            mask=batch['kind']==kind
            subgroup={k:v[mask] for k,v in batch.items()}
            subout={k:v[mask] for k,v in out.items()}
            subloss,_,_=criterion(subout,subgroup,av[mask])
            key=int(kind);previous=strata.get(key,[0.,0]);previous[0]+=float(subloss)*int(mask.sum());previous[1]+=int(mask.sum());strata[key]=previous
        for k,v in parts.items():parts_total[k]=parts_total.get(k,0)+float(v)*len(ids)
        for i,(pi,gi) in enumerate(matches):
            counts.append(int((d['probability'][i]>=.5).sum())==len(gi));observations+=len(gi)
            if len(pi):
                e=torch.linalg.vector_norm(d['position'][i,pi]-batch['positions'][i,gi],dim=-1)*1000
                errors.extend(e.cpu().tolist());success+=int(((e<=10)&(d['probability'][i,pi]>=.5)).sum())
        if start%128==0:s.status(stage='validation',evaluated=min(start+16,len(indices)),eval_total=len(indices))
    return dict(loss=total/len(indices),components={k:v/len(indices) for k,v in parts_total.items()},
                balanced_loss=float(np.mean([v[0]/v[1] for v in strata.values()])),stratum_losses={str(k):v[0]/v[1] for k,v in strata.items()},
                assignment_position_mm=float(np.mean(errors)) if errors else None,count_accuracy=float(np.mean(counts)),
                recall_at_10mm=success/observations if observations else None)


def plot_curves(run,curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,2,figsize=(11,9),layout='constrained')
    for seed in (1,2,3):
        for j,arm in enumerate(('fixed','fixed_wrist')):
            rows=[r for r in curves if r['seed']==seed and r['arm']==arm]
            ax=axes[seed-1,j]
            if rows:
                ax.plot([r['epoch'] for r in rows],[r['train_loss'] for r in rows],label='Train: gesamte Epoche')
                ax.plot([r['epoch'] for r in rows],[r['validation_loss'] for r in rows],label='Validation: vollständig')
                ax.plot([r['epoch'] for r in rows],[r['probe_loss'] for r in rows],label='Train-Probe: Evalmodus',linestyle=':')
            ax.set_title(f'{arm} | Seed {seed}');ax.set_xlabel('Epoche');ax.set_ylabel('Gewichteter Gesamt-Loss');ax.set_yscale('log');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(run/'loss.png',dpi=130);fig.savefig(run/'loss.svg');plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,6),layout='constrained')
    for ax,key in zip(axes.ravel(),['detection','position','size','rotation','visibility','total']):
        for seed in (1,2,3):
            rows=[r for r in curves if r['seed']==seed and r['arm']=='fixed_wrist']
            y=[r['validation_components'][key] if key!='total' else r['validation_loss'] for r in rows]
            ax.plot([r['epoch'] for r in rows],y,label=f'Seed {seed}')
        ax.set_title(key);ax.set_xlabel('Epoche');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(run/'loss_components.png',dpi=130);plt.close(fig)


@torch.no_grad()
def geometry_round(s,models,data,epoch,selected=False):
    index_path=s.run/'geometry/index.json'
    index=json.loads(index_path.read_text()) if index_path.exists() else []
    fixed=[]
    for n in range(6):fixed.extend(np.flatnonzero(data['count']==n)[:2].tolist())
    fixed=list(dict.fromkeys(fixed))[:12]
    rng=np.random.default_rng(811000+epoch);rotating=rng.choice(len(data['images']),min(4,len(data['images'])),replace=False).tolist()
    panel=list(dict.fromkeys(fixed+rotating))
    checkpoint_path=s.run/'checkpoints/latest.pth'
    checkpoint_hash=hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() if checkpoint_path.exists() else None
    for (seed,arm),member in models.items():
        member['model'].eval()
        batch=tensor_batch(data,panel);out,_=run_model(member['model'],batch,arm);decoded=decode(out)
        for local,scene_id in enumerate(panel):
            if time.time()>s.deadline-120:return
            actual_epoch=member['best_epoch'] if selected else epoch
            name=f'{"best_" if selected else ""}epoch_{actual_epoch:03d}_{arm}_seed{seed}_scene{scene_id:04d}'
            folder=s.run/'geometry'/name
            scene=dict(label=f'Vision V2 | {"Best " if selected else ""}Epoche {actual_epoch} | Seed {seed} | {arm} | Val-Szene {scene_id}',
                ground_truth=gt_boxes(data,scene_id,arm),predictions=boxes(decoded,local),
                bounds=[[-.23,.23],[-.23,.23],[.78,1.18]],epoch=actual_epoch,seed=seed,variant=arm,
                checkpoint_sha256=hashlib.sha256((s.run/'checkpoints'/f'{arm}_seed{seed}_best.pth').read_bytes()).hexdigest() if selected else checkpoint_hash,selected_checkpoint=selected,
                family=data['family'][scene_id].tolist(),updates=member['step'])
            result=render(scene,folder)
            Image.fromarray(np.concatenate(data['images'][scene_id],axis=1)).save(folder/'inputs.png')
            for suffix,label,kind in [('overlay.png','3D-Abgleich','geometry'),('inputs.png','Kameraeingaben','geometry-input'),('metrics.json','Geometriekennzahlen','geometry-metrics')]:
                index.append(dict(name=name+'_'+suffix,file=f'geometry/{name}/{suffix}',kind=kind,epoch=actual_epoch,seed=seed,variant=arm,
                                  label=f'{label} · {"Best " if selected else ""}Epoche {actual_epoch} · Seed {seed} · {arm} · Szene {scene_id}'))
            s.status(stage='geometry',epoch=epoch,model=f'{arm}_seed{seed}',scene=scene_id)
    save(index_path,index)


def checkpoint(s,models,epoch,sampler_position=0):
    value=dict(epoch=epoch,sampler_position=sampler_position,torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),numpy_rng=np.random.get_state(),config=s.cfg,
        models={f'{seed}/{arm}':dict(model=m['model'].state_dict(),optimizer=m['opt'].state_dict(),step=m['step'],best=m['best'],best_epoch=m['best_epoch'],stale=m['stale']) for (seed,arm),m in models.items()})
    atomic_checkpoint(s.run/'checkpoints/latest.pth',value,torch)


def worker(run):
    settings();s=Session(run)
    s.status(stage='initializing',step=0,epoch=0)
    cfg=s.cfg
    for name,expected in json.loads((run/'source_hashes.json').read_text()).items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=expected:raise RuntimeError(f'Frozen source changed: {name}')
    save(run/'runtime.json',dict(torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name(),parameters=904112))
    # Freeze the exact data/code/config before training; preparation is inside the deadline.
    g=Generator()
    try:
        train=s.data('train',cfg['dataset']['train'],6200001,g)
        valid=s.data('validation',cfg['dataset']['validation'],7200001,g)
        save(run/'data/generation_report.json',dict(rejections=g.rejections,train=len(train['images']),validation=len(valid['images'])))
    finally:g.close()
    assert not set(map(tuple,train['family'])).intersection(map(tuple,valid['family']))
    models={};curves=[]
    for seed in (1,2,3):
        for arm in ('fixed','fixed_wrist'):
            torch.manual_seed(seed);model=initialize(ScenePerception()).cuda()
            models[(seed,arm)]=dict(model=model,opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001),step=0,best=float('inf'),best_epoch=0,stale=0)
    probe_ids=np.arange(min(128,len(train['images'])))
    def validate(epoch,training_losses=None):
        for (seed,arm),m in models.items():
            probe=evaluate(s,m['model'],train,arm,probe_ids);val=evaluate(s,m['model'],valid,arm)
            if not np.isfinite(val['loss']):raise RuntimeError('nonfinite validation loss')
            row=dict(seed=seed,arm=arm,epoch=epoch,updates=m['step'],time=now(),elapsed_seconds=time.time()-cfg['started_unix'],
                train_loss=training_losses[(seed,arm)] if training_losses else probe['loss'],probe_loss=probe['loss'],
                validation_loss=val['loss'],validation_components=val['components'],validation_mm=val['assignment_position_mm'],
                selection_loss=val['balanced_loss'],validation_strata=val['stratum_losses'],
                validation_count_accuracy=val['count_accuracy'],validation_recall_10mm=val['recall_at_10mm'])
            curves.append(row)
            if val['balanced_loss']<m['best']:
                if val['balanced_loss']<m['best']*.995:m['stale']=0
                else:m['stale']+=1
                m['best']=val['balanced_loss'];m['best_epoch']=epoch
                atomic_checkpoint(run/'checkpoints'/f'{arm}_seed{seed}_best.pth',dict(model=m['model'].state_dict(),epoch=epoch,step=m['step'],validation=val),torch)
            else:m['stale']+=1
            s.status(stage='validation',epoch=epoch,step=m['step'],loss=val['loss'],model=f'{arm}_seed{seed}',latest_metrics=row)
        save(run/'curves.json',curves);plot_curves(run,curves);checkpoint(s,models,epoch)
    validate(0);geometry_round(s,models,valid,0)
    steps_per_epoch=math.ceil(len(train['images'])/32);completed_epoch=0;stop_reason='maximum_epochs'
    maximum_epochs=cfg['optimization']['maximum_epochs']
    for epoch in range(1,maximum_epochs+1):
        losses={key:0. for key in models};seen=0
        # Same scene order for all seed pairs; dropout RNG additionally paired per seed.
        order=np.random.default_rng(921000+epoch).permutation(len(train['images']))
        for at in range(0,len(order),32):
            if s.should_stop():
                stop_reason='user_stop' if (run/'STOP_REQUESTED').exists() else 'time_budget'
                checkpoint(s,models,epoch,sampler_position=at);break
            ids=order[at:at+32];seen+=len(ids)
            for (seed,arm),m in models.items():
                step=m['step'];warmup=steps_per_epoch*5;total=steps_per_epoch*100
                factor=(step+1)/warmup if step<warmup else .05+.95*.5*(1+math.cos(math.pi*(step-warmup)/max(1,total-warmup)))
                for group in m['opt'].param_groups:group['lr']=.0003*factor
                m['model'].train();m['opt'].zero_grad();batch_loss=0.
                for micro in range(0,len(ids),16):
                    torch.manual_seed(seed*100000000+epoch*100000+at+micro)
                    batch=tensor_batch(train,ids[micro:micro+16]);out,av=run_model(m['model'],batch,arm)
                    loss,_,_=criterion(out,batch,av)
                    if not torch.isfinite(loss):raise RuntimeError('nonfinite training loss')
                    (loss*len(batch['images'])/len(ids)).backward();batch_loss+=float(loss.detach())*len(batch['images'])
                torch.nn.utils.clip_grad_norm_(m['model'].parameters(),1.,error_if_nonfinite=True);m['opt'].step();m['step']+=1
                losses[(seed,arm)]+=batch_loss
            if at//32%10==0:s.status(stage='train',epoch=epoch,step=models[(1,'fixed')]['step'],batch=at//32,batches=steps_per_epoch,loss=batch_loss/len(ids))
            if models[(1,'fixed')]['step']%100==0:checkpoint(s,models,epoch,sampler_position=at+len(ids))
        else:
            completed_epoch=epoch;validate(epoch,{key:value/seen for key,value in losses.items()})
            if epoch%5==0:geometry_round(s,models,valid,epoch)
            if all(m['stale']>=15 for m in models.values()):stop_reason='early_stopping';break
            continue
        break
    if stop_reason=='user_stop':s.status(stage='cancelled_by_user',epoch=completed_epoch);return
    # Freeze all six selections before generating reserved data. No training after this point.
    selected=[]
    for (seed,arm),m in models.items():
        p=run/'checkpoints'/f'{arm}_seed{seed}_best.pth'
        selected.append(dict(seed=seed,arm=arm,selected_epoch=m['best_epoch'],updates_paid=m['step'],sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        m['model'].load_state_dict(torch.load(p,map_location='cuda',weights_only=False)['model'])
    save(run/'selection.json',dict(time=now(),models=selected))
    # A labelled final snapshot uses selected models; epoch is last complete training epoch.
    geometry_round(s,models,valid,completed_epoch,selected=True)
    tests={};g=Generator()
    try:
        test=s.data('reserved_test',cfg['dataset']['test'],cfg['reserved_seeds'][0],g)
        for (seed,arm),m in models.items():tests[f'{seed}/{arm}']=evaluate(s,m['model'],test,arm)
        test_ood=s.data('reserved_ood',cfg['dataset']['ood'],cfg['reserved_seeds'][1],g)
        for (seed,arm),m in models.items():tests[f'ood/{seed}/{arm}']=evaluate(s,m['model'],test_ood,arm)
    finally:g.close()
    save(run/'results.json',dict(stop_reason=stop_reason,completed_epochs=completed_epoch,selection=selected,tests=tests,elapsed_seconds=time.time()-cfg['started_unix']))
    s.status(stage='complete',epoch=completed_epoch,stop_reason=stop_reason)


def prepare(run,smoke=False):
    preflight=json.loads((HERE/'preflight_002/report.json').read_text())
    if not preflight.get('passed'):raise RuntimeError('Preflight did not pass')
    run.mkdir(exist_ok=False);(run/'checkpoints').mkdir();(run/'data').mkdir();(run/'geometry').mkdir()
    cfg=json.loads((HERE/'PROPOSED_CONFIG.json').read_text());start=time.time()
    cfg.update(status='prepared',started=now(),started_unix=start,deadline_unix=start+(1800 if smoke else 36000),loss='weighted detection / position / size / rotation / visibility',
        dataset=dict(train=32 if smoke else 12000,validation=16 if smoke else 2000,test=16 if smoke else 2000,ood=16 if smoke else 512),seeds=[1,2,3],preflight=preflight,
        estimated_epoch_seconds=preflight['seconds_per_update']*2*6*375,
        detection_background_weight=1.,microbatch=16)
    cfg['checkpoint_selection']='Mean of the four available arrangement-stratum validation losses; overall validation loss plotted separately'
    cfg['matching_cost']='5 * normalized position L1 + normalized size L1 - detection probability; symmetry-aware rotation in training loss'
    cfg['reserved_seeds']=[8900001,8900002] if smoke else [8201001,8201002]
    if smoke:cfg['optimization']['maximum_epochs']=1
    cfg['smoke']=smoke
    save(run/'config.json',cfg)
    source=run/'source';source.mkdir()
    for name in ['train.py','scene_data.py','learning.py','model_prototype.py','compare_geometry.py','preflight.py']:
        shutil.copy2(HERE/name,source/name)
    save(run/'source_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()})
    save(run/'status.json',dict(stage='prepared',time=now(),heartbeat_unix=time.time()))
    print(json.dumps(dict(run=str(run.resolve()),deadline_unix=cfg['deadline_unix'])),flush=True)


def supervisor(run):
    # Reuse proven independent-process / sleep inhibition and deadline code,
    # but launch this worker, not the V1 worker.
    import ctypes,subprocess
    from night import independence
    proof=independence();save(run/'independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Refusing job-bound supervisor')
    kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState(0x80000001)
    cfg=json.loads((run/'config.json').read_text())
    try:
        with (run/'worker.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,str(HERE/'train.py'),'worker',str(run)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            save(run/'supervisor.json',dict(pid=os.getpid(),worker_pid=process.pid,deadline_unix=cfg['deadline_unix'],started=now()))
            reason=None
            while process.poll() is None:
                time.sleep(15);status=run/'status.json'
                if time.time()>cfg['deadline_unix']+120:reason='hard_deadline';break
                if status.exists() and time.time()-status.stat().st_mtime>1200:reason='no_progress_20_minutes';break
            if reason:
                process.terminate();process.wait(timeout=30);save(run/'status.json',dict(stage='error',reason=reason,time=now()))
            save(run/'supervisor_exit.json',dict(returncode=process.returncode,reason=reason,time=now()))
    finally:kernel.SetThreadExecutionState(0x80000000)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','worker','supervise']);parser.add_argument('run',type=Path);parser.add_argument('--smoke',action='store_true');a=parser.parse_args();run=a.run.resolve()
    try:
        if a.mode=='prepare':prepare(run,a.smoke)
        elif a.mode=='supervise':supervisor(run)
        else:worker(run)
    except Exception as e:
        if run.exists():save(run/'status.json',dict(stage='error',error=repr(e),time=now()))
        traceback.print_exc();raise
