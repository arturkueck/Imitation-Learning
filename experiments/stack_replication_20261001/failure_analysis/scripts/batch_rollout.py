"""Independent native batch-1 graphs on four CUDA streams; isolated episode RNGs.

No UNet batching or sampler changes. Each simulator and random stream remains independent.
"""
import argparse,random,time,gc
from collections import deque
import numpy as np,torch
from common import *
from localise import localise
from graph_sampler import GraphSampler,install
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint
from robustness import Intervention,refresh_observation
import video_views

def main():
    p=argparse.ArgumentParser();p.add_argument('seed',type=int);p.add_argument('--horizon',type=int,default=2);p.add_argument('--steps',type=int,default=10);p.add_argument('--starts',type=int,default=40);p.add_argument('--group',default='replanning');p.add_argument('--workers',type=int,default=4);p.add_argument('--native-reference',action='store_true');args=p.parse_args();numerics()
    assert args.horizon in (1,2,4) and args.steps in (5,10,20,50)
    tag='' if args.group=='replanning' else ('_ddimstudy' if args.group=='ddim' else '_'+args.group);name=f'diffusion_seed{args.seed}_h{args.horizon}_ddim{args.steps}'+tag
    if args.native_reference:name+='_native_reference'
    dest=OUT/'rollouts'/name;dest.mkdir(parents=True,exist_ok=True);rs=json.loads((dest/'results.json').read_text()) if (dest/'results.json').exists() else [];es=json.loads((dest/'events.json').read_text()) if (dest/'events.json').exists() else [];done={r['start_seed'] for r in rs}
    if globals().get('shared_reference') is not None:
        policy,ck=shared_reference
    else:
        ck=load_dict_from_checkpoint(ckpt_path=checkpoint('diffusion',args.seed));cfg=json.loads(ck['config']);cfg['algo']['horizon']['action_horizon']=args.horizon;cfg['algo']['ddim']['num_inference_timesteps']=args.steps;ck['config']=json.dumps(cfg);policy,_=policy_from_checkpoint(ckpt_dict=ck)
    model=policy.policy;native=model._get_action_trajectory
    installed=install(model,args.seed);graphs=[installed]+[GraphSampler(model) for _ in range(args.workers-1)];streams=[torch.cuda.Stream() for _ in graphs];live=[]
    actors=[];t0=time.monotonic()
    for seed in PROTOCOL['fixed_start_seeds'][:args.starts]:
        if seed in done:continue
        env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=False)
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);policy.start_episode();obs=env.reset();obs=env.reset_to(env.get_state());intervention=Intervention(env,'nominal',seed);intervention.apply();obs=refresh_observation(env);assert intervention.initial_state_hash==PROTOCOL['fixed_start_hashes'][str(seed)];video_views.setup_cameras(env)
        noises=[];rngs={};maximum=(540+args.horizon-1)//args.horizon
        for call in range(1,maximum+1):
            check=args.group.startswith('stream_validation') or call<=2 or call%100==0
            if check:before=torch.cuda.get_rng_state().clone()
            noises.append(torch.randn((1,16,7),device=model.device))
            if check:rngs[call]=(before,torch.cuda.get_rng_state().clone())
        actors.append(dict(seed=seed,env=env,obs=obs,queue=deque(),trace=[],observations={k:[] for k in KEYS},measured=None,success=False,complete=False,noises=torch.stack(noises),rngs=rngs,numpy_rng=np.random.get_state(),python_rng=random.getstate(),hash=intervention.initial_state_hash,chunk_calls=0,pinned=torch.empty((1,2,15),dtype=torch.float64,pin_memory=True)))
    torch.cuda.synchronize()
    while any(not a['complete'] for a in actors):
        pending=[]
        with torch.no_grad():
            for actor in actors:
                if actor['complete'] or actor['queue']:continue
                actor['chunk_calls']+=1;rawob={k:np.asarray(actor['obs'][k]) for k in KEYS}
                if args.native_reference:
                    torch.cuda.set_rng_state(actor['rngs'][actor['chunk_calls']][0]);ob=policy._prepare_observation(rawob);sequence=native(ob);pending.append((actor,sequence,None))
                else:
                    j=len(pending)%len(graphs);stream=streams[j];stream.wait_stream(torch.cuda.current_stream())
                    packed=np.concatenate([rawob[k] for k in sorted(model.obs_shapes)],axis=-1)[None]
                    actor['pinned'].numpy()[:]=packed
                    with torch.cuda.stream(stream):
                        co=actor['pinned'].to(model.device,non_blocking=True).float().flatten(1);sequence=graphs[j].infer_cond(co,actor['noises'][actor['chunk_calls']-1])
                    pending.append((actor,sequence,co))
            for stream in streams:stream.synchronize()
            # RNG state operations and native audit calls only after all graphs have completed.
            for actor,sequence,co in pending:
                if not args.native_reference and actor['chunk_calls'] in actor['rngs']:
                    from robomimic.utils import tensor_utils as TU
                    rawob={k:np.asarray(actor['obs'][k]) for k in KEYS};ob=policy._prepare_observation(rawob);native_cond=TU.time_distributed({'obs':ob,'goal':None},graphs[0].nets['policy']['obs_encoder'],inputs_as_kwargs=True).flatten(1);cond_error=float(abs(native_cond-co).max());assert cond_error==0,cond_error;before,after=actor['rngs'][actor['chunk_calls']];torch.cuda.set_rng_state(before);reference=native(ob);rng_equal=bool(torch.equal(after,torch.cuda.get_rng_state()));error=float(abs(reference-sequence).max());assert error==0 and rng_equal,(actor['seed'],actor['chunk_calls'],error);live.append(dict(start_seed=actor['seed'],chunk_call=actor['chunk_calls'],max_abs_error=error,condition_max_abs_error=cond_error,rng_state_equal=rng_equal))
                actor['queue'].extend(sequence[0].cpu().numpy().copy())
        for actor in actors:
            if actor['complete']:continue
            np.random.set_state(actor['numpy_rng']);random.setstate(actor['python_rng']);env=actor['env'];raw=env.base_env;step=len(actor['trace']);po={k:np.asarray(actor['obs'][k]) for k in KEYS}
            for k in KEYS:actor['observations'][k].append(po[k].copy())
            action=actor['queue'].popleft().copy();obs,_,end,_=env.step(action);actor['obs']=obs;actor['numpy_rng']=np.random.get_state();actor['python_rng']=random.getstate();pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids]);held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));eef=np.asarray(obs['robot0_eef_pos']).reshape(-1,3)[-1];fingers=np.asarray(obs['robot0_gripper_qpos']).reshape(-1,2)[-1];ok=bool(env.is_success()['task']);actor['trace'].append(np.r_[step,pos.ravel(),quat.ravel(),eef,fingers,action,action,held,raw.check_contact(*raw.cubes),ok])
            if actor['measured'] is None and (ok or end or step==499):actor['measured']=step+1;actor['success']=ok
            if actor['measured'] is not None and len(actor['trace'])==actor['measured']+40:
                actor['complete']=True;env.base_env.close();t=np.array(actor['trace']);m=actor['measured'];metrics=extra_metrics(t,m);metrics['sustained_success']=bool(actor['success'] and np.all(t[m:,36]>0));f,e=localise(t,m,metrics);r=dict(model='diffusion',training_seed=args.seed,start_seed=actor['seed'],executed_actions=args.horizon,ddim_steps=args.steps,comparison_group=args.group,initial_state_sha256=actor['hash'],measured_steps=m,**(metrics|f))
                if args.horizon==2 and args.steps==10:
                    old=np.load(rollouts('diffusion',args.seed)/f"{actor['seed']}.npz")['trace'];count=min(len(old),len(t));r.update(parity_frames=count,baseline_max_abs_error=float(abs(t[:count]-old[:count]).max()),baseline_action_max_abs_error=float(abs(t[:count,20:27]-old[:count,20:27]).max()),historical_trace_bitwise_equal=bool(np.array_equal(t[:count],old[:count])),first_action_max_abs_error=float(abs(t[0,20:27]-old[0,20:27]).max()))
                np.savez_compressed(dest/f"{actor['seed']}.npz",trace=t,measured=m,**{k:np.array(v) for k,v in actor['observations'].items()});rs.append(r);es.append(dict(start_seed=actor['seed'],**e));rs.sort(key=lambda r:r['start_seed']);es.sort(key=lambda r:r['start_seed']);(dest/'results.json').write_text(json.dumps(rs,indent=2));(dest/'events.json').write_text(json.dumps(es,indent=2));print(f"diffusion/{args.seed} h={args.horizon} steps={args.steps} start={actor['seed']} stack={r['sustained_success']} first_missing={r['first_unfulfilled_task_indicator']} elapsed={time.monotonic()-t0:.1f}s",flush=True)
        if actors and len(actors[0]['trace'])%100==0:print(f"FRAME {len(actors[0]['trace'])} active={sum(not a['complete'] for a in actors)} elapsed={time.monotonic()-t0:.1f}s",flush=True)
    (dest/'graph_live_parity.json').write_text(json.dumps(live,indent=2));(dest/'complete.json').write_text(json.dumps(dict(starts=len(rs),elapsed_seconds=time.monotonic()-t0,streams=args.workers,sampling_batch_size=1,independent_episode_rngs=True,native_reference=args.native_reference)))
    print('COMPLETE',name,len(rs),time.monotonic()-t0,flush=True)

if __name__=='__main__':main()
