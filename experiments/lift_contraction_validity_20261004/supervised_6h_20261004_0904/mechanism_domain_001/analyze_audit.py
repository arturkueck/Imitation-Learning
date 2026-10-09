"""Independent numerical/provenance/domain audit; no simulator reruns or fits."""
import hashlib,json,math,time
from pathlib import Path
import h5py,numpy as np,psutil
O=Path(__file__).resolve().parent;S=O.parent;R=S.parents[2];P=S/'attempts/attempt_002'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def diff(a,b):
    if isinstance(a,dict):
        assert set(a)==set(b)
        return max([diff(a[k],b[k]) for k in a]+[0.])
    if a is None or isinstance(a,(str,bool)):return 0. if a==b else float('inf')
    return float(np.max(np.abs(np.asarray(a)-np.asarray(b)),initial=0))
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
def vecscore(y,p,selection):
    y,p=np.asarray(y),np.asarray(p);n=float(np.linalg.norm(y));err=float(np.linalg.norm(y-p))
    deg=n<selection['degenerate_threshold_m'];cos=float(y@p/max(n*float(np.linalg.norm(p)),1e-15))
    rel=err/n if n>=selection['degenerate_threshold_m'] else None
    return dict(observed_m=y.tolist(),predicted_m=p.tolist(),observed_norm_m=n,error_m=err,
                relative_error=rel,cosine=cos,degenerate=deg,legacy_degenerate=n<selection['legacy_degenerate_threshold_m'],
                passed=bool(not deg and cos>=.8 and rel<=.5))
def summary(rows):
    good=[x for x in rows if not x['degenerate']]
    return dict(scored=len(rows),nondegenerate=len(good),degenerate=len(rows)-len(good),
                legacy_degenerate=sum(x['legacy_degenerate'] for x in rows),passed=sum(x['passed'] for x in rows),
                median_error_m=float(np.median([x['error_m'] for x in rows])) if rows else None,
                median_relative_error_nondegenerate=float(np.median([x['relative_error'] for x in good])) if good else None)
def central(row,kind,axis):
    m,p=[row['branches'][f'{kind}_{axis}_{sign}'] for sign in ['minus','plus']]
    return (np.array(p['before_measure']['eef_m'])-m['before_measure']['eef_m'],
            np.array(p['action'])-m['action'],np.array(p['next_eef_m'])-m['next_eef_m'])

start=time.perf_counter();r=read(O/'result.json');sel=read(O/'selection.json');cal=read(O/'calibration.json')
sup=read(O/'supervisor_result.json');launch=read(O/'launch.json')
assert r['state'] in ['COMPLETE_DATA','DOMAIN_GATE_FAILED'] and sup['returncode']==0 and not sup.get('timed_out',False)
assert sup['worker_job_closed'] and not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
assert launch['deadline_unix']<=read(S/'session.json')['deadline_unix']
for name,digest in read(O/'source_hashes.json').items():
    source=S/'build_domain_worker.py' if name=='worker_builder_sha256' else O/name
    assert sha(source)==digest,name
for name,digest in cal['calibration_sources'].items():assert sha(Path(name))==digest
assert sha(P/'B0/model_final.pth')==sel['checkpoint_sha256']
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256']
assert r['fit_updates']==r['policy_training_updates']==0
manifest=read(P/'dataset_manifest.json');rng=np.random.default_rng(sel['seed'])
assert rng.choice(sorted(set(manifest['train_demos'])-set(sel['excluded_prior_demos'])),4,replace=False).tolist()==sel['selected_demos']
assert not set(sel['selected_demos'])&set(cal['fit_demos'])
assert len(r['rows'])==12 and sum(len(x['branches']) for x in r['rows'])==336
HISTORY=['goal_pos','goal_ori','initial_joint','initial_ref_pos','initial_ref_ori_mat','origin_pos','origin_ori',
         '_goal_update_mode','kp','kd','action_scale','action_input_transform','action_output_transform']
audits=[];eligible=[]
with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
    for row in r['rows']:
        assert row['split']=='heldout' and row['demo'] in sel['selected_demos']
        assert row['t']==int(row['fraction']*(len(f['data/'+row['demo']+'/actions'])-1))
        branches=row['branches'];ref=branches['reference'];checks=[]
        assert len(branches)==28
        anchor_error=max(diff(ref['anchor'],b['anchor']) for b in branches.values())
        repeat_error=float(np.linalg.norm(np.array(ref['next_eef_m'])-branches['repeat']['next_eef_m']))
        paired=[diff(ref['before'],b['before']) for name,b in branches.items() if name.startswith('B_')]
        paired += [diff(branches[f'A_{axis}_{sign}']['before'],branches[f'Pfull_{axis}_{sign}']['before']) for axis in range(3) for sign in ['minus','plus']]
        for name,b in branches.items():
            a,z=b['anchor'],b['before'];obs=b['observation']
            aux=max([diff(a['sim'][k],z['sim'][k]) for k in a['sim'] if k not in ['qpos','qvel']]+[0.])
            aux=max(aux,diff(a['gripper_memory'],z['gripper_memory']),diff(a['controllers']['right_gripper'],z['controllers']['right_gripper']),
                    float(np.linalg.norm(np.array(obs['robot0_eef_pos'])-b['before_measure']['eef_m'])),
                    float(np.linalg.norm(np.array(obs['object'])[-3:]-(np.array(obs['object'])[:3]-obs['robot0_eef_pos']))))
            contacted=bool(b['initial_robot_contacts'] or b['step_robot_contacts'] or b['final_robot_contacts'])
            physical=True;physical_metrics={}
            if b['intervention'] is not None:
                _,axis,sign=name.split('_');axis=int(axis);requested=np.zeros(3);requested[axis]=(-1 if sign=='minus' else 1)*sel['physical_delta_m']
                am,zm=b['anchor_measure'],b['before_measure']
                error=float(np.linalg.norm(np.array(zm['eef_m'])-am['eef_m']-requested))
                rotation=np.array(zm['orientation']).reshape(3,3);initial=np.array(am['orientation']).reshape(3,3)
                angle=float(np.arccos(np.clip((np.trace(initial.T@rotation)-1)/2,-1,1)))
                lv=float(np.linalg.norm(np.array(zm['linear_velocity'])-am['linear_velocity']));av=float(np.linalg.norm(np.array(zm['angular_velocity'])-am['angular_velocity']))
                q=np.asarray(z['controllers']['right']['qpos_index'],dtype=int);v=np.asarray(z['controllers']['right']['qvel_index'],dtype=int)
                uq=np.setdiff1d(np.arange(len(a['sim']['qpos'])),q);uv=np.setdiff1d(np.arange(len(a['sim']['qvel'])),v)
                qerr=float(np.max(np.abs(np.array(z['sim']['qpos'])[uq]-np.array(a['sim']['qpos'])[uq]),initial=0))
                verr=float(np.max(np.abs(np.array(z['sim']['qvel'])[uv]-np.array(a['sim']['qvel'])[uv]),initial=0))
                hist=max([diff(a['controllers']['right'][k],z['controllers']['right'][k]) for k in HISTORY if k in a['controllers']['right']]+[0.])
                objerr=diff(ref['observation']['object'][:7],obs['object'][:7])
                physical=bool(error<=sel['position_tolerance_m'] and angle<=1e-4 and lv<=1e-5 and av<=1e-4 and qerr<=1e-9 and verr<=1e-9 and hist<=1e-9 and objerr<=1e-9 and b['intervention']['joint_limits_passed'])
                physical_metrics=dict(position_error_m=error,orientation_error_rad=angle,linear_velocity_error=lv,angular_velocity_error=av,
                                      untouched_qpos_error=qerr,untouched_qvel_error=verr,history_error=hist,object_pose_error=objerr,
                                      joint_limit_source='Frozen worker assertion; model joint ranges not reconstructed by this raw-state audit.')
            checks.append(dict(branch=name,aux_error=aux,aux_passed=aux<=1e-9,physical_passed=physical,contacted=contacted,physical_metrics=physical_metrics))
        technical=bool(anchor_error<=1e-9 and repeat_error<=1e-6 and max(paired)<=1e-9 and all(x['aux_passed'] and x['physical_passed'] for x in checks))
        free=not any(x['contacted'] for x in checks);passed=technical and free
        assert technical==row['gates']['technical_passed'] and free==row['gates']['contact_free'] and passed==row['gates']['passed']
        audits.append(dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],technical_passed=technical,contact_free=free,eligible=passed,
                           anchor_start_error=anchor_error,repeat_error_m=repeat_error,same_probe_start_error=max(paired),checks=checks,
                           reference_initial_contacts=ref['initial_robot_contacts'],reference_step_contacts=ref['step_robot_contacts'],reference_final_contacts=ref['final_robot_contacts']))
        if passed:eligible.append(row)
A,B3,B7,K=[np.asarray(cal[k]) for k in ['A','B3','B7','K_OLS']]
strata={}
for fraction in sel['anchor_fractions']:
    rows=[x for x in r['rows'] if x['fraction']==fraction];valid=[x for x in eligible if x['fraction']==fraction]
    audits_here=[x for x in audits if x['fraction']==fraction]
    b_scores={i:[] for i in range(7)};a_scores=[];a_identity=[];xyz={m:[] for m in ['B3','OLS']};probes=[]
    for row in valid:
        ref=row['branches']['reference']
        for axis in range(7):
            _,da,dy=central(row,'B',axis);score=vecscore(dy,da@B7,sel);score.update(demo=row['demo'],t=row['t'],axis=axis,action_difference_7d=da.tolist());b_scores[axis].append(score)
            if axis<3:
                xyz['B3'].append(vecscore(dy,da[:3]@B3,sel));xyz['OLS'].append(vecscore(dy,da[:3]@K,sel))
        for axis in range(3):
            dx,_,dy=central(row,'A',axis);a_scores.append(vecscore(dy,dx@A,sel));a_identity.append(vecscore(dy,dx,sel))
            for sign in ['minus','plus']:
                b=row['branches'][f'Pfull_{axis}_{sign}'];delta=np.asarray(b['before_measure']['eef_m'])-ref['before_measure']['eef_m'];da=np.asarray(b['action'])-ref['action']
                observed=np.asarray(b['next_eef_m'])-ref['next_eef_m'];ratio=float(np.linalg.norm(observed)/np.linalg.norm(delta))
                predictions={'I_OLS':delta+da[:3]@K,'A_B3':delta@A+da[:3]@B3,'A_B7':delta@A+da@B7}
                models={}
                for name,p in predictions.items():
                    score=vecscore(observed,p,sel);pr=float(np.linalg.norm(p)/np.linalg.norm(delta))
                    models[name]={**score,'predicted_ratio':pr,'absolute_ratio_error':abs(ratio-pr),
                                  'false_pass':pr<sel['ratio_threshold'] and not ratio<sel['ratio_threshold'],
                                  'false_penalty':not pr<sel['ratio_threshold'] and ratio<sel['ratio_threshold']}
                probes.append(dict(demo=row['demo'],t=row['t'],axis=axis,sign=sign,actual_delta_m=delta.tolist(),action_difference_7d=da.tolist(),
                                   observed_ratio=ratio,models=models))
    policy={}
    for model in ['I_OLS','A_B3','A_B7']:
        policy[model]=dict(conditional_cases=len(probes),planned_cases=6*len(rows),
                           median_absolute_ratio_error=float(np.median([x['models'][model]['absolute_ratio_error'] for x in probes])) if probes else None,
                           observed_below_threshold=sum(x['observed_ratio']<sel['ratio_threshold'] for x in probes),
                           predicted_below_threshold=sum(x['models'][model]['predicted_ratio']<sel['ratio_threshold'] for x in probes),
                           false_pass=sum(x['models'][model]['false_pass'] for x in probes),false_penalty=sum(x['models'][model]['false_penalty'] for x in probes))
    flat=[x for rows_axis in b_scores.values() for x in rows_axis]
    strata[str(fraction)]=dict(planned_anchors=len(rows),eligible_anchors=len(valid),
                               technical_failed=sum(not x['technical_passed'] for x in audits_here),contact_failed=sum(not x['contact_free'] for x in audits_here),
                               planned_B7_responses=7*len(rows),unscored_B7_due_domain=7*(len(rows)-len(valid)),
                               B7={**summary(flat),'by_component':{i:{**summary(rows_axis),'raw':rows_axis} for i,rows_axis in b_scores.items()}},
                               A_calibrated=summary(a_scores),A_identity=summary(a_identity),xyz={k:summary(v) for k,v in xyz.items()},
                               policy=policy,conditional_policy_raw=probes)
assert len(eligible)==sum(x['eligible_anchors'] for x in strata.values())
assert (r['state']=='COMPLETE_DATA')==(len(eligible)==12)
result=dict(state='AUDIT_VERIFIED_DOMAIN_COMPLETE' if len(eligible)==12 else 'AUDIT_VERIFIED_DOMAIN_GATE_FAILED',
            worker_state=r['state'],planned_anchors=12,executed_anchors=12,planned_branches=336,executed_branches=336,eligible_anchors=len(eligible),
            policy_training_updates=0,fit_updates=0,worker_exited=True,supervisor_exited=True,source_hashes_verified=True,
            selection_reproduced=True,source_sha256=sha(Path(__file__)),raw_sha256=sha(O/'result.json'),strata=strata,
            physical_audits=audits,worker_counts=r['counts'],worker_elapsed_seconds=r['elapsed_seconds'],analysis_elapsed_seconds=time.perf_counter()-start,
            decision='No global domain/training gate if any anchor invalid; conditional valid scores only. No claim that all contact dynamics are unmodellable.',
            joint_limit_audit_limit='Uses frozen worker joint-limit checks; all other listed geometry/history/auxiliary gates recomputed from stored states.')
with (O/'analysis_verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k not in ['physical_audits','strata']},indent=2))
for group,v in strata.items():print(json.dumps(dict(stratum=group,**{k:x for k,x in v.items() if k not in ['B7','conditional_policy_raw']},B7_summary={k:x for k,x in v['B7'].items() if k!='by_component'}),indent=2))
