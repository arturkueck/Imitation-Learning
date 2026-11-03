"""Bounded V3 perception run. Independent Windows supervisor; no hardware commands."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys,json,time,math,hashlib,argparse,traceback,shutil,subprocess
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'experiments/visual_overnight_20261101'))
from night import save,atomic_checkpoint,independence


def now():return datetime.now(timezone.utc).isoformat()
def deadline():return datetime.fromisoformat(json.loads((HERE/'session.json').read_text())['deadline']).timestamp()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


class Session:
    def __init__(self,run):
        self.run=run;self.cfg=json.loads((run/'config.json').read_text());self.state={};self.deadline=self.cfg['deadline_unix']
    def status(self,**values):
        self.state.update(values);self.state.update(time=now(),heartbeat_unix=time.time(),pid=os.getpid())
        save(self.run/'status.json',self.state)
    def stopped(self,reserve=0):return time.time()>=self.deadline-reserve or (self.run/'STOP_REQUESTED').exists()


def collect(s,g,split,count,seed):
    import numpy as np
    folder=s.run/'data'/split;folder.mkdir(parents=True,exist_ok=False)
    arrays={};counts=np.zeros(6,int);kinds=np.zeros(4,int);start=time.time()
    for i in range(count):
        if s.stopped(1800):raise TimeoutError('Global deadline during data generation')
        row=g.family(seed,i,s.run/'observations'/split/f'{i:06d}',ood=split=='test_geometry_ood',camera_ood=split=='test_camera_ood')
        if not arrays:
            for k,v in row.items():arrays[k]=np.lib.format.open_memmap(folder/f'{k}.npy',mode='w+',dtype=v.dtype,shape=(count,)+v.shape)
        for k,v in row.items():arrays[k][i]=v
        counts[int(row['count'])]+=1;kinds[int(row['kind'])]+=1
        if i%25==0:s.status(stage='render',split=split,rendered=i+1,render_total=count,
                           loss=None,seconds_per_family=(time.time()-start)/(i+1))
    for v in arrays.values():v.flush()
    save(folder/'manifest.json',dict(split=split,count=count,seed=seed,count_histogram=counts.tolist(),
        kind_histogram=kinds.tolist(),elapsed_seconds=time.time()-start,rejections=g.rejections.copy(),
        files={p.name:sha(p) for p in sorted(folder.glob('*.npy'))},
        labels='oracle evaluation/training only',observations='RGB and calibrated rays',poses=6))
    return arrays


def load_data(run,split):
    import numpy as np
    return {p.stem:np.load(p,mmap_mode='r') for p in (run/'data'/split).glob('*.npy')}


def evaluate(s,model,data,variant,indices=None,original=False):
    import numpy as np,torch
    from model_v3 import context_arrays,tensor_context,predict
    from learning import criterion,decode
    model.eval();ids=np.arange(len(data['images'])) if indices is None else np.asarray(indices)
    total=0.;parts={};errors=[];correct=[];success=0;observations=0;strata={};bands={}
    with torch.inference_mode():
        for at in range(0,len(ids),8):
            sub=ids[at:at+8];arrays=context_arrays(data,sub,variant,current=0 if original else None)
            batch=tensor_context(arrays);out,av=predict(model,batch);loss,components,matches=criterion(out,batch,av);d=decode(out)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite validation loss')
            total+=float(loss)*len(sub)
            for k,v in components.items():parts[k]=parts.get(k,0.)+float(v)*len(sub)
            for i,(pi,gi) in enumerate(matches):
                pred=int((d['probability'][i]>=.5).sum());correct.append(pred==len(gi));observations+=len(gi)
                if len(pi):
                    error=torch.linalg.vector_norm(d['position'][i,pi]-batch['positions'][i,gi],dim=-1)*1000
                    errors.extend(error.cpu().tolist());success+=int(((error<=10)&(d['probability'][i,pi]>=.5)).sum())
            # Loss selection balances the four arrangement strata, as in V2.
            for kind in torch.unique(batch['kind']):
                mask=batch['kind']==kind
                l,_,_=criterion({k:v[mask] for k,v in out.items()},{k:v[mask] for k,v in batch.items()},av[mask])
                k=str(int(kind));old=strata.get(k,[0.,0]);strata[k]=[old[0]+float(l)*int(mask.sum()),old[1]+int(mask.sum())]
            for band in np.unique(arrays['current']):
                mask=torch.as_tensor(arrays['current']==band,device='cuda')
                l,_,_=criterion({k:v[mask] for k,v in out.items()},{k:v[mask] for k,v in batch.items()},av[mask])
                k=str(int(band));old=bands.get(k,[0.,0]);bands[k]=[old[0]+float(l)*int(mask.sum()),old[1]+int(mask.sum())]
            if at%128==0:s.status(stage='validation',evaluated=min(at+8,len(ids)),eval_total=len(ids),model=variant)
    return dict(loss=total/len(ids),components={k:v/len(ids) for k,v in parts.items()},
                balanced_loss=float(np.mean([x[0]/x[1] for x in strata.values()])),
                stratum_losses={k:x[0]/x[1] for k,x in strata.items()},pose_losses={k:x[0]/x[1] for k,x in bands.items()},
                assignment_position_mm=float(np.mean(errors)) if errors else None,
                count_accuracy=float(np.mean(correct)),recall_at_10mm=success/observations if observations else None,
                denominator_gt_observable=observations,scenes=len(ids))


def plots(run,curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,2,figsize=(11,9),layout='constrained')
    for seed in [1,2,3]:
        for col,variant in enumerate(['M1','M2']):
            rows=[x for x in curves if x['seed']==seed and x['arm']==variant];ax=axes[seed-1,col]
            for key,label in [('train_loss','Training'),('validation_loss','Validation'),('probe_loss','Train-Probe (eval)')]:
                ax.plot([x['epoch'] for x in rows],[x[key] for x in rows],label=label)
            ax.set(title=f'{variant}, Seed {seed}',xlabel='Epoche (Teilstände gekennzeichnet)',ylabel='Loss');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(run/'loss.png',dpi=130);fig.savefig(run/'loss.svg');plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,6),layout='constrained')
    for ax,key in zip(axes.flat,['detection','position','size','rotation','visibility','learning_rate']):
        for seed in [1,2,3]:
            for variant in ['M1','M2']:
                rows=[x for x in curves if x['seed']==seed and x['arm']==variant]
                ax.plot([x['epoch'] for x in rows],[x['learning_rate'] if key=='learning_rate' else x['validation_components'][key] for x in rows],label=f'{variant}/{seed}')
        ax.set(title=key,xlabel='Epoche');ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=6);fig.savefig(run/'loss_components.png',dpi=130);plt.close(fig)


def geometry(s,models,data,epoch,tag=''):
    import numpy as np,torch
    from PIL import Image
    from model_v3 import context_arrays,tensor_context,predict
    from learning import decode,boxes
    from compare_geometry import render
    indexpath=s.run/'geometry/index.json';index=json.loads(indexpath.read_text()) if indexpath.exists() else []
    ids=[]
    for n in range(6):ids.extend(np.flatnonzero(data['count']==n)[:2].tolist())
    for (seed,variant),m in models.items():
        m['model'].eval();a=context_arrays(data,ids,variant);b=tensor_context(a)
        with torch.inference_mode():raw,av=predict(m['model'],b);decoded=decode(raw)
        for k,i in enumerate(ids):
            if s.stopped(120):break
            name=f'{tag}epoch_{epoch:06.2f}_{variant}_seed{seed}_scene{i:04d}';folder=s.run/'geometry'/name
            observable=a['active'][k]&((a['visibility'][k]>=.05)&av[k].cpu().numpy()[None]).any(-1)
            gt=[dict(center=a['positions'][k,j].tolist(),size=a['sizes'][k,j].tolist(),rotation=a['rotations'][k,j].tolist(),observable=bool(observable[j])) for j in np.flatnonzero(a['active'][k])]
            scene=dict(label=f'Vision V3 | {tag}Epoche {epoch:.2f} | {variant} Seed {seed} | Szene {i}',
                ground_truth=gt,predictions=boxes(decoded,k),bounds=[[-.23,.23],[-.23,.23],[.78,1.18]],
                epoch=epoch,seed=seed,variant=variant,family=a['family'][k].tolist(),updates=m['step'])
            render(scene,folder)
            Image.fromarray(np.concatenate(a['images'][k,:3],axis=1)).save(folder/'inputs.png')
            save(folder/'context.json',dict(available=a['view_available'][k].tolist(),
                note='Input montage shows two fixed and current wrist; M2 history described by availability and dataset context'))
            for file,kind in [('overlay.png','geometry'),('inputs.png','geometry-input'),('metrics.json','geometry-metrics')]:
                index.append(dict(name=name+'_'+file,file=f'geometry/{name}/{file}',kind=kind,epoch=epoch,seed=seed,variant=variant,label=f'{tag}{variant} Seed {seed} Epoche {epoch:.2f} Szene {i}'))
            s.status(stage='geometry',epoch=epoch,model=f'{variant}/{seed}',scene=i)
    save(indexpath,index)


def checkpoint(s,models,epoch,sampler_position=0):
    import numpy as np,torch
    value=dict(epoch=epoch,sampler_position=sampler_position,torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),
        numpy_rng=np.random.get_state(),config=s.cfg,models={f'{seed}/{variant}':dict(model=m['model'].state_dict(),optimizer=m['opt'].state_dict(),
          step=m['step'],best=m['best'],best_epoch=m['best_epoch'],stale=m['stale']) for (seed,variant),m in models.items()})
    atomic_checkpoint(s.run/'checkpoints/latest.pth',value,torch)


def worker(run):
    import numpy as np,torch
    from preflight import settings
    from model_v3 import ScenePerception,context_arrays,tensor_context,predict
    from learning import criterion
    from data_v3 import PoseGenerator
    settings();s=Session(run);s.status(stage='initializing',epoch=0,step=0)
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    for rel,expected in s.cfg['source_hashes'].items():
        if sha(ROOT/rel)!=expected:raise RuntimeError('Frozen source changed: '+rel)
    save(run/'runtime.json',dict(torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name(),parameters=904112))
    g=PoseGenerator()
    try:
        bank=g.make_bank();save(run/'pose_bank.json',bank)
        train=collect(s,g,'train',s.cfg['dataset']['train'],s.cfg['data_seeds']['train'])
        valid=collect(s,g,'validation',s.cfg['dataset']['validation'],s.cfg['data_seeds']['validation'])
    finally:g.close()
    if set(map(tuple,train['family'])).intersection(map(tuple,valid['family'])):raise RuntimeError('Family leakage')
    models={};curves=[]
    selection=json.loads((ROOT/'experiments/visual_scene_v2_20261101/run_001/selection.json').read_text())['models']
    for seed in [1,2,3]:
        record=next(x for x in selection if x['seed']==seed and x['arm']=='fixed_wrist')
        parent=ROOT/f'experiments/visual_scene_v2_20261101/run_001/checkpoints/fixed_wrist_seed{seed}_best.pth'
        if sha(parent)!=record['sha256']:raise RuntimeError('Parent checkpoint hash changed')
        for variant in ['M1','M2']:
            torch.manual_seed(seed);model=ScenePerception().cuda();model.load_state_dict(torch.load(parent,map_location='cuda',weights_only=False)['model'])
            models[(seed,variant)]=dict(model=model,opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4),step=0,best=float('inf'),best_epoch=0,stale=0)
    # Frozen V2 controls use the same family panel before any new optimizer updates.
    references={}
    for seed in [1,2,3]:
        references[str(seed)]=dict(robust=evaluate(s,models[(seed,'M1')]['model'],valid,'M1'),
                                 original=evaluate(s,models[(seed,'M1')]['model'],valid,'M1',original=True))
    save(run/'reference_metrics.json',references)
    def validate(epoch,losses=None,partial=False):
        for (seed,variant),m in models.items():
            probe=evaluate(s,m['model'],train,variant,np.arange(min(128,len(train['images']))))
            val=evaluate(s,m['model'],valid,variant)
            row=dict(seed=seed,arm=variant,epoch=epoch,partial_epoch=partial,updates=m['step'],time=now(),
                elapsed_seconds=time.time()-s.cfg['started_unix'],train_loss=losses[(seed,variant)] if losses else None,
                probe_loss=probe['loss'],validation_loss=val['loss'],validation_components=val['components'],
                validation_mm=val['assignment_position_mm'],validation_count_accuracy=val['count_accuracy'],
                validation_recall_10mm=val['recall_at_10mm'],selection_loss=val['balanced_loss'],
                validation_strata=val['stratum_losses'],pose_losses=val['pose_losses'],learning_rate=m['opt'].param_groups[0]['lr'])
            if epoch==0:row['train_loss']=None # No epoch has been trained; no invented training loss.
            curves.append(row)
            if val['balanced_loss']<m['best']:
                m['stale']=0 if val['balanced_loss']<m['best']*.995 else m['stale']+1
                m['best']=val['balanced_loss'];m['best_epoch']=epoch
                atomic_checkpoint(run/'checkpoints'/f'{variant}_seed{seed}_best.pth',dict(model=m['model'].state_dict(),epoch=epoch,step=m['step'],validation=val),torch)
            else:m['stale']+=1
            s.status(stage='validation',epoch=epoch,step=m['step'],loss=val['loss'],model=f'{variant}_seed{seed}',latest_metrics=row)
        save(run/'curves.json',curves);plots(run,curves);checkpoint(s,models,epoch)
    validate(0);geometry(s,models,valid,0)
    steps_per_epoch=math.ceil(len(train['images'])/32);stop_reason='maximum_epochs';last_epoch=0
    for epoch in range(1,s.cfg['optimization']['maximum_epochs']+1):
        losses={key:0. for key in models};seen=0
        order=np.random.default_rng(9370000+epoch).permutation(len(train['images']))
        for at in range(0,len(order),32):
            if time.time()>=s.cfg['perception_training_end_unix'] or s.stopped(900):
                stop_reason='user_stop' if (run/'STOP_REQUESTED').exists() else 'phase_time_budget';break
            ids=order[at:at+32];seen+=len(ids)
            for (seed,variant),m in models.items():
                warmup=3*steps_per_epoch;total=60*steps_per_epoch;step=m['step']
                factor=(step+1)/warmup if step<warmup else .05+.95*.5*(1+math.cos(math.pi*(step-warmup)/max(1,total-warmup)))
                for group in m['opt'].param_groups:group['lr']=1e-4*factor
                m['model'].train();m['opt'].zero_grad(set_to_none=True);batch_loss=0.
                for micro in range(0,len(ids),4):
                    torch.manual_seed(seed*100000000+epoch*100000+at+micro)
                    a=context_arrays(train,ids[micro:micro+4],variant,epoch=epoch,training=True)
                    batch=tensor_context(a);out,av=predict(m['model'],batch);loss,_,_=criterion(out,batch,av)
                    if not torch.isfinite(loss):raise RuntimeError('Nonfinite training loss')
                    (loss*len(a['images'])/len(ids)).backward();batch_loss+=float(loss.detach())*len(a['images'])
                torch.nn.utils.clip_grad_norm_(m['model'].parameters(),1.,error_if_nonfinite=True);m['opt'].step();m['step']+=1
                losses[(seed,variant)]+=batch_loss
            if at//32%10==0:s.status(stage='train',epoch=epoch,step=models[(1,'M1')]['step'],batch=at//32,batches=steps_per_epoch,loss=batch_loss/len(ids))
            if models[(1,'M1')]['step']%100==0:checkpoint(s,models,epoch,sampler_position=at+len(ids))
        else:
            last_epoch=epoch;validate(epoch,{k:v/seen for k,v in losses.items()})
            if epoch%5==0:geometry(s,models,valid,epoch)
            if all(m['stale']>=10 for m in models.values()):stop_reason='early_stopping';break
            continue
        if seen:
            last_epoch=epoch-1+seen/len(order);validate(last_epoch,{k:v/seen for k,v in losses.items()},partial=True)
        break
    if stop_reason=='user_stop':raise RuntimeError('User stop requested; no success handoff')
    selected=[];final={}
    for (seed,variant),m in models.items():
        path=run/'checkpoints'/f'{variant}_seed{seed}_best.pth'
        m['model'].load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model'])
        final[f'{seed}/{variant}']=dict(robust=evaluate(s,m['model'],valid,variant),original=evaluate(s,m['model'],valid,variant,original=True))
        selected.append(dict(seed=seed,arm=variant,selected_epoch=m['best_epoch'],updates_paid=m['step'],sha256=sha(path)))
    save(run/'selection.json',dict(time=now(),models=selected,selection_only='model_validation_no_end_tests'))
    geometry(s,models,valid,last_epoch,tag='best_')
    result=dict(stop_reason=stop_reason,completed_epochs=last_epoch,selection=selected,validation=final,
                references=references,elapsed_seconds=time.time()-s.cfg['started_unix'],final_tests_evaluated=False,
                next_phase='followup_review_then_requests_and_reserved_tests')
    save(run/'results.json',result)
    save(run/'checkpoint_hashes.json',{p.name:sha(p) for p in sorted((run/'checkpoints').glob('*.pth'))})
    s.status(stage='complete',epoch=last_epoch,stop_reason=stop_reason,training_complete=True,validation_complete=True)


def supervise(run):
    import ctypes,psutil
    proof=independence();save(run/'independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Supervisor must be outside job object')
    kernel=ctypes.windll.kernel32;kernel.SetThreadExecutionState(0x80000001)
    cfg=json.loads((run/'config.json').read_text());process=None
    try:
        with (run/'worker.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,str(HERE/'train_v3.py'),'worker',str(run)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        identities=[dict(pid=os.getpid(),create_time=psutil.Process().create_time()),dict(pid=process.pid,create_time=psutil.Process(process.pid).create_time())]
        from deadline_guard import register
        register(os.getpid(),'perception_supervisor',run);register(process.pid,'perception_worker',run)
        save(run/'supervisor.json',dict(pid=os.getpid(),worker_pid=process.pid,deadline_unix=cfg['deadline_unix'],started=now()))
        save(run/'handoff_result.json',dict(schema_version=1,run_id=run.name,status='running',workers=identities))
        reason=None
        while process.poll() is None:
            time.sleep(5)
            if time.time()>=cfg['deadline_unix']:reason='global_deadline';break
            p=run/'status.json'
            if p.exists() and time.time()-p.stat().st_mtime>1800:reason='no_progress_30_minutes';break
        if reason:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        status=json.loads((run/'status.json').read_text()) if (run/'status.json').exists() else {}
        okay=process.returncode==0 and status.get('stage')=='complete'
        if okay:
            artifacts={key:dict(path=name,sha256=sha(run/name)) for key,name in [('metrics','results.json'),('curves','loss.png'),('checkpoint_manifest','checkpoint_hashes.json')]}
            save(run/'handoff_result.json',dict(schema_version=1,run_id=run.name,status='completed',training_complete=True,validation_complete=True,workers=identities,artifacts=artifacts))
        else:
            save(run/'handoff_result.json',dict(schema_version=1,run_id=run.name,status='failed',workers=identities,error=reason or status.get('error') or f'worker_exit_{process.returncode}'))
        save(run/'supervisor_exit.json',dict(time=now(),returncode=process.returncode,reason=reason))
    finally:kernel.SetThreadExecutionState(0x80000000)


def prepare(run,smoke=False):
    cfg=json.loads((HERE/'PROPOSED_CONFIG.json').read_text());session=json.loads((HERE/'session.json').read_text())
    pilot=json.loads((HERE/'data_pilot_002/report.json').read_text());preflight=json.loads((HERE/'preflight_002/report.json').read_text())
    if not pilot['passed'] or not preflight['passed']:raise RuntimeError('Preflight/pilot missing or failed')
    run.mkdir(exist_ok=False)
    for folder in ['checkpoints','data','geometry','source']:(run/folder).mkdir()
    start=datetime.fromisoformat(session['start_at']).timestamp()
    cfg.update(status='prepared',training_enabled=True,training_started=False,started=session['start_at'],started_unix=start,
        deadline_unix=deadline(),perception_training_end_unix=min(start+8*3600,deadline()-3600),
        dataset=dict(train=12000,validation=2000),seeds=[1,2,3],variants=['M1','M2'],paired_seeds=[1,2,3],
        data_seeds=dict(train=9364001,validation=9365001),smoke=smoke,
        pilot_report=pilot,preflight=preflight,checkpoint_selection='balanced arrangement model-validation loss; reserved tests untouched',
        reserved_seeds=dict(request_train=9366001,request_validation=9367001,request_calibration=9368001,test_iid=9369001,test_camera_ood=9371001,test_geometry_ood=9372001))
    cfg.pop('training_started',None);cfg.pop('optimizer_updates',None)
    cfg['models']['M2']='implemented variable-view history: 2 fixed + 0..3 wrist, shared role embeddings, 904112 parameters'
    if smoke:
        cfg['dataset']=dict(train=32,validation=16);cfg['data_seeds']=dict(train=9364101,validation=9365101)
        cfg['optimization']['maximum_epochs']=1
    sources=[HERE/x for x in ['train_v3.py','data_v3.py','physical_setup.py','model_v3.py','request_heads.py','preflight_v3.py','deadline_guard.py','monitor_check.py','completion_gate.py','session.json','PLAN.md','FOLLOWUP.md','PREPARATION_NOTES.md']]
    sources += [ROOT/'experiments/visual_scene_v2_20261101'/x for x in ['scene_data.py','learning.py','model_prototype.py','compare_geometry.py','preflight.py']]
    sources += [ROOT/'praxis/src/active_view'/x for x in ['collision.py','geometry.py','capture_requests.py']]
    sources += [ROOT/'experiments/visual_overnight_20261101/night.py',ROOT/'experiments/visual_scene_v2_20261101/run_001/selection.json']
    cfg['source_hashes']={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    for p in sources:
        target=run/'source'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    save(run/'config.json',cfg);save(run/'status.json',dict(stage='prepared',time=now(),heartbeat_unix=time.time()))
    return cfg


def launch(run):
    prepare(run)
    from completion_gate import mutate
    mutate('arm',run=run.relative_to(HERE).as_posix())
    flags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
    if (HERE/'deadline_guard.lock').exists():raise RuntimeError('Existing guard lock: inspect existing session first')
    with (HERE/'deadline_guard.log').open('x',encoding='utf-8') as log:
        guardian=subprocess.Popen([sys._base_executable,str(HERE/'deadline_guard.py'),'guard'],stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    save(HERE/'deadline_guard_launch.json',dict(pid=guardian.pid,time=now(),deadline_unix=deadline()))
    with (run/'supervisor.log').open('w',encoding='utf-8') as log:
        p=subprocess.Popen([sys._base_executable,str(HERE/'train_v3.py'),'supervise',str(run)],stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    save(run/'launch.json',dict(pid=p.pid,time=now(),deadline_unix=deadline()));print(json.dumps(dict(run=str(run),pid=p.pid)),flush=True)


if __name__=='__main__':
    # Base Python used for detached supervisor still needs this project's packages.
    import site
    site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','worker','supervise','launch']);parser.add_argument('run',type=Path);parser.add_argument('--smoke',action='store_true');a=parser.parse_args();run=a.run.resolve()
    try:
        if a.mode=='prepare':prepare(run,smoke=a.smoke)
        else:{'worker':worker,'supervise':supervise,'launch':launch}[a.mode](run)
    except Exception as error:
        if run.exists():save(run/'status.json',dict(stage='error',error=repr(error),time=now(),heartbeat_unix=time.time()))
        traceback.print_exc();raise
