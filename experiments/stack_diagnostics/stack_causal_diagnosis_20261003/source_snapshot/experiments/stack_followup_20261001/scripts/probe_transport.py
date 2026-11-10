"""Teacher-forced prediction and paired observation probes, unchanged weights."""
import json, argparse
import numpy as np
import torch
from transport_data import demos,history,KEYS,ROOT,OUT,summary
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint
parser=argparse.ArgumentParser();parser.add_argument('--checkpoint');parser.add_argument('--tag',default='baseline');args=parser.parse_args()
old=json.loads((ROOT/'experiments/stack_followup_20261001/evaluation/fixed_scheduler_h2/evaluation_results.json').read_text())
ckpt=load_dict_from_checkpoint(ckpt_path=args.checkpoint or old['checkpoint']);cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4); policy,ckpt=policy_from_checkpoint(ckpt_dict=ckpt); ds=demos()
samples=[]
for d in ds:
    # All validation examples; matched 20 training demos to expose fitting vs generalization.
    if d['split']=='train' and int(d['name'].split('_')[-1])>=23: continue
    for phase in (2,3,4,5):
        ids=np.flatnonzero((d['phase']==phase)&(d['label_error']<.01))
        for i in ids[::2]:
            samples.append(dict(demo=d['name'],split=d['split'],phase=phase,step=int(i),obs=history(d,i),action=d['actions'][i],
                future_actions=d['actions'][[i,min(i+1,len(d['actions'])-1)]],progress=float((i-ids[0])/max(1,ids[-1]-ids[0]))))

def infer(observations,seed=713):
    batches=[]
    for start in range(0,len(observations),32):
        ob={k:torch.tensor(np.stack([o[k] for o in observations[start:start+32]]),dtype=torch.float32,device=policy.policy.device) for k in KEYS}
        torch.manual_seed(seed+start)
        with torch.no_grad(): a=policy.policy._get_action_trajectory(ob)
        batches.append(a.cpu().numpy())
    return np.concatenate(batches)

observations=[s['obs'] for s in samples]
predictions=np.stack([infer(observations,seed=713+10000*r) for r in range(3)])
expected=np.stack([s['action'] for s in samples]); future=np.stack([s['future_actions'] for s in samples])
phase=np.array([s['phase'] for s in samples]); split=np.array([s['split'] for s in samples]); progress=np.array([s['progress'] for s in samples])
def metric(pred,expert,ob):
    vec=np.stack([o['object'][-1,:2]-o['object'][-1,3:5] for o in ob]);dist=np.linalg.norm(vec,axis=1);p=pred[:,:2];e=expert[:,:2]
    pm=np.linalg.norm(p,axis=1);em=np.linalg.norm(e,axis=1);valid=(em>.1)&(dist>.02)
    cos=(p*e).sum(axis=1)/np.maximum(pm*em,1e-9)
    gcos=(p*vec).sum(axis=1)/np.maximum(pm*dist,1e-9)
    return dict(n=len(pred),xy_rmse=float(np.sqrt(np.mean((p-e)**2))),xy_mae=float(np.mean(abs(p-e))),
        xy_magnitude_ratio=summary(pm[valid]/em[valid]),cosine_with_expert=summary(cos[valid]),
        wrong_direction_fraction=float((cos[valid]<0).mean()) if valid.any() else None,
        small_action_fraction=float((pm[valid]<.05).mean()) if valid.any() else None,
        goal_cosine=summary(gcos[valid]),gripper_sign_accuracy=float(((pred[:,-1]>0)==(expert[:,-1]>0)).mean()),
        opening_fraction=float((pred[:,-1]<0).mean()),z_mae=float(np.mean(abs(pred[:,2]-expert[:,2]))))
scores={}
for sp in ('train','valid'):
    for ph in (2,3,4,5):
        mask=(split==sp)&(phase==ph); ii=np.flatnonzero(mask)
        scores[f'{sp}_phase{ph}']=metric(predictions[:,mask,0,:].reshape(-1,7),np.tile(expected[mask],(3,1)),[observations[i] for _ in range(3) for i in ii])
        if ph==4:
            for l,r in ((0,.25),(.25,.75),(.75,1.001)):
                m=mask&(progress>=l)&(progress<r); jj=np.flatnonzero(m)
                scores[f'{sp}_transport_{l}_{r}']=metric(predictions[:,m,0,:].reshape(-1,7),np.tile(expected[m],(3,1)),[observations[i] for _ in range(3) for i in jj])
np.savez_compressed(OUT/f'{args.tag}_teacher_predictions.npz',predictions=predictions,expected=expected,future=future,phase=phase,split=split,progress=progress,
    **{k:np.stack([o[k] for o in observations]) for k in KEYS})
(OUT/f'{args.tag}_teacher_samples.json').write_text(json.dumps([{k:v for k,v in s.items() if k not in ('obs','action','future_actions')} for s in samples],indent=2))
result=dict(checkpoint=args.checkpoint or old['checkpoint'],teacher_forcing=scores,draws=3)

if args.tag=='baseline':
    # Same noise for original and +-4cm target perturbation, all other inputs fixed.
    ids=np.flatnonzero((split=='valid')&(phase==4)&(progress<.5))
    bounds=json.loads((OUT/'data_behavior.json').read_text())['A_start_quantiles']
    eligible=[i for i in ids if np.all(observations[i]['object'][:,0]-.04>=bounds[0][0]) and np.all(observations[i]['object'][:,0]+.04<=bounds[-1][0])]
    ob=[observations[i] for i in eligible]
    plus=[{k:v.copy() for k,v in o.items()} for o in ob];minus=[{k:v.copy() for k,v in o.items()} for o in ob]
    for o in plus:o['object'][:,0]+=.04
    for o in minus:o['object'][:,0]-=.04
    p=np.stack([infer(plus,713+10000*r) for r in range(3)]);m=np.stack([infer(minus,713+10000*r) for r in range(3)]);diff=(p[:,:,0,0]-m[:,:,0,0]).ravel()
    result['goal_shift_probe']=dict(n_observations=len(ob),draws=3,x_response=summary(diff),correct_response_fraction=float((diff>0).mean()),common_diffusion_noise=True)
    # Restore exact stored states to reconstruct full policy inputs, including EEF quaternion.
    env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False);roll_obs=[];roll_info=[]
    for path in sorted((ROOT/'experiments/stack_placement_20261001/baseline').glob('*.npz')):
        data=np.load(path);t=data['trace']; held=(t[:,34]>0)&(t[:,6]>.88);first=np.flatnonzero(held)
        if not len(first):continue
        env.reset()
        # Two consecutive post-action states correspond to the next replanning observation.
        for i in np.arange(first[0],min(first[0]+80,len(t)-1),8):
            if t[i,34]==0:continue
            hs=[]
            for j in (max(0,i-1),i):
                obs=env.unwrapped.reset_to({'states':data['states'][j]})
                hs.append({k:np.asarray(obs[k]) for k in KEYS})
            o={k:np.stack([v[k] for v in hs]) for k in KEYS}
            # Physics state and cached step observations differ slightly. Use recorded EEF/finger values.
            assert np.max(abs(o['object'][-1]-t[i,1:7]))<.001
            roll_info_error=float(np.max(abs(o['robot0_eef_pos'][-1]-t[i,15:18])))
            for frame,j in enumerate((max(0,i-1),i)):
                o['robot0_eef_pos'][frame]=t[j,15:18]
                o['robot0_gripper_qpos'][frame]=t[j,18:20]
            roll_obs.append(o);roll_info.append(dict(seed=int(path.stem),step=int(i),cube_z=float(t[i,6]),eef_z=float(t[i,17])))
            roll_info[-1]['restored_vs_cached_eef_error_m']=roll_info_error
    env.base_env.close()
    roll_pred=np.stack([infer(roll_obs,seed=990+10000*r) for r in range(3)])
    raised=[{k:v.copy() for k,v in o.items()} for o in roll_obs]
    for o in raised:
        # Shift held cube and EEF together; preserve grip offset and two-frame velocity.
        dz=1.05-o['object'][-1,5]
        o['object'][:,5]+=dz;o['robot0_eef_pos'][:,2]+=dz
    raised_pred=np.stack([infer(raised,seed=990+10000*r) for r in range(3)])
    desired=np.stack([np.r_[np.clip(.6*(o['object'][-1,:2]-o['robot0_eef_pos'][-1,:2])/.05,-1,1),0,0,0,0,1] for o in roll_obs])
    result['rollout_observation_probe']=dict(n_observations=len(roll_obs),draws=3,original=metric(roll_pred[:,:,0,:].reshape(-1,7),np.tile(desired,(3,1)),roll_obs*3),raised_to_expert_height=metric(raised_pred[:,:,0,:].reshape(-1,7),np.tile(desired,(3,1)),raised*3),
        restored_vs_cached_eef_error_m=summary([r['restored_vs_cached_eef_error_m'] for r in roll_info]),
        caveat='Counterfactual predictions only; EEF position/fingers from exact trace, EEF quaternion reconstructed from physics state. Fixed fingers/orientation can remain outside expert distribution. No simulator controller correction.')
    np.savez_compressed(OUT/'rollout_observation_probes.npz',original=roll_pred,raised=raised_pred,desired=desired,
        **{k:np.stack([o[k] for o in roll_obs]) for k in KEYS})
    (OUT/'rollout_probe_samples.json').write_text(json.dumps(roll_info,indent=2))
(OUT/f'{args.tag}_prediction_analysis.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
