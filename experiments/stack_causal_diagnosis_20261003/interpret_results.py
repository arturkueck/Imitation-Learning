"""Post-hoc interpretation of saved results only; no policy or simulator execution."""
import hashlib,json
from pathlib import Path
import h5py,numpy as np

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
protocol=read(OUT/'protocol.json');rows=read(OUT/'experiment_1_phases/results.json');baseline=read(OUT/'experiment_0_baseline/results.json')
assert len(rows)==90 and len(baseline)==40
assert read(OUT/'complete.json')['state']=='COMPLETED'
assert read(OUT/'experiment_0_baseline/complete.json')['episodes']==40
assert read(OUT/'experiment_1_phases/complete.json')['episodes']==90
assert sum(r['sustained_success'] for r in rows if r['model']=='expert')==30

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

# Verify sealed evaluation outputs before interpreting them; new analysis files are separate.
frozen=read(OUT/'output_hashes.json')
assert all(sha(OUT/name)==h for name,h in frozen.items()),'An evaluation output differs from its completion hash'
assert sha(Path(protocol['checkpoint']))==protocol['checkpoint_sha256']
assert sha(ROOT/'experiments/stack_normalization_20261001/C/direct/seed_1/model_final.pth')==protocol['direct_checkpoint_sha256']
assert sha(Path(protocol['dataset']))==protocol['dataset_sha256']

groups={};details=[];actions_checked=0;chunks_checked=0
with h5py.File(protocol['dataset'],'r') as f:
    for r in rows:
        z=np.load(OUT/'experiment_1_phases'/f"{r['demo']}_{r['phase']}_{r['model']}.npz")
        group=f['data'][r['demo']];k=r['expert_frame'];initial=z['initial_state']
        assert np.array_equal(initial,group['states'][k])
        h=hashlib.sha256(initial.tobytes()).hexdigest()
        assert h==r['saved_state_sha256']==r['replayed_state_sha256']
        groups.setdefault((r['demo'],r['phase']),[]).append(h)
        for key in ('object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos'):
            assert np.array_equal(z[key][0],group['obs'][key][[max(0,k-1),k]])
        t=z['trace'];m=int(z['measured']);a=t[:m];tail=t[m:]
        assert m==r['measured_steps'] and len(tail)==40
        assert np.isfinite(t).all() and abs(t[:,20:27]).max()<=1.00001
        assert np.array_equal(t[:,20:27],t[:,27:34]);actions_checked+=len(t)
        stable=bool(a[-1,36]>0 and (tail[:,36]>0).all() and not tail[:,34].any() and (tail[:,35]>0).all())
        assert stable==r['sustained_success']
        if r['model']=='diffusion':
            chunks=z['chunks'];starts=z['chunk_start_steps'];assert chunks.shape[1:]==(16,7)
            for step in range(len(t)):
                ci=int(np.searchsorted(starts,step,side='right')-1);slot=1+step-int(starts[ci]);assert slot in (1,2)
                assert np.array_equal(t[step,20:27],chunks[ci,slot])
            chunks_checked+=len(chunks)
        delta=a[:,4:7]-a[:,1:4];xy=np.linalg.norm(delta[:,:2],axis=1);held=a[:,34]>0
        release=(xy<.009)&(abs(delta[:,2]-.04)<.008)&~held&(a[:,35]>0)
        rid=np.flatnonzero(release);first=int(rid[0]) if len(rid) else None
        # Include initial grasp -> first action loss, omitted by the old first-loss helper.
        prev=np.r_[True,held[:-1]];losses=np.flatnonzero(prev&~held)
        opening_losses=[]
        for i in losses:
            opening_losses.append(dict(step=int(i),time_s=float((i+1)*.05),opening_command=bool(a[i,26]<0),xy_mm=float(xy[i]*1000),height_difference_mm=float(delta[i,2]*1000),valid_release_geometry=bool(release[i])))
        initial_xy=r['initial_geometry']['xy_m']*1000
        details.append(dict(model=r['model'],demo=r['demo'],phase=r['phase'],initial_xy_mm=initial_xy,initial_lower=r['initial_geometry']['lower'],initial_position=r['initial_geometry']['position'],native_stack=bool(a[:,36].any()),stable_stack=stable,measured_steps=m,gripper_switches=r['gripper_sign_switches'],first_release_step=first,first_release_seconds=float((first+1)*.05) if first is not None else None,first_release_xy_mm=float(xy[first]*1000) if first is not None else None,first_release_gripper_command=float(a[first,26]) if first is not None else None,grasp_losses=opening_losses,minimum_held_xy_mm=float(xy[held].min()*1000) if held.any() else None,xy_end_main_mm=float(xy[-1]*1000),xy_end_tail_mm=float(np.linalg.norm(t[-1,4:6]-t[-1,1:3])*1000),max_held_xy_mm=float(xy[held].max()*1000) if held.any() else None,tail_grasp_frames=int(tail[:,34].sum()),tail_contact_frames=int(tail[:,35].sum()),tail_success_frames=int(tail[:,36].sum()),first_tail_failure_after_success_step=next((int(m+i) for i in range(len(tail)) if tail[i,36]==0),None) if a[-1,36]>0 else None,max_rotation_command_norm=r['max_rotation_command_norm'],first_xy_over_expert=r.get('first_action_xy_over_expert'),full_rollout_goal_cosine=r['pre_action_goal_cosine_mean']))
        failure=details[-1]['first_tail_failure_after_success_step']
        if failure is not None:
            state=z['states'][failure];tr=t[failure]
            # Cached body poses can lag integrated qpos by one MuJoCo microstep.
            assert len(state)==45 and np.allclose(state[10:13],tr[1:4],atol=.003) and np.allclose(state[17:20],tr[4:7],atol=.003)
            details[-1]['first_tail_failure_constraints']=dict(xy_mm=float(np.linalg.norm(tr[4:6]-tr[1:3])*1000),relative_height_mm=float((tr[6]-tr[3])*1000),base_z_mm=float(tr[3]*1000),cube_A_linear_velocity_m_s=float(np.linalg.norm(state[33:36])),cube_A_angular_velocity_rad_s=float(np.linalg.norm(state[36:39])),cube_B_linear_velocity_m_s=float(np.linalg.norm(state[39:42])),cube_B_angular_velocity_rad_s=float(np.linalg.norm(state[42:45])),B_grasp=bool(tr[34]),AB_contact=bool(tr[35]),caveat='Native criterion also checks grasp of A; that flag is not stored in trace. A violated velocity/geometry constraint is evidence, not a full causal attribution to the last action.')
assert len(groups)==30 and all(len(h)==3 and len(set(h))==1 for h in groups.values())
original=read(ROOT/'experiments/stack_normalization_20261001/C/diffusion/seed_1/rollouts/results.json')
baseline_counts={k:sum(bool(r[k]) for r in baseline) for k in ('grasp','lift','transport_started','position','lower','release','sustained_success')}
original_counts={k:sum(bool(r[k]) for r in original) for k in baseline_counts}
phase_summary=[]
for phase in protocol['phase_anchors'][0]['anchors']:
    for model in ('expert','direct','diffusion'):
        s=[r for r in details if r['phase']==phase and r['model']==model]
        phase_summary.append(dict(phase=phase,model=model,n=len(s),native_stacks=sum(r['native_stack'] for r in s),stable_stacks=sum(r['stable_stack'] for r in s),already_positioned_at_start=sum(r['initial_position'] for r in s),already_lowered_at_start=sum(r['initial_lower'] for r in s),median_gripper_switches=float(np.median([r['gripper_switches'] for r in s])),median_first_xy_over_expert=float(np.median([r['first_xy_over_expert'] for r in s if r['first_xy_over_expert'] is not None])) if any(r['first_xy_over_expert'] is not None for r in s) else None))
verification=dict(passed=True,output_hashes_verified=len(frozen),checkpoints_and_dataset_hashes_verified=True,expert_controls_success=30,paired_anchor_groups=30,exact_saved_initial_states=90,exact_saved_initial_histories=90,phase_actions_checked=actions_checked,diffusion_chunks_checked=chunks_checked,stability_tails_checked=90,training_or_rollouts_executed=False)
summary=dict(verification=verification,baseline_counts=baseline_counts,original_baseline_counts=original_counts,new_baseline_success_ids=[r['seed'] for r in baseline if r['sustained_success']],original_baseline_success_ids=[r['seed'] for r in original if r['sustained_success']],phase_summary=phase_summary,episodes=details)
(OUT/'interpretation_details.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
(OUT/'interpretation_verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='episodes'},indent=2))
print('LATE DIFFUSION CASES')
print(json.dumps([r for r in details if r['model']=='diffusion' and r['phase']=='F_before_release'],indent=2))
