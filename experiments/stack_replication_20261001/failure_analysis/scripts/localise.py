"""Post-step states and causal-order-neutral failure annotations."""
import numpy as np
from common import *

ORDER=['grasp','lift','transport_started','near','position','lower','release','sustained_success']

def localise(t, measured, r):
    a=t[:measured];held=a[:,34]>0;act=a[:,20:27];xy=np.linalg.norm(act[:,:2],axis=1);xyz=np.linalg.norm(act[:,:3],axis=1)
    dist=np.linalg.norm(a[:,4:6]-a[:,1:3],axis=1);height=a[:,6]-a[:,3]
    # Loss = native grasp true -> false. A task-valid release is separately tagged.
    losses=np.flatnonzero(held[:-1]&~held[1:])+1
    switches=np.flatnonzero(np.sign(act[:-1,6])!=np.sign(act[1:,6]))+1
    events=[]
    for i in losses:
        valid=bool(dist[i]<.009 and abs(height[i]-.04)<.008 and a[i,35]>0)
        nextgrasp=np.flatnonzero(held[i:]);end=int(i+nextgrasp[0]) if len(nextgrasp) else measured;duration=int(end-i)
        events.append(dict(post_step_index=int(i),seconds=float((i+1)*.05),task_valid_release=valid,ungrasped_duration_frames=duration,sustained_at_least3_frames=bool(duration>=3),cube_lifted_before=bool(a[i-1,6]>.88),cube_height_m=float(a[i,6]),xy_distance_m=float(dist[i]),eef_cube_distance_before_m=float(np.linalg.norm(a[i-1,15:18]-a[i-1,4:7])),eef_cube_distance_at_event_m=float(np.linalg.norm(a[i,15:18]-a[i,4:7])),cube_height_change_next5frames_m=float(a[min(i+5,measured-1),6]-a[i,6]),gripper_before=float(act[i-1,6]),gripper_at_event=float(act[i,6]),xy_before=float(xy[i-1]),xyz_before=float(xyz[i-1]),xy_event_command=float(xy[i]),xyz_event_command=float(xyz[i]),opening_at_event=bool(act[i,6]<0),opening_in_last3_commands=bool(np.any(act[max(0,i-2):i+1,6]<0))))
    accidental=[e for e in events if not e['task_valid_release']]
    first=next((k for k in ORDER if not r[k]),None)
    # Missing phase is censored at horizon; no fabricated failure timestamp.
    tail_bad=np.flatnonzero(t[measured:,36]<=0)
    stability_failure=int(measured+tail_bad[0]) if r['stack'] and not r['sustained_success'] and len(tail_bad) else None
    anchor=stability_failure if stability_failure is not None else (accidental[0]['post_step_index'] if accidental and not r['sustained_success'] else None)
    full_act=t[:,20:27];full_xy=np.linalg.norm(full_act[:,:2],axis=1);full_xyz=np.linalg.norm(full_act[:,:3],axis=1)
    liftmask=held&(a[:,6]>.88);transportmask=held&(a[:,6]>.98)
    switches_events=[dict(post_step_index=int(i),seconds=float((i+1)*.05),before=float(act[i-1,6]),after=float(act[i,6]),held_before=bool(held[i-1]),held_after=bool(held[i])) for i in switches]
    out=dict(first_unfulfilled_task_indicator=first,first_unfulfilled_with_expert_fullheight=next((k for k in ['grasp','lift','correct_lift']+ORDER[2:] if not r[k]),None),max_cube_height_m=float(a[:,6].max()),max_held_cube_height_m=float(a[held,6].max()) if held.any() else None,max_eef_height_m=float(a[:,17].max()),min_xy_distance_m=float(dist.min()),min_xy_distance_held_lifted_m=float(dist[liftmask].min()) if liftmask.any() else None,min_xy_distance_held_above_098_m=float(dist[transportmask].min()) if transportmask.any() else None,first_loss_seconds=events[0]['seconds'] if events else None,first_accidental_loss_seconds=accidental[0]['seconds'] if accidental else None,loss_count=len(events),accidental_loss_count=len(accidental),sustained_accidental_loss_count=sum(e['sustained_at_least3_frames'] for e in accidental),gripper_switch_count=len(switches),first_gripper_switch_seconds=float((switches[0]+1)*.05) if len(switches) else None,opening_while_held_fraction=float((act[held,6]<0).mean()) if held.any() else None,error_anchor='first_non_task_valid_grasp_loss' if anchor is not None else ('success' if r['sustained_success'] else 'unfulfilled_indicator_censored_at_horizon'),xy_immediately_before_error=float(full_xy[anchor-1]) if anchor is not None else None,xyz_immediately_before_error=float(full_xyz[anchor-1]) if anchor is not None else None,xy_at_horizon=float(xy[-1]),xyz_at_horizon=float(xyz[-1]),held_lifted_xy_mean=float(xy[liftmask].mean()) if liftmask.any() else None)
    # A failed stability tail has an observed failure time, unlike a phase never reached.
    if stability_failure is not None:out['error_anchor']='first_native_success_loss_in_stability_tail'
    out.update(error_anchor_post_step_index=anchor,error_anchor_seconds=float((anchor+1)*.05) if anchor is not None else None,
        xy_immediately_before_error=float(full_xy[anchor-1]) if anchor is not None else None,
        xyz_immediately_before_error=float(full_xyz[anchor-1]) if anchor is not None else None,
        z_immediately_before_error=float(full_act[anchor-1,2]) if anchor is not None else None,
        gripper_immediately_before_error=float(full_act[anchor-1,6]) if anchor is not None else None,
        xy_error_event_command=float(full_xy[anchor]) if anchor is not None else None,
        xyz_error_event_command=float(full_xyz[anchor]) if anchor is not None else None,
        first_stability_failure_seconds=float((stability_failure+1)*.05) if stability_failure is not None else None,
        available_trace_frames=len(t),available_stability_tail_frames=len(t)-measured,
        max_cube_height_full_trace_m=float(t[:,6].max()),min_xy_distance_full_trace_m=float(np.linalg.norm(t[:,4:6]-t[:,1:3],axis=1).min()))
    out.update({f'indicator_{k}':bool(r[k]) for k in ORDER})
    out['indicator_expert_fullheight']=bool(r['correct_lift'])
    return out,dict(losses=events,gripper_switches=switches_events,phase_first_steps=r.get('first_steps'),full_lift_end=r.get('full_lift_end'),transport_start=r.get('transport_start'))

def baseline():
    rows=[];events=[];audit=[]
    for kind in ('direct','diffusion'):
        for seed in (1,2,3):
            source=rollouts(kind,seed);rs=json.loads((source/'results.json').read_text());assert len(rs)==40
            for r in rs:
                assert r['initial_state_sha256']==PROTOCOL['fixed_start_hashes'][str(r['seed'])]
                z=np.load(source/f"{r['seed']}.npz");t=z['trace'];m=int(z['measured']) if 'measured' in z else r['measured_steps'];assert m==r['measured_steps'];assert np.isfinite(t).all()
                # Recompute all historical indicators from traces rather than trust report prose.
                metrics=extra_metrics(t,m);metrics['sustained_success']=bool(metrics['stack'] and len(t[m:])==40 and np.all(t[m:,36]>0))
                assert all(metrics[k]==r[k] for k in ORDER)
                f,e=localise(t,m,metrics);base=dict(model=kind,training_seed=seed,start_seed=r['seed'],executed_actions=2,ddim_steps=10 if kind=='diffusion' else 0,measured_steps=m,sustained_success=metrics['sustained_success'])
                rows.append(dict(**base,**f));events.append(dict(**base,**e))
            audit.append(dict(model=kind,seed=seed,starts_verified=40,stable_stacks=sum(r['sustained_success'] for r in rs)))
    csvwrite('baseline_failures.csv',rows);dump('baseline_failures.json',rows);dump('baseline_events.json',events);dump('baseline_audit.json',audit)
    print(json.dumps(audit),flush=True)

if __name__=='__main__':baseline()
