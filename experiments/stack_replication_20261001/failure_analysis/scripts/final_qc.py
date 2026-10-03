"""Independent completeness, trace, common-control, and native-inference verification."""
import json
import numpy as np
from common import *

records=[];native_checks=0;unique_episodes=0;traces=0
expected=[]
for kind in ('direct','diffusion'):
    for seed in (1,2,3):
        for h in (1,2,4):expected.append((kind,seed,h,0 if kind=='direct' else 10,'replanning'))
        if kind=='diffusion':
            for steps in (5,10,50):expected.append((kind,seed,2,steps,'ddim'))
summary=json.loads((OUT/'closed_loop_summary.json').read_text())
assert len(summary)==27
actual={(r['model'],r['training_seed'],r['executed_actions'],r['ddim_steps'],r['comparison_group']) for r in summary}
assert actual==set(expected)
for kind,seed,h,steps,group in expected:
    dirname=f'{kind}_seed{seed}_h{h}_ddim{10 if kind=="direct" else steps}'+('_ddimstudy' if group=='ddim' else '')
    path=OUT/'rollouts'/dirname;rows=json.loads((path/'results.json').read_text())
    assert len(rows)==40 and sorted(r['start_seed'] for r in rows)==PROTOCOL['fixed_start_seeds']
    shared=group=='ddim' and steps==10
    for r in rows:
        assert r['initial_state_sha256']==PROTOCOL['fixed_start_hashes'][str(r['start_seed'])]
        data=np.load(path/f"{r['start_seed']}.npz");t=data['trace'];m=r['measured_steps']
        assert 0<m<=500 and t.shape==(m+40,37) and int(data['measured'])==m
        assert np.isfinite(t).all() and np.array_equal(t[:,20:27],t[:,27:34])
        assert np.array_equal(t[:,0],np.arange(len(t)))
        assert np.isin(t[:,34:37],[0,1]).all()
        for key in KEYS:assert len(data[key])==len(t) and np.isfinite(data[key]).all()
        if r['sustained_success']:assert np.all(t[m:,36]>0) and np.all(t[m:,35]>0) and np.all(t[m:,34]==0)
        if shared:
            control=np.load(OUT/'rollouts'/f'diffusion_seed{seed}_h2_ddim10'/f"{r['start_seed']}.npz")
            assert r['shared_replanning_baseline'] and np.array_equal(t,control['trace'])
        else:unique_episodes+=1
        traces+=1
    checks=0
    if kind=='diffusion':
        meta=json.loads((path/'complete.json').read_text());assert meta['streams']==1 and meta['sampling_batch_size']==1
        parity=json.loads((path/'graph_live_parity.json').read_text())
        assert len(parity)>=80
        assert all(p['max_abs_error']==0 and p['condition_max_abs_error']==0 and p['rng_state_equal'] for p in parity)
        assert {p['start_seed'] for p in parity}==set(PROTOCOL['fixed_start_seeds'])
        checks=len(parity)
        if not shared:native_checks+=checks
    records.append(dict(model=kind,training_seed=seed,executed_actions=h,ddim_steps=steps,group=group,starts_verified=40,shared_control=shared,native_chunk_checks=checks,stable_stacks=sum(r['sustained_success'] for r in rows)))
assert unique_episodes==960 and traces==1080
for seed in (1,2,3):
    for steps in (5,10,20,50):
        a=np.load(OUT/f'diffusion_seed{seed}_ddim{steps}.npz')['chunks']
        assert a.shape==(420,64,16,7) and np.isfinite(a).all()
inputs=json.loads((OUT/'final_input_verification.json').read_text())
assert inputs['checkpoints_unchanged']==6 and inputs['data_unchanged'] and inputs['noise_identity_unchanged']
base=json.loads((OUT/'baseline_failures.json').read_text());flat=json.loads((OUT/'closed_loop_failures.json').read_text())
assert len(base)==240 and len(flat)==1080
dump('final_evaluation_audit.json',dict(no_training=True,final_checkpoints_unchanged=6,data_unchanged=True,unique_new_rollouts=unique_episodes,table_rows_including_shared_controls=traces,historical_rollouts=240,configurations=27,offline_chunks=3*4*420*64,offline_shape_each=[420,64,16,7],unique_closed_native_chunk_checks=native_checks,maximum_native_action_error=0,all_rng_checks_equal=True,all_initial_hashes_equal=True,all_new_traces_complete_and_finite=True,shared_ddim10_controls_bitwise_equal=True,records=records))
print('Final QC passed:',unique_episodes,'unique rollouts;',native_checks,'native chunk checks; 27 full configurations.')
