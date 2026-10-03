"""Exact-operation CUDA graph replay of the existing DDIM sampler (no math changes)."""
import time,types
import numpy as np,torch
from common import *
from robomimic.utils import tensor_utils as TU
from diffusers import DDIMScheduler

class GraphSampler:
    def __init__(self,model):
        self.model=model;self.nets=model.ema.averaged_model;self.device=model.device
        self.steps=model.algo_config.ddim.num_inference_timesteps
        self.scheduler=DDIMScheduler.from_config(model.noise_scheduler.config);self.scheduler.set_timesteps(self.steps)
        self.static_noise=torch.zeros((1,16,7),device=self.device);self.static_cond=torch.zeros((1,30),device=self.device)
        # Native UNet copies each scalar CPU timestep to CUDA. Pre-copy the exact same int64 values.
        self.gpu_steps=[t.to(self.device) for t in self.scheduler.timesteps]
        def denoise():
            a=self.static_noise
            for t,gpu_t in zip(self.scheduler.timesteps,self.gpu_steps):
                eps=self.nets['policy']['noise_pred_net'](sample=a,timestep=gpu_t,global_cond=self.static_cond)
                a=self.scheduler.step(eps,t,a).prev_sample
            return a
        with torch.no_grad():
            # Warm the exact native shapes before capture; neither weights nor RNG are changed.
            stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
            with torch.cuda.stream(stream):
                for _ in range(3):denoise()
            torch.cuda.current_stream().wait_stream(stream);torch.cuda.synchronize()
            self.graph=torch.cuda.CUDAGraph()
            with torch.cuda.graph(self.graph):self.output=denoise()
    def infer(self,obs_dict,goal_dict=None):
        assert all(v.shape[0]==1 for v in obs_dict.values())
        co=TU.time_distributed({'obs':obs_dict,'goal':goal_dict},self.nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1)
        return self.infer_cond(co)
    def infer_cond(self,co,noise=None):
        if noise is None:noise=torch.randn((1,16,7),device=self.device)
        self.static_noise.copy_(noise);self.static_cond.copy_(co);self.graph.replay()
        h=self.model.algo_config.horizon.action_horizon
        return self.output[:,1:1+h].clone()

def install(model,seed):
    native=model._get_action_trajectory;graph=GraphSampler(model);records=[]
    ids=[0,9,10,20,100,209,210,419]
    with torch.no_grad():
        for index in ids:
            ob={k:torch.tensor(PANEL[k][index:index+1],device=model.device,dtype=torch.float32) for k in KEYS}
            torch.manual_seed(919+index);a=native(ob);state_native=torch.cuda.get_rng_state().clone()
            torch.manual_seed(919+index);b=graph.infer(ob);state_graph=torch.cuda.get_rng_state().clone()
            error=float(abs(a-b).max());rng_equal=bool(torch.equal(state_native,state_graph));records.append(dict(panel_index=index,max_abs_error=error,rng_state_equal=rng_equal));assert error==0 and rng_equal,(index,error,rng_equal)
        ob={k:torch.tensor(PANEL[k][:1],device=model.device,dtype=torch.float32) for k in KEYS}
        timings={}
        for label,fn in [('native',native),('graph',graph.infer)]:
            torch.cuda.synchronize();start=time.monotonic()
            for _ in range(10):fn(ob)
            torch.cuda.synchronize();timings[label]=(time.monotonic()-start)/10
    dump(f'graph_sampler_seed{seed}_steps{graph.steps}_h{model.algo_config.horizon.action_horizon}.json',dict(seed=seed,steps=graph.steps,parity=records,seconds_per_chunk=timings,operation='same native DDIM operations; scalar timestep CUDA copies precomputed; initial torch.randn outside capture; cloned action slice; no model, sampler, precision or RNG changes'))
    model._get_action_trajectory=graph.infer
    graph.native=native;graph.live_checks=[];graph.calls=0
    def checked(obs_dict,goal_dict=None):
        graph.calls+=1;check=graph.calls<=16 or graph.calls%100==0
        if check:state_before=torch.cuda.get_rng_state().clone()
        b=graph.infer(obs_dict,goal_dict)
        if check:
            state_after=torch.cuda.get_rng_state().clone();torch.cuda.set_rng_state(state_before);a=native(obs_dict,goal_dict);state_native=torch.cuda.get_rng_state().clone();torch.cuda.set_rng_state(state_after)
            error=float(abs(a-b).max());equal=bool(torch.equal(state_after,state_native));graph.live_checks.append(dict(chunk_call=graph.calls,max_abs_error=error,rng_state_equal=equal));assert error==0 and equal,(graph.calls,error,equal)
        return b
    model._get_action_trajectory=checked
    return graph

if __name__=='__main__':
    import argparse
    from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
    p=argparse.ArgumentParser();p.add_argument('--steps',type=int,default=10);args=p.parse_args();numerics();ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',1));c=json.loads(ck['config']);c['algo']['horizon']['action_horizon']=2;c['algo']['ddim']['num_inference_timesteps']=args.steps;ck['config']=json.dumps(c);policy,_=policy_from_checkpoint(ckpt_dict=ck);install(policy.policy,1);print('Exact graph/RNG parity passed.',flush=True)
