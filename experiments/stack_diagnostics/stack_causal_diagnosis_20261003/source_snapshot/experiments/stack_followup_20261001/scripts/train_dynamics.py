"""Exactly matched uniform continuations; information representation is the treatment."""
import argparse,json,math,time,random
import numpy as np,torch
from dynamics_common import OUT,augment,numerics,load_training,digest
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
p=argparse.ArgumentParser();p.add_argument('variant',choices=['baseline','dynamics']);v=p.parse_args().variant;folder=OUT/v;folder.mkdir(exist_ok=True);protocol=json.loads((OUT/'protocol.json').read_text());assert not (folder/'model_final.pth').exists()
random.seed(1);np.random.seed(1);torch.manual_seed(1);torch.set_num_threads(4)
ckpt=load_dict_from_checkpoint(ckpt_path=str(OUT/'initial_expanded.pth'));wrapper,ckpt=policy_from_checkpoint(ckpt_dict=ckpt);model=wrapper.policy;model.deserialize(ckpt['model'],load_optimizers=True);model.ema.optimization_step=30000;numerics()
optim=model.optimizers['policy'];assert {int(s['step'].item()) for s in optim.state.values()}=={30000}
for g in optim.param_groups:g['lr']=g['initial_lr']=.0001
def factor(i):return i/500 if i<500 else max(0.,.5*(1+math.cos(math.pi*(i-500)/4500)))
model.lr_schedulers['policy']=torch.optim.lr_scheduler.LambdaLR(optim,factor)
ds,ob,a,c,w,refs,events=load_training();ob=augment(ob,v);cdf=np.cumsum(np.ones(len(a))/len(a));cdf[-1]=1
random.seed(1);np.random.seed(1);torch.manual_seed(1);rng=np.random.default_rng(1);model.set_train();ids_all=[];losses=[];lrs=[];counts=np.zeros(len(a),int);start=time.monotonic()
for update in range(5000):
    ids=np.searchsorted(cdf,rng.random(8),side='right');ids_all.append(ids);np.add.at(counts,ids,1);lr=optim.param_groups[0]['lr'];lrs.append(lr)
    batch=model.process_batch_for_training(dict(obs={k:torch.from_numpy(z[ids]) for k,z in ob.items()},actions=torch.from_numpy(a[ids])))
    info=model.train_on_batch(batch,epoch=301+update//100,validate=False);model.on_gradient_step();loss=float(info['losses']['l2_loss'].item());assert math.isfinite(loss);losses.append(loss)
    if (update+1)%100==0:
        status=dict(state='TRAINING',updates=update+1,total=5000,elapsed_seconds=time.monotonic()-start,last100_loss=float(np.mean(losses[-100:])));(folder/'status.json').write_text(json.dumps(status,indent=2));print(v,json.dumps(status),flush=True)
model.set_eval();ckpt['model']=model.serialize();ckpt['representation']=dict(variant=v,protocol=protocol,feature_key='zz_dynamics');torch.save(ckpt,folder/'model_final.pth');assert {int(s['step'].item()) for s in optim.state.values()}=={35000};assert model.ema.optimization_step==35000
np.savez_compressed(folder/'training_audit.npz',sample_indices=np.array(ids_all),sample_counts=counts,lr=np.array(lrs),loss=np.array(losses))
(folder/'training_audit.json').write_text(json.dumps(dict(variant=v,gradient_updates=5000,samples=40000,sampling='uniform',optimizer_final_step=35000,ema_final_step=35000,source_sha256=protocol['source_sha256'],initial_expanded_sha256=digest(OUT/'initial_expanded.pth'),final_sha256=digest(folder/'model_final.pth'),elapsed_seconds=time.monotonic()-start),indent=2));(folder/'status.json').write_text(json.dumps(dict(state='COMPLETED',updates=5000),indent=2))
