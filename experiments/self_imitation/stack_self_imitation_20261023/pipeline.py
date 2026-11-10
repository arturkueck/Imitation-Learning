"""Bounded collection, pre-action dataset audit and paired A/B/C pilot."""
from pathlib import Path
import sys,json,time,random,hashlib,copy,os
from collections import defaultdict
import numpy as np
import torch
OUT=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'experiments/self_imitation/stack_phased_8h_20261023'
sys.path.insert(0,str(BASE))
from method import PhaseNet,Policy,vector,write,digest,offline,evaluate,old,ACTIVE,DATA

def bound(deadline):
    if time.time()>=deadline or (OUT/'STOP').exists():raise TimeoutError('Session deadline or STOP')

def observation(env,obs):
    return np.r_[np.array([env.sim.data.body_xpos[i] for i in env.cube_ids]).flatten(),obs['robot0_eef_pos'],obs['robot0_eef_quat'],obs['robot0_gripper_qpos']]

@torch.no_grad()
def collect_episode(env,model,count,seed,deadline):
    bound(deadline);np.random.seed(seed);random.seed(seed);obs=env.reset();initial=env.sim.get_state().flatten().copy()
    policy=Policy(model);stage=1;pair=0;tail=0;retreat=False;retreat_done=False;records=defaultdict(list);first=None
    for t in range(500 if count==2 else 1000):
        bound(deadline);positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        phase=policy.phase;steps=policy.steps
        anchor=(positions[stage if phase<4 else stage-1].copy() if policy.anchor is None else policy.anchor.copy())
        x=vector(obs,anchor,steps);pre=observation(env,obs);state=env.sim.get_state().flatten().copy()
        action,actual_phase,prob=policy.action(obs,positions[stage-1],positions[stage]);done=int(policy.phase!=phase)
        assert actual_phase==phase
        next_obs,_,_,_=env.step(action);post=observation(env,next_obs)
        v2=old.prefix_valid(env,2);valid=old.prefix_valid(env,count)
        velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes])
        contacts=[env.check_contact(env.cubes[i],env.cubes[i+1]) for i in range(count-1)]
        fingers=[env.check_contact(env.robots[0].gripper,c) for c in env.cubes]
        row=dict(x=x,a=action,p=phase,y=done,phase_steps=steps,anchor=anchor,stage=stage,retreat=retreat,
            pre_obs=pre,post_obs=post,pre_state=state,prob=prob,valid2=v2,valid=valid,velocities=velocities,contacts=contacts,fingers=fingers)
        pair=pair+1 if v2 else 0;event=0
        if first is None and pair>=10:first=t+1
        if retreat and policy.phase>0:retreat=False;retreat_done=True;stage=2;policy.reset();event=2
        elif count==3 and stage==1 and policy.phase==6 and pair>=10:
            if not retreat_done:policy.reset();policy.anchor=env.sim.data.body_xpos[env.cube_ids[1]].copy();retreat=True;event=1
            else:stage=2;policy.reset();event=2
        row['controller_event']=event
        for k,v in row.items():records[k].append(v)
        obs=next_obs;tail=tail+1 if valid else 0
        if tail>=50:break
    arrays={k:np.asarray(v) for k,v in records.items()};arrays['initial']=initial
    return arrays,dict(seed=seed,count=count,success=tail>=50,frames=t+1,first_stack_step=first,initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest())

def audit_episode(a,model,count):
    n=len(a['x']);assert a['x'].shape==(n,10) and a['a'].shape==(n,7)
    assert all(np.isfinite(v).all() for v in a.values())
    if n>1:assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
    posend=count*3;e=posend
    recompute=np.c_[(a['pre_obs'][:,e:e+3]-a['anchor'])/.1,a['pre_obs'][:,e+3:e+7],a['pre_obs'][:,e+7:e+9]/.04,np.minimum(a['phase_steps'],100)/20]
    assert np.allclose(recompute,a['x'],rtol=1e-6,atol=1e-6)
    ids=np.unique(np.linspace(0,n-1,min(n,20),dtype=int))
    # Match the actual single-frame inference path: batched CUDA GEMMs can
    # differ by several float32 ulps, particularly near zero actions.
    with torch.no_grad():
        outputs=[model(torch.tensor(a['x'][j:j+1],device='cuda'),torch.tensor(a['p'][j:j+1],device='cuda')) for j in ids]
        pred=torch.cat([v[0] for v in outputs]);z=torch.cat([v[1] for v in outputs])
    assert np.array_equal(pred.cpu().numpy(),a['a'][ids][:,ACTIVE])
    assert np.array_equal(a['y'][ids],((z.sigmoid().cpu().numpy()>=.8)&(a['p'][ids]<6)).astype(int))
    assert not a['a'][:,3:6].any()
    tail=0;maximum=0
    for ok in a['valid']:tail=tail+1 if ok else 0;maximum=max(maximum,tail)
    return maximum>=50

def collection(teachers,deadline,smoke=False,resume=False):
    allrows=[]
    for count,base in [(2,121000),(3,120000)]:
        folder=OUT/('smoke_data' if smoke else 'datasets')/f'stack{count}'
        start=0
        if folder.exists() and resume and not smoke:
            previous=json.loads((folder/'manifest.json').read_text())['rows']
            assert [r['seed'] for r in previous]==list(range(base,base+len(previous)))
            for r in previous:
                with np.load(r['path']) as data:a={k:data[k].copy() for k in data.files}
                assert audit_episode(a,teachers[r['teacher']-1],count)==r['success']
            allrows.extend(previous);start=len(previous)
        else:folder.mkdir(parents=True,exist_ok=False)
        env=old.make_env(count)
        xml=env.model.get_xml();xmlfile=folder/'model.xml'
        if xmlfile.exists():assert xmlfile.read_text(encoding='utf-8')==xml
        else:xmlfile.write_text(xml,encoding='utf-8')
        try:
            for i in range(start,2 if smoke else 400):
                seed=(63004+i if smoke else base+i);teacher=i%3
                a,r=collect_episode(env,teachers[teacher],count,seed,deadline)
                assert audit_episode(a,teachers[teacher],count)==r['success']
                r.update(teacher=teacher+1,split='train' if i<300 else 'valid',path=str(folder/f'{seed}.npz'))
                np.savez_compressed(r['path'],**a);allrows.append(r)
                write(folder/'manifest.json',dict(complete=(i+1==(2 if smoke else 400)),rows=[x for x in allrows if x['count']==count]))
                write(OUT/('smoke_status.json' if smoke else 'status.json'),dict(state='COLLECTING',count=count,attempt=i+1,successes=sum(x['success'] for x in allrows if x['count']==count)))
        finally:env.close()
    if not smoke:
        write(OUT/'dataset_manifest.json',dict(complete=True,rows=allrows))
        for count in [2,3]:
            train_hashes={r['initial_sha256'] for r in allrows if r['count']==count and r['split']=='train'}
            valid_hashes={r['initial_sha256'] for r in allrows if r['count']==count and r['split']=='valid'}
            assert not train_hashes&valid_hashes,'Identical state across splits'
            for split,minimum in [('train',30),('valid',10)]:
                assert sum(r['success'] and r['count']==count and r['split']==split for r in allrows)>=minimum,('Data gate failed',count,split)
    return allrows

class EpisodePool:
    def __init__(self,rows,count,split='train'):
        self.episodes=[];self.phase_episodes={p:[] for p in range(7)}
        for r in rows:
            if not(r['success'] and r['count']==count and r['split']==split):continue
            with np.load(r['path']) as a:d={k:a[k].copy() for k in ['x','a','p','y']}
            idx=len(self.episodes);self.episodes.append(d)
            for p in range(7):
                ids=np.flatnonzero(d['p']==p)
                if len(ids):self.phase_episodes[p].append((idx,ids))
        assert self.episodes and all(self.phase_episodes.values())
    def sample(self,rng,n):
        out=[]
        for _ in range(n):
            p=int(rng.integers(7));groups=self.phase_episodes[p];ep,ids=groups[int(rng.integers(len(groups)))];j=int(rng.choice(ids));d=self.episodes[ep];out.append((d['x'][j],d['a'][j][ACTIVE],p))
        return np.stack([x[0] for x in out]),np.stack([x[1] for x in out]).astype('float32'),np.array([x[2] for x in out])

def train(arm,seed,parent,rows,deadline,steps=30000,smoke=False):
    folder=OUT/('smoke_train' if smoke else 'training')/f'{arm}_seed{seed}';folder.mkdir(parents=True,exist_ok=False)
    data=np.load(BASE/'training_arrays.npz');x,a,p,y=[data['train_'+k] for k in ['x','a','p','y']]
    valid=tuple(data['valid_'+k] for k in ['x','a','p','y']);groups=[np.flatnonzero(p==k) for k in range(7)]
    pw=torch.tensor([min(50.,max(1.,(1-y[j]).sum()/max(y[j].sum(),1))) for j in groups],device='cuda')
    model=PhaseNet().cuda();model.load_state_dict(torch.load(parent,map_location='cpu',weights_only=False)['model'])
    opt=torch.optim.AdamW(model.parameters(),lr=3e-5,weight_decay=1e-6)
    rng=np.random.default_rng(seed);extra_rng=np.random.default_rng(seed+10000)
    pool=None if arm=='A' else EpisodePool(rows,2 if arm=='B' else 3)
    init_hash=digest(parent);curve=[];start=time.time();best=(-1,-1)
    own_before=None
    new_valid=None
    if pool:
        bx,ba,bp=pool.sample(np.random.default_rng(123),256)
        with torch.no_grad():own_before=float((model(torch.tensor(bx,device='cuda'),torch.tensor(bp,device='cuda'))[0]-torch.tensor(ba,device='cuda')).square().mean())
        if not smoke:new_valid=EpisodePool(rows,2 if arm=='B' else 3,'valid').sample(np.random.default_rng(321),512)
    write(folder/'config.json',dict(arm=arm,seed=seed,parent=str(parent),parent_sha256=init_hash,updates=steps,batch=64,lr=3e-5,new_fraction=0 if arm=='A' else .25,
        new_action_mse_before_training=own_before,completion_loss='original expert examples only',optimizer='fresh identical AdamW per arm',sampling='original phase balanced; new phase then episode then frame',retreat=True))
    for u in range(1,steps+1):
        bound(deadline);ph=rng.integers(7,size=64);ids=np.array([rng.choice(groups[k]) for k in ph]);n=64 if arm=='A' else 48
        bx=x[ids[:n]];ba=a[ids[:n]];bp=p[ids[:n]]
        if pool:
            xx,aa,pp=pool.sample(extra_rng,16);bx=np.r_[bx,xx];ba=np.r_[ba,aa];bp=np.r_[bp,pp]
        pred,z=model(torch.tensor(bx,device='cuda'),torch.tensor(bp,device='cuda'));actor=(pred-torch.tensor(ba,device='cuda')).square().mean()
        mask=torch.tensor(p[ids[:n]]<6,device='cuda');labels=torch.tensor(y[ids[:n]],device='cuda')
        bce=torch.nn.functional.binary_cross_entropy_with_logits(z[:n][mask],labels[mask],pos_weight=pw[torch.tensor(p[ids[:n]],device='cuda')][mask])
        loss=actor+.1*bce;assert torch.isfinite(loss)
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);opt.step()
        if u%1000==0 or u==steps:
            ck=dict(model=model.state_dict(),optimizer=opt.state_dict(),update=u,parent=str(parent),original_rng=rng.bit_generator.state,extra_rng=extra_rng.bit_generator.state)
            tmp=folder/'latest.tmp';torch.save(ck,tmp);tmp.replace(folder/'latest.pth');write(folder/'status.json',dict(state='TRAINING',update=u,elapsed_seconds=time.time()-start))
        if u in [3000,10000,30000] or u==steps:
            metric=dict(update=u,actor_loss=float(actor.detach()),completion_loss=float(bce.detach()),offline_original_valid=offline(model,valid))
            if new_valid:
                vx,va,vp=new_valid
                with torch.no_grad():metric['new_valid_actor_mse']=float((model(torch.tensor(vx,device='cuda'),torch.tensor(vp,device='cuda'))[0]-torch.tensor(va,device='cuda')).square().mean())
            if not smoke:
                for count in [2,3]:metric[f'dev{count}']=evaluate(model,count,list(range(122000,122050)),folder/f'dev{count}_{u}.json',deadline,.8,True)
                if all(metric[f'dev{k}']['complete'] for k in [2,3]):
                    score=(metric['dev3']['successes'],metric['dev2']['successes'])
                    if score>best:best=score;torch.save(ck,folder/'best.pth');write(folder/'best.json',dict(update=u,dev3=score[0],dev2=score[1]))
            curve.append(metric);write(folder/'learning_curve.json',curve)
    assert digest(parent)==init_hash
    write(folder/'status.json',dict(state='TRAINING_COMPLETE',updates=steps,elapsed_seconds=time.time()-start))

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--resume-collection',action='store_true');args=parser.parse_args()
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    plan=json.loads((OUT/'protocol.json').read_text());deadline=time.time()+600 if args.smoke else plan['deadline']
    teachers=[]
    for info in plan['teachers']:
        assert digest(info['path'])==info['sha256'];m=PhaseNet().cuda().eval();m.load_state_dict(torch.load(info['path'],map_location='cpu',weights_only=False)['model']);teachers.append(m)
    original_hash=digest(DATA)
    if args.resume_collection:assert not (OUT/'training').exists(),'Collection resume forbidden after training starts'
    rows=collection(teachers,deadline,args.smoke,args.resume_collection)
    if args.smoke:
        # Sample successful real episodes, then verify a genuine mixed optimizer update.
        good=[r for r in rows if r['success']]
        for arm in ['A','B','C']:
            if arm!='A' and not any(r['count']==(2 if arm=='B' else 3) for r in good):continue
            train(arm,99,plan['teachers'][0]['path'],rows,deadline,steps=5,smoke=True)
        write(OUT/'preflight.json',dict(state='PASSED',episodes=len(rows),successes=len(good),pre_action_alignment=True,teacher_action_recomputed=True));return
    baseline=OUT/'teacher_baseline';baseline.mkdir()
    for i,m in enumerate(teachers):
        for count in [2,3]:
            write(OUT/'status.json',dict(state='TEACHER_BASELINE',teacher=i+1,count=count))
            result=evaluate(m,count,list(range(122000,122050)),baseline/f'teacher{i+1}_stack{count}.json',deadline,.8,True);assert result['complete']
    for seed in [1,2,3]:
        for arm in ['A','B','C']:
            write(OUT/'status.json',dict(state='TRAINING',arm=arm,seed=seed));train(arm,seed,plan['teachers'][seed-1]['path'],rows,deadline)
    # Freeze all development-selected models before any final test is observed.
    import shutil
    final=OUT/'final_test';final.mkdir();selected={}
    for seed in [1,2,3]:
        for arm in ['A','B','C']:
            name=f'{arm}_seed{seed}';src=OUT/'training'/name/'best.pth';dst=final/(name+'.pth');shutil.copy2(src,dst);selected[name]=dict(path=str(dst),sha256=digest(dst))
    write(final/'selection.json',selected)
    for name,info in selected.items():
        bound(deadline);m=PhaseNet().cuda().eval();m.load_state_dict(torch.load(info['path'],map_location='cpu',weights_only=False)['model'])
        for count,seeds in [(3,list(range(125000,125100))),(2,list(range(126000,126050)))]:
            write(OUT/'status.json',dict(state='FINAL_EVALUATION',model=name,count=count))
            result=evaluate(m,count,seeds,final/f'{name}_stack{count}.json',deadline,.8,True);assert result['complete']
    assert digest(DATA)==original_hash
    write(OUT/'status.json',dict(state='COMPLETED',original_dataset_unchanged=True))

if __name__=='__main__':main()
