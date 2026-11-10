"""Bounded, predeclared BC composition pilot. No online training labels."""
from pathlib import Path
import os, sys, json, time, random, math, hashlib, argparse, copy
from collections import deque
import numpy as np
import torch
from torch import nn
import h5py
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
import robosuite
from task_extensions.environments import StackFour
from audit import DATA

class StackThree(StackFour):
    cube_count=3

def write(path,value):
    path=Path(path); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)); tmp.replace(path)

def features(o,arm):
    a,b=np.split(np.asarray(o['object']),2,axis=-1); e=np.asarray(o['robot0_eef_pos'])
    if arm=='relative': xyz=np.concatenate([a-e,b-e,a-b],axis=-1)/.1
    else: xyz=(np.concatenate([a,b,e],axis=-1)-np.tile([0,0,.8],3))/.1
    return np.concatenate([xyz,o['robot0_eef_quat'],np.asarray(o['robot0_gripper_qpos'])/.04],axis=-1).astype('float32')

def load_data(arm):
    groups={s:[[],[]] for s in ('train','valid')}
    with h5py.File(DATA,'r') as f:
        train={v.decode() for v in f['mask/train'][:]}
        for name in sorted(f['data'],key=lambda s:int(s.split('_')[-1])):
            d=f['data'][name]; a=d['actions'][:].astype('float32'); n=len(a)
            x=features({k:d['obs'][k][:] for k in ('object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos')},arm)
            hist=np.stack([x[np.maximum(np.arange(n)-1,0)],x],axis=1).reshape(n,30)
            y=a[np.clip(np.arange(n)[:,None]+np.arange(-1,15)[None,:],0,n-1)]
            part=groups['train' if name in train else 'valid'];part[0].append(hist);part[1].append(y)
    return {s:tuple(np.concatenate(v) for v in pair) for s,pair in groups.items()}

class Block(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.LayerNorm(512),nn.Linear(512,512),nn.SiLU(),nn.Linear(512,512))
    def forward(self,x):return (x+self.net(x))/math.sqrt(2)

class Model(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.Linear(30,512),nn.SiLU(),Block(),Block(),Block(),nn.Linear(512,112),nn.Tanh())
    def forward(self,x):return self.net(x).reshape(-1,16,7)

def make_env(count):
    meta=json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())
    kwargs=copy.deepcopy(meta['environment']['env_kwargs'])
    kwargs.update(has_offscreen_renderer=False,use_camera_obs=False,has_renderer=False,horizon=1000,hard_reset=False)
    return robosuite.make('StackTwo' if count==2 else 'StackThree',**kwargs)

def prefix_valid(env,count):
    p=[env.sim.data.body_xpos[i] for i in env.cube_ids[:count]]
    if abs(p[0][2]-(env.table_offset[2]+.02))>.008:return False
    for i in range(count-1):
        if np.linalg.norm(p[i+1][:2]-p[i][:2])>.009 or abs(p[i+1][2]-p[i][2]-.04)>.008:return False
        if not env.check_contact(env.cubes[i],env.cubes[i+1]):return False
    for c in env.cubes[:count]:
        if env._check_grasp(env.robots[0].gripper,c):return False
        # Require no finger contact, stronger than only 'not grasped'.
        if env.check_contact(env.robots[0].gripper,c):return False
        v=env.sim.data.get_joint_qvel(c.joints[0])
        if np.linalg.norm(v[:3])>.03 or np.linalg.norm(v[3:])>.3:return False
    return True

@torch.no_grad()
def evaluate(model,arm,count,seeds,deadline,path):
    env=make_env(count); rows=[]; model.eval()
    try:
        for seed in seeds:
            if time.time()>=deadline:raise TimeoutError('Global deadline')
            np.random.seed(seed);random.seed(seed);obs=env.reset()
            initial=env.sim.get_state().flatten().copy()
            stage=1; history=deque(maxlen=2);queue=deque();first_run=0;tail=0; first_step=None
            max_lift=[False]*count;grasp=[False]*count;start=time.perf_counter()
            for step in range(500 if count==2 else 1000):
                if time.time()>=deadline:raise TimeoutError('Global deadline')
                positions=np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                for i,c in enumerate(env.cubes):
                    max_lift[i] |= bool(positions[i,2]>.88)
                    grasp[i] |= bool(env._check_grasp(env.robots[0].gripper,c))
                local={k:obs[k] for k in ('robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos')}
                local['object']=np.r_[positions[stage-1],positions[stage]]
                x=features(local,arm);history.append(x)
                if len(history)==1:history.append(x.copy())
                if not queue:
                    chunk=model(torch.as_tensor(np.stack(history).reshape(1,30),device='cuda'))[0].cpu().numpy()
                    queue.extend(chunk[1:3])
                obs,_,_,_=env.step(queue.popleft())
                first_run=first_run+1 if prefix_valid(env,2) else 0
                if first_run>=10 and first_step is None:first_step=step+1
                if count==3 and stage==1 and first_run>=10:
                    stage=2;queue.clear();history.clear()
                valid=prefix_valid(env,count)
                tail=tail+1 if valid else 0
                # 0.5 s acquisition plus 2 s continuously stable under policy control.
                if tail>=50:break
            rows.append(dict(seed=seed,success=tail>=50,steps=step+1,first_stack_step=first_step,
                second_skill_started=stage==2,grasp=grasp,lift=max_lift,stable_tail_frames=tail,
                initial_state=initial.tolist(),initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
                seconds=time.perf_counter()-start))
            write(path,dict(count=count,arm=arm,complete=len(rows)==len(seeds),successes=sum(r['success'] for r in rows),n=len(rows),rows=rows))
    finally:env.close()
    model.train()
    return sum(r['success'] for r in rows)/len(rows)

@torch.no_grad()
def val_loss(model,data):
    model.eval();total=0
    for i in range(0,len(data[0]),256):
        x=torch.as_tensor(data[0][i:i+256],device='cuda');y=torch.as_tensor(data[1][i:i+256],device='cuda')
        total+=torch.nn.functional.mse_loss(model(x),y,reduction='sum').item()
    model.train();return total/(len(data[0])*112)

def train(arm,seed,deadline,smoke=False):
    folder=OUT/(f'smoke_{arm}_{seed}' if smoke else f'{arm}_seed{seed}');folder.mkdir(exist_ok=False)
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    rng=np.random.default_rng(seed);data=load_data(arm);x,y=data['train'];model=Model().cuda()
    opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-6)
    total=4 if smoke else 30000; milestones=[4] if smoke else [1000,3000,10000,30000]
    config=dict(arm=arm,seed=seed,updates=total,batch=8,architecture='3 residual blocks, width 512, two frames, 16-action chunk',
        parameters=sum(p.numel() for p in model.parameters()),optimizer='AdamW',lr=1e-4,weight_decay=1e-6,
        schedule='500 update warmup, cosine to 30000',ema=False,loss='MSE all 16x7 actions',executed_slice=[1,3],
        sampling='uniform anchors with replacement; paired RNG across arms',train_frames=len(x),
        dataset_sha256=json.loads((OUT/'dataset_audit.json').read_text())['sha256'],milestones=milestones)
    config['runtime']=dict(torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name(0),python=sys.version)
    write(folder/'config.json',config);start=time.time();evaluation_seconds=0.;records=[];last_losses=[];best=None;best_score=-1
    for update in range(1,total+1):
        if time.time()>=deadline:raise TimeoutError('Global deadline')
        ids=rng.integers(len(x),size=8)
        lr=1e-4*(min(update/500,1) if update<=500 else .5*(1+math.cos(math.pi*(update-500)/29500)))
        for g in opt.param_groups:g['lr']=lr
        pred=model(torch.as_tensor(x[ids],device='cuda'));target=torch.as_tensor(y[ids],device='cuda')
        loss=torch.nn.functional.mse_loss(pred,target)
        if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
        opt.zero_grad(set_to_none=True);loss.backward();opt.step();last_losses.append(loss.item())
        if update%250==0 or update==total:
            write(folder/'status.json',dict(state='TRAINING',update=update,effective_epochs=update*8/len(x),loss=float(np.mean(last_losses[-250:])),elapsed_seconds=time.time()-start))
        if update%1000==0 or update==total:
            state=dict(model=model.state_dict(),optimizer=opt.state_dict(),update=update,config=config,
                numpy_sampler=rng.bit_generator.state,torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),
                python_rng=random.getstate(),numpy_rng=np.random.get_state())
            tmp=folder/'latest.tmp';torch.save(state,tmp);tmp.replace(folder/'latest.pth')
        if update in milestones:
            checkpoint=folder/f'update_{update}.pth';torch.save(state,checkpoint)
            eval_start=time.time()
            # Evaluation may touch global RNGs; preserve training RNG states.
            py_rng=random.getstate();np_rng=np.random.get_state();cpu_rng=torch.get_rng_state();gpu_rng=torch.cuda.get_rng_state_all()
            v=val_loss(model,data['valid']);seeds=list(range(61000,61001 if smoke else 61020))
            score2=evaluate(model,arm,2,seeds,deadline,folder/f'dev2_{update}.json')
            # One unconditional late diagnostic prevents a gate hiding transfer failure.
            score3=None
            if score2>=.8 or update==total:
                score3=evaluate(model,arm,3,seeds if score2>=.8 or smoke else seeds[:5],deadline,folder/f'dev3_{update}.json')
            random.setstate(py_rng);np.random.set_state(np_rng);torch.set_rng_state(cpu_rng);torch.cuda.set_rng_state_all(gpu_rng)
            evaluation_seconds+=time.time()-eval_start
            records.append(dict(update=update,effective_epochs=update*8/len(x),valid_mse=v,dev2=score2,dev3=score3,
                elapsed_seconds=time.time()-start,training_and_checkpoint_seconds=time.time()-start-evaluation_seconds,evaluation_seconds=evaluation_seconds))
            write(folder/'learning_curve.json',records)
            if score3 is not None and score2>=.8 and score3>best_score:best=checkpoint;best_score=score3
            print(json.dumps(dict(arm=arm,seed=seed,**records[-1])),flush=True)
    write(folder/'status.json',dict(state='TRAINING_COMPLETE',update=total,selected=str(best) if best else None,dev3=best_score))
    return dict(arm=arm,seed=seed,folder=str(folder),selected=str(best) if best else None,dev3=best_score)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--deadline',type=float,default=None);args=parser.parse_args()
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    deadline=args.deadline or time.time()+8*3600
    if args.smoke:
        result=train('relative',99,deadline,True);write(OUT/'smoke_result.json',result);return
    results=[]
    try:
        for seed in [1,2,3]:
            for arm in ['raw','relative']:
                write(OUT/'worker_status.json',dict(state='RUNNING',arm=arm,seed=seed,deadline=deadline))
                results.append(train(arm,seed,deadline));write(OUT/'run_index.json',results)
        # Test seeds never influence checkpoint selection or training.
        for r in results:
            if r['selected'] is None:continue
            state=torch.load(r['selected'],map_location='cpu',weights_only=False);model=Model().cuda();model.load_state_dict(state['model'])
            r['test3']=evaluate(model,r['arm'],3,list(range(72000,72100)),deadline,Path(r['folder'])/'test3.json')
            write(OUT/'run_index.json',results)
        write(OUT/'worker_status.json',dict(state='COMPLETED',results=results))
    except TimeoutError:
        write(OUT/'worker_status.json',dict(state='TIME_BUDGET_REACHED',results=results));raise

if __name__=='__main__':main()
