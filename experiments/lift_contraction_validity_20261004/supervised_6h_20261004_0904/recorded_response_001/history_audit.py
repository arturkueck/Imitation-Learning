"""Independent recorded geometry, retained-memory and cross-history canonical-state audit."""
import hashlib
import h5py,numpy as np
def diff(a,b):
    if isinstance(a,dict):
        assert set(a)==set(b)
        return max([diff(a[k],b[k]) for k in a]+[0.])
    if a is None or isinstance(a,(str,bool)):return 0. if a==b else float('inf')
    return float(np.max(np.abs(np.asarray(a)-np.asarray(b)),initial=0))
def angle(a,b):
    a,b=np.array(a),np.array(b);return float(2*np.arccos(np.clip(abs(a@b)/(np.linalg.norm(a)*np.linalg.norm(b)),0,1)))
def changed(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        return [v for k in sorted(set(a)|set(b)) for v in changed(a.get(k),b.get(k),path+'/'+k)]
    if a is None or b is None:return [] if a is b else [path]
    if isinstance(a,(str,bool)) or isinstance(b,(str,bool)):return [] if a==b else [path]
    x,y=np.asarray(a),np.asarray(b)
    return [path] if x.shape!=y.shape or not np.array_equal(x,y) else []
def verify(O,r,sel):
    R=O.parent.parents[2];audit=[];pairs=[]
    with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
        for row in r['rows']:
            assert row['history'] in sel['histories']
            d=f['data/'+row['demo']];t=row['t'];ref=row['branches']['reference'];recorded=d['states'][t]
            o=ref['observation'];want={k:d['obs/'+k][t] for k in ['object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']}
            metrics=dict(eef_position_error_m=float(np.linalg.norm(np.array(o['robot0_eef_pos'])-want['robot0_eef_pos'])),
                         object_position_error_m=float(np.linalg.norm(np.array(o['object'])[:3]-want['object'][:3])),
                         object_relative_error_m=float(np.linalg.norm(np.array(o['object'])[-3:]-want['object'][-3:])),
                         eef_orientation_error_rad=angle(o['robot0_eef_quat'],want['robot0_eef_quat']),
                         object_orientation_error_rad=angle(o['object'][3:7],want['object'][3:7]),
                         gripper_qpos_error=float(np.max(np.abs(np.array(o['robot0_gripper_qpos'])-want['robot0_gripper_qpos']))))
            geometry=max(metrics[k] for k in ['eef_position_error_m','object_position_error_m','object_relative_error_m'])<=1e-6 and max(metrics[k] for k in ['eef_orientation_error_rad','object_orientation_error_rad'])<=1e-4 and metrics['gripper_qpos_error']<=1e-9
            assert geometry==row['gates']['recorded_geometry_passed']
            for name,b in row['branches'].items():
                p=b['preparation'];a=b['anchor'];expected=p['expected_retained_memory']
                actual=dict(right={k:a['controllers']['right'][k] for k in expected['right']},
                            right_gripper={k:a['controllers']['right_gripper'][k] for k in expected['right_gripper']},
                            gripper={k:a['gripper_memory'][k] for k in expected['gripper']})
                memory=diff(expected,actual);assert memory<=1e-9 and p['history']==row['history']
                qpos,qvel=np.array(a['sim']['qpos']),np.array(a['sim']['qvel'])
                assert np.array_equal(qpos,recorded[1:1+len(qpos)]) and np.array_equal(qvel,recorded[1+len(qpos):1+len(qpos)+len(qvel)])
                assert a['sim_time']==float(recorded[0]) and a['env_time']['timestep']==t
                assert not a['env_time']['done'] and a['env_time']['cur_time']==a['sim_time']
                assert all(np.max(np.abs(a['sim'][k]),initial=0)==0 for k in sel['standardized_aux_fields'])
                assert not a['sim']['mocap_pos'] and not a['sim']['mocap_quat']
                assert hashlib.sha256(recorded.tobytes()).hexdigest()==p['recorded_state_sha256']
                for k,v in p['recorded_observation'].items():assert np.array_equal(v,want[k])
                assert p['geometry_passed']==geometry and p['retained_memory_error']==0 and p['state_roundtrip_error']==0
            audit.append(dict(demo=row['demo'],t=t,history=row['history'],geometry_passed=geometry,metrics=metrics,
                              retained_memory_verified_branches=len(row['branches']),canonical_recorded_state_verified=True))
    for demo in sel['selected_demos']:
        for fraction in sel['anchor_fractions']:
            rows=[x for x in r['rows'] if x['demo']==demo and x['fraction']==fraction]
            assert len(rows)==2 and {x['history'] for x in rows}==set(sel['histories'])
            rows.sort(key=lambda x:sel['histories'].index(x['history']))
            refs=[x['branches']['reference'] for x in rows];snap=[x['before'] for x in refs]
            physical=diff(snap[0]['sim'],snap[1]['sim']);clock=diff(snap[0]['env_time'],snap[1]['env_time'])
            assert physical==clock==0
            assert diff(refs[0]['observation'],refs[1]['observation'])<=1e-9
            assert diff(refs[0]['action'],refs[1]['action'])<=1e-9
            pairs.append(dict(demo=demo,t=rows[0]['t'],fraction=fraction,same_full_physical_state_error=physical,
                              same_env_clock_error=clock,controller_fields_differ=changed(snap[0]['controllers'],snap[1]['controllers']),
                              gripper_fields_differ=changed(snap[0]['gripper_memory'],snap[1]['gripper_memory']),
                              both_domain_eligible=all(x['gates']['passed'] for x in rows),
                              reference_next_eef_difference_m=float(np.linalg.norm(np.array(refs[0]['next_eef_m'])-refs[1]['next_eef_m']))))
    return dict(state='RECORDED_GEOMETRY_MEMORY_AND_CROSS_HISTORY_VERIFIED',branch_count=672,
                geometry_audits=audit,cross_history_pairs=pairs,
                limitation='Only the two explicit prepared histories; no original Expert/controller-history reconstruction claim.')
