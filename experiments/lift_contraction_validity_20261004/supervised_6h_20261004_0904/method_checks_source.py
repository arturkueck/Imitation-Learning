"""Numerical checks for masked undefined caches and full-action derivatives."""
import numpy as np
import torch
from loss_reference import reference_loss,action_region_mask

def run_checks():
    torch.manual_seed(4100413); dtype=torch.float64; checks={}
    delta=(torch.eye(3,dtype=dtype)*.005).requires_grad_(); A=torch.eye(3,dtype=dtype).repeat(3,1,1).requires_grad_()
    B=(torch.randn(3,7,3,dtype=dtype)*.006).requires_grad_(); da=(torch.randn(3,7,dtype=dtype)*.04).requires_grad_()
    eps=torch.tensor([.0021163913289946276,.003,0.],dtype=dtype,requires_grad=True);weights=torch.tensor([1.,.5,0.],dtype=dtype,requires_grad=True)
    with torch.no_grad():delta[2]=float('nan');A[2]=float('nan');B[2]=float('nan');da[2]=float('nan');eps[2]=float('nan')
    loss,info=reference_loss(delta,da,A,B,eps,weights)
    grads=torch.autograd.grad(loss,[da,delta,A,B,eps,weights],allow_unused=True)
    assert torch.isfinite(loss) and torch.isfinite(grads[0]).all() and not grads[0][2].any() and all(x is None for x in grads[1:])
    checks['undefined_zero_weight_cache_excluded_before_math']=True;checks['cache_annotations_have_no_gradients']=True
    dn=delta[:2].detach().numpy(); an=A[:2].detach().numpy(); bn=B[:2].detach().numpy(); un=da[:2].detach().numpy()
    pred=np.einsum('ni,nij->nj',dn,an)+np.einsum('ni,nij->nj',un,bn); upper=np.linalg.norm(pred,axis=-1)/np.linalg.norm(dn,axis=-1)+eps[:2].detach().numpy()
    expected=float(np.sum(weights[:2].detach().numpy()*np.maximum(upper**2-.99**2,0))/3)
    assert abs(expected-float(loss.detach()))<1e-14;checks['independent_numpy_formula_full_batch_denominator']=True
    good=da.detach().clone();good[2]=0;direction=torch.randn_like(good);direction/=direction.norm();step=1e-6
    values=[];signs=[]
    for sign in [-1,1]:
        v,z=reference_loss(delta,good+sign*step*direction,A,B,eps,weights);values.append(float(v));signs.append((z['hinge']>0).tolist())
    analytic=float((grads[0]*direction).sum());numerical=(values[1]-values[0])/(2*step)
    assert signs[0]==signs[1] and abs(analytic-numerical)<1e-8;checks['full_7D_action_directional_derivative']=dict(analytic=analytic,central_difference=numerical,absolute_error=abs(analytic-numerical))
    assert torch.any(grads[0][:2,3:]!=0);checks['rotational_and_gripper_columns_reach_gradient']=True
    zero,zi=reference_loss(delta,da,A,B,eps,torch.zeros_like(weights)); zg=torch.autograd.grad(zero,da)[0]
    assert zero==0 and torch.isfinite(zg).all() and not zg.any();checks['all_masked_batch_finite_zero_gradient']=True
    for field in ['zero_delta','nonfinite_active_B','negative_epsilon']:
        d=delta.detach().clone();b=B.detach().clone();e=eps.detach().clone()
        if field=='zero_delta':d[0]=0
        elif field=='nonfinite_active_B':b[0]=float('nan')
        else:e[0]=-1
        try:reference_loss(d,da,A,b,e,weights)
        except ValueError:checks['reject_'+field]=True
        else:raise AssertionError(field)
    low=torch.full((1,7),-.1,dtype=dtype);high=-low;base=torch.zeros_like(low);inside=base.clone();outside=base.clone();outside[0,6]=.11
    assert action_region_mask(base,inside,low,high).item() and not action_region_mask(base,outside,low,high).item()
    checks['action_support_gate_covers_all_7_axes']=True
    return dict(state='NUMERICAL_REFERENCE_CHECKS_PASSED',checks=checks,optimizer_updates=0,physics_steps=0)
