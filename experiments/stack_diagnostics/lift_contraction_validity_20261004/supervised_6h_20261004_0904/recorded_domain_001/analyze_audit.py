"""Recompute geometry/index/hash gates and descriptive gradient linkage."""
import json,hashlib,time
from pathlib import Path
import numpy as np,h5py,psutil
O=Path(__file__).resolve().parent;S=O.parent;R=S.parents[2];P=S/'attempts/attempt_002'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
def angle(a,b):
    a,b=np.array(a),np.array(b);return float(2*np.arccos(np.clip(abs(a@b)/(np.linalg.norm(a)*np.linalg.norm(b)),0,1)))
def norm(a,b):return float(np.linalg.norm(np.array(a)-np.array(b)))
def close(a,b):assert abs(a-b)<1e-12,(a,b)
start=time.perf_counter();r=read(O/'result.json');sel=read(O/'selection.json');sup=read(O/'supervisor_result.json');launch=read(O/'launch.json')
assert r['state']=='COMPLETE_STATIC_AUDIT' and sup['returncode']==0 and not sup.get('timed_out',False)
assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
assert sup['worker_job_closed'] and launch['deadline_unix']<=read(S/'session.json')['deadline_unix']
assert r['policy_training_updates']==r['optimizer_constructions']==r['action_rollout_steps']==0
assert r['reset_to_calls']==r['explicit_forward_calls']==len(r['rows'])==60
for name,digest in read(O/'source_hashes.json').items():assert sha(O/name)==digest
assert sha(P/'B0/model_final.pth')==sel['checkpoint_sha256']==r['checkpoint_sha256_after']
assert sha(S/'gradient_audit_001/result.json')==sel['source_gradient_sha256']
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256']
gradient=read(S/'gradient_audit_001/result.json');lookup={(x['demo'],x['t']):x for x in gradient['rows']}
assert [{k:x[k] for k in ['demo','split','t','fraction','phase','length']} for x in gradient['rows']]==sel['frames']
assert [(x['demo'],x['t']) for x in r['rows']]==[(x['demo'],x['t']) for x in sel['frames']]
with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
    for x in r['rows']:
        d=f['data/'+x['demo']];t=x['t'];a,b=x['recorded'],x['reconstructed'];m=x['metrics']
        for k,v in a.items():assert np.array_equal(v,d['obs/'+k][t])
        close(norm(a['robot0_eef_pos'],b['robot0_eef_pos']),m['eef_position_error_m'])
        close(norm(a['object'][:3],b['object'][:3]),m['object_position_error_m'])
        close(norm(a['object'][-3:],b['object'][-3:]),m['object_relative_error_m'])
        close(angle(a['robot0_eef_quat'],b['robot0_eef_quat']),m['eef_orientation_error_rad'])
        close(angle(a['object'][3:7],b['object'][3:7]),m['object_orientation_error_rad'])
        close(float(np.max(np.abs(np.array(a['robot0_gripper_qpos'])-b['robot0_gripper_qpos']))),m['gripper_qpos_error'])
        geometry=max(m[k] for k in ['eef_position_error_m','object_position_error_m','object_relative_error_m'])<=sel['position_tolerance_m'] and max(m[k] for k in ['eef_orientation_error_rad','object_orientation_error_rad'])<=sel['orientation_tolerance_rad'] and m['gripper_qpos_error']<=sel['gripper_qpos_tolerance']
        assert geometry==x['geometry_passed'] and bool(not x['robot_contacts'])==x['contact_free']
        assert x['static_annotation_eligible']==(geometry and not x['robot_contacts'])
        assert hashlib.sha256(d['states'][t].tobytes()).hexdigest()==x['recorded_state_sha256']
        xml=d.attrs['model_file'];assert hashlib.sha256(xml.encode() if isinstance(xml,str) else xml).hexdigest()==x['xml_sha256']
summaries={}
for split in ['train','valid']:
    for phase in ['early','later']:
        rows=[x for x in r['rows'] if x['split']==split and x['phase']==phase];linked={}
        for label,flag in [('statically_eligible',True),('not_statically_eligible',False)]:
            subset=[lookup[(x['demo'],x['t'])] for x in rows if x['static_annotation_eligible']==flag]
            linked[label]=dict(frames=len(subset),demos=len(set(x['demo'] for x in subset)),
                               regularizers={name:dict(active_perturbations=sum(x['regularizers'][name]['active_perturbations'] for x in subset),
                                                        total_perturbations=6*len(subset),
                                                        median_gradient_norm_ratio_to_BC=float(np.median([x['regularizers'][name]['norm_ratio_to_BC'] for x in subset])) if subset else None)
                                             for name in ['OLS','B3','B7']})
        summaries[split+'_'+phase]=dict(planned_frames=len(rows),geometry_passed=sum(x['geometry_passed'] for x in rows),
                                        contact_free=sum(x['contact_free'] for x in rows),static_annotation_eligible=sum(x['static_annotation_eligible'] for x in rows),
                                        gradient_linkage=linked)
domain=read(S/'mechanism_domain_001/analysis_verification.json')
accepts=[not x['reference_initial_contacts'] for x in domain['physical_audits']]
truth=[x['eligible'] for x in domain['physical_audits']]
counterexample=dict(source_sha256=sha(S/'mechanism_domain_001/analysis_verification.json'),anchors=12,initial_contact_free=sum(accepts),
                    full_domain_eligible=sum(truth),false_accepts=sum(p and not y for p,y in zip(accepts,truth)),
                    interpretation='Descriptive previously seen live anchors, not a classifier validation or mask fit.')
output=dict(state='STATIC_AUDIT_VERIFIED',frames=60,geometry_passed=sum(x['geometry_passed'] for x in r['rows']),
            static_annotation_eligible=sum(x['static_annotation_eligible'] for x in r['rows']),policy_training_updates=0,
            source_sha256=sha(Path(__file__)),raw_sha256=sha(O/'result.json'),source_hashes_verified=True,indices_reproduced=True,
            worker_exited=True,supervisor_exited=True,checkpoint_hash_unchanged=True,summaries=summaries,
            max_geometry_errors={k:max(x['metrics'][k] for x in r['rows']) for k in ['eef_position_error_m','object_position_error_m','object_relative_error_m','eef_orientation_error_rad','object_orientation_error_rad','gripper_qpos_error']},
            unique_robot_contact_pairs=sorted(set(tuple(pair) for x in r['rows'] for pair in x['robot_contacts'])),
            initial_contact_counterexample=counterexample,analysis_elapsed_seconds=time.perf_counter()-start,
            decision='Static annotations are available at these recorded BC indices; dynamic validity, original history and recovery-label semantics remain unproved.')
with (O/'analysis_verification.json').open('x',encoding='utf-8') as f:json.dump(output,f,indent=2,allow_nan=False)
print(json.dumps(output,indent=2))
