"""Permutation invariant, observable-object losses and physical decoding."""
import itertools
import numpy as np
import torch
from torch.nn import functional as F
from scipy.optimize import linear_sum_assignment

ORIGIN=[0.,0.,.8]
SYMMETRIES=[]
for p in itertools.permutations(range(3)):
    for signs in itertools.product((-1,1),repeat=3):
        s=np.eye(3)[:,p]*signs
        if np.linalg.det(s)>.5:SYMMETRIES.append(s)
SYMMETRIES=np.array(SYMMETRIES,dtype=np.float32)


def initialize(model):
    with torch.no_grad():
        model.head[-1].bias[0]=-1
        model.head[-1].bias[1:4]=torch.tensor([0.,0.,.3])
        model.head[-1].bias[4:7]=.54132485
        model.head[-1].bias[7:13]=torch.tensor([1.,0.,0.,0.,1.,0.])
    return model


def decode(out):
    a=F.normalize(out['rotation_6d'][...,:3],dim=-1,eps=1e-6)
    b=out['rotation_6d'][...,3:];b=F.normalize(b-(a*b).sum(-1,keepdim=True)*a,dim=-1,eps=1e-6)
    R=torch.stack([a,b,torch.linalg.cross(a,b)],dim=-1)
    return dict(position=out['position']*.1+out['position'].new_tensor(ORIGIN),
                size=F.softplus(out['dimensions_raw'])*.05,rotation=R,
                probability=out['detection_logits'].sigmoid(),visibility=out['visibility_logits'].sigmoid())


def tensor_batch(data,indices,device='cuda'):
    return {k:torch.as_tensor(v[indices],device=device) for k,v in data.items()}


def run_model(model,batch,arm):
    images=batch['images'].permute(0,1,4,2,3).float()/255
    available=torch.ones((len(images),3),dtype=torch.bool,device=images.device)
    if arm=='fixed':available[:,2]=False
    return model(images,batch['rays'],available),available


def criterion(out,batch,available):
    d=decode(out);device=out['position'].device;B=len(out['position'])
    # Five slots have no extreme foreground/background imbalance. A 0.1
    # background weight caused over-counting in the tiny-set acceptance test.
    targets=torch.zeros_like(out['detection_logits']);weights=torch.ones_like(targets)
    components={k:out['position'].sum()*0 for k in ['position','size','rotation','visibility']}
    matches=[];rotation_group=torch.tensor(SYMMETRIES,device=device)
    for b in range(B):
        observable=batch['active'][b]&((batch['visibility'][b]>=.05)&available[b][None]).any(-1)
        gt=torch.where(observable)[0]
        if not len(gt):matches.append(([],[]));continue
        position=torch.cdist(d['position'][b],batch['positions'][b,gt].float(),p=1)/.1
        size=torch.cdist(d['size'][b],batch['sizes'][b,gt].float(),p=1)/.1
        cost=5*position+size-d['probability'][b,:,None]
        ii,jj=linear_sum_assignment(cost.detach().cpu().numpy());pi=torch.tensor(ii,device=device);gi=gt[torch.tensor(jj,device=device)]
        matches.append((ii,gi.detach().cpu().numpy()))
        targets[b,pi]=1;weights[b,pi]=1
        components['position']+=F.smooth_l1_loss(d['position'][b,pi]/.1,batch['positions'][b,gi].float()/.1,beta=.1)/B
        components['size']+=F.smooth_l1_loss(d['size'][b,pi]/.1,batch['sizes'][b,gi].float()/.1,beta=.1)/B
        trueR=batch['rotations'][b,gi].float();sizes=batch['sizes'][b,gi].float()
        # Only size-preserving signed permutations are physical box symmetries.
        permuted=torch.einsum('sij,nj->nsi',rotation_group.abs().transpose(-1,-2),sizes)
        allowed=(permuted-sizes[:,None]).abs().amax(-1)<1e-5
        equivalent=trueR[:,None]@rotation_group[None]
        relative=d['rotation'][b,pi,None].transpose(-1,-2)@equivalent
        cosine=((relative.diagonal(dim1=-2,dim2=-1).sum(-1)-1)/2).clamp(-1+1e-6,1-1e-6)
        angles=torch.acos(cosine)/np.pi
        components['rotation']+=angles.masked_fill(~allowed,10).min(-1).values.mean()/B
        vl=F.binary_cross_entropy_with_logits(out['visibility_logits'][b,pi],(batch['visibility'][b,gi]>=.05).float(),reduction='none')
        components['visibility']+=(vl*available[b]).sum()/(len(pi)*available[b].sum())/B
    components['detection']=F.binary_cross_entropy_with_logits(out['detection_logits'],targets,weight=weights)
    total=components['detection']+5*components['position']+components['size']+.5*components['rotation']+.25*components['visibility']
    return total,components,matches


def boxes(decoded,index,threshold=.5):
    d={k:v[index].detach().cpu().numpy() for k,v in decoded.items()}
    return [dict(center=d['position'][i].tolist(),size=d['size'][i].tolist(),rotation=d['rotation'][i].tolist(),score=float(d['probability'][i])) for i in range(5) if d['probability'][i]>=threshold]
