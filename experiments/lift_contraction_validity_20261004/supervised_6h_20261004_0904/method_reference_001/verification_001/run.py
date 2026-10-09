"""Independent NumPy formula and annotation/support reconstruction, no gradients."""
import json,hashlib,time,importlib.util,traceback
from pathlib import Path
import numpy as np,h5py,torch
O=Path(__file__).resolve().parent;D=O.parent;S=D.parent;ROOT=S.parents[2];P=S/'attempts/attempt_002';DATA=S/'error_margin_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=time.monotonic();result=dict(state='RUNNING',optimizer_constructions=0,optimizer_updates=0,physics_steps=0,rows=[])
try:
    r=read(D/'result.json');raw=read(DATA/'result.json');local=read(DATA/'local_identification.json');cal=read(DATA/'calibration.json');filterrows=read(DATA/'filter_analysis.json')['rows'];spec=read(D/'selection.json')
    assert r['state']=='REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE'
    for n,h in read(D/'source_hashes.json').items():assert sha(D/n)==h,n
    for n,h in spec['input_hashes'].items():assert sha(S/n)==h,n
    module=importlib.util.spec_from_file_location('pilot',P/'run.py');core=importlib.util.module_from_spec(module);module.loader.exec_module(core);core.bootstrap()
    from robomimic.config import config_factory
    from robomimic.algo.bc import BC
    import robomimic.utils.obs_utils as ObsUtils
    ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False);cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg);torch.set_num_threads(2)
    model=BC.__new__(BC);model.algo_config=cfg.algo;model.obs_config=cfg.observation;model.global_config=cfg;model.device=torch.device('cpu');model.ac_dim=ckpt['shape_metadata']['ac_dim'];model.obs_key_shapes=ckpt['shape_metadata']['all_shapes']
    model._create_shapes(cfg.observation.modalities,model.obs_key_shapes);model._create_networks();model.nets.load_state_dict(ckpt['model']['nets']);model.nets.eval();assert not hasattr(model,'optimizers')
    lr={(x['demo'],x['t']):x for x in local['rows']};A=np.asarray(cal['A']);epsilon=read(DATA/'margin_spec.json')['empirical_normalized_vector_error_max'];maximum_loss_error=0.;maximum_ratio_error=0.
    with h5py.File(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as data,torch.inference_mode():
        for recorded,audit,filters in zip(raw['rows'],r['rows'],filterrows):
            demo,t=recorded['demo'],recorded['t'];assert (demo,t)==(audit['demo'],audit['t'])
            obs={k:torch.as_tensor(data['data/'+demo+'/obs/'+k][t],dtype=torch.float32).reshape(1,-1) for k in model.obs_shapes}
            base=np.clip(model.nets['policy'](obs_dict=obs,goal_dict=None).numpy(),-1,1)
            delta=torch.eye(3).repeat_interleave(2,dim=0)*.005;delta[::2]*=-1
            noisy={k:v.repeat(6,1) for k,v in obs.items()};noisy['robot0_eef_pos']+=delta;noisy['object'][:,-3:]-=delta
            changed=np.clip(model.nets['policy'](obs_dict=noisy,goal_dict=None).numpy(),-1,1)
            low=np.asarray([recorded['branches'][f'B_{axis}_minus']['action'][axis] for axis in range(7)],dtype=np.float32)
            high=np.asarray([recorded['branches'][f'B_{axis}_plus']['action'][axis] for axis in range(7)],dtype=np.float32)
            region=np.all((base>=low)&(base<=high)&(changed>=low)&(changed<=high),axis=1);assert int(region.sum())==audit['action_region_cases']
            feature_errors={k:float(np.max(np.abs(obs[k].numpy().ravel()-np.asarray(recorded['branches']['reference']['observation'][k])))) for k in obs}
            assert feature_errors==audit['feature_absolute_errors'];mapping=all(v<=spec['feature_absolute_tolerance'] for v in feature_errors.values())
            info=lr[(demo,t)];assert info['identification_performed']==audit['cache_identification_available'] and mapping==audit['feature_mapping_passed']
            if info['identification_performed']:
                B=np.asarray(info['B_local']);prediction=delta.double().numpy()@A+(changed-base).astype(np.float64)@B
                ratio=np.linalg.norm(prediction,axis=1)/np.linalg.norm(delta.double().numpy(),axis=1)
            else:ratio=np.zeros(6)
            verified={}
            for name,value in audit['regularizers'].items():
                mask=region&bool(info['identification_performed'] and mapping and filters['masks'][name.split('_')[0]])
                assert mask.astype(float).tolist()==value['weights']
                used_epsilon=epsilon if name.endswith('margin') else 0.
                active=mask&(ratio+used_epsilon>.99);expected=float(np.sum(np.maximum((ratio+used_epsilon)**2-.99**2,0)*mask)/6)
                err=abs(expected-value['loss']);maximum_loss_error=max(maximum_loss_error,err)
                ratioerr=max([abs(x-y) for x,y,w in zip(ratio,value['raw_ratio'],mask) if w]+[0.]);maximum_ratio_error=max(maximum_ratio_error,ratioerr)
                assert err<1e-6 and ratioerr<1e-6 and int(active.sum())==value['active_perturbations']
                verified[name]=dict(numpy_loss=expected,absolute_loss_difference=err,weights_verified=True,active_cases=int(active.sum()))
            result['rows'].append(dict(demo=demo,t=t,variants=verified))
    assert sha(P/'B0/model_final.pth')==spec['checkpoint_sha256'] and sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5')==spec['dataset_sha256']
    assert all(p.grad is None for p in model.nets.parameters())
    result.update(state='NUMPY_FORMULA_CACHE_AND_ACTION_SUPPORT_VERIFIED',frames_verified=12,variants_per_frame=4,planned_cases=72,
                  maximum_loss_difference=maximum_loss_error,maximum_ratio_difference=maximum_ratio_error,
                  main_result_sha256=sha(D/'result.json'),source_sha256=sha(Path(__file__)),checkpoint_sha256=spec['checkpoint_sha256'],dataset_sha256=spec['dataset_sha256'],
                  policy_forward_batches=24,policy_input_samples=84,not_new_confirmation_data=True)
except BaseException:result.update(state='FAILED',error=traceback.format_exc());traceback.print_exc()
result['elapsed_seconds']=time.monotonic()-start
with (O/'result.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));raise SystemExit(0 if result['state']=='NUMPY_FORMULA_CACHE_AND_ACTION_SUPPORT_VERIFIED' else 2)
