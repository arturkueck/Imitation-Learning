"""Read-only audit of saved data / C rollouts; no policy inference or training."""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/stack_normalization_20261001/scripts'))
from common import KEYS, DATA, Normalizer, digest, demos, checkpoint

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def describe(x):
    x = np.asarray(x)
    return dict(n=len(x), min=float(x.min()), max=float(x.max()), mean=float(x.mean()), std=float(x.std()), median=float(np.median(x))) if len(x) else None

def main():
    import h5py
    from robomimic.config import config_factory
    from robomimic.utils import obs_utils
    from robomimic.utils.dataset import SequenceDataset
    config = json.loads((ROOT/'experiments/stack_normalization_20261001/C/diffusion/seed_1/config.json').read_text())
    obs_utils.initialize_obs_utils_with_config(config_factory('diffusion_policy', dic=config))
    ds = demos(); norm = Normalizer('C')
    names = ['approach', 'descent_to_grasp', 'grasp', 'lift', 'transport_and_alignment', 'lowering', 'release', 'retreat']
    phase_rows=[]; quat_rows=[]; channels=[]; transitions=[]
    for split in ('train', 'valid'):
        selected=[d for d in ds if d['split']==split]
        count=np.bincount(np.concatenate([d['phase'] for d in selected]), minlength=8)
        for ph,n in enumerate(count):
            phase_rows.append(dict(split=split,phase=ph,name=names[ph],frames=int(n),fraction=float(n/count.sum())))
        for k in KEYS:
            a=np.concatenate([d['obs'][k] for d in selected]); z=norm.observations({k:a})[k]
            for j in range(a.shape[-1]):
                channels.append(dict(split=split,key=k,channel=j,raw=describe(a[:,j]),normalized=describe(z[:,j]),scale=float(norm.obs[k]['scale'][0,j])))
        for d in selected:
            q=d['obs']['robot0_eef_quat']; dot=np.sum(q[1:]*q[:-1],axis=-1)
            quat_rows.append(dict(demo=d['name'],split=split,norm_max_error=float(abs(np.linalg.norm(q,axis=-1)-1).max()),adjacent_antipodal_sign_flips=int((dot<0).sum()),minimum_adjacent_dot=float(dot.min())))
            for t in np.flatnonzero(np.diff(d['phase'])!=0)+1:
                transitions.append(dict(demo=d['name'],split=split,frame=int(t),before=int(d['phase'][t-1]),after=int(d['phase'][t]),xyz_jump=float(np.linalg.norm(d['actions'][t,:3]-d['actions'][t-1,:3])),eef_delta_m=float(np.linalg.norm(d['obs']['robot0_eef_pos'][t]-d['obs']['robot0_eef_pos'][t-1]))))
    save('phase_counts.json',phase_rows); save('normalization_channels.json',channels);save('quaternion_audit.json',quat_rows)
    save('transition_events.json',transitions)
    # Random anchors AND all transition kinds in train: raw values are checked against the real loader.
    dataset=SequenceDataset(hdf5_path=str(DATA), obs_keys=KEYS, action_keys=['actions'],
        dataset_keys=['actions','rewards','dones'], action_config=config_factory('diffusion_policy',dic=config).train.action_config,
        frame_stack=2,seq_length=16,pad_frame_stack=True,pad_seq_length=True,
        hdf5_cache_mode='low_dim',hdf5_normalize_obs=False,filter_by_attribute='train',load_next_obs=False)
    indices=list(np.random.default_rng(991).choice(len(dataset),40,replace=False))
    for ph in range(1,7):
        tr=next(e for e in transitions if e['split']=='train' and e['after']==ph)
        indices.extend(dataset._demo_id_to_start_indices[tr['demo']]+tr['frame']+o for o in (-1,0,1))
    rows=[]; byname={d['name']:d for d in ds}
    for ix in sorted(set(indices)):
        item=dataset[int(ix)];name=dataset._index_to_demo_id[ix];t=int(ix-dataset._demo_id_to_start_indices[name]);d=byname[name];n=len(d['actions'])
        oi=np.clip([t-1,t],0,n-1);ai=np.clip(np.arange(t-1,t+15),0,n-1)
        oe=max(float(abs(item['obs'][k][:2]-d['obs'][k][oi]).max()) for k in KEYS)
        ae=float(abs(item['actions'][:16]-d['actions'][ai]).max());assert oe<1e-7 and ae==0
        rows.append(dict(demo=name,frame=t,observation_indices=oi.tolist(),action_indices=ai.tolist(),first_executed_action_index=t,obs_error=oe,action_error=ae))
    save('temporal_alignment.json',dict(passed=True,checks=rows,loader_rows=17,used_action_rows=16,executed_chunk_indices=[1,2],collector_state_timing='pre-action',trace_state_timing='post-action'))
    # Per-episode descriptions preserve denominators and do not claim causality.
    episodes=[];events=[]
    train=np.concatenate([d['obs']['object'] for d in ds if d['split']=='train'])
    expert_geom=np.c_[train[:,3:5]-train[:,:2],train[:,5]-train[:,2]]
    limits=np.quantile(expert_geom,[0,1],axis=0)
    for kind in ('diffusion','direct'):
        rd=ROOT/f'experiments/stack_normalization_20261001/C/{kind}/seed_1/rollouts'
        for p in sorted(rd.glob('*.npz')):
            z=np.load(p);m=int(z['measured']);a=z['trace'][:m];held=a[:,34]>0;g=a[:,26];geom=np.c_[a[:,4:6]-a[:,1:3],a[:,6]-a[:,3]]
            safe=held&(a[:,6]>.88)&((np.linalg.norm(geom[:,:2],axis=1)>.02)|(geom[:,2]>.06))
            sign=g>0;switches=np.flatnonzero(sign[1:]!=sign[:-1])+1
            losses=np.flatnonzero(held[:-1]&~held[1:])+1
            offset=np.linalg.norm(a[:,15:18]-a[:,4:7],axis=1)
            for i in losses:
                events.append(dict(model=kind,start=int(p.stem),step=int(i),opening_at_loss=bool(g[i]<0),opening_previous3=bool((g[max(0,i-2):i+1]<0).any()),xy_distance_m=float(np.linalg.norm(geom[i,:2])),relative_height_m=float(geom[i,2]),eef_B_distance_m=float(offset[i]),valid_release_geometry=bool(np.linalg.norm(geom[i,:2])<.009 and abs(geom[i,2]-.04)<.008 and a[i,35]>0)))
            episodes.append(dict(model=kind,start=int(p.stem),measured=m,gripper_sign_switches=int(len(switches)),grasp_losses=int(len(losses)),clearly_before_release_held_frames=int(safe.sum()),opening_frames_in_that_region=int((safe&(g<0)).sum()),opening_fraction_in_that_region=float((g[safe]<0).mean()) if safe.any() else None,max_B_height_m=float(a[:,6].max()),max_held_EEF_B_offset_m=float(offset[held].max()) if held.any() else None,geometry_outside_expert_global_minmax_frames=int(((geom<limits[0])|(geom>limits[1])).any(axis=1).sum()),raw_vs_executed_max_error=float(abs(a[:,20:27]-a[:,27:34]).max())))
    # Geometric coverage, compared with held-out Expert frames rather than arbitrary raw thresholds.
    from scipy.spatial import cKDTree
    def features(ob):
        o=np.asarray(ob['object']);e=np.asarray(ob['robot0_eef_pos']);g=np.asarray(ob['robot0_gripper_qpos'])
        return np.c_[o[:,3:]-o[:,:3],e-o[:,3:],g]
    ft=np.concatenate([features(d['obs']) for d in ds if d['split']=='train'])
    fv=np.concatenate([features(d['obs']) for d in ds if d['split']=='valid'])
    offset=ft.mean(0);scale=ft.std(0)+1e-3;tree=cKDTree((ft-offset)/scale)
    vd=tree.query((fv-offset)/scale)[0];threshold=float(np.quantile(vd,.95));coverage=[]
    for kind in ('diffusion','direct'):
        rd=ROOT/f'experiments/stack_normalization_20261001/C/{kind}/seed_1/rollouts'
        for p in sorted(rd.glob('*.npz')):
            z=np.load(p);m=int(z['measured']);ob={k:z[k][:m,-1] for k in KEYS};a=z['trace'][:m]
            distance=tree.query((features(ob)-offset)/scale)[0]
            held_lift=(a[:,34]>0)&(a[:,6]>.88)
            losses=[r for r in events if r['model']==kind and r['start']==int(p.stem) and not r['valid_release_geometry']]
            coverage.append(dict(model=kind,start=int(p.stem),all_frame_distances=describe(distance),held_lift_distances=describe(distance[held_lift]),held_lift_frames=int(held_lift.sum()),held_lift_frames_above_valid_expert_q95=int((held_lift&(distance>threshold)).sum()),pre_loss_distances=[dict(step=r['step'],distance=float(distance[r['step']]),pre_action_time=True) for r in losses]))
    save('geometric_coverage.json',dict(features=['B_minus_A_xyz','EEF_minus_B_xyz','finger_qpos_2'],train_fit_mean=offset.tolist(),train_fit_scale=scale.tolist(),valid_expert_nearest_train=describe(vd),valid_expert_q95=threshold,episodes=coverage,caveats=['Nearest single-frame geometry is a diagnostic proximity score, not a probability or causal OOD proof.','Expert and policy frames differ in phase frequencies.','No object orientation or contact feature in policy observation; orientation/recovery claims require the separate simulator-state analysis.','A policy can succeed from states distant from the Expert, as Direct demonstrates.']))
    # Saved simulator quaternions permit a separate cube-tilt audit; they are not policy inputs.
    from scipy.spatial.transform import Rotation
    def tilt(qwxyz):
        q=np.asarray(qwxyz);assert abs(np.linalg.norm(q,axis=1)-1).max()<1e-6
        rz=Rotation.from_quat(q[:,[1,2,3,0]]).as_matrix()[:,2,:]
        return np.degrees(np.arccos(np.clip(np.max(abs(rz),axis=1),0,1)))
    expert_tilt=[];layout_error=0.
    with h5py.File(DATA,'r') as f:
        for d in ds:
            if d['split']!='train':continue
            state=f['data'][d['name']]['states'][:];assert state.shape[1]==45
            error=float(abs(state[:,17:20]-d['obs']['object'][:,3:]).max());layout_error=max(layout_error,error)
            assert error<.003,'Unexpected simulator-state layout: B position does not match'
            expert_tilt.extend(tilt(state[:,20:24])[np.isin(d['phase'],[3,4,5])])
    orientations=[]
    for kind in ('diffusion','direct'):
        rd=ROOT/f'experiments/stack_normalization_20261001/C/{kind}/seed_1/rollouts'
        for p in sorted(rd.glob('*.npz')):
            z=np.load(p);a=z['trace'][:int(z['measured'])];mask=(a[:,34]>0)&(a[:,6]>.88)
            orientations.append(dict(model=kind,start=int(p.stem),held_lift_nearest_cube_face_tilt_degrees=describe(tilt(a[:,11:15])[mask])))
    save('object_orientation_audit.json',dict(expert_train_lift_transport_lowering_tilt_degrees=describe(expert_tilt),simulator_layout_B_position_max_error_m=layout_error,episodes=orientations,definition='angle of the closest cube face normal to world vertical; cube 90-degree symmetries respected',object_orientation_is_policy_input=False,caveat='Descriptive orientation audit; not an isolated causal test or evidence that new observations/recovery demos are needed.'))
    save('C_gripper_episodes.json',episodes);save('C_grasp_loss_events.json',events)
    with (OUT/'C_gripper_episodes.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(episodes[0]));w.writeheader();w.writerows(episodes)
    # All reports read before implementation; hash source evidence for later interpretation.
    reports=list((ROOT/'experiments').rglob('*.md'))
    reports=[p for p in reports if 'source_snapshot' not in p.parts and OUT not in p.parents]
    files=reports+[DATA,checkpoint('C','diffusion',1),checkpoint('C','direct',1),ROOT/'experiments/stack_normalization_20261001/normalization_stats.json']
    save('input_hashes.json',{str(p.relative_to(ROOT)):digest(p) for p in files})
    # A compact temporal visualization of actual Expert targets, without inference.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for d in [d for d in ds if d['split']=='valid'][:3]:
        fig,axs=plt.subplots(3,1,figsize=(11,7),sharex=True)
        t=np.arange(len(d['actions']))*.05
        axs[0].plot(t,d['obs']['robot0_eef_pos'][:,2],label='EEF z');axs[0].plot(t,d['obs']['object'][:,5],label='B z');axs[0].set_ylabel('m');axs[0].legend()
        axs[1].plot(t,np.linalg.norm(d['actions'][:,:2],axis=1),label='XY norm');axs[1].plot(t,d['actions'][:,2],label='Z');axs[1].legend();axs[1].set_ylabel('controller units')
        axs[2].step(t,d['actions'][:,6],where='post',label='gripper');axs[2].step(t,d['phase']/6,where='post',label='phase / 6');axs[2].legend();axs[2].set_xlabel('pre-action time (s)')
        for ax in axs:
            for i in np.flatnonzero(np.diff(d['phase'])!=0)+1:ax.axvline(t[i],alpha=.3,color='black')
        fig.suptitle(f"Expert temporal alignment: {d['name']}; obs[t] -> action[t]");fig.tight_layout();fig.savefig(OUT/f"expert_temporal_alignment_{d['name']}.png");plt.close(fig)
    summary={kind:dict(episodes=40,median_gripper_switches=float(np.median([r['gripper_sign_switches'] for r in episodes if r['model']==kind])),loss_events=sum(r['grasp_losses'] for r in episodes if r['model']==kind),premature_open_frames=sum(r['opening_frames_in_that_region'] for r in episodes if r['model']==kind),held_pre_release_frames=sum(r['clearly_before_release_held_frames'] for r in episodes if r['model']==kind)) for kind in ('diffusion','direct')}
    summary['quaternion_sign_flips']=sum(r['adjacent_antipodal_sign_flips'] for r in quat_rows)
    summary['temporal_checks']=len(rows)
    for kind in ('diffusion','direct'):
        ev=[r for r in events if r['model']==kind];bad=[r for r in ev if not r['valid_release_geometry']]
        summary[kind].update(valid_geometry_loss_events=len(ev)-len(bad),non_release_geometry_loss_events=len(bad),non_release_losses_with_opening=sum(r['opening_at_loss'] for r in bad),losses_further_than_3cm=sum(r['xy_distance_m']>.03 for r in bad))
        cr=[r for r in coverage if r['model']==kind]
        summary[kind]['held_lift_geometry_frames_above_expert_valid_q95']=sum(r['held_lift_frames_above_valid_expert_q95'] for r in cr)
        summary[kind]['held_lift_geometry_frames']=sum(r['held_lift_frames'] for r in cr)
    summary['caveats']=['Global min/max is a weak OOD screen, not a density estimate.', 'Late phase success cannot be inferred from offline or event correlations.', 'No new rollouts or training in this audit.']
    save('audit_summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
