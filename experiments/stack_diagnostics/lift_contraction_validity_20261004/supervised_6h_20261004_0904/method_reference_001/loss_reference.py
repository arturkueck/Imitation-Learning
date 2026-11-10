"""Experimental loss reference. Not registered as a production BC algorithm.

All geometry, response matrices, masks and error envelopes are frozen cache
annotations. No function here estimates a valid envelope or grants stability.
"""
import math
import torch


def reference_loss(delta, action_difference, A, B, epsilon, weights, rho=.99):
    n=action_difference.shape[0]
    if not math.isfinite(rho) or not 0<=rho<1:
        raise ValueError('rho must be finite and in [0,1)')
    shapes=[(delta,(n,3)),(action_difference,(n,7)),(A,(n,3,3)),(B,(n,7,3)),(epsilon,(n,)),(weights,(n,))]
    if n==0 or any(tuple(x.shape)!=shape for x,shape in shapes):
        raise ValueError('Nonempty explicit per-example shapes are required')
    if any(x.device!=action_difference.device or x.dtype!=action_difference.dtype for x,_ in shapes):
        raise ValueError('All inputs must share floating dtype/device')
    if not action_difference.is_floating_point():raise ValueError('Floating tensors required')
    # Masked rows can contain an absent cache (NaN). Select BEFORE evaluating
    # norms/matrix products; NaN*0 would corrupt both loss and gradients.
    delta,A,B,epsilon,weights=[x.detach() for x in [delta,A,B,epsilon,weights]]
    if not torch.isfinite(weights).all() or (weights<0).any():raise ValueError('Weights must be finite and nonnegative')
    active=weights>0; index=active.nonzero(as_tuple=True)[0]
    zero=torch.where(torch.isfinite(action_difference),action_difference,torch.zeros_like(action_difference)).sum()*0
    raw_ratio=action_difference.new_zeros(n);upper_ratio=action_difference.new_zeros(n);hinge=action_difference.new_zeros(n)
    if len(index)==0:return zero,dict(raw_ratio=raw_ratio,upper_ratio=upper_ratio,hinge=hinge,weighted_rows=active)
    d,da,a,b,e,w=delta[index],action_difference[index],A[index],B[index],epsilon[index],weights[index]
    if any(not torch.isfinite(x).all() for x in [d,da,a,b,e]):raise ValueError('Active inputs must be finite')
    scale=torch.linalg.vector_norm(d,dim=-1)
    if (scale<=0).any() or (e<0).any():raise ValueError('Active delta must be nonzero and envelope nonnegative')
    prediction=torch.einsum('ni,nij->nj',d,a)+torch.einsum('ni,nij->nj',da,b)
    ratio=torch.linalg.vector_norm(prediction,dim=-1)/scale
    upper=ratio+e; value=torch.relu(upper.square()-rho*rho)
    raw_ratio=raw_ratio.index_copy(0,index,ratio);upper_ratio=upper_ratio.index_copy(0,index,upper);hinge=hinge.index_copy(0,index,value)
    # Denominator is the entire planned batch, never just surviving rows.
    loss=(w*value).sum()/n+zero
    return loss,dict(raw_ratio=raw_ratio,upper_ratio=upper_ratio,hinge=hinge,weighted_rows=active)


def action_region_mask(nominal, perturbed, low, high):
    """Detached componentwise support gate; not a dynamical validity proof."""
    if nominal.shape!=perturbed.shape or nominal.shape!=low.shape or nominal.shape!=high.shape or nominal.shape[-1]!=7:
        raise ValueError('Matched 7D action shapes required')
    x,y,lo,hi=[v.detach() for v in [nominal,perturbed,low,high]]
    valid=torch.isfinite(x).all(-1)&torch.isfinite(y).all(-1)&torch.isfinite(lo).all(-1)&torch.isfinite(hi).all(-1)&(lo<=hi).all(-1)
    return valid&(x>=lo).all(-1)&(x<=hi).all(-1)&(y>=lo).all(-1)&(y<=hi).all(-1)
