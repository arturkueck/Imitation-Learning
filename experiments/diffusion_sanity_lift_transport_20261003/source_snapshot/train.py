"""Historical trainers with normalization alone, finite guards and update audits."""
import argparse, time, random, math, traceback
import numpy as np, torch
from common import *
from replication_common import weight_digest
from diffusers.training_utils import EMAModel
LIVE_AUDIT={}

def finite_optimizer(opt, args, kwargs):
    grads=[p.grad for g in opt.param_groups for p in g['params'] if p.grad is not None]
    assert grads and torch.isfinite(torch.stack(torch._foreach_norm(grads))).all(), 'Nonfinite gradient; stopped BEFORE optimizer.step'

def train_direct(dest, n, seed):
    from balance_common import load_training
    torch.set_num_threads(4); random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.backends.cuda.matmul.allow_tf32=False
    model=DirectChunk().cuda();ema=EMAModel(model=model,power=.75);opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-6)
    opt.register_step_pre_hook(finite_optimizer)
    sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda i:i/500 if i<500 else max(0.,.5*(1+math.cos(math.pi*(i-500)/29500))))
    write(dest/'initialization.json',dict(training_seed=seed,fresh_random_initialization=True,initial_weights_sha256=weight_digest(model)))
    ds,ob,a,c,w,refs,events=load_training();x=flatten(n.observations(ob));a=n.actions(a)
    assert x.shape==(len(a),30) and np.isfinite(x).all() and abs(a).max()<=1.000001
    config=read(dest/'config.json');np.savez_compressed(dest/'training_refs.npz',refs=np.array(refs))
    idsall=[];losses=[];lrs=[];rng=np.random.default_rng(seed);start=time.monotonic()
    LIVE_AUDIT.update(loss=losses,lr=lrs,sample_indices=idsall)
    for i in range(30000):
        ids=rng.integers(len(a),size=8);idsall.append(ids)
        inputs=torch.tensor(x[ids],device='cuda');target=torch.tensor(a[ids],device='cuda',dtype=torch.float32)
        opt.zero_grad(set_to_none=True);pred=model(inputs);loss=torch.nn.functional.mse_loss(pred,target)
        assert torch.isfinite(loss), 'Nonfinite loss; stopped BEFORE optimizer.step'
        loss.backward();opt.step();ema.step(model);lrs.append(opt.param_groups[0]['lr']);sched.step();losses.append(float(loss.detach()))
        if (i+1)%500==0:
            status=dict(updates=i+1,total=30000,loss_last500=float(np.mean(losses[-500:])),elapsed_seconds=time.monotonic()-start)
            write(dest/'status.json',status); print(json.dumps(status),flush=True)
    assert {int(s['step']) for s in opt.state.values()}=={30000} and sched.last_epoch==30000 and ema.optimization_step==30000
    torch.save(dict(model=model.state_dict(),ema=ema.averaged_model.state_dict(),optimizer=opt.state_dict(),lr_scheduler=sched.state_dict(),ema_step=ema.optimization_step,config=config,normalization_stats=read(OUT/'normalization_stats.json')),dest/'model_final.pth')
    np.savez_compressed(dest/'training_audit.npz',sample_indices=np.array(idsall),loss=losses,lr=lrs)
    return dict(optimizer_updates=30000,scheduler_updates=30000,ema_updates=30000,training_seconds=time.monotonic()-start,loss_last500=float(np.mean(losses[-500:])),loss_last=float(losses[-1]))

def train_diffusion(dest,n,seed):
    from scheduler_fix import install
    install()
    from robomimic.config import config_factory
    from robomimic.utils.torch_utils import get_torch_device
    from robomimic.scripts.train import train
    import robomimic.utils.train_utils as TU
    import robomimic.utils.dataset as DU
    from robomimic.algo.diffusion_policy import DiffusionPolicyUNet
    # Freeze train-fit stats for validation too, including cache_mode='all'.
    old_action=DU.SequenceDataset.get_action_normalization_stats
    def get_action(self):
        if self.filter_by_attribute=='train':
            native=old_action(self)
            expected=n.action if n.action_enabled else {'offset':np.zeros((1,7),np.float32),'scale':np.ones((1,7),np.float32)}
            for key in ('scale','offset'):assert np.allclose(native['actions'][key],expected[key],atol=1e-6,rtol=0)
        return {'actions':n.action} if n.action_enabled else {'actions':dict(offset=np.zeros((1,7),np.float32),scale=np.ones((1,7),np.float32))}
    DU.SequenceDataset.get_action_normalization_stats=get_action
    old_obs=DU.SequenceDataset.normalize_obs
    def get_obs(self):
        if self.filter_by_attribute=='train':
            native=old_obs(self)
            for k in KEYS:
                for key in ('offset','scale'):assert np.allclose(native[k][key],n.obs[k][key],atol=1e-6,rtol=0)
        return n.obs
    DU.SequenceDataset.normalize_obs=get_obs
    old_train=DiffusionPolicyUNet.train_on_batch;losses=[];lrs=[];validation=[];start=time.monotonic();model_ref=[];hooks=[]
    sampled=[];valid_sampled=[];active_epoch=[False];old_getitem=DU.SequenceDataset.__getitem__;latest_batch=[];batch_checks={}
    LIVE_AUDIT.update(loss=losses,lr=lrs,validation=validation,sample_indices=sampled,validation_indices=valid_sampled)
    def sampled_getitem(self,index):
        if active_epoch[0]:
            (sampled if self.filter_by_attribute=='train' else valid_sampled).append(int(index))
            latest_batch.append((self,int(index)));latest_batch[:]=latest_batch[-8:]
        return old_getitem(self,index)
    DU.SequenceDataset.__getitem__=sampled_getitem
    def audited_batch(model,batch,epoch,validate=False):
        if not model_ref:
            model_ref.append(model)
            write(dest/'initialization.json',dict(training_seed=seed,fresh_random_initialization=True,initial_weights_sha256=weight_digest(model.nets)))
            hooks.append(model.optimizers['policy'].register_step_pre_hook(finite_optimizer))
        assert all(torch.isfinite(v).all() for v in batch['obs'].values()) and torch.isfinite(batch['actions']).all()
        assert batch['actions'].abs().max()<=1.000001
        split='valid' if validate else 'train'
        if split not in batch_checks:
            import h5py
            errors=[]
            with h5py.File(DATA,'r') as f:
                assert len(latest_batch)==8
                for j,(dataset,index) in enumerate(latest_batch):
                    assert dataset.filter_by_attribute==split
                    name=dataset._index_to_demo_id[index];frame=index-dataset._demo_id_to_start_indices[name];d=f['data'][name];length=len(d['actions'])
                    history_indices=np.clip([frame-1,frame],0,length-1)
                    raw_ob={k:d['obs/'+k][:][history_indices] for k in KEYS};expected_ob=n.observations(raw_ob)
                    for k in KEYS:errors.append(float(abs(expected_ob[k]-batch['obs'][k][j].cpu().numpy()).max()))
                    raw_a=d['actions'][:][np.clip(np.arange(frame-1,frame+15),0,length-1)]
                    errors.append(float(abs(n.actions(raw_a)-batch['actions'][j].cpu().numpy()).max()))
            assert max(errors)<1e-6,'Training/validation transform differs from frozen normalizer'
            batch_checks[split]=max(errors)
            write(dest/'training_transform_checks.json',batch_checks)
        info=old_train(model,batch,epoch,validate=validate);loss=float(info['losses']['l2_loss'])
        assert np.isfinite(loss), 'Nonfinite diffusion loss'
        if validate:validation.append([epoch,loss])
        else:losses.append(loss);lrs.append(model.optimizers['policy'].param_groups[0]['lr'])
        return info
    DiffusionPolicyUNet.train_on_batch=audited_batch
    old_mse=torch.nn.functional.mse_loss
    def checked_mse(*a,**kw):
        loss=old_mse(*a,**kw);assert torch.isfinite(loss),'Nonfinite diffusion loss BEFORE backward';return loss
    torch.nn.functional.mse_loss=checked_mse
    old_epoch=TU.run_epoch
    def epoch(model,*a,**kw):
        active_epoch[0]=True
        try:result=old_epoch(model,*a,**kw)
        finally:active_epoch[0]=False
        updates={int(v['step']) for v in model.optimizers['policy'].state.values()};assert len(updates)==1
        assert next(iter(updates))==len(losses)==model.lr_schedulers['policy'].last_epoch==model.ema.optimization_step
        write(dest/'status.json',dict(updates=len(losses),total=30000,loss_last500=float(np.mean(losses[-500:])),elapsed_seconds=time.monotonic()-start))
        return result
    TU.run_epoch=epoch
    config=read(dest/'config.json');cfg=config_factory(config['algo_name'],dic=config);cfg.lock()
    train(cfg,device=get_torch_device(try_to_use_cuda=True),resume=False)
    model=model_ref[0];assert len(losses)==30000 and len(validation)==6000
    assert len(sampled)==240000 and len(valid_sampled)==48000
    np.savez_compressed(dest/'training_audit.npz',loss=losses,lr=lrs,validation=validation,sample_indices=np.asarray(sampled).reshape(30000,8),validation_indices=np.asarray(valid_sampled).reshape(6000,8))
    write(dest/'normalization_training_verified.json',dict(train_stats_match_native=True,validation_uses_train_stats=True,finite_guards_before_every_optimizer_update=True,actual_batch_transform_max_error=batch_checks))
    return dict(optimizer_updates=30000,scheduler_updates=model.lr_schedulers['policy'].last_epoch,ema_updates=model.ema.optimization_step,training_seconds=time.monotonic()-start,loss_last500=float(np.mean(losses[-500:])),loss_last=float(losses[-1]),validation_batches=len(validation))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=VARIANTS);p.add_argument('kind',choices=['direct','diffusion']);p.add_argument('seed',type=int);args=p.parse_args()
    dest=folder(args.variant,args.kind,args.seed);assert not (dest/'training_complete.json').exists() and not (dest/'initialization.json').exists()
    start=time.monotonic()
    try:
        result=(train_direct if args.kind=='direct' else train_diffusion)(dest,Normalizer(args.variant),args.seed)
        write(dest/'training_complete.json',dict(variant=args.variant,kind=args.kind,seed=args.seed,total_process_seconds=time.monotonic()-start,**result))
    except Exception:
        if LIVE_AUDIT:np.savez_compressed(dest/'training_audit_partial.npz',**{k:np.asarray(v) for k,v in LIVE_AUDIT.items()})
        write(dest/'aborted.json',dict(stage='training',cause=traceback.format_exc(),elapsed_seconds=time.monotonic()-start,recorded_completed_losses=len(LIVE_AUDIT.get('loss',[])),partial_audit='training_audit_partial.npz' if LIVE_AUDIT else None));raise
