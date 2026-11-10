"""Matched representation experiment: four continuous features from two frames."""
import json,copy,random
import numpy as np
import torch
from balance_common import SOURCE,load_training,digest,rollout_metrics
from transport_data import ROOT,DATA,KEYS,summary
OUT=ROOT/'experiments/stack_diagnostics/stack_dynamics_20261001';OUT.mkdir(exist_ok=True)
DKEY='zz_dynamics';FEATURES=['delta_eef_z','velocity_eef_z','delta_B_z','velocity_B_z']
def numerics():
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
def raw_features(ob):
    e=np.asarray(ob['robot0_eef_pos']);b=np.asarray(ob['object']);de=e[...,1,2]-e[...,0,2];db=b[...,1,5]-b[...,0,5]
    return np.stack([de,de/.05,db,db/.05],axis=-1)
def augment(ob,variant,scales=None):
    if scales is None:scales=json.loads((OUT/'protocol.json').read_text())['feature_normalization']
    r=raw_features(ob);value=(r-np.array(scales['mean']))/np.array(scales['std']) if variant=='dynamics' else np.zeros_like(r)
    return {**ob,DKEY:np.repeat(value[...,None,:],2,axis=-2).astype(np.float32)}
def extra_metrics(t,measured):
    m=rollout_metrics(t,measured);a=t[:measured];held=a[:,34]>0;am=np.linalg.norm(a[:,20:22],axis=1);vec=a[:,1:3]-a[:,4:6];cos=(a[:,20:22]*vec).sum(1)/np.maximum(am*np.linalg.norm(vec,axis=1),1e-9)
    from balance_common import first_run
    # Motion before full lift; same transport criterion as historical metric except height gate.
    vel=np.vstack([np.zeros(2),np.diff(a[:,4:6],axis=0)*20]);vn=np.linalg.norm(vel,axis=1);vc=(vel*vec).sum(1)/np.maximum(vn*np.linalg.norm(vec,axis=1),1e-9)
    premature=first_run(held&(a[:,6]>.88)&((a[:,6]<1.045)|(a[:,17]<1.049))&(vn>.02)&(vc>.5))
    early_command=first_run(held&(a[:,6]>.88)&((a[:,6]<1.045)|(a[:,17]<1.049))&(am>.25)&(cos>.5))
    lift=m['full_lift_end'];start=m['transport_start'];premature_prior=premature is not None and (lift is None or premature<lift)
    return dict(**m,correct_lift=lift is not None,premature_transport=bool(premature_prior),premature_motion_start=premature,premature_command_start=early_command,max_cube_height_m=float(a[:,6].max()),max_held_cube_height_m=float(a[held,6].max()) if held.any() else None,cube_height_at_transport_start_m=float(a[start,6]) if start is not None else None,seconds_after_reset_at_transport_start=float((start+1)*.05) if start is not None else None)
def prepare():
    from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
    if (OUT/'protocol.json').exists():raise RuntimeError('Frozen experiment already exists')
    torch.set_num_threads(4);ds,obs,actions,critical,w,refs,events=load_training();raw=raw_features(obs);mean=raw.mean(0);std=raw.std(0);assert np.all(std>1e-6)
    scales=dict(names=FEATURES,mean=mean.tolist(),std=std.tolist(),method='train-only population standardization; no clipping',fit_frames=len(raw))
    byname={d['name']:d for d in ds};phase=np.array([byname[n]['phase'][i] for n,i in refs]);stats={}
    for ph,name in [(3,'lift'),(4,'transport')]:stats[name]={key:dict(raw=summary(raw[phase==ph,j]),normalized=summary(((raw-mean)/std)[phase==ph,j])) for j,key in enumerate(FEATURES)}
    (OUT/'feature_distribution.json').write_text(json.dumps(stats,indent=2))
    p=dict(source_checkpoint=SOURCE['checkpoint'],source_sha256=digest(SOURCE['checkpoint']),dataset_sha256=digest(DATA),gradient_updates=5000,batch_size=8,seed=1,sampling='uniform, identical sampled indices and diffusion noise streams',feature_normalization=scales,features_repeated_in_both_history_slots=True,history_frames=2,optional_height_reference_features=False,baseline='original raw observations plus four constant-zero capacity-control channels',dynamics='same raw observations plus standardized continuous dynamics channels',architecture='identical UNet in both arms; only FiLM input widths expanded by 8; added weights and moments zero',optimizer='restore AdamW and EMA; optimization_step 30000',lr_schedule=dict(initial_lr=.0001,warmup=500,cosine_updates=5000),inference=dict(ddim_steps=10,action_horizon=2,prediction_horizon=16),rollouts=dict(seeds=list(range(46000,46020)),horizon=500,tail=40),black_image_demos_unchanged=62,classification='A/B/C/D after evaluation; no best-checkpoint selection')
    original=load_dict_from_checkpoint(ckpt_path=SOURCE['checkpoint']);old_policy,_=policy_from_checkpoint(ckpt_dict=original)
    ckpt=copy.deepcopy(original);cfg=json.loads(ckpt['config']);cfg['observation']['modalities']['obs']['low_dim'].append(DKEY);cfg['train']['num_epochs']=50;cfg['experiment']['epoch_every_n_steps']=100;ckpt['config']=json.dumps(cfg)
    ckpt['shape_metadata']['all_shapes'][DKEY]=(4,);ckpt['shape_metadata']['all_obs_keys'].append(DKEY)
    # Source condition = time embedding256 + frame0[15] + frame1[15].
    keep=np.r_[np.arange(271),np.arange(275,290)];changed=[]
    for section in ('nets','ema'):
        for name,value in list(ckpt['model'][section].items()):
            if name.endswith('cond_encoder.1.weight'):
                assert value.shape[1]==286;new=value.new_zeros((value.shape[0],294));new[:,keep]=value;ckpt['model'][section][name]=new
                if section=='nets':changed.append(name)
    names=[n for n,v in old_policy.policy.nets.named_parameters()];optim=ckpt['model']['optimizers']['policy'];ids=[i for g in optim['param_groups'] for i in g['params']];assert len(names)==len(ids)
    for name,pid in zip(names,ids):
        if name in changed:
            for key in ('exp_avg','exp_avg_sq'):
                value=optim['state'][pid][key];new=value.new_zeros((value.shape[0],294));new[:,keep]=value;optim['state'][pid][key]=new
    # Verify function-preserving expansion against original EMA inference.
    new_policy,_=policy_from_checkpoint(ckpt_dict=ckpt);new_policy.policy.deserialize(ckpt['model'],load_optimizers=True);new_policy.policy.ema.optimization_step=30000
    subset={k:obs[k][:8] for k in KEYS};aug=augment(subset,'dynamics',scales)
    def infer(policy,ob):
        torch.manual_seed(919)
        with torch.no_grad():return policy.policy._get_action_trajectory({k:torch.tensor(v,dtype=torch.float32,device=policy.policy.device) for k,v in ob.items()}).cpu().numpy()
    numerics();orig=infer(old_policy,subset);baseline=infer(new_policy,augment(subset,'baseline',scales));dynamics=infer(new_policy,aug)
    error=float(abs(orig-baseline).max());print('INITIAL_PARITY_ERROR',error,'BASE_DYN',float(abs(baseline-dynamics).max()),flush=True)
    assert error<1e-4;assert np.array_equal(baseline,dynamics)
    assert list(new_policy.policy.obs_shapes)[-1]==DKEY
    parameters_old=sum(v.numel() for v in old_policy.policy.nets.parameters());parameters_new=sum(v.numel() for v in new_policy.policy.nets.parameters())
    p['initial_prediction_max_error_vs_original']=error;p['initial_baseline_vs_dynamics_equal']=True;p['parameters_original']=parameters_old;p['parameters_both_variants']=parameters_new;p['expanded_weight_names']=changed
    p['numerics']='FP32, TF32 disabled, cudnn benchmark disabled; identical both arms'
    (OUT/'protocol.json').write_text(json.dumps(p,indent=2));torch.save(ckpt,OUT/'initial_expanded.pth');np.savez_compressed(OUT/'training_features.npz',raw=raw,normalized=(raw-mean)/std,phase=phase)
    print(json.dumps(p,indent=2))
if __name__=='__main__':prepare()
