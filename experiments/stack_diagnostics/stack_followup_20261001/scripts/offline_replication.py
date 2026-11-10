"""Repeat the unchanged validation panel, identical noises for every trained model."""
import argparse,json
import numpy as np,torch
from replication_common import ROOT,folder,checkpoint,OUT
from direct_common import DirectChunk,flatten,KEYS
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
from robomimic.utils import tensor_utils as TU
from diffusers import DDIMScheduler
p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('seed',type=int);args=p.parse_args();dest=folder(args.kind,args.seed);dest.mkdir(parents=True,exist_ok=True);prior=ROOT/'experiments/stack_diagnostics/stack_switch_20261001';panel=np.load(prior/'panel.npz');torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
if args.kind=='direct':
    ck=torch.load(checkpoint('direct',args.seed),map_location='cpu',weights_only=False);model=DirectChunk().cuda().eval();model.load_state_dict(ck['ema']);x=flatten({k:panel[k] for k in KEYS});parts=[]
    with torch.no_grad():
        for i in range(0,len(x),128):parts.append(model(torch.tensor(x[i:i+128],device='cuda')).cpu().numpy())
    np.savez_compressed(dest/'offline_predictions.npz',chunks=np.concatenate(parts));native_error=None
else:
    ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',args.seed));c=json.loads(ck['config']);c['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(c);policy,_=policy_from_checkpoint(ckpt_dict=ck);model=policy.policy;nets=model.ema.averaged_model;device=model.device;obs={k:torch.tensor(panel[k],device=device,dtype=torch.float32) for k in KEYS}
    with torch.no_grad():cond=TU.time_distributed({'obs':obs,'goal':None},nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1)
    for name in ('common','paired'):
        noise=np.load(prior/(name+'_noise.npz'));ids=noise['panel_index'];chunks=[];sch=DDIMScheduler.from_config(model.noise_scheduler.config);sch.set_timesteps(10)
        with torch.no_grad():
            for start in range(0,len(ids),64):
                a=torch.tensor(noise['noise'][start:start+64],device=device);co=cond[ids[start:start+64]]
                for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=co),t,a).prev_sample
                chunks.append(a.cpu().numpy())
        np.savez_compressed(dest/(name+'_offline.npz'),chunks=np.concatenate(chunks),panel_index=ids,draw=noise['draw'])
    torch.manual_seed(919)
    with torch.no_grad():native=model._get_action_trajectory({k:v[:4] for k,v in obs.items()})
    torch.manual_seed(919);a=torch.randn((4,16,7),device=device)
    with torch.no_grad():
        for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=cond[:4]),t,a).prev_sample
    native_error=float(abs(native-a[:,1:3]).max());assert native_error<1e-6
(dest/'offline_verification.json').write_text(json.dumps(dict(original_validation_panel=True,common_sampling_noise_across_training_seeds=True,ddim_steps=10 if args.kind=='diffusion' else None,native_sampler_max_error=native_error),indent=2))
