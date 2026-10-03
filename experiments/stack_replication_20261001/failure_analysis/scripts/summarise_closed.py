"""Aggregate all starts, retaining training seeds as independent replicates."""
from collections import Counter
import numpy as np
from common import *
from localise import localise,ORDER

def main():
    summary=[];flat=[];details=[];parity=[];temporal=[]
    paths=sorted((OUT/'rollouts').glob('*/results.json'))
    for path in paths:
        rs=json.loads(path.read_text())
        if len(rs)!=40:continue
        first=rs[0];k=first['model'];s=first['training_seed'];h=first['executed_actions'];steps=first['ddim_steps'];group=first.get('comparison_group','replanning')
        for r in rs:
            assert r['initial_state_sha256']==PROTOCOL['fixed_start_hashes'][str(r['start_seed'])]
            z=np.load(path.parent/f"{r['start_seed']}.npz");t=z['trace'];m=r['measured_steps'];assert np.isfinite(t).all();metrics=extra_metrics(t,m);metrics['sustained_success']=bool(metrics['stack'] and len(t[m:])==40 and np.all(t[m:,36]>0));assert metrics['sustained_success']==r['sustained_success']
            if metrics['sustained_success']:assert np.all(t[m:,35]>0) and np.all(t[m:,34]==0), (path,r['start_seed'],'stable stack requires contact and released object')
            f,e=localise(t,m,metrics);base=dict(model=k,training_seed=s,start_seed=r['start_seed'],executed_actions=h,ddim_steps=steps,comparison_group=group,measured_steps=m,sustained_success=r['sustained_success']);flat.append(dict(**base,**f));details.append(dict(**base,**e))
            if h==2 and steps in (0,10):parity.append({key:r.get(key) for key in ['model','training_seed','start_seed','comparison_group','shared_replanning_baseline','historical_trace_bitwise_equal','baseline_max_abs_error','baseline_action_max_abs_error','first_action_max_abs_error']})
            a=t[:m];act=a[:,20:27];xy=np.linalg.norm(act[:,:2],axis=1);held=a[:,34]>0;liftmask=held&(a[:,6]>.88);cos=(act[:,:2]*(a[:,1:3]-a[:,4:6])).sum(1)/np.maximum(xy*np.linalg.norm(a[:,1:3]-a[:,4:6],axis=1),1e-9)
            eligible=liftmask[1:]&liftmask[:-1]&(xy[1:]>.05)&(xy[:-1]>.05);boundary=(np.arange(1,m)%h==0);reversal=(act[1:,:2]*act[:-1,:2]).sum(1)<0;gflip=np.sign(act[1:,6])!=np.sign(act[:-1,6]);online=[]
            for label,mask in [('replan_boundary',eligible&boundary),('within_chunk',eligible&~boundary)]:
                online.append(dict(location=label,n_pairs=int(mask.sum()),xy_reversals=int((reversal&mask).sum()),gripper_sign_switches=int((gflip&mask).sum())))
            temporal.append(dict(**base,held_lifted_frames=int(liftmask.sum()),strong_targeted_held_lifted_frames=int((liftmask&(xy>.25)&(cos>.5)).sum()),held_lifted_open_frames=int((liftmask&(act[:,6]<0)).sum()),pairs=online))
        stages={key:sum(r[key] for r in rs) for key in ORDER}
        def median(key):
            v=[r[key] for r in rs if r[key] is not None];return float(np.median(v)) if v else None
        lost=[r for r in rs if r['accidental_loss_count']>0]
        summary.append(dict(model=k,training_seed=s,executed_actions=h,ddim_steps=steps,comparison_group=group,n_starts=40,stable_stacks=stages['sustained_success'],stage_counts=stages,first_missing_counts=dict(Counter(r['first_unfulfilled_task_indicator'] or 'success' for r in rs)),max_height_m_median=median('max_cube_height_m'),held_lifted_min_distance_m_median=median('min_xy_distance_held_lifted_m'),n_starts_held_lifted_distance_available=sum(r['min_xy_distance_held_lifted_m'] is not None for r in rs),starts_with_accidental_loss=len(lost),gripper_switch_count_median=median('gripper_switch_count'),opening_while_held_fraction_median=median('opening_while_held_fraction'),held_lifted_xy_mean_median=median('held_lifted_xy_mean'),stable_start_seeds=[r['start_seed'] for r in rs if r['sustained_success']]))
    dump('closed_loop_summary.json',summary);csvwrite('closed_loop_failures.csv',flat);dump('closed_loop_failures.json',flat);dump('closed_loop_events.json',details);dump('historical_replay_comparison.json',parity);dump('closed_loop_action_coherence.json',temporal)
    # Paired changes per start; no invalid binomial confidence interval pooled over training seeds.
    changes=[]
    for kind in ('direct','diffusion'):
        for seed in (1,2,3):
            for group in ('replanning','ddim'):
                base=[r for r in flat if r['model']==kind and r['training_seed']==seed and r['executed_actions']==2 and r['ddim_steps'] in (0,10) and r['comparison_group']==group]
                if len(base)!=40:continue
                b={r['start_seed']:r for r in base}
                arms={(r['executed_actions'],r['ddim_steps']) for r in flat if r['model']==kind and r['training_seed']==seed and r['comparison_group']==group}
                for h,steps in sorted(arms):
                    if h==2 and steps in (0,10):continue
                    rs=[r for r in flat if r['model']==kind and r['training_seed']==seed and r['executed_actions']==h and r['ddim_steps']==steps and r['comparison_group']==group]
                    phases={key:dict(newly_reached_start_seeds=[r['start_seed'] for r in rs if r['indicator_'+key] and not b[r['start_seed']]['indicator_'+key]],no_longer_reached_start_seeds=[r['start_seed'] for r in rs if not r['indicator_'+key] and b[r['start_seed']]['indicator_'+key]]) for key in ORDER}
                    changes.append(dict(model=kind,training_seed=seed,executed_actions=h,ddim_steps=steps,comparison_group=group,rescued_start_seeds=[r['start_seed'] for r in rs if r['sustained_success'] and not b[r['start_seed']]['sustained_success']],lost_start_seeds=[r['start_seed'] for r in rs if not r['sustained_success'] and b[r['start_seed']]['sustained_success']],max_height_paired_mean_delta_m=float(np.mean([r['max_cube_height_m']-b[r['start_seed']]['max_cube_height_m'] for r in rs])),phase_paired_changes=phases))
    dump('closed_loop_paired_changes.json',changes)
    print(json.dumps([{k:r[k] for k in ['model','training_seed','executed_actions','ddim_steps','stable_stacks']} for r in summary],indent=2),flush=True)

if __name__=='__main__':main()
