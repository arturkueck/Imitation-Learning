"""Time-bounded three-seed training, periodic rollouts, resumable snapshots."""
import argparse,time,random,json,math
import numpy as np
import torch
from method import OUT,PhaseNet,offline,evaluate,write

def restore_rng(ck,rng):
    rng.bit_generator.state=ck['sampler_rng'];torch.set_rng_state(ck['torch_rng']);torch.cuda.set_rng_state_all(ck['cuda_rng']);random.setstate(ck['python_rng']);np.random.set_state(ck['numpy_rng'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);args=p.parse_args();plan=json.load(open(args.plan))
    folder=OUT/plan['name'];folder.mkdir(exist_ok=False);write(folder/'plan.json',plan)
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    data=np.load(OUT/'training_arrays.npz');train=tuple(data['train_'+k] for k in ['x','a','p','y']);valid=tuple(data['valid_'+k] for k in ['x','a','p','y'])
    x,a,ph,y=train;ids=[np.flatnonzero(ph==i) for i in range(7)]
    posweight=np.array([min(50.,max(1.,(1-y[j]).sum()/max(y[j].sum(),1))) for j in ids],dtype='float32')
    write(folder/'conditions.json',dict(batch=64,sampling='uniform phase then uniform frame within phase, with replacement',lr=plan['lr'],
        optimizer='AdamW weight_decay1e-6',loss='MSE four active actions + lambda * BCE phase completion0..5',completion_lambda=plan['completion_lambda'],
        completion_positive_weights=posweight.tolist(),threshold=plan['threshold'],phase_labels='reconstructed original expert',
        epoch_definition='sampled frames / 27322; balanced sampling is not an ordinary epoch',test_seeds_used=False))
    states={};rngs={};updates={};models={};optimizers={};train_seconds={};histories={};best_scores={}
    for seed in plan['seeds']:
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        model=PhaseNet(plan.get('width',128)).cuda();opt=torch.optim.AdamW(model.parameters(),lr=plan['lr'],weight_decay=1e-6);rng=np.random.default_rng(seed)
        parent=plan.get('parents',{}).get(str(seed));updates[seed]=0;train_seconds[seed]=0.;histories[seed]=[]
        if parent:
            ck=torch.load(parent,map_location='cpu',weights_only=False);model.load_state_dict(ck['model'])
            if plan.get('restore_optimizer',True):opt.load_state_dict(ck['optimizer'])
            updates[seed]=ck['update'];restore_rng(ck,rng)
        models[seed]=model;optimizers[seed]=opt;rngs[seed]=rng
        best_scores[seed]=(-1,-1)
        seedpath=folder/f'seed{seed}';seedpath.mkdir();write(seedpath/'initialization.json',dict(seed=seed,parent=parent,initial_update=updates[seed]))
    start=time.time();round_id=0;deadline=plan['train_deadline']
    while time.time()<deadline:
        round_id+=1
        for seed in plan['seeds']:
            if time.time()>=deadline:break
            model=models[seed];opt=optimizers[seed];rng=rngs[seed];losses=[];tick=time.time();seedpath=folder/f'seed{seed}'
            for step in range(plan['updates_per_round']):
                if time.time()>=deadline:break
                phases=rng.integers(7,size=64);batch=np.array([rng.choice(ids[i]) for i in phases])
                tx=torch.tensor(x[batch],device='cuda');ta=torch.tensor(a[batch],device='cuda');tp=torch.tensor(ph[batch],device='cuda');ty=torch.tensor(y[batch],device='cuda')
                pred,z=model(tx,tp);actor=(pred-ta).square().mean();mask=tp<6
                bce=torch.nn.functional.binary_cross_entropy_with_logits(z[mask],ty[mask],pos_weight=torch.tensor(posweight[ph[batch]][mask.cpu().numpy()],device='cuda')) if mask.any() else z.sum()*0
                loss=actor+plan['completion_lambda']*bce
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
                for g in opt.param_groups:g['lr']=plan['lr']*min((updates[seed]+1)/500,1)
                opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);opt.step();updates[seed]+=1
                losses.append([float(actor.detach()),float(bce.detach())])
                if (step+1)%500==0:
                    write(folder/'status.json',dict(state='TRAINING',round=round_id,seed=seed,updates=updates,elapsed_seconds=time.time()-start,deadline=deadline))
            train_seconds[seed]+=time.time()-tick
            ck=dict(model=model.state_dict(),optimizer=opt.state_dict(),update=updates[seed],sampler_rng=rng.bit_generator.state,
                torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),python_rng=random.getstate(),numpy_rng=np.random.get_state(),plan=plan)
            tmp=seedpath/'latest.tmp';torch.save(ck,tmp);tmp.replace(seedpath/'latest.pth')
            if round_id==1 or round_id%5==0:torch.save(ck,seedpath/f'round{round_id}_u{updates[seed]}.pth')
            if time.time()>=deadline:break
            metric=dict(round=round_id,update=updates[seed],sample_pass_equivalent=updates[seed]*64/len(x),
                train_seconds=train_seconds[seed],loss=np.mean(losses,axis=0).tolist() if losses else None,offline=offline(model,valid))
            # Always probe composition; prior two-only gates hid transfer information.
            seeds=list(range(63000,63000+plan['dev_episodes']))
            for count in [2,3]:
                if time.time()>=deadline:break
                metric[f'dev{count}']=evaluate(model,count,seeds,seedpath/f'dev{count}_round{round_id}.json',deadline,plan['threshold'],plan.get('retreat',False))
            histories[seed].append(metric);write(seedpath/'learning_curve.json',histories[seed]);print(json.dumps(dict(seed=seed,**metric)),flush=True)
            if metric.get('dev3',{}).get('complete') and metric.get('dev2',{}).get('complete'):
                score=(metric['dev3']['successes']/metric['dev3']['n'],metric['dev2']['successes']/metric['dev2']['n'])
                if score>best_scores[seed]:
                    best_scores[seed]=score;tmp=seedpath/'best.tmp';torch.save(ck,tmp);tmp.replace(seedpath/'best.pth')
                    write(seedpath/'best.json',dict(update=updates[seed],round=round_id,dev3=score[0],dev2=score[1],selection='lexicographic dev3, then dev2, earlier checkpoint on tie'))
        if plan.get('max_rounds') and round_id>=plan['max_rounds']:break
    write(folder/'status.json',dict(state='TRAINING_COMPLETE',updates=updates,rounds=round_id,elapsed_seconds=time.time()-start,train_seconds=train_seconds,checkpoints={str(s):str(folder/f'seed{s}/latest.pth') for s in plan['seeds']}))

if __name__=='__main__':main()
