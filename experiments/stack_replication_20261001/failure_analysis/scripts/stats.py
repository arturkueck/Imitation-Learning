"""All chunk positions, conditional sample distributions, paired sampler comparisons."""
import argparse
import numpy as np
from common import *

def stats(a,seed,kind,steps):
    if a.ndim==3:a=a[:,None]
    xy,xyz,cos=fields(a);expected=PANEL['expected'][:,None];exy=np.linalg.norm(expected[...,:2],axis=-1)
    error=a-expected;var=a.var(1,ddof=1) if a.shape[1]>1 else np.zeros_like(a[:,0]);mu=a.mean(1)
    groups={'all_panel':np.ones(len(META),bool),'before_switch':OFFSETS<0,'after_switch_0_2':(OFFSETS>=0)&(OFFSETS<=2),'transport_6_10':OFFSETS>=6}
    chunkrows=[];obsrows=[]
    for group,mask in groups.items():
        for j in range(16):
            v=xy[mask,:,j];vxyz=xyz[mask,:,j];valid=exy[mask,0,j]>.05;ratio=v[valid]/exy[mask,0,j][valid,None]
            z=a[mask,:,j,2];g=a[mask,:,j,6];ex=PANEL['expected'][mask,j]
            row=dict(model=kind,training_seed=seed,ddim_steps=steps,group=group,chunk_index=j,position_1based=j+1,relative_action_time_frames=j-1,observations=int(mask.sum()),draws=a.shape[1],xyz_mean=float(vxyz.mean()),xy_mean=float(v.mean()),xy_q10=float(np.quantile(v,.1)),xy_q50=float(np.quantile(v,.5)),xy_q90=float(np.quantile(v,.9)),z_mean=float(z.mean()),z_abs_fraction_xyz_mean=float((abs(z)/np.maximum(vxyz,1e-9)).mean()),goal_cosine_mean=float(cos[mask,:,j].mean()),away_fraction=float((cos[mask,:,j]<0).mean()),gripper_mean=float(g.mean()),opening_fraction=float((g<0).mean()),sample_var_all7_mean=float(var[mask,j].mean()),sample_var_xyz_sum_mean=float(var[mask,j,:3].sum(-1).mean()),sample_var_x_mean=float(var[mask,j,0].mean()),sample_var_y_mean=float(var[mask,j,1].mean()),sample_var_z_mean=float(var[mask,j,2].mean()),sample_var_gripper_mean=float(var[mask,j,6].mean()),xy_std_across_samples_mean=float(v.std(1,ddof=1).mean()) if a.shape[1]>1 else 0.,expert_xyz_mean=float(np.linalg.norm(ex[:,:3],axis=1).mean()),expert_xy_mean=float(np.linalg.norm(ex[:,:2],axis=1).mean()),expert_z_mean=float(ex[:,2].mean()),expert_gripper_mean=float(ex[:,6].mean()),expert_mse7=float((error[mask,:,j]**2).mean()),expert_rmse_xyz=float(np.sqrt((error[mask,:,j,:3]**2).mean())),xy_over_expert_median=float(np.median(ratio)) if valid.any() else None,p_strong_targeted=float(((v>.25)&(cos[mask,:,j]>.5)).mean()),p_strong_targeted_closed=float(((v>.25)&(cos[mask,:,j]>.5)&(g>0)).mean()),mean_action_xy_mean=float(np.linalg.norm(mu[mask,j,:2],axis=-1).mean()))
            chunkrows.append(row)
    if kind=='diffusion':
        for i,meta in enumerate(META):
            for j in range(16):
                v=xy[i,:,j];c=cos[i,:,j];z=a[i,:,j,2];g=a[i,:,j,6];norm=float(np.linalg.norm(mu[i,j,:2]));mc=float(mu[i,j,:2]@GOAL[i]/max(norm*np.linalg.norm(GOAL[i]),1e-9));usable=(v>.25)&(c>.5)
                lift=(v<.12)&(z>.02)&(g>0);transport=usable&(z<-.05)&(g>0)
                obsrows.append(dict(training_seed=seed,ddim_steps=steps,panel_index=i,demo=meta['demo'],frame=meta['step'],offset=meta['offset'],chunk_index=j,draws=len(v),xy_mean=float(v.mean()),xy_q05=float(np.quantile(v,.05)),xy_q10=float(np.quantile(v,.1)),xy_q25=float(np.quantile(v,.25)),xy_q50=float(np.quantile(v,.5)),xy_q75=float(np.quantile(v,.75)),xy_q90=float(np.quantile(v,.9)),xy_q95=float(np.quantile(v,.95)),goal_cosine_mean=float(c.mean()),goal_cosine_q10=float(np.quantile(c,.1)),goal_cosine_q50=float(np.quantile(c,.5)),goal_cosine_q90=float(np.quantile(c,.9)),mean_action_xy=norm,mean_action_goal_cosine=mc,p_strong_targeted=float(usable.mean()),p_strong_targeted_closed=float((usable&(g>0)).mean()),p_expert_half_strength_targeted=float(((v>.5*exy[i,0,j])&(c>.5)).mean()),p_lift_mode=float(lift.mean()),p_transport_mode=float(transport.mean()),both_modes_15pct=bool(lift.mean()>=.15 and transport.mean()>=.15),all_samples_weak=bool(np.all(v<=.25)),mean_weak_with_usable_samples=bool(norm<=.25 and usable.any()),sample_var_x=float(var[i,j,0]),sample_var_y=float(var[i,j,1]),sample_var_z=float(var[i,j,2]),sample_var_gripper=float(var[i,j,6]),xy_sample_variance=float(v.var(ddof=1)),expert_xy=float(exy[i,0,j])))
    paired=[]
    for group,mask in groups.items():
        # Observation is the pairing unit; sample means prevent treating draws as independent demos.
        x=xy[mask].mean(1);xx=xyz[mask].mean(1);ex=exy[mask,0]
        for tail in ([2,3,4],list(range(2,16))):
            later=x[:,tail].mean(1);delta=x[:,1]-later
            paired.append(dict(model=kind,seed=seed,steps=steps,group=group,first_executed_index=1,comparison_indices=tail,first_xy_mean=float(x[:,1].mean()),later_xy_mean=float(later.mean()),paired_xy_delta_mean=float(delta.mean()),paired_xy_delta_median=float(np.median(delta)),fraction_first_weaker=float((delta<0).mean()),first_xyz_mean=float(xx[:,1].mean()),later_xyz_mean=float(xx[:,tail].mean()),expert_first_xy_mean=float(ex[:,1].mean()),expert_later_xy_mean=float(ex[:,tail].mean()),expert_adjusted_xy_delta_mean=float(((x[:,1]-ex[:,1])-(x[:,tail]-ex[:,tail]).mean(1)).mean())))
    return chunkrows,obsrows,paired

def main():
    p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');args=p.parse_args();chunks=[];obs=[];paired=[]
    for seed in (1,2,3):
        c,o,b=stats(direct_chunks(seed),seed,'direct',0);chunks+=c;paired+=b
        for steps in (5,10,20,50):
            path=OUT/f'diffusion_seed{seed}_ddim{steps}.npz'
            if not path.exists():
                if args.partial:continue
                raise FileNotFoundError(path)
            c,o,b=stats(np.load(path)['chunks'],seed,'diffusion',steps);chunks+=c;obs+=o;paired+=b
    csvwrite('chunk_position_metrics.csv',chunks);dump('chunk_position_metrics.json',chunks);csvwrite('sample_observation_metrics.csv',obs);dump('chunk_first_vs_later.json',paired)
    summary=[]
    for seed in (1,2,3):
        for steps in (5,10,20,50):
            for group in ('all_panel','before_switch','after_switch_0_2','transport_6_10'):
                selected=[r for r in obs if r['training_seed']==seed and r['ddim_steps']==steps and r['chunk_index']==1 and (group=='all_panel' or (group=='before_switch' and r['offset']<0) or (group=='after_switch_0_2' and 0<=r['offset']<=2) or (group=='transport_6_10' and r['offset']>=6))]
                if not selected:continue
                keys=['xy_mean','xy_q10','xy_q50','xy_q90','mean_action_xy','goal_cosine_mean','mean_action_goal_cosine','p_strong_targeted','p_strong_targeted_closed','p_lift_mode','p_transport_mode','both_modes_15pct','all_samples_weak','mean_weak_with_usable_samples','sample_var_x','sample_var_y','sample_var_z','sample_var_gripper','xy_sample_variance']
                summary.append(dict(seed=seed,steps=steps,group=group,n_observations=len(selected),**{k:float(np.mean([r[k] for r in selected])) for k in keys}))
    dump('sample_summary.json',summary)
    # Paired step comparison uses precisely the same first 64 noise draws.
    comparison=[]
    for seed in (1,2,3):
        base=OUT/f'diffusion_seed{seed}_ddim10.npz'
        if not base.exists():continue
        a=np.load(base)['chunks'];x,_,c=fields(a)
        for steps in (5,20,50):
            path=OUT/f'diffusion_seed{seed}_ddim{steps}.npz'
            if not path.exists():continue
            b=np.load(path)['chunks'];draws=min(a.shape[1],b.shape[1]);y,_,d=fields(b[:,:draws]);mask=OFFSETS>=6
            comparison.append(dict(seed=seed,steps=steps,draws_paired=draws,transport_xy_delta_mean=float((y[mask,:,1]-x[mask,:draws,1]).mean()),transport_cosine_delta_mean=float((d[mask,:,1]-c[mask,:draws,1]).mean()),transport_usable_probability_delta=float((((y[mask,:,1]>.25)&(d[mask,:,1]>.5)).astype(float)-((x[mask,:draws,1]>.25)&(c[mask,:draws,1]>.5)).astype(float)).mean()),mean_abs_all7_change=float(abs(b-a[:,:draws]).mean())))
    dump('ddim_paired_comparison.json',comparison)
    print(json.dumps([r for r in summary if r['group']=='transport_6_10'],indent=2),flush=True)

if __name__=='__main__':main()
