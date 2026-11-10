"""Matched continuation: sampling weights are the sole between-arm difference."""
import argparse,json,math,time,random
import numpy as np
import torch
from balance_common import EXP,load_training,digest,KEYS
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint
parser=argparse.ArgumentParser();parser.add_argument('variant',choices=['uniform','balanced']);args=parser.parse_args()
p=json.loads((EXP/'protocol.json').read_text());variant=args.variant;folder=EXP/variant;folder.mkdir(exist_ok=True)
if (folder/'model_final.pth').exists():raise RuntimeError('Refusing to overwrite trained model')
assert digest(p['source_checkpoint'])==p['source_sha256']
random.seed(p['seed']);np.random.seed(p['seed']);torch.manual_seed(p['seed']);torch.set_num_threads(4)
ckpt=load_dict_from_checkpoint(ckpt_path=p['source_checkpoint']);cfg=json.loads(ckpt['config'])
cfg['train']['num_epochs']=50;cfg['experiment']['epoch_every_n_steps']=100
ckpt['config']=json.dumps(cfg);wrapped,ckpt=policy_from_checkpoint(ckpt_dict=ckpt);model=wrapped.policy
model.deserialize(ckpt['model'],load_optimizers=True)
optimizer=model.optimizers['policy'];steps={int(v['step'].item()) for v in optimizer.state.values() if 'step' in v}
assert steps=={30000};assert model.ema is not None;model.ema.optimization_step=30000
# Rebuild only the exhausted LR clock; preserve all AdamW state and both raw/EMA weights.
for group in optimizer.param_groups:group['lr']=.0001;group['initial_lr']=.0001
def factor(i):
    if i<500:return i/500
    return max(0.,.5*(1+math.cos(math.pi*(i-500)/4500)))
scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,factor)
model.lr_schedulers['policy']=scheduler
ds,obs,actions,c,w,refs,events=load_training()
uniform=np.ones(len(c))/len(c);cdf=np.cumsum(w if variant=='balanced' else uniform);cdf[-1]=1
random.seed(1);np.random.seed(1);torch.manual_seed(1);rng=np.random.default_rng(1)
model.set_train();logs=[];lr_values=[];sampled_critical=0;sampled_total=0;sample_counts=np.zeros(len(c),int)
begin=time.monotonic()
initial=dict(raw_weight_sha256=digest(p['source_checkpoint']),optimizer_steps=30000,ema_optimization_step=model.ema.optimization_step,
    raw_vs_source_equal=all(torch.equal(v,ckpt['model']['nets'][k].to(v.device)) for k,v in model.nets.state_dict().items()),
    ema_vs_source_equal=all(torch.equal(v,ckpt['model']['ema'][k].to(v.device)) for k,v in model.ema.averaged_model.state_dict().items()))
assert initial['raw_vs_source_equal'] and initial['ema_vs_source_equal']
for update in range(5000):
    ids=np.searchsorted(cdf,rng.random(8),side='right');sampled_critical+=int(c[ids].sum());sampled_total+=8;np.add.at(sample_counts,ids,1)
    batch=dict(obs={k:torch.from_numpy(obs[k][ids]) for k in KEYS},actions=torch.from_numpy(actions[ids]))
    batch=model.process_batch_for_training(batch);lr=optimizer.param_groups[0]['lr'];lr_values.append(lr)
    info=model.train_on_batch(batch,epoch=301+update//100,validate=False);model.on_gradient_step()
    loss=float(info['losses']['l2_loss'].item());assert math.isfinite(loss)
    logs.append(dict(update=update+1,loss=loss,lr=lr))
    if (update+1)%100==0:
        state=dict(state='TRAINING',variant=variant,updates=update+1,total_updates=5000,
            sampled_critical_fraction=sampled_critical/sampled_total,mean_last100_loss=float(np.mean([r['loss'] for r in logs[-100:]])),elapsed_seconds=time.monotonic()-begin)
        (folder/'status.json').write_text(json.dumps(state,indent=2));print(json.dumps(state),flush=True)
model.set_eval();ckpt['model']=model.serialize();ckpt['continuation']=dict(variant=variant,updates=5000,source_sha256=p['source_sha256'],protocol=p,ema_optimization_step=35000)
torch.save(ckpt,folder/'model_final.pth')
final_steps={int(v['step'].item()) for v in optimizer.state.values() if 'step' in v};assert final_steps=={35000};assert model.ema.optimization_step==35000
np.savez_compressed(folder/'sampling_audit.npz',sample_counts=sample_counts,lr=np.array(lr_values),critical=c)
(folder/'training_log.json').write_text(json.dumps(logs,indent=2))
(folder/'training_audit.json').write_text(json.dumps(dict(initial=initial,final_optimizer_steps=35000,final_ema_step=35000,
    gradient_updates=5000,samples=40000,critical_samples=sampled_critical,sampling_seed=1,noise_seed=1,
    effective_critical_mass=sampled_critical/sampled_total,final_checkpoint_sha256=digest(folder/'model_final.pth'),
    elapsed_seconds=time.monotonic()-begin),indent=2))
(folder/'status.json').write_text(json.dumps(dict(state='COMPLETED',updates=5000),indent=2));print('TRAINING_COMPLETED',flush=True)
