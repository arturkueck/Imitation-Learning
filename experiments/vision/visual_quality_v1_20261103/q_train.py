"""Three small quality heads, train-family normalization, validation-only selection."""
import math,time
from pathlib import Path
import numpy as np
import torch
from q_model import QualityModel,loss
from q_protocol import verify,save,read,sha,now
from q_data import load
from pipeline.common import check_stop

def weights(families):
    _,inverse,count=np.unique(families,axis=0,return_inverse=True,return_counts=True)
    return (1/count[inverse]).astype(np.float32)

def subset(data):
    m=data['eligible']&data['labelled']
    return {k:v[m] for k,v in data.items()}

def train(run):
    run=Path(run);cfg=verify(run)
    if (run/'head_freeze.json').exists():raise RuntimeError('Heads already frozen')
    train=subset(load(run,'request_train'));valid=subset(load(run,'request_validation'))
    if len(train['x'])<300 or len(valid['x'])<60:raise RuntimeError('Insufficient eligible training/validation proposals')
    counts=np.bincount(train['classes'],minlength=3)
    if min(counts[0],counts[2])<100:raise RuntimeError('Insufficient harmful/helpful training labels; do not change thresholds automatically')
    mean=train['x'].mean(0);std=train['x'].std(0);std[std<1e-5]=1.
    scaler=dict(mean=mean.tolist(),std=std.tolist(),source='request_train_only');save(run/'scaler.json',scaler)
    def tensors(data):
        return dict(x=torch.tensor(np.clip((data['x']-mean)/std,-8,8)),y=torch.tensor(data['classes']),g=torch.tensor(data['gains']),w=torch.tensor(weights(data['family'])))
    a=tensors(train);v=tensors(valid);probe=tensors({k:z[train['family'][:,1]<128] for k,z in train.items()})
    torch.set_num_threads(2);curves=[];folder=run/'checkpoints';folder.mkdir(exist_ok=True)
    if list(folder.glob('*.pth')):raise RuntimeError('Checkpoints exist; targeted recovery required, no overwrite')
    def evaluate(model,data):
        model.eval()
        with torch.no_grad():return float(loss(model,data['x'],data['y'],data['g'],data['w']))
    selected=[]
    for seed in cfg['seeds']:
        torch.manual_seed(seed);model=QualityModel();opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
        best=float('inf');stale=0;updates=0
        for epoch in range(81):
            check_stop(run,120);train_loss=None
            if epoch:
                model.train();order=torch.randperm(len(a['x']),generator=torch.Generator().manual_seed(seed*1000+epoch));total=0.;mass=0.
                lr=.001*(.1+.9*.5*(1+math.cos(math.pi*(epoch-1)/80)))
                for pg in opt.param_groups:pg['lr']=lr
                for at in range(0,len(order),256):
                    check_stop(run,60);idx=order[at:at+256];opt.zero_grad();l=loss(model,a['x'][idx],a['y'][idx],a['g'][idx],a['w'][idx]);l.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();updates+=1;total+=float(l.detach())*float(a['w'][idx].sum());mass+=float(a['w'][idx].sum())
                train_loss=total/mass
            vl=evaluate(model,v);pl=evaluate(model,probe)
            if not all(np.isfinite(x) for x in [vl,pl]):raise RuntimeError('Nonfinite validation/probe loss')
            curves.append(dict(seed=seed,epoch=epoch,updates=updates,train_loss=train_loss,validation_loss=vl,probe_loss=pl,time=now()))
            if vl<best-1e-5:
                best=vl;stale=0;temp=folder/f'seed{seed}_best.tmp';torch.save(dict(model=model.state_dict(),seed=seed,epoch=epoch,updates=updates,validation_loss=vl,protocol_sha256=sha(run/'config.json')),temp);temp.replace(folder/f'seed{seed}_best.pth')
            else:stale+=1
            temp=folder/f'seed{seed}_latest.tmp';torch.save(dict(model=model.state_dict(),optimizer=opt.state_dict(),epoch=epoch,updates=updates,torch_rng=torch.get_rng_state()),temp);temp.replace(folder/f'seed{seed}_latest.pth')
            save(run/'curves.json',curves);save(run/'status.json',dict(stage='training',seed=seed,epoch=epoch,updates=updates,time=now(),training_started=updates>0))
            if epoch%5==0:plots(run,curves)
            if epoch and stale>=10:break
        path=folder/f'seed{seed}_best.pth'
        if torch.load(path,map_location='cpu',weights_only=False)['updates']==0:raise RuntimeError('Best checkpoint never learned; no trained head promoted')
        selected.append(dict(seed=seed,file=path.relative_to(run).as_posix(),sha256=sha(path)))
    save(run/'head_freeze.json',dict(models=selected,scaler_sha256=sha(run/'scaler.json'),protocol_sha256=sha(run/'config.json')))
    plots(run,curves)

def plots(run,curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for seed,ax in enumerate(axes,1):
        rows=[r for r in curves if r['seed']==seed]
        for name,label in [('train_loss','Training'),('validation_loss','Validation'),('probe_loss','Feste Trainingsprobe')]:
            p=[(r['epoch'],r[name]) for r in rows if r[name] is not None]
            if p:ax.plot(*zip(*p),label=label)
        ax.set(title=f'Seed{seed}',xlabel='Epoche',ylabel='Qualitäts-Loss');ax.grid(alpha=.2)
        if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(Path(run)/'loss.png',dpi=140);plt.close(fig)
