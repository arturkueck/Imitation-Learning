"""V3 loss with explicit paired target membership and one shared assignment.

GT union membership is a training label only. Camera role visibility remains
contextual. Original V3 learning.py is preserved.
"""
import numpy as np
import torch
from torch.nn import functional as F
from scipy.optimize import linear_sum_assignment
from learning import decode,SYMMETRIES

def paired_criterion(out,batch,available):
    d=decode(out);B=len(out['position']);device=out['position'].device
    targets=torch.zeros_like(out['detection_logits'])
    parts={k:out['position'].sum()*0 for k in ['position','size','rotation','visibility']}
    sym=torch.tensor(SYMMETRIES,device=device);matches=[]
    for b in range(B):
        gt=torch.where(batch['active'][b]&batch['target_observable_override'][b])[0]
        if not len(gt):matches.append(([],[]));continue
        cost=5*torch.cdist(d['position'][b],batch['positions'][b,gt].float(),p=1)/.1
        cost+=torch.cdist(d['size'][b],batch['sizes'][b,gt].float(),p=1)/.1-d['probability'][b,:,None]
        ii,jj=linear_sum_assignment(cost.detach().cpu().numpy());pi=torch.tensor(ii,device=device);gi=gt[torch.tensor(jj,device=device)]
        matches.append((ii,gi.detach().cpu().numpy()));targets[b,pi]=1
        parts['position']+=F.smooth_l1_loss(d['position'][b,pi]/.1,batch['positions'][b,gi].float()/.1,beta=.1)/B
        parts['size']+=F.smooth_l1_loss(d['size'][b,pi]/.1,batch['sizes'][b,gi].float()/.1,beta=.1)/B
        sizes=batch['sizes'][b,gi].float();permuted=torch.einsum('sij,nj->nsi',sym.abs().transpose(-1,-2),sizes)
        allowed=(permuted-sizes[:,None]).abs().amax(-1)<1e-5
        equivalent=batch['rotations'][b,gi].float()[:,None]@sym[None]
        relative=d['rotation'][b,pi,None].transpose(-1,-2)@equivalent
        cosine=((relative.diagonal(dim1=-2,dim2=-1).sum(-1)-1)/2).clamp(-1+1e-6,1-1e-6)
        parts['rotation']+=(torch.acos(cosine)/np.pi).masked_fill(~allowed,10).min(-1).values.mean()/B
        role=F.binary_cross_entropy_with_logits(out['visibility_logits'][b,pi],(batch['visibility'][b,gi]>=.05).float(),reduction='none')
        parts['visibility']+=(role*available[b]).sum()/(len(pi)*available[b].sum())/B
    parts['detection']=F.binary_cross_entropy_with_logits(out['detection_logits'],targets)
    loss=parts['detection']+5*parts['position']+parts['size']+.5*parts['rotation']+.25*parts['visibility']
    return loss,parts,matches
