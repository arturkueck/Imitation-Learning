"""Frozen-policy offline gradients. No optimizer constructed or step performed."""
import copy, hashlib, importlib.util, json, time, traceback
from pathlib import Path
import h5py
import numpy as np
import torch

O=Path(__file__).resolve().parent; S=O.parent; R=S.parents[2]; P=S/'attempts/attempt_002'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    t=p.with_suffix('.json.tmp');t.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8');t.replace(p)
def state_hash(nets):
    h=hashlib.sha256()
    for name,value in sorted(nets.state_dict().items()):
        h.update(name.encode());h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
def stop():
    if (O/'STOP_REQUESTED').exists():raise InterruptedError('Fixed diagnostic deadline')

def tensors(obs, label, dtype):
    return {k:torch.as_tensor(v,dtype=dtype).reshape(1,-1) for k,v in obs.items()}, torch.as_tensor(label,dtype=dtype).reshape(1,-1)

def losses(model, obs, label, calibration, selection):
    base=model.nets['policy'](obs_dict=obs,goal_dict=None)
    official=model._compute_losses({'actions':base},{'actions':label})
    radius=selection['radius_m'];delta=torch.eye(3,dtype=base.dtype).repeat_interleave(2,dim=0)*radius
    delta[::2]*=-1
    shifted={k:v.repeat(6,1) for k,v in obs.items()}
    shifted['robot0_eef_pos']=shifted['robot0_eef_pos']+delta
    shifted['object']=shifted['object'].clone();shifted['object'][:,-3:]-=delta
    perturbed=model.nets['policy'](obs_dict=shifted,goal_dict=None)
    da=perturbed-base
    A,B3,B7,K=[torch.as_tensor(calibration[k],dtype=base.dtype) for k in ['A','B3','B7','K_OLS']]
    errors={'OLS':delta+da[:,:3]@K,'B3':delta@A+da[:,:3]@B3,'B7':delta@A+da@B7}
    ratio2={k:v.square().sum(-1)/delta.square().sum(-1) for k,v in errors.items()}
    hinge={k:v-selection['target_ratio']**2 for k,v in ratio2.items()}
    out={'BC':official['action_loss']};out.update({k:torch.relu(v).mean() for k,v in hinge.items()})
    return out, hinge, official

def norm(g):return float(torch.sqrt(sum(x.double().square().sum() for x in g)))
def dot(g,h):return float(sum((x.double()*y.double()).sum() for x,y in zip(g,h)))
def ratio(a,b):return a/b if b>0 else None

def finite_difference(model, obs, label, calibration, selection):
    # Main policy never changes. Perturb only a detached clone, restore exactly.
    clone=copy.copy(model);clone.nets=copy.deepcopy(model.nets).double()
    before=state_hash(clone.nets);params=list(clone.nets.parameters());originals=[x.detach().clone() for x in params]
    ob={k:v.double() for k,v in obs.items()};y=label.double();epsilon=selection['finite_difference_epsilon']
    checks={}
    for name in ['BC','OLS','B3','B7']:
        values,hinge,_=losses(clone,ob,y,calibration,selection)
        g=torch.autograd.grad(values[name],params,retain_graph=True);n=norm(g)
        if n==0:
            checks[name]={'state':'DEGENERATE_ZERO_GRADIENT','gradient_norm':n};continue
        direction=[x/n for x in g]; samples=[];active=[]
        for sign in [-1,1]:
            with torch.no_grad():
                for p,z,d in zip(params,originals,direction):p.copy_(z+sign*epsilon*d)
                v,h,_=losses(clone,ob,y,calibration,selection)
                samples.append(float(v[name]));active.append({k:(z>0).tolist() for k,z in h.items()})
        with torch.no_grad():
            for p,z in zip(params,originals):p.copy_(z)
        observed=(samples[1]-samples[0])/(2*epsilon);analytic=dot(g,direction)
        error=abs(observed-analytic);relative=error/max(abs(analytic),1e-15)
        kink=name!='BC' and active[0][name]!=active[1][name]
        passed=error<=selection['finite_difference_absolute_tolerance'] or relative<=selection['finite_difference_relative_tolerance']
        checks[name]=dict(state='RELU_BOUNDARY' if kink else ('VERIFIED' if passed else 'DERIVATIVE_FAILED'),
                          epsilon=epsilon,analytic=analytic,central_difference=observed,absolute_error=error,relative_error=relative,
                          minus_plus_losses=samples,active_masks=active,gradient_norm=n)
    assert state_hash(clone.nets)==before
    return dict(checks=checks,clone_exactly_restored=True,clone_initial_final_sha256=before,
                state='VERIFIED' if all(v['state']=='VERIFIED' for v in checks.values()) else 'LIMITED_OR_FAILED')

def summarize(rows):
    out={}
    for name in ['OLS','B3','B7']:
        rr=[x['regularizers'][name] for x in rows]
        quotients=[x['norm_ratio_to_BC'] for x in rr if x['norm_ratio_to_BC'] is not None]
        cosines=[x['cosine_to_BC'] for x in rr if x['cosine_to_BC'] is not None]
        out[name]=dict(frames=len(rows),active_perturbations=sum(x['active_perturbations'] for x in rr),
                       total_perturbations=6*len(rows),active_frames=sum(x['active_perturbations']>0 for x in rr),
                       zero_gradient_frames=sum(x['gradient_norm']==0 for x in rr),
                       median_loss=float(np.median([x['loss'] for x in rr])),
                       median_gradient_norm=float(np.median([x['gradient_norm'] for x in rr])),
                       median_norm_ratio_to_BC=float(np.median(quotients)) if quotients else None,
                       undefined_norm_ratios=len(rr)-len(quotients),ratio_above_10=sum(x>10 for x in quotients),
                       ratio_below_point1=sum(x<.1 for x in quotients),
                       median_cosine_to_BC=float(np.median(cosines)) if cosines else None,
                       undefined_cosines=len(rr)-len(cosines),negative_cosines=sum(x<0 for x in cosines))
    paired={}
    for denom in ['OLS','B3']:
        q=[ratio(x['regularizers']['B7']['gradient_norm'],x['regularizers'][denom]['gradient_norm']) for x in rows]
        defined=[v for v in q if v is not None]
        paired['B7_over_'+denom]=dict(median=float(np.median(defined)) if defined else None,defined=len(defined),undefined=len(q)-len(defined))
    return dict(frames=len(rows),demos=len(set(x['demo'] for x in rows)),regularizers=out,paired_gradient_norms=paired,
                median_BC_loss=float(np.median([x['BC_loss'] for x in rows])),median_BC_gradient_norm=float(np.median([x['BC_gradient_norm'] for x in rows])))

def run():
    start=time.monotonic();result=dict(state='RUNNING',policy_training_updates=0,optimizer_constructions=0,rows=[])
    assert not (O/'result.json').exists();write(O/'result.json',result)
    try:
        selection=read(O/'selection.json');calibration=read(O/'calibration.json')
        assert sha(P/'B0/model_final.pth')==selection['checkpoint_sha256']
        assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==selection['dataset_sha256']
        for path,digest in calibration['calibration_sources'].items():assert sha(Path(path))==digest
        spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
        from robomimic.config import config_factory
        from robomimic.algo.bc import BC
        import robomimic.utils.obs_utils as ObsUtils
        torch.set_num_threads(2);torch.manual_seed(selection['seed'])
        ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False)
        cfg=config_factory('bc',dic=json.loads(ckpt['config']))
        assert not cfg.train.hdf5_normalize_obs and not cfg.algo.rnn.enabled and not cfg.algo.transformer.enabled
        ObsUtils.initialize_obs_utils_with_config(cfg)
        # Deliberately bypass Algo.__init__, which otherwise creates Adam.
        model=BC.__new__(BC);model.algo_config=cfg.algo;model.obs_config=cfg.observation;model.global_config=cfg
        model.device=torch.device('cpu');model.ac_dim=ckpt['shape_metadata']['ac_dim'];model.obs_key_shapes=ckpt['shape_metadata']['all_shapes']
        model._create_shapes(cfg.observation.modalities,model.obs_key_shapes);model._create_networks()
        model.nets.load_state_dict(ckpt['model']['nets']);model.nets.eval();assert not hasattr(model,'optimizers')
        initial=state_hash(model.nets);params=list(model.nets.parameters());names=[k for k,_ in model.nets.named_parameters()]
        result.update(selection=selection,initial_parameter_sha256=initial,checkpoint_sha256_before=sha(P/'B0/model_final.pth'),
                      effective_loss_weights=dict(cfg.algo.loss),parameter_count=sum(x.numel() for x in params),
                      parameter_names=names,device='cpu',dtype='float32',torch=torch.__version__,
                      input_hashes={k:sha(O/k) for k in ['PROTOCOL.md','selection.json','calibration.json','source_hashes.json']})
        with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
            for split,demos in [('train',selection['train_demos']),('valid',selection['valid_demos'])]:
                for demo in demos:
                    d=f['data/'+demo];length=len(d['actions']);times=[int(z*(length-1)) for z in selection['fractions']]
                    assert len(set(times))==5
                    for fraction,t in zip(selection['fractions'],times):
                        stop();obs,label=tensors({k:d['obs/'+k][t] for k in model.obs_shapes},d['actions'][t],torch.float32)
                        v,hinge,official=losses(model,obs,label,calibration,selection)
                        gradients={name:torch.autograd.grad(loss,params,retain_graph=True) for name,loss in v.items()}
                        bc_norm=norm(gradients['BC']);reg={}
                        for name in ['OLS','B3','B7']:
                            n=norm(gradients[name]);cross=dot(gradients[name],gradients['BC'])
                            reg[name]=dict(loss=float(v[name].detach()),hinge_arguments=hinge[name].detach().tolist(),
                                           active_perturbations=int((hinge[name]>0).sum()),gradient_norm=n,norm_ratio_to_BC=ratio(n,bc_norm),
                                           cosine_to_BC=ratio(cross,n*bc_norm),dot_with_BC=cross,
                                           parameter_squared_norms=[float(x.double().square().sum()) for x in gradients[name]],
                                           parameter_dot_with_BC=[float((x.double()*y.double()).sum()) for x,y in zip(gradients[name],gradients['BC'])])
                        row=dict(demo=demo,split=split,t=t,length=length,fraction=fraction,phase='early' if fraction<=.15 else 'later',
                                 BC_loss=float(v['BC'].detach()),official_loss_components={k:float(z.detach()) for k,z in official.items()},
                                 BC_gradient_norm=bc_norm,BC_parameter_squared_norms=[float(x.double().square().sum()) for x in gradients['BC']],
                                 regularizers=reg)
                        result['rows'].append(row)
                        if demo==selection['finite_difference_demo'] and fraction==selection['finite_difference_fraction']:
                            result['finite_difference']=finite_difference(model,obs,label,calibration,selection)
                        result['elapsed_seconds']=time.monotonic()-start;write(O/'result.json',result)
                    print(f'{split} {demo}: {len(result["rows"])} frames',flush=True)
        result['summaries']={split+'_'+phase:summarize([x for x in result['rows'] if x['split']==split and x['phase']==phase])
                             for split in ['train','valid'] for phase in ['early','later']}
        train=[x for x in result['rows'] if x['split']=='train'];valid=[x for x in result['rows'] if x['split']=='valid'];scales={}
        for old in ['OLS','B3']:
            q=[ratio(x['regularizers'][old]['gradient_norm'],x['regularizers']['B7']['gradient_norm']) for x in train]
            pos=[v for v in q if v is not None and v>0];value=float(np.median(pos)) if pos else None
            validation=[value*x['regularizers']['B7']['norm_ratio_to_BC'] for x in valid if value is not None and x['regularizers']['B7']['norm_ratio_to_BC'] is not None]
            scales[old+'_to_B7']=dict(descriptive_lambda=value,train_positive_defined=len(pos),train_undefined=sum(v is None for v in q),
                                    train_zero_defined=sum(v==0 for v in q),valid_defined=len(validation),
                                    valid_median_scaled_norm_ratio_to_BC=float(np.median(validation)) if validation else None,
                                    not_selected_for_training=True)
        result.update(descriptive_scales=scales,final_parameter_sha256=state_hash(model.nets),checkpoint_sha256_after=sha(P/'B0/model_final.pth'),
                      main_parameter_grads_remain_none=all(p.grad is None for p in params))
        assert result['initial_parameter_sha256']==result['final_parameter_sha256']
        assert result['checkpoint_sha256_before']==result['checkpoint_sha256_after'] and result['main_parameter_grads_remain_none']
        result['state']='COMPLETE' if result['finite_difference']['state']=='VERIFIED' else 'DERIVATIVE_GATE_LIMITED'
        result['decision']='Offline loss/gradient scale evidence only; no validity transfer to contact states, no policy updates or training authorization.'
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc,InterruptedError) else 'FAILED',error=traceback.format_exc());traceback.print_exc();return 2
    finally:
        result['elapsed_seconds']=time.monotonic()-start;write(O/'result.json',result)

if __name__=='__main__':raise SystemExit(run())
