"""64 paired draws per observation at every DDIM inference length."""
import argparse, time, gc
import numpy as np, torch
from common import *
from robomimic.utils.file_utils import load_dict_from_checkpoint, policy_from_checkpoint
from robomimic.utils import tensor_utils as TU
from diffusers import DDIMScheduler

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,required=True);p.add_argument('--batch',type=int,default=128);args=p.parse_args()
    numerics(); start=time.monotonic()
    noise_path=OUT/'noise64.npy'
    if not noise_path.exists():
        noise=np.random.default_rng(20261001).standard_normal((len(META),64,16,7)).astype(np.float32)
        old=np.load(PRIOR/'common_noise.npz');m=old['draw']<8
        noise[old['panel_index'][m],old['draw'][m]]=old['noise'][m]
        np.save(noise_path,noise)
    noise=np.load(noise_path); ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',args.seed));cfg=json.loads(ck['config']);cfg['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(cfg)
    policy,_=policy_from_checkpoint(ckpt_dict=ck);model=policy.policy;nets=model.ema.averaged_model;device=model.device
    ob={k:torch.tensor(PANEL[k],device=device,dtype=torch.float32) for k in KEYS}
    with torch.inference_mode():cond=TU.time_distributed({'obs':ob,'goal':None},nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1)
    audit=[]
    for steps in (10,5,20,50):
        path=OUT/f'diffusion_seed{args.seed}_ddim{steps}.npz'
        if path.exists() and np.load(path)['chunks'].shape[1]>=64:print('REUSE',path.name,flush=True);continue
        draws=64
        out=np.empty((len(META),draws,16,7),np.float32)
        old=existing_diffusion(args.seed,steps)
        sch=DDIMScheduler.from_config(model.noise_scheduler.config);sch.set_timesteps(steps)
        ids=np.repeat(np.arange(len(META)),draws);ds=np.tile(np.arange(draws),len(META))
        # Recompute first 8 draws to independently audit prior artifacts, then reuse where equal.
        t0=time.monotonic()
        with torch.inference_mode():
            for i in range(0,len(ids),args.batch):
                ii=ids[i:i+args.batch];dd=ds[i:i+args.batch];a=torch.tensor(noise[ii,dd],device=device);co=cond[ii]
                for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=co),t,a).prev_sample
                out[ii,dd]=a.cpu().numpy()
                if i % (args.batch*40)==0:print(f'seed={args.seed} DDIM={steps} draws={draws} {i}/{len(ids)} elapsed={time.monotonic()-t0:.1f}s',flush=True)
        err=float(abs(out[:,:8]-old).max()) if old is not None else None
        np.savez_compressed(path,chunks=out,draws=draws,steps=steps)
        audit.append(dict(seed=args.seed,ddim_steps=steps,draws=draws,seconds=time.monotonic()-t0,max_error_existing=err,timesteps=sch.timesteps.cpu().tolist(),scheduler=dict(sch.config)))
        print('COMPLETE',json.dumps(audit[-1]),flush=True)
    # Native batch-1 sampler parity at each inference length, using native CUDA noise.
    parity=[]
    with torch.inference_mode():
        for steps in (5,10,20,50):
            model.algo_config.unlock();model.algo_config.ddim.num_inference_timesteps=steps;model.algo_config.lock()
            torch.manual_seed(919);native=model._get_action_trajectory({k:v[:1] for k,v in ob.items()})
            torch.manual_seed(919);a=torch.randn((1,16,7),device=device);sch=DDIMScheduler.from_config(model.noise_scheduler.config);sch.set_timesteps(steps)
            for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=cond[:1]),t,a).prev_sample
            e=float(abs(native-a[:,1:3]).max());assert e<1e-6;parity.append(dict(steps=steps,max_error=e))
    dump(f'offline_audit_seed{args.seed}.json',dict(runs=audit,native_parity=parity,seconds=time.monotonic()-start))

if __name__=='__main__':main()
