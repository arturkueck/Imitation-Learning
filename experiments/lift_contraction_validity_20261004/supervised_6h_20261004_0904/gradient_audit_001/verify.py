"""Independent audit of raw gradient statistics, selection and unchanged policy."""
import json,hashlib,math
from pathlib import Path
import numpy as np
import h5py,psutil,torch
O=Path(__file__).resolve().parent;S=O.parent;R=S.parents[2];P=S/'attempts/attempt_002'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
def close(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)
r=read(O/'result.json');selection=read(O/'selection.json');sup=read(O/'supervisor_result.json');launch=read(O/'launch.json')
assert r['state']=='COMPLETE' and sup['returncode']==0 and not sup.get('timed_out',False)
assert sup['worker_job_closed'] and not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
assert launch['deadline_unix']<=read(S/'session.json')['deadline_unix']
for name,digest in read(O/'source_hashes.json').items():assert sha(O/name)==digest
for name,digest in r['input_hashes'].items():assert sha(O/name)==digest
cal=read(O/'calibration.json')
for name,digest in cal['calibration_sources'].items():assert sha(Path(name))==digest
assert r['policy_training_updates']==r['optimizer_constructions']==0 and r['main_parameter_grads_remain_none']
assert r['initial_parameter_sha256']==r['final_parameter_sha256']==read(P/'B0/training_result.json')['final_parameters_sha256']
assert sha(P/'B0/model_final.pth')==r['checkpoint_sha256_before']==r['checkpoint_sha256_after']==selection['checkpoint_sha256']
checkpoint=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False)
h=hashlib.sha256()
for name,t in sorted(checkpoint['model']['nets'].items()):h.update(name.encode());h.update(t.cpu().contiguous().numpy().tobytes())
assert h.hexdigest()==r['final_parameter_sha256']
config=json.loads(checkpoint['config']);assert config['algo']['loss']==r['effective_loss_weights']==dict(l2_weight=1.,l1_weight=0.,cos_weight=0.)
manifest=read(P/'dataset_manifest.json');excluded=set(selection['excluded_prior_demos']);rng=np.random.default_rng(selection['seed'])
assert rng.choice(sorted(set(manifest['train_demos'])-excluded),8,replace=False).tolist()==selection['train_demos']
assert rng.choice(sorted(set(manifest['valid_demos'])-excluded),4,replace=False).tolist()==selection['valid_demos']
assert not set(selection['train_demos'])&set(selection['valid_demos'])
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==selection['dataset_sha256']
assert len(r['rows'])==60
with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
    for split in ['train','valid']:
        for demo in selection[split+'_demos']:
            rows=[x for x in r['rows'] if x['demo']==demo]
            assert len(rows)==5 and all(x['split']==split for x in rows)
            for x in rows:
                assert x['t']==int(x['fraction']*(len(f['data/'+demo+'/actions'])-1))
                assert x['fraction'] in selection['fractions'] and x['phase']==('early' if x['fraction']<=.15 else 'later')
                close(x['official_loss_components']['action_loss'],x['BC_loss'])
                close(x['official_loss_components']['l2_loss'],x['BC_loss'])
                bc=math.sqrt(sum(x['BC_parameter_squared_norms']));close(bc,x['BC_gradient_norm'])
                for name,z in x['regularizers'].items():
                    n=math.sqrt(sum(z['parameter_squared_norms']));cross=sum(z['parameter_dot_with_BC'])
                    close(n,z['gradient_norm']);close(cross,z['dot_with_BC']);close(n/bc,z['norm_ratio_to_BC']);close(cross/n/bc,z['cosine_to_BC'])
                    # Worker averages six float32 values; bound reduction rounding
                    # by six machine epsilons rather than comparing to float64 exactly.
                    expected=sum(max(v,0) for v in z['hinge_arguments'])/6
                    assert math.isclose(expected,z['loss'],rel_tol=6*np.finfo(np.float32).eps,abs_tol=np.finfo(np.float32).tiny)
                    assert sum(v>0 for v in z['hinge_arguments'])==z['active_perturbations']
for group,summary in r['summaries'].items():
    split,phase=group.split('_');rows=[x for x in r['rows'] if x['split']==split and x['phase']==phase]
    assert len(rows)==summary['frames']
    for name,z in summary['regularizers'].items():
        q=[x['regularizers'][name] for x in rows]
        assert sum(x['active_perturbations'] for x in q)==z['active_perturbations']
        assert sum(x['gradient_norm']==0 for x in q)==z['zero_gradient_frames']==0
        close(float(np.median([x['norm_ratio_to_BC'] for x in q])),z['median_norm_ratio_to_BC'])
        close(float(np.median([x['cosine_to_BC'] for x in q])),z['median_cosine_to_BC'])
        assert sum(x['cosine_to_BC']<0 for x in q)==z['negative_cosines']
    for old in ['OLS','B3']:
        close(float(np.median([x['regularizers']['B7']['gradient_norm']/x['regularizers'][old]['gradient_norm'] for x in rows])),summary['paired_gradient_norms']['B7_over_'+old]['median'])
for old in ['OLS','B3']:
    scale=float(np.median([x['regularizers'][old]['gradient_norm']/x['regularizers']['B7']['gradient_norm'] for x in r['rows'] if x['split']=='train']))
    close(scale,r['descriptive_scales'][old+'_to_B7']['descriptive_lambda'])
    close(float(np.median([scale*x['regularizers']['B7']['norm_ratio_to_BC'] for x in r['rows'] if x['split']=='valid'])),r['descriptive_scales'][old+'_to_B7']['valid_median_scaled_norm_ratio_to_BC'])
assert r['finite_difference']['clone_exactly_restored']
for name,z in r['finite_difference']['checks'].items():
    assert z['state']=='VERIFIED'
    observed=(z['minus_plus_losses'][1]-z['minus_plus_losses'][0])/(2*z['epsilon'])
    close(observed,z['central_difference']);close(z['analytic'],z['gradient_norm'])
    error=abs(observed-z['analytic']);close(error,z['absolute_error'])
    assert error<=selection['finite_difference_absolute_tolerance'] or error/z['analytic']<=selection['finite_difference_relative_tolerance']
    if name!='BC':assert z['active_masks'][0][name]==z['active_masks'][1][name]
audit=dict(state='VERIFIED',frames=60,perturbations_per_loss=360,train_demos=8,valid_demos=4,
           worker_exited=True,supervisor_exited=True,optimizer_constructions=0,policy_training_updates=0,
           source_hashes_verified=True,selection_reproduced=True,statistics_recomputed=True,
           checkpoint_and_parameter_hashes_unchanged=True,finite_difference='VERIFIED_ON_ONE_FIXED_TRAIN_PROBE',
           result_sha256=sha(O/'result.json'),source_sha256=sha(Path(__file__)),
           limitations='Recorded observations, one policy seed. No physical-model domain or BC task improvement established.')
with (O/'verification.json').open('x',encoding='utf-8') as f:json.dump(audit,f,indent=2)
print(json.dumps(audit,indent=2))
