"""Strict acquired-view contexts and immutable fresh/replay dataset access."""
import json,hashlib
from pathlib import Path
import numpy as np
from .common import ROOT,sha,read

SLOTS=['initial','near','medium','oblique','right','left','base','elevated']

def choose_history(row,variant,epoch=0,seed=0,kind=None):
    valid=row['pose_available'];roles=list(row['slot_roles'])
    if not valid[0]:raise ValueError('Missing initial acquisition')
    rng=np.random.default_rng(np.random.SeedSequence([94831111,int(epoch),int(seed),*map(int,row['family'])]))
    if kind=='initial':return [0]
    side=kind=='side' or (kind is None and variant=='B' and not row.get('is_replay',False))
    allowed=['right','left','base','elevated'] if side else ['near','medium','oblique']
    pool=[i for i,r in enumerate(roles) if r in allowed and valid[i]]
    if not pool:return [0] # No invented acquisition / no hidden old-view substitution.
    count=min(len(pool),2 if kind is not None else int(rng.integers(1,3)))
    return [0]+rng.choice(pool,count,replace=False).tolist()

def context(row,history):
    if not history or history[0]!=0 or len(history)>3 or len(set(history))!=len(history):raise ValueError('Invalid acquired history')
    if any(i<0 or i>=len(row['images']) or not row['pose_available'][i] for i in history):raise ValueError('Unavailable/future acquisition')
    images=np.zeros((5,3,160,160),np.float32);rays=np.zeros((5,20,20,6),np.float32);available=np.zeros(5,bool)
    current=history[-1];images[:2]=row['images'][current,:2].transpose(0,3,1,2)/255.;rays[:2]=row['rays'][current,:2];available[:2]=True
    visible=np.zeros((5,3),np.float32);visible[:,:2]=row['visibility'][current,:,:2]
    for slot,pose in enumerate(reversed(history),2):
        images[slot]=row['images'][pose,2].transpose(2,0,1)/255.;rays[slot]=row['rays'][pose,2];available[slot]=True
        visible[:,2]=np.maximum(visible[:,2],row['visibility'][pose,:,2])
    result={k:np.array(row[k],copy=True) for k in ['positions','sizes','rotations','active','count','kind','family']}
    result.update(images=images,rays=rays,view_available=available,visibility=visible)
    return result

def pair(row,variant,epoch=0,seed=0,kind=None):
    history=choose_history(row,variant,epoch,seed,kind)
    before=context(row,[0]);after=context(row,history)
    union=row['active']&((before['visibility']>=.05).any(-1)|(after['visibility']>=.05).any(-1))
    for b in [before,after]:b['target_observable_override']=union.copy()
    return before,after,history

def batch_pairs(rows,variant,epoch=0,seed=0,kind=None):
    pairs=[pair(row,variant,epoch,seed,kind) for row in rows]
    return [{k:np.stack([p[j][k] for p in pairs]) for k in pairs[0][j]} for j in [0,1]]

class Store:
    def __init__(self,run,split,verify=True):
        self.run=Path(run);self.split=split;self.folder=self.run/'data'/split
        seal=read(self.folder/'seal.json')
        if sha(self.folder/'index.json')!=seal['index_sha256']:raise RuntimeError('Dataset index changed')
        self.records=read(self.folder/'index.json')['records']
        self.replay=[];self.maps=None
        if split=='train':
            cfg=read(self.run/'config.json');self.replay=cfg['replay']['indices'];folder=ROOT/cfg['replay']['directory']
            self.maps={p.stem:np.load(p,mmap_mode='r',allow_pickle=False) for p in folder.glob('*.npy')}
        if verify:
            for r in self.records:
                if sha(self.folder/r['file'])!=r['sha256']:raise RuntimeError('Dataset content changed: '+r['file'])
        self.hash=sha(self.folder/'seal.json')
    def __len__(self):return len(self.records)+len(self.replay)
    def __getitem__(self,index):
        if index<len(self.records):
            r=self.records[index]
            with np.load(self.folder/r['file'],allow_pickle=False) as z:value={k:np.array(z[k]) for k in z.files}
            if list(map(int,value['family']))!=r['family'] or r['split']!=self.split:raise RuntimeError('Family identity/role does not match sealed index')
            value['slot_roles']=SLOTS;value['is_replay']=False;return value
        at=self.replay[index-len(self.records)];value={k:np.array(v[at],copy=True) for k,v in self.maps.items()}
        value['pose_available']=np.ones(len(value['images']),bool);value['slot_roles']=['initial','near','near','medium','medium','oblique'];value['is_replay']=True
        return value
