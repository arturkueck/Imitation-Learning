"""Matched three-draw teacher forcing on all train/validation demos."""
import argparse,json
import numpy as np
import torch
from balance_common import EXP,SOURCE,event,first_run
from transport_data import demos,history,KEYS,summary
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
p=argparse.ArgumentParser();p.add_argument('variant');args=p.parse_args();folder=EXP/args.variant;folder.mkdir(exist_ok=True)
path=SOURCE['checkpoint'] if args.variant=='source' else str(folder/'model_final.pth')
ckpt=load_dict_from_checkpoint(ckpt_path=path);cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4);policy,_=policy_from_checkpoint(ckpt_dict=ckpt);ds=demos();samples=[]
for d in ds:
    k=event(d);ids=set(range(max(0,k-10),min(len(d['actions'])-1,k+31),2))
    ids.update([int(i) for i in np.flatnonzero(np.isin(d['phase'],[3,4])) if (i-(k-10))%2==0])
    for i in sorted(ids):samples.append((d,i,k))
obs={key:np.stack([history(d,i)[key] for d,i,k in samples]) for key in KEYS}
pred=[]
for draw in range(3):
    chunks=[]
    for start in range(0,len(samples),64):
        torch.manual_seed(713+draw*10000+start)
        ob={key:torch.tensor(v[start:start+64],dtype=torch.float32,device=policy.policy.device) for key,v in obs.items()}
        with torch.no_grad():a=policy.policy._get_action_trajectory(ob)
        chunks.append(a.cpu().numpy())
    pred.append(np.concatenate(chunks));print('draw',draw,flush=True)
pred=np.array(pred);expected=np.stack([d['actions'][[i,min(i+1,len(d['actions'])-1)]] for d,i,k in samples])
phase=np.array([[d['phase'][i],d['phase'][min(i+1,len(d['phase'])-1)]] for d,i,k in samples]);splits=np.array([d['split'] for d,i,k in samples]);offsets=np.array([i-k for d,i,k in samples])
scores={}
for split in ('train','valid'):
    for ph in (3,4):
        mask=(splits[:,None]==split)&(phase==ph);e=np.tile(expected[mask],(3,1));a=pred[:,mask,:].reshape(-1,7)
        pm=np.linalg.norm(a[:,:2],axis=1);em=np.linalg.norm(e[:,:2],axis=1);active=em>.1;cos=(a[:,:2]*e[:,:2]).sum(1)/np.maximum(pm*em,1e-9)
        scores[f'{split}_phase{ph}']=dict(n_frames=int(mask.sum()),xy_ratio=summary(pm[active]/em[active]),direction_cosine=summary(cos[active]),wrong_direction=float(np.mean(cos[active]<0)) if active.any() else None,opening=float(np.mean(a[:,-1]<0)),z_mae=float(np.mean(abs(a[:,2]-e[:,2]))),positive_z_fraction=float(np.mean(a[:,2]>.1)))
boundary=[];transport_trials=[]
for d in ds:
    k=event(d);ii=[j for j,(dd,i,kk) in enumerate(samples) if dd['name']==d['name'] and -10<=i-k<=30];steps=np.array([samples[j][1] for j in ii]);order=np.argsort(steps);ii=np.array(ii)[order];steps=steps[order]
    # Dedicated event-relative cadence prevents mixing overlapping prediction chunks.
    keep=(steps-(k-10))%2==0;ii=ii[keep];steps=steps[keep]
    for draw in range(3):
        a=pred[draw,ii].reshape(-1,7);ts=np.stack([steps,steps+1],axis=1).ravel();valid=(ts>=k-10)&(ts<=k+30);a=a[valid];ts=ts[valid]
        v=d['obs']['object'][ts,:2]-d['obs']['robot0_eef_pos'][ts,:2];m=np.linalg.norm(a[:,:2],axis=1);cos=(a[:,:2]*v).sum(1)/np.maximum(m*np.linalg.norm(v,axis=1),1e-9)
        onset=first_run((m>.25)&(cos>.5));post=ts>=k;pair=post[1:]&post[:-1]&(m[1:]>.01)&(m[:-1]>.01)&(np.diff(ts)==1)
        flips=((a[1:,:2]*a[:-1,:2]).sum(1)<0)&pair
        boundary.append(dict(demo=d['name'],split=d['split'],draw=draw,onset_offset=int(ts[onset]-k) if onset is not None else None,post_xy_mean=float(m[post].mean()),pre_xy_mean=float(m[~post].mean()),reversals=int(flips.sum()),pairs=int(pair.sum())))
    jj=np.array([j for j,(dd,i,kk) in enumerate(samples) if dd['name']==d['name']]);tt=np.array([samples[j][1] for j in jj]);times=np.stack([tt,tt+1],axis=1).ravel();ph=d['phase'][np.minimum(times,len(d['phase'])-1)]
    for draw in range(3):
        aa=pred[draw,jj].reshape(-1,7);mm=np.linalg.norm(aa[:,:2],axis=1);pair=(ph[1:]==4)&(ph[:-1]==4)&(mm[1:]>.01)&(mm[:-1]>.01)&(np.diff(times)==1)
        transport_trials.append(dict(demo=d['name'],split=d['split'],draw=draw,reversals=int((((aa[1:,:2]*aa[:-1,:2]).sum(1)<0)&pair).sum()),pairs=int(pair.sum())))
out=dict(checkpoint=path,draws=3,scores=scores,boundary={})
for split in ('train','valid'):
    b=[r for r in boundary if r['split']==split];on=[r['onset_offset'] for r in b if r['onset_offset'] is not None]
    out['boundary'][split]=dict(n=len(b),onset_found_fraction=len(on)/len(b),onset_offset_steps=summary(on),post_xy_mean=summary([r['post_xy_mean'] for r in b]),pre_xy_mean=summary([r['pre_xy_mean'] for r in b]),reversal_fraction=sum(r['reversals'] for r in b)/sum(r['pairs'] for r in b))
    tr=[r for r in transport_trials if r['split']==split];out['boundary'][split]['full_transport_reversal_fraction']=sum(r['reversals'] for r in tr)/sum(r['pairs'] for r in tr)
np.savez_compressed(folder/'offline_predictions.npz',predictions=pred,expected=expected,phase=phase,split=splits,offsets=offsets,**obs)
(folder/'offline_samples.json').write_text(json.dumps([dict(demo=d['name'],step=i,event=k,split=d['split']) for d,i,k in samples],indent=2))
(folder/'boundary_trials.json').write_text(json.dumps(boundary,indent=2));(folder/'offline_results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
