"""Frozen weights, existing diffusers samplers; save full chunks and denoising paths."""
import argparse,json,time
import numpy as np
import torch
from switch_data import OUT
from transport_data import KEYS
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
from robomimic.utils import tensor_utils as TensorUtils
from diffusers import DDIMScheduler,DDPMScheduler
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--paired',action='store_true');args=p.parse_args();v=args.variant;folder=OUT/v;folder.mkdir(exist_ok=True);protocol=json.loads((OUT/'protocol.json').read_text());data=np.load(OUT/'panel.npz');meta=json.loads((OUT/'panel.json').read_text())
ckpt=load_dict_from_checkpoint(ckpt_path=protocol['checkpoints'][v]);cfg=json.loads(ckpt['config']);cfg['algo']['horizon']['action_horizon']=2;ckpt['config']=json.dumps(cfg);torch.set_num_threads(4);policy,_=policy_from_checkpoint(ckpt_dict=ckpt);model=policy.policy;nets=model.ema.averaged_model if model.ema is not None else model.nets
device=model.device;ob={k:torch.tensor(data[k],device=device,dtype=torch.float32) for k in KEYS}
with torch.no_grad():cond=TensorUtils.time_distributed({'obs':ob,'goal':None},nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(start_dim=1)
panel_ids=[];draws=[];noise=[];n=len(meta);boundary=np.array([i for i,r in enumerate(meta) if r['offset'] in (-1,0)])
for draw in range(32):
    ids=np.arange(n) if draw<8 and not args.paired else boundary;g=torch.Generator().manual_seed(713+10000*draw);z=torch.randn((n,16,7),generator=g)
    if args.paired:
        for i in boundary:
            if meta[i]['offset']==-1:z[i]=z[i+1]
    panel_ids.extend(ids);draws.extend([draw]*len(ids));noise.append(z[ids])
panel_ids=np.array(panel_ids);draws=np.array(draws);noise=torch.cat(noise)
np.savez_compressed(OUT/('paired_noise.npz' if args.paired else 'common_noise.npz'),noise=noise.numpy(),panel_index=panel_ids,draw=draws)
configs=[('ddim10',10,0,False),('ddim20',20,0,False),('ddim50',50,0,False),('ddim100',100,0,False),('ddim10_eta1',10,1,False),('ddim100_eta1',100,1,False),('ddpm100',100,0,True)]
if args.paired:configs=[('paired_ddim10',10,0,False),('paired_ddim100',100,0,False)]
for name,steps,eta,ddpm in configs:
    begin=time.monotonic();scheduler=(DDPMScheduler if ddpm else DDIMScheduler).from_config(model.noise_scheduler.config);scheduler.set_timesteps(steps);assert torch.equal(scheduler.betas,model.noise_scheduler.betas)
    chunks=[];paths=[];eps_paths=[];x0_paths=[];path_ids=[]
    for start in range(0,len(noise),64):
        ids=panel_ids[start:start+64];a=noise[start:start+64].to(device);c=cond[ids];g=torch.Generator(device=device).manual_seed(88000+start)
        selected=np.flatnonzero((ids<42)&np.isin(ids,[9,10,30,31])&(draws[start:start+64]<8));path=[];ep=[];x0=[]
        with torch.no_grad():
            for t in scheduler.timesteps:
                eps=nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=c)
                result=scheduler.step(model_output=eps,timestep=t,sample=a,**({'generator':g} if ddpm else {'eta':eta,'generator':g}));a=result.prev_sample
                if len(selected):path.append(a[selected].cpu().numpy());ep.append(eps[selected].cpu().numpy());x0.append(result.pred_original_sample[selected].cpu().numpy())
        chunks.append(a.cpu().numpy())
        if len(selected):paths.append(np.stack(path,axis=1));eps_paths.append(np.stack(ep,axis=1));x0_paths.append(np.stack(x0,axis=1));path_ids.extend(start+selected)
    np.savez_compressed(folder/(name+'.npz'),chunks=np.concatenate(chunks),panel_index=panel_ids,draw=draws,timesteps=scheduler.timesteps.numpy(),path_sample_index=np.array(path_ids),paths=np.concatenate(paths),epsilon_paths=np.concatenate(eps_paths),x0_paths=np.concatenate(x0_paths))
    (folder/(name+'_scheduler.json')).write_text(json.dumps(dict(scheduler=dict(scheduler.config),eta=eta,inference_steps=steps,elapsed_seconds=time.monotonic()-begin),indent=2));print(v,name,time.monotonic()-begin,flush=True)
# Verify diagnostic DDIM loop equals the native implementation with identical GPU noise.
small={k:val[:4] for k,val in ob.items()};torch.manual_seed(919)
with torch.no_grad():native=model._get_action_trajectory(small)
torch.manual_seed(919);a=torch.randn((4,16,7),device=device);scheduler=DDIMScheduler.from_config(model.noise_scheduler.config);scheduler.set_timesteps(10)
with torch.no_grad():
    for t in scheduler.timesteps:
        eps=nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=cond[:4]);a=scheduler.step(eps,t,a).prev_sample
error=float(torch.max(abs(a[:,1:3]-native)).item());assert error<1e-6
if args.paired:
    (folder/'paired_verification.json').write_text(json.dumps(dict(native_ddim_max_error=error,training=False,weights_changed=False,initial_noise_same_before_after=True),indent=2));raise SystemExit()
# Forward-noised expert chunks: inspect denoiser independently of long sampler paths.
gt=torch.tensor(data['expected'],device=device,dtype=torch.float32);torch.manual_seed(441);eps_true=torch.randn_like(gt);decoded=[];errors=[]
for t in (0,10,30,50,70,90,99):
    xt=model.noise_scheduler.add_noise(gt,eps_true,torch.full((n,),t,device=device,dtype=torch.long));parts=[];errs=[]
    with torch.no_grad():
        for start in range(0,n,64):
            ep=nets['policy']['noise_pred_net'](sample=xt[start:start+64],timestep=t,global_cond=cond[start:start+64]);alpha=model.noise_scheduler.alphas_cumprod[t].to(device);clean=(xt[start:start+64]-(1-alpha).sqrt()*ep)/alpha.sqrt();parts.append(clean.clamp(-1,1).cpu().numpy());errs.append(((ep-eps_true[start:start+64])**2).cpu().numpy())
    decoded.append(np.concatenate(parts));errors.append(np.concatenate(errs))
np.savez_compressed(folder/'forward_denoiser.npz',timesteps=np.array([0,10,30,50,70,90,99]),decoded=np.array(decoded),epsilon_squared_error=np.array(errors))
(folder/'verification.json').write_text(json.dumps(dict(native_ddim_max_error=error,training=False,weights_changed=False,beta_schedules_identical=True),indent=2))
