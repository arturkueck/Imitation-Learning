"""Exploratory cache/gradient audit on already observed data. No optimizer."""
import copy,hashlib,importlib.util,json,time,traceback
from pathlib import Path
import numpy as np,torch,h5py
from loss_reference import reference_loss,action_region_mask
from checks import run_checks
O=Path(__file__).resolve().parent;S=O.parent;ROOT=S.parents[2];P=S/'attempts/attempt_002';D=S/'error_margin_001'
COUNTS={'main_forward_batches':0,'main_policy_input_samples':0,'clone_forward_batches':0,'clone_policy_input_samples':0,'physics_steps':0,'optimizer_constructions':0,'optimizer_updates':0}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(p)
def state_hash(nets):
    digest=hashlib.sha256()
    for name,value in sorted(nets.state_dict().items()):digest.update(name.encode());digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()
def stop():
    if (O/'STOP_REQUESTED').exists():raise InterruptedError('Fixed session/job deadline')
def norm(g):return float(torch.sqrt(sum(x.double().square().sum() for x in g)))
def dot(g,h):return float(sum((x.double()*y.double()).sum() for x,y in zip(g,h)))
def forward(model,obs,clone=False):
    tag='clone' if clone else 'main';COUNTS[tag+'_forward_batches']+=1;COUNTS[tag+'_policy_input_samples']+=len(next(iter(obs.values())))
    unbounded=model.nets['policy'](obs_dict=obs,goal_dict=None)
    return torch.clamp(unbounded,-1,1),((unbounded<=-1)|(unbounded>=1)).detach()
def inputs(model,ob,delta,clone=False):
    base,bclip=forward(model,ob,clone)
    shifted={k:v.repeat(6,1) for k,v in ob.items()}
    shifted['robot0_eef_pos']=shifted['robot0_eef_pos']+delta;shifted['object']=shifted['object'].clone();shifted['object'][:,-3:]-=delta
    pert,pclip=forward(model,shifted,clone)
    return base,pert,dict(base=bclip.tolist(),perturbed=pclip.tolist()),shifted
def finite_difference(model,ob,delta,A,B,eps,weights):
    clone=copy.copy(model);clone.nets=copy.deepcopy(model.nets).double();params=list(clone.nets.parameters())
    originals=[x.detach().clone() for x in params];before=state_hash(clone.nets);ob={k:v.double() for k,v in ob.items()};delta,A,B=delta.double(),A.double(),B.double()
    checks={};step=1e-5
    for name,w in weights.items():
        stop();epsilon=eps if name.endswith('margin') else 0.
        base,pert,clip,_=inputs(clone,ob,delta,True)
        loss,info=reference_loss(delta,pert-base,A,B,torch.full((6,),epsilon,dtype=torch.float64),w.double())
        grads=torch.autograd.grad(loss,params);size=norm(grads)
        if size==0:checks[name]=dict(state='ZERO_GRADIENT',gradient_norm=0.);continue
        direction=[g/size for g in grads];values=[];masks=[];clippings=[]
        for sign in [-1,1]:
            with torch.no_grad():
                for p,z,d in zip(params,originals,direction):p.copy_(z+sign*step*d)
                b,a,c,_=inputs(clone,ob,delta,True)
                value,z=reference_loss(delta,a-b,A,B,torch.full((6,),epsilon,dtype=torch.float64),w.double())
                values.append(float(value));masks.append((z['hinge']>0).tolist());clippings.append(c)
        with torch.no_grad():
            for p,z in zip(params,originals):p.copy_(z)
        numerical=(values[1]-values[0])/(2*step);analytic=dot(grads,direction);relative=abs(analytic-numerical)/max(abs(analytic),1e-15)
        kink=masks[0]!=masks[1] or clippings[0]!=clippings[1]
        passed=relative<=1e-5 or abs(analytic-numerical)<=1e-7
        checks[name]=dict(state='NONSMOOTH_BOUNDARY' if kink else 'VERIFIED' if passed else 'DERIVATIVE_FAILED',epsilon=step,analytic=analytic,central_difference=numerical,
                          relative_error=relative,absolute_error=abs(analytic-numerical),frozen_weights=w.tolist(),gradient_norm=size)
    assert state_hash(clone.nets)==before
    return dict(checks=checks,clone_restored=True,clone_initial_final_sha256=before,parameters_modified_only_on_detached_clone=True)

def run():
    start=time.monotonic();result=dict(state='RUNNING',rows=[],counts=COUNTS,policy_updates=0,new_response_fits=0)
    assert not (O/'result.json').exists();write(O/'result.json',result)
    try:
        spec=read(O/'selection.json')
        for name,digest in read(O/'source_hashes.json').items():assert sha(O/name)==digest,name
        for name,digest in spec['input_hashes'].items():assert sha(S/name)==digest,name
        assert sha(P/'B0/model_final.pth')==spec['checkpoint_sha256'] and sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5')==spec['dataset_sha256']
        result['numerical_checks']=run_checks()
        frozen=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(frozen);frozen.loader.exec_module(core);core.bootstrap()
        from robomimic.algo.bc import BC
        from robomimic.config import config_factory
        import robomimic.utils.obs_utils as ObsUtils
        torch.set_num_threads(2);torch.manual_seed(spec['seed'])
        ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False);cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg)
        assert not cfg.train.hdf5_normalize_obs and not cfg.algo.rnn.enabled and not cfg.algo.transformer.enabled
        model=BC.__new__(BC);model.algo_config=cfg.algo;model.obs_config=cfg.observation;model.global_config=cfg;model.device=torch.device('cpu');model.ac_dim=ckpt['shape_metadata']['ac_dim'];model.obs_key_shapes=ckpt['shape_metadata']['all_shapes']
        model._create_shapes(cfg.observation.modalities,model.obs_key_shapes);model._create_networks();model.nets.load_state_dict(ckpt['model']['nets']);model.nets.eval()
        assert not hasattr(model,'optimizers');params=list(model.nets.parameters());initial=state_hash(model.nets);keys=list(model.obs_shapes)
        raw=read(D/'result.json');physical=read(D/'analysis_verification.json');local=read(D/'local_identification.json');cal=read(D/'calibration.json');filters=read(D/'filter_analysis.json')
        localrows={(x['demo'],x['t']):x for x in local['rows']};epsilon=read(D/'margin_spec.json')['empirical_normalized_vector_error_max']
        assert len(raw['rows'])==12 and spec['first_fd_anchor']==dict(demo=raw['rows'][0]['demo'],t=raw['rows'][0]['t'])
        assert initial==read(P/'B0/training_result.json')['final_parameters_sha256']
        names=['M0_raw','M0_margin','M2_raw','M2_margin'];global_grads={name:[torch.zeros_like(x) for x in params] for name in names+['BC']}
        result.update(initial_parameter_sha256=initial,policy_feature_keys=keys,parameter_count=sum(p.numel() for p in params),epsilon_fixed=epsilon,checkpoint_sha256_before=sha(P/'B0/model_final.pth'),dataset_sha256_before=sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5'),selection=spec,
                      mathematical_mask_is_not_dynamic_oracle=True,cache_available_only_after_privileged_physical_gate=True,planned_frames=12,planned_perturbations=72,gradient_lambda_for_diagnostics=1.,effective_BC_loss_weights=dict(cfg.algo.loss))
        with h5py.File(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as data:
            for index,(row,audit,filterrow) in enumerate(zip(raw['rows'],physical['physical_audits'],filters['rows'])):
                stop();demo,t=row['demo'],row['t'];assert audit['demo']==filterrow['demo']==demo and audit['t']==filterrow['t']==t
                ref=row['branches']['reference'];annotation=localrows[(demo,t)];available=annotation['identification_performed'];dtype=torch.float32
                ob={k:torch.as_tensor(data['data/'+demo+'/obs/'+k][t],dtype=dtype).reshape(1,-1) for k in keys}
                label=torch.as_tensor(data['data/'+demo+'/actions'][t],dtype=dtype).reshape(1,-1)
                feature_errors={k:float(np.max(np.abs(ob[k].numpy().ravel()-np.asarray(ref['observation'][k])))) for k in keys}
                mapping_passed=all(v<=spec['feature_absolute_tolerance'] for v in feature_errors.values())
                delta=torch.eye(3,dtype=dtype).repeat_interleave(2,dim=0)*.005;delta[::2]*=-1
                base,pert,clip,shifted=inputs(model,ob,delta)
                official=model._compute_losses({'actions':model.nets['policy'](obs_dict=ob,goal_dict=None)},{'actions':label})
                COUNTS['main_forward_batches']+=1;COUNTS['main_policy_input_samples']+=1
                bc=official['action_loss'];bcgrad=torch.autograd.grad(bc,params,retain_graph=True);bcsize=norm(bcgrad)
                physical_obs={k:torch.as_tensor(np.array([row['branches'][f'Pfull_{axis}_{sign}']['observation'][k] for axis in range(3) for sign in ['minus','plus']]),dtype=dtype) for k in keys}
                with torch.no_grad():physical_actions,_=forward(model,physical_obs)
                stored=np.asarray([row['branches'][f'Pfull_{axis}_{sign}']['action'] for axis in range(3) for sign in ['minus','plus']])
                physical_action_error=float(np.max(np.abs(physical_actions.numpy()-stored)))
                semantic_errors={k:float(torch.max(torch.abs(physical_obs[k]-shifted[k])).detach()) for k in keys}
                action_semantic_error=float(torch.max(torch.abs(physical_actions-pert)).detach())
                nominal_action_error=float(np.max(np.abs(base.detach().numpy().ravel()-np.asarray(ref['action']))))
                low=torch.tensor([row['branches'][f'B_{axis}_minus']['action'][axis] for axis in range(7)],dtype=dtype).repeat(6,1)
                high=torch.tensor([row['branches'][f'B_{axis}_plus']['action'][axis] for axis in range(7)],dtype=dtype).repeat(6,1)
                region=action_region_mask(base.repeat(6,1),pert,low,high)
                B=torch.tensor(annotation['B_local'],dtype=dtype).repeat(6,1,1) if available else torch.full((6,7,3),float('nan'),dtype=dtype)
                A=torch.tensor(cal['A'],dtype=dtype).repeat(6,1,1);weights={};lossstats={}
                for name in names:
                    domain=filterrow['masks'][name.split('_')[0]]
                    w=region.to(dtype)*float(domain and available and mapping_passed);weights[name]=w
                    e=torch.full((6,),epsilon if name.endswith('margin') else 0.,dtype=dtype)
                    value,info=reference_loss(delta,pert-base,A,B,e,w);g=torch.autograd.grad(value,params,retain_graph=True);size=norm(g);cross=dot(g,bcgrad)
                    for total,current in zip(global_grads[name],g):total.add_(current.detach()/12)
                    lossstats[name]=dict(loss=float(value.detach()),weighted_perturbations=int((w>0).sum()),active_perturbations=int(((info['hinge']>0)&(w>0)).sum()),
                                         full_planned_denominator=6,gradient_norm=size,norm_ratio_to_BC=size/bcsize if bcsize>0 else None,
                                         cosine_to_BC=cross/(size*bcsize) if size*bcsize>0 else None,weights=w.tolist(),raw_ratio=info['raw_ratio'].detach().tolist(),upper_ratio=info['upper_ratio'].detach().tolist())
                for total,current in zip(global_grads['BC'],bcgrad):total.add_(current.detach()/12)
                result['rows'].append(dict(demo=demo,t=t,fraction=row['fraction'],cache_identification_available=available,cache_is_privileged_post_physical_validation=available,
                                           independent_nominal_mask=filterrow['masks'],dynamic_domain_label_for_audit_only=audit['eligible'],feature_mapping_passed=mapping_passed,
                                           feature_absolute_errors=feature_errors,action_region_cases=int(region.sum()),planned_cases=6,nominal_action_error=nominal_action_error,
                                           physical_action_reproduction_error=physical_action_error,sensor_vs_physical_feature_errors=semantic_errors,
                                           sensor_vs_physical_action_max_difference=action_semantic_error,BC_loss=float(bc.detach()),BC_gradient_norm=bcsize,regularizers=lossstats))
                if index==0:
                    assert available and mapping_passed
                    result['finite_difference']=finite_difference(model,ob,delta,A,B,epsilon,weights)
                write(O/'result.json',result);print(f'cache {demo} t={t}: mapping={mapping_passed}, B_available={available}, region={int(region.sum())}/6',flush=True)
        result['summaries']={}
        for name in names:
            values=[r['regularizers'][name] for r in result['rows']];g=global_grads[name];bcg=global_grads['BC'];size=norm(g);bcsize=norm(bcg)
            result['summaries'][name]=dict(planned_frames=12,planned_perturbations=72,weighted_perturbations=sum(x['weighted_perturbations'] for x in values),
                                          active_perturbations=sum(x['active_perturbations'] for x in values),batch_mean_loss=sum(x['loss'] for x in values)/12,
                                          global_gradient_norm=size,global_norm_ratio_to_BC=size/bcsize if bcsize>0 else None,global_cosine_to_BC=dot(g,bcg)/(size*bcsize) if size*bcsize>0 else None,
                                          unavailable_or_excluded_cases=72-sum(x['weighted_perturbations'] for x in values))
        result.update(final_parameter_sha256=state_hash(model.nets),checkpoint_sha256_after=sha(P/'B0/model_final.pth'),dataset_sha256_after=sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5'),main_parameter_grads_remain_none=all(p.grad is None for p in params),elapsed_seconds=time.monotonic()-start)
        assert result['final_parameter_sha256']==initial and result['checkpoint_sha256_before']==result['checkpoint_sha256_after'] and result['dataset_sha256_before']==result['dataset_sha256_after'] and result['main_parameter_grads_remain_none']
        failed=any(v['state']=='DERIVATIVE_FAILED' for v in result['finite_difference']['checks'].values())
        assert not failed,'Smooth directional derivative failed; preserve outputs'
        result['state']='REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE'
        result['decision']='Formula/gradient/cache evidence only. Cache requires privileged physics; fixed empirical envelope failed transfer. No policy update, practical training gate or robust algorithm improvement.'
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc,InterruptedError) else 'FAILED',error=traceback.format_exc());traceback.print_exc();return 2
    finally:result['elapsed_seconds']=time.monotonic()-start;write(O/'result.json',result)
if __name__=='__main__':raise SystemExit(run())
