"""Resumable paired trainer primitives; validation never changes sampler state."""
import copy,random,os
from pathlib import Path
import numpy as np
import torch
from .common import sha,save

def forward(model,batch):
    raw=model(batch['images'],batch['rays'],batch['view_available'])
    roles=torch.stack([batch['view_available'][:,0],batch['view_available'][:,1],batch['view_available'][:,2:].any(1)],1)
    return raw,roles
def tensors(arrays,device):return {k:torch.as_tensor(v,device=device) for k,v in arrays.items()}
def learning_rate(step,steps_per_epoch,epochs,base=1e-4,warmup_epochs=3):
    warm=warmup_epochs*steps_per_epoch;total=epochs*steps_per_epoch
    if step<warm:return base*(step+1)/max(1,warm)
    return base*(.05+.95*.5*(1+np.cos(np.pi*min(1.,(step-warm)/max(1,total-warm)))))

def checkpoint(path,tracks,cursor,curves,extras):
    state=dict(schema=1,cursor=copy.deepcopy(cursor),curves=copy.deepcopy(curves),extras=copy.deepcopy(extras),
        tracks={key:dict(model=t['model'].state_dict(),optimizer=t['optimizer'].state_dict(),step=t['step'],best=t['best'],best_epoch=t['best_epoch'],
            grads={name:None if p.grad is None else p.grad for name,p in t['model'].named_parameters()}) for key,t in tracks.items()},
        rng=dict(torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,numpy=np.random.get_state(),python=random.getstate()))
    path=Path(path);path.parent.mkdir(exist_ok=True,parents=True);tmp=path.with_suffix('.pth.tmp')
    with tmp.open('wb') as f:torch.save(state,f);f.flush();os.fsync(f.fileno())
    tmp.replace(path);save(path.with_suffix('.sha256.json'),dict(sha256=sha(path),cursor=cursor))

def restore(path,tracks,device='cuda'):
    path=Path(path)
    if sha(path)!=__import__('json').loads(path.with_suffix('.sha256.json').read_text())['sha256']:raise RuntimeError('Checkpoint hash mismatch')
    state=torch.load(path,map_location=device,weights_only=False)
    if set(state['tracks'])!=set(tracks):raise RuntimeError('Checkpoint track mismatch')
    for key,t in tracks.items():
        s=state['tracks'][key];t['model'].load_state_dict(s['model']);t['optimizer'].load_state_dict(s['optimizer']);t.update(step=s['step'],best=s['best'],best_epoch=s['best_epoch'])
        for name,p in t['model'].named_parameters():p.grad=None if s['grads'][name] is None else s['grads'][name].to(device).clone()
    torch.set_rng_state(state['rng']['torch'].cpu())
    if state['rng']['cuda'] is not None:torch.cuda.set_rng_state_all([v.cpu() for v in state['rng']['cuda']])
    np.random.set_state(state['rng']['numpy']);random.setstate(state['rng']['python'])
    return state['cursor'],state['curves'],state['extras']

def saved_rng():
    return dict(torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,numpy=np.random.get_state(),python=random.getstate())
def put_rng(s):
    torch.set_rng_state(s['torch'])
    if s['cuda'] is not None:torch.cuda.set_rng_state_all(s['cuda'])
    np.random.set_state(s['numpy']);random.setstate(s['python'])
