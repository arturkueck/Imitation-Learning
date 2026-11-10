"""Shared-weight variable-view extension. No extra perception parameters."""
from pathlib import Path
import sys
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
from model_prototype import ScenePerception as V2

class ScenePerception(V2):
    def forward(self,images,rays,view_available):
        b,v,c,h,w=images.shape
        if c!=3 or h!=160 or w!=160 or not 2<=v<=5:raise ValueError('Expected 2..5 calibrated RGB views')
        if rays.shape!=(b,v,20,20,6):raise ValueError('Invalid calibrated ray grid')
        if view_available.shape!=(b,v) or not view_available.any(dim=1).all():raise ValueError('Missing views')
        images=images*view_available[:,:,None,None,None]
        features=self.backbone(images.reshape(b*v,c,h,w)).reshape(b,v,128,20,20)
        tokens=features.permute(0,1,3,4,2)+self.ray_projection(rays)
        roles=torch.tensor([0,1]+[2]*(v-2),device=images.device)
        tokens=tokens+self.view_embedding(roles)[None,:,None,None,:]
        tokens=tokens.reshape(b,v*400,128)
        padding=(~view_available.bool())[:,:,None].expand(b,v,400).reshape(b,v*400)
        slots=self.decoder(self.queries[None].expand(b,-1,-1),tokens,memory_key_padding_mask=padding)
        out=self.head(slots)
        return dict(detection_logits=out[...,0],position=out[...,1:4],dimensions_raw=out[...,4:7],
                    rotation_6d=out[...,7:13],visibility_logits=out[...,13:16])


def context_arrays(data,ids,variant='M1',epoch=0,training=False,current=None,history=None):
    """Prefix-only histories; no future candidate pixels enter a context."""
    import numpy as np
    ids=np.asarray(ids);n=len(ids)
    if current is None:
        current=np.random.default_rng(713000+epoch).integers(0,6,n) if training else ids%6
    current=np.broadcast_to(np.asarray(current,dtype=int),(n,)).copy()
    views=3 if variant in ['M0','M1'] else 5
    images=np.zeros((n,views,160,160,3),np.uint8);rays=np.zeros((n,views,20,20,6),np.float32)
    available=np.zeros((n,views),bool);visible=np.zeros((n,5,3),np.float32)
    rng=np.random.default_rng(916000+epoch+int(ids[0] if n else 0))
    for k,(i,p) in enumerate(zip(ids,current)):
        images[k,:2]=data['images'][i,p,:2];rays[k,:2]=data['rays'][i,p,:2];available[k,:2]=True
        visible[k,:,:2]=data['visibility'][i,p,:,:2]
        if history is not None:
            wrist=list(history[k])
            if any(x>p or x<0 for x in wrist):raise ValueError('History includes future/unavailable image')
        elif views==3:wrist=[int(p)]
        else:
            earlier=list(range(int(p)))
            wrist=[int(p)]+earlier[-2:]
            if training:
                length=int(rng.integers(0,len(wrist)+1));wrist=wrist[:length]
        if len(wrist)>views-2:raise ValueError('Too many wrist images')
        for j,old in enumerate(wrist):
            images[k,j+2]=data['images'][i,old,2];rays[k,j+2]=data['rays'][i,old,2];available[k,j+2]=True
            visible[k,:,2]=np.maximum(visible[k,:,2],data['visibility'][i,old,:,2])
    result={key:np.array(data[key][ids],copy=True) for key in ['positions','sizes','rotations','active','count','kind','family']}
    result.update(images=images,rays=rays,visibility=visible,view_available=available,current=current)
    return result


def tensor_context(arrays,device='cuda'):
    return {k:torch.as_tensor(v,device=device) for k,v in arrays.items()}


def predict(model,batch):
    out=model(batch['images'].permute(0,1,4,2,3).float()/255,batch['rays'],batch['view_available'])
    role_available=torch.stack([batch['view_available'][:,0],batch['view_available'][:,1],batch['view_available'][:,2:].any(1)],1)
    return out,role_available
