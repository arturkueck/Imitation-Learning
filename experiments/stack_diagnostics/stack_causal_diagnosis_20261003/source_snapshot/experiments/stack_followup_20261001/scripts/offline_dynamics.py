"""Frozen boundary observations and matched initial diffusion noise, DDIM10 only."""
import argparse,json
import numpy as np,torch
from dynamics_common import OUT,ROOT,KEYS,augment,numerics
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
from robomimic.utils import tensor_utils as TU
from diffusers import DDIMScheduler

p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--train-boundary',action='store_true');args=p.parse_args();v=args.variant
prior=ROOT/'experiments/stack_switch_20261001';panel=np.load(prior/'panel.npz')
prefix=''
if args.train_boundary:
    from transport_data import demos,history
    from balance_common import event
    rows=[];meta=[]
    for d in sorted(demos(),key=lambda d:int(d['name'].split('_')[-1])):
        if d['split']!='train':continue
        k=event(d)
        for o in (-1,0):rows.append(history(d,k+o));meta.append(dict(demo=d['name'],offset=o))
    panel={k:np.stack([r[k] for r in rows]) for k in KEYS};prefix='train_'
    (OUT/'train_boundary_panel.json').write_text(json.dumps(meta,indent=2))
ckpt=load_dict_from_checkpoint(ckpt_path=str(OUT/v/'model_final.pth'));cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg)
torch.set_num_threads(4);policy,_=policy_from_checkpoint(ckpt_dict=ckpt);model=policy.policy;numerics();nets=model.ema.averaged_model
ob={k:torch.tensor(x,device=model.device,dtype=torch.float32) for k,x in augment({k:panel[k] for k in KEYS},v).items()}
with torch.no_grad():cond=TU.time_distributed({'obs':ob,'goal':None},nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1)
for name in ('common','paired'):
    if not args.train_boundary:z=np.load(prior/(name+'_noise.npz'))
    else:
        noises=[]
        for d in range(8):
            n=torch.randn((len(rows),16,7),generator=torch.Generator().manual_seed(713+10000*d)).numpy()
            if name=='paired':n[::2]=n[1::2]
            noises.append(n)
        z=dict(noise=np.concatenate(noises),panel_index=np.tile(np.arange(len(rows)),8),draw=np.repeat(np.arange(8),len(rows)))
    idx=z['panel_index'];noise=z['noise'];parts=[]
    sch=DDIMScheduler.from_config(model.noise_scheduler.config);sch.set_timesteps(10)
    with torch.no_grad():
        for start in range(0,len(idx),64):
            a=torch.tensor(noise[start:start+64],device=model.device);c=cond[idx[start:start+64]]
            for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=c),t,a).prev_sample
            parts.append(a.cpu().numpy())
    np.savez_compressed(OUT/v/(prefix+name+'_offline.npz'),chunks=np.concatenate(parts),panel_index=idx,draw=z['draw'])
    print(v,name,len(idx),flush=True)
# Native sampler parity with same GPU-generated noise.
small={k:a[:4] for k,a in ob.items()};torch.manual_seed(919)
with torch.no_grad():native=model._get_action_trajectory(small)
torch.manual_seed(919);a=torch.randn((4,16,7),device=model.device)
with torch.no_grad():
    for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=cond[:4]),t,a).prev_sample
error=float(abs(a[:,1:3]-native).max());assert error<1e-6
(OUT/v/(prefix+'offline_verification.json')).write_text(json.dumps(dict(native_sampler_max_error=error,original_panel=not args.train_boundary,original_common_and_paired_noise=not args.train_boundary,train_boundary=args.train_boundary,ddim_steps=10),indent=2))
