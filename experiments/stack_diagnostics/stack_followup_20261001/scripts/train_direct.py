"""Fixed-budget direct MSE regression, same expert chunks as original diffusion."""
import json,math,time,random
import numpy as np,torch
from direct_common import OUT,DirectChunk,flatten,DATA,SOURCE
from diffusers.training_utils import EMAModel
from balance_common import load_training,digest
assert not (OUT/'model_final.pth').exists();torch.set_num_threads(4);random.seed(1);np.random.seed(1);torch.manual_seed(1);torch.backends.cuda.matmul.allow_tf32=False
model=DirectChunk().cuda();ema=EMAModel(model=model,power=.75);opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-6)
sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda i:i/500 if i<500 else max(0.,.5*(1+math.cos(math.pi*(i-500)/29500))))
ds,ob,a,c,w,refs,events=load_training();x=flatten(ob);assert x.shape==(len(a),30);assert np.max(abs(a))<=1.000001
config=dict(model='8-block residual MLP; width2048; pre-LayerNorm; SiLU; residual / sqrt(2); tanh output',observation_keys=['object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos'],observation_dim_per_frame=15,history_frames=2,input_dim=30,output_dim=112,chunk_length=16,executed_actions=2,executed_slice=[1,3],parameter_count=sum(p.numel() for p in model.parameters()),diffusion_parameter_count=65648903,loss='mean squared error across batch, all 16 time positions and all 7 action components',action_normalization='identity, exactly as diffusion; target range [-1,1]; tanh bounds output',observation_normalization=False,dynamics_features=False,phase_balancing=False,gradient_updates=30000,batch_size=8,seed=1,optimizer=dict(name='AdamW',lr=1e-4,betas=[.9,.999],epsilon=1e-8,weight_decay=1e-6),lr_schedule='cosine,500 warmup,30000 updates',ema_power=.75,gradient_clip=None,training_frames=len(a),train_demos=180,valid_demos=20,dataset_sha256=digest(DATA),diffusion_checkpoint=SOURCE['checkpoint'],diffusion_checkpoint_sha256=digest(SOURCE['checkpoint']),sampling='uniform with replacement; exact historical diffusion sample indices unavailable',rollout_seeds=list(range(46000,46040)),black_image_demos_unchanged=62)
(OUT/'config.json').write_text(json.dumps(config,indent=2));np.savez_compressed(OUT/'training_refs.npz',refs=np.array(refs));idsall=[];losses=[];lrs=[];rng=np.random.default_rng(1);start=time.monotonic()
for i in range(30000):
    ids=rng.integers(len(a),size=8);idsall.append(ids);inputs=torch.tensor(x[ids],device='cuda');target=torch.tensor(a[ids],device='cuda',dtype=torch.float32);opt.zero_grad(set_to_none=True);prediction=model(inputs);loss=torch.nn.functional.mse_loss(prediction,target);assert torch.isfinite(loss);loss.backward();opt.step();ema.step(model);lrs.append(opt.param_groups[0]['lr']);sched.step();losses.append(float(loss.detach()))
    if (i+1)%500==0:
        status=dict(updates=i+1,total=30000,loss_last500=float(np.mean(losses[-500:])),elapsed_seconds=time.monotonic()-start);(OUT/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
torch.save(dict(model=model.state_dict(),ema=ema.averaged_model.state_dict(),optimizer=opt.state_dict(),lr_scheduler=sched.state_dict(),ema_step=ema.optimization_step,config=config),OUT/'model_final.pth');np.savez_compressed(OUT/'training_audit.npz',sample_indices=np.array(idsall),loss=losses,lr=lrs);(OUT/'status.json').write_text(json.dumps(dict(state='COMPLETED',updates=30000,elapsed_seconds=time.monotonic()-start),indent=2))
