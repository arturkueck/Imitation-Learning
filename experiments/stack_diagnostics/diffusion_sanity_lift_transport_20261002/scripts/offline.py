"""Original expert boundary panel/noises, predictions saved in physical action units."""
import argparse,time,traceback
import numpy as np,torch
from common import *
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
from robomimic.utils import tensor_utils as TU
from diffusers import DDIMScheduler

def run(v,kind,seed):
    dest=folder(v,kind,seed);n=Normalizer(v);prior=ROOT/'experiments/stack_diagnostics/stack_switch_20261001';panel=np.load(prior/'panel.npz');torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;start=time.monotonic()
    normalized=n.observations({k:panel[k] for k in KEYS});native_error=None;inverse_error=0.
    if kind=='direct':
        ck=torch.load(checkpoint(v,kind,seed),map_location='cpu',weights_only=False);model=DirectChunk().cuda().eval();model.load_state_dict(ck['ema']);x=flatten(normalized);parts=[]
        with torch.no_grad():
            for i in range(0,len(x),128):parts.append(model(torch.tensor(x[i:i+128],device='cuda')).cpu().numpy())
        chunks=np.concatenate(parts);raw=n.inverse_actions(chunks);n.check_actions(raw)
        np.savez_compressed(dest/'offline_predictions.npz',chunks=raw)
    else:
        ck=load_dict_from_checkpoint(ckpt_path=str(checkpoint(v,kind,seed)));c=json.loads(ck['config']);c['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(c)
        policy,_=policy_from_checkpoint(ckpt_dict=ck);model=policy.policy;nets=model.ema.averaged_model;device=model.device
        obs=policy._prepare_observation({k:panel[k] for k in KEYS},batched_ob=True)
        obs_error=max(float(abs(obs[k].cpu().numpy()-normalized[k]).max()) for k in KEYS)
        assert obs_error<1e-6,'Native offline observation transform differs from frozen formula'
        with torch.no_grad():cond=TU.time_distributed({'obs':obs,'goal':None},nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1)
        for name in ('common','paired'):
            noise=np.load(prior/(name+'_noise.npz'));ids=noise['panel_index'];chunks=[];sch=DDIMScheduler.from_config(model.noise_scheduler.config);sch.set_timesteps(10)
            with torch.no_grad():
                for startidx in range(0,len(ids),64):
                    a=torch.tensor(noise['noise'][startidx:startidx+64],device=device);co=cond[ids[startidx:startidx+64]]
                    for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=co),t,a).prev_sample
                    chunks.append(a.cpu().numpy())
            norm=np.concatenate(chunks);raw=n.inverse_actions(norm);n.check_actions(raw)
            inverse_error=max(inverse_error,float(abs(n.actions(raw)-norm).max()));assert inverse_error<1e-6
            np.savez_compressed(dest/(name+'_offline.npz'),chunks=raw,panel_index=ids,draw=noise['draw'])
        torch.manual_seed(919)
        with torch.no_grad():native=model._get_action_trajectory({k:v[:4] for k,v in obs.items()})
        torch.manual_seed(919);a=torch.randn((4,16,7),device=device)
        with torch.no_grad():
            for t in sch.timesteps:a=sch.step(nets['policy']['noise_pred_net'](sample=a,timestep=t,global_cond=cond[:4]),t,a).prev_sample
        native_error=float(abs(native-a[:,1:3]).max());assert native_error<1e-6
        # Test complete checkpoint wrapper, including observation scaling and inverse actions.
        for i in range(4):
            po={k:panel[k][i] for k in KEYS};policy.start_episode();torch.manual_seed(919+i)
            with torch.no_grad():actual=np.asarray(policy(ob=po)).reshape(7)
            policy.start_episode();torch.manual_seed(919+i)
            with torch.no_grad():norm_action=model._get_action_trajectory({k:obs[k][i:i+1] for k in KEYS})[0,0].cpu().numpy()
            expected=n.inverse_actions(norm_action).reshape(7)
            inverse_error=max(inverse_error,float(abs(expected-actual).max()));assert inverse_error<1e-6
    write(dest/'offline_verification.json',dict(original_validation_panel=True,common_noise_unchanged=True,native_sampler_max_error=native_error,denormalization_max_error=inverse_error,elapsed_seconds=time.monotonic()-start))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=VARIANTS);p.add_argument('kind');p.add_argument('seed',type=int);a=p.parse_args()
    try:run(a.variant,a.kind,a.seed)
    except Exception:
        write(folder(a.variant,a.kind,a.seed)/'aborted.json',dict(stage='offline',cause=traceback.format_exc()));raise
