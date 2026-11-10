"""Bounded setup CLI: prepare, warmup, train, smoke. Long runs require opt-in."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import random
import shutil
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'runtime/numba_cache'))
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
sys.path.insert(0,str(ROOT/'experiments/self_imitation/retreat_gate_20261104'))
import compare as controller
from compare import native
import numpy as np
import torch
from core import Learner,returns,sample,concat
from transition_pilot import dump,sha

ARRAYS=ROOT/'experiments/self_imitation/stack_phased_8h_20261023/training_arrays.npz'
KEYS=('state','next_state','x','next_x','phase','next_phase','action','reward','terminal','return')


def stop(out,deadline):
    if time.time()>=deadline or (out/'STOP').exists():raise TimeoutError('Fixed deadline or STOP; no automatic resume')


def parent(seed):
    p=ROOT/f'experiments/self_imitation/stack_self_imitation_20261023/final_test/C_seed{seed}.pth'
    return dict(seed=seed,path=str(p),sha256=sha(p))


def features(env,seq,obs,frame,horizon):
    positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    policy=seq.policy
    anchor=positions[seq.stage if policy.phase<4 else seq.stage-1].copy() if policy.anchor is None else policy.anchor.copy()
    x=native.historical.vector(obs,anchor,policy.steps)
    full=native.historical.observation(env,obs)
    runtime=np.r_[np.eye(7)[policy.phase],np.eye(2)[seq.stage-1],anchor,
        policy.steps/100,seq.pair/10,float(seq.retreat),seq.gate.run/3,
        seq.retreat_actions/200,max(0,horizon-frame)/horizon,float(policy.anchor is None)]
    state=np.r_[env.sim.get_state().flatten(),full,runtime].astype('float32')
    return state,x,policy.phase


class Behavior(torch.nn.Module):
    def __init__(self,model,std,seed):
        super().__init__();self.model=model;self.std=np.array(std);self.rng=np.random.default_rng(seed)
    def forward(self,x,phase):
        action,done=self.model(x,phase)
        if self.std.any():
            noise=torch.as_tensor(self.rng.normal(size=tuple(action.shape))*self.std,device=action.device,dtype=action.dtype)
            action=(action+noise).clamp(-1,1)
        return action,done


@torch.no_grad()
def episode(model,seed,cfg,out,deadline,noise=None):
    env=native.historical.make_env(3)
    try:
        np.random.seed(seed);random.seed(seed);env.reset();env.sim.forward()
        obs=env._get_observations(force_update=True)
        initial=env.sim.get_state().flatten().copy()
        model=Behavior(model,noise or [0,0,0,0],seed+177)
        seq=controller.GuardedSequencer(model,3,controller.Clearance(env))
        records=[];tail=0;success=False
        for frame in range(cfg['finite_task_horizon']):
            stop(out,deadline)
            state,x,p=features(env,seq,obs,frame,cfg['finite_task_horizon'])
            positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            action,actual,_=seq.policy.action(obs,positions[seq.stage-1],positions[seq.stage]);assert actual==p
            env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
            fingers=np.array([native.finger_contact(env,c) for c in env.cubes])
            valid=np.array([native.historical.old.prefix_valid(env,k) and not fingers[:k].any() for k in (2,3)])
            seq.advance(valid[seq.stage-1],env.sim.data.body_xpos[env.cube_ids[seq.stage]])
            tail=tail+1 if valid[-1] else 0;success=tail>=50
            terminal=success or seq.timed_out or frame+1==cfg['finite_task_horizon']
            ns,nx,np_=features(env,seq,obs,frame+1,cfg['finite_task_horizon'])
            records.append((state,ns,x,nx,p,np_,action[[0,1,2,6]],float(success),float(terminal)))
            if terminal:break
        arrays={k:np.asarray([r[i] for r in records],dtype='int64' if k in ('phase','next_phase') else 'float32')
                for i,k in enumerate(KEYS[:-1])}
        arrays['return']=returns(arrays['reward'],arrays['terminal'],cfg['gamma'])
        assert np.array_equal(arrays['next_state'][:-1],arrays['state'][1:])
        assert np.array_equal(arrays['next_x'][:-1],arrays['x'][1:])
        assert all(np.isfinite(a).all() for a in arrays.values())
        assert arrays['terminal'][-1]==1 and arrays['terminal'][:-1].sum()==0
        return arrays,dict(seed=seed,success=bool(success),frames=len(records),
            controller_timeout=bool(seq.timed_out),initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
            termination='success' if success else 'controller_failure' if seq.timed_out else 'finite_task_horizon',
            external_truncation=False,state_dim=arrays['state'].shape[1])
    finally:env.close()


def seal(out,cfg,config_path):
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'config.json',cfg)
    files=[Path(__file__),HERE/'core.py',Path(controller.__file__),Path(native.__file__),
           Path(native.historical.__file__),Path(sys.modules['method'].__file__)]
    snap=out/'source_snapshot';snap.mkdir()
    hashes={}
    for i,p in enumerate(files):
        shutil.copy2(p,snap/f'{i:02d}_{p.name}');hashes[str(p)]=sha(p)
    dump(out/'provenance.json',dict(source_hashes=hashes,config_sha256=sha(config_path),
        parent_checkpoints=[parent(s) for s in cfg['seeds']],original_arrays_sha256=sha(ARRAYS),
        software=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__),
        data_contract='Current simulator/controller features only; outcomes used solely for labels; no old endtest rollout files'))


def store_episode(folder,arrays,row,split):
    folder.mkdir(parents=True,exist_ok=True);p=folder/f"{row['seed']}.npz"
    assert not p.exists();np.savez_compressed(p,**arrays)
    row.update(path=str(p.resolve()),sha256=sha(p),split=split)
    return row


def load_data(folder):
    m=json.loads((folder/'manifest.json').read_text());assert m['complete']
    train=[];valid=[];families={}
    for row in m['rows']:
        assert row['split'] in ('train','valid') and not row.get('external_truncation',True)
        assert families.setdefault(row['initial_sha256'],row['split'])==row['split'],'Train/valid family leakage'
        assert sha(row['path'])==row['sha256']
        with np.load(row['path'],allow_pickle=False) as f:a={k:f[k].copy() for k in KEYS}
        assert all(np.isfinite(v).all() for v in a.values())
        (train if row['split']=='train' else valid).append(a)
    return concat(train),concat(valid),m


def original_bc():
    with np.load(ARRAYS,allow_pickle=False) as f:
        return dict(x=f['train_x'].copy(),phase=f['train_p'].copy(),action=f['train_a'].copy())


def bc_batch(data,rng,n):
    ids=rng.integers(len(data['x']),size=n)
    return {k:v[ids] for k,v in data.items()}


def init_learner(seed,data,cfg):
    model=native.historical.load(parent(seed)['path'])
    return Learner(model,data['state'].mean(0),data['state'].std(0),cfg,seed)


def prepare(out,cfg,deadline):
    rows=[];models=[native.historical.load(parent(s)['path']) for s in cfg['seeds']]
    c=cfg['collection']
    for split,count,base in (('train',c['train_episodes'],c['train_seed_start']),('valid',c['valid_episodes'],c['valid_seed_start'])):
        for i in range(count):
            dump(out/'status.json',dict(state='COLLECTING',split=split,episode=i+1,total=count,pid=os.getpid(),updated_unix=time.time()))
            model_index=i%len(models);a,r=episode(models[model_index],base+i,cfg,out,deadline)
            r['teacher']=parent(cfg['seeds'][model_index])
            rows.append(store_episode(out/split,a,r,split))
            dump(out/'manifest.json',dict(complete=len(rows)==c['train_episodes']+c['valid_episodes'],rows=rows,
                config_sha256=sha(out/'config.json'),controller_sha256=sha(controller.__file__),
                predetermined_attempts=True,technical_only=False,ready_for_training=False))
    train,valid,m=load_data(out)
    successes=sum(r['success'] for r in rows if r['split']=='train')
    assert successes>=20 and c['train_episodes']-successes>=5,'Insufficient success/failure diversity; no retry until success'
    dump(out/'data_audit.json',dict(train_episodes=c['train_episodes'],valid_episodes=c['valid_episodes'],
        train_frames=len(train['state']),valid_frames=len(valid['state']),state_dim=train['state'].shape[1],
        initial_families_disjoint=True,train_successes=successes,train_failures=c['train_episodes']-successes,
        normalization='Training frames only',reward=cfg['reward']))
    m['ready_for_training']=True;m['data_audit_sha256']=sha(out/'data_audit.json')
    dump(out/'manifest.json',m)


def warmup(out,cfg,data_path,deadline,steps=None,technical=False):
    data,valid,m=load_data(data_path)
    assert (technical and m.get('technical_only')) or (m.get('ready_for_training') and not m.get('technical_only')),'Data gates not passed'
    if not technical:assert sha(data_path/'data_audit.json')==m['data_audit_sha256']
    assert m['controller_sha256']==sha(controller.__file__)
    assert json.loads((data_path/'config.json').read_text())==cfg
    scores={}
    for seed in cfg['seeds']:
        learner=init_learner(seed,data,cfg);folder=out/f'seed{seed}';folder.mkdir()
        learner.save(folder/'random.pth',dict(initialization='random'))
        before={k:v.clone() for k,v in learner.actor.state_dict().items()}
        rng=np.random.default_rng(seed);curve=[]
        for update in range(1,(steps or cfg['warmup_updates'])+1):
            stop(out,deadline);loss=learner.warm(sample(data,rng,cfg['batch_size']))
            if update==1 or update%100==0 or update==(steps or cfg['warmup_updates']):
                curve.append(dict(update=update,loss=loss));dump(folder/'curve.json',curve)
                dump(out/'status.json',dict(state='CRITIC_WARMUP',seed=seed,step=update,loss=loss,pid=os.getpid(),updated_unix=time.time()))
        assert all(torch.equal(before[k],learner.actor.state_dict()[k]) for k in before)
        score=learner.validate(valid)
        score['constant_train_mean_mse']=float(np.mean((valid['return']-data['return'].mean())**2))
        score['beats_constant']=score['return_mse']<=score['constant_train_mean_mse']
        score['behavior_return_only']=True
        learner.save(folder/'warm.pth',dict(validation=score,actor_unchanged=True))
        scores[str(seed)]=score
    dump(out/'validation.json',scores)
    dump(out/'data_reference.json',dict(path=str(data_path.resolve()),manifest_sha256=sha(data_path/'manifest.json')))


def restore(seed,data,cfg,path):
    learner=init_learner(seed,data,cfg);ck=torch.load(path,map_location='cuda',weights_only=False)
    assert ck['config']==cfg
    for name in ('actor','reference','critic','target_actor','target_critic'):getattr(learner,name).load_state_dict(ck[name])
    learner.actor_opt.load_state_dict(ck['actor_optimizer']);learner.critic_opt.load_state_dict(ck['critic_optimizer'])
    learner.warm_updates=ck['warm_updates'];learner.generator.set_state(ck['sampler_generator'].cpu())
    return learner


def train(out,cfg,data_path,warm_path,deadline,technical=False):
    data,valid,manifest=load_data(data_path)
    assert (technical and manifest.get('technical_only')) or (manifest.get('ready_for_training') and not manifest.get('technical_only'))
    assert json.loads((data_path/'config.json').read_text())==cfg
    ref=json.loads((warm_path/'data_reference.json').read_text())
    assert ref['manifest_sha256']==sha(data_path/'manifest.json')
    validation=json.loads((warm_path/'validation.json').read_text())
    assert all(s['finite'] and (technical or s['beats_constant']) for s in validation.values()),'Critic failed held-out behavior-return gate'
    originals=original_bc();members={};history=[];evaluations={}
    for seed in cfg['seeds']:
        for arm,ac in cfg['arms'].items():
            kind='random' if ac['critic']=='random' else 'warm'
            learner=restore(seed,data,cfg,warm_path/f'seed{seed}/{kind}.pth')
            name=f'{arm}_seed{seed}';folder=out/name;folder.mkdir()
            members[name]=dict(learner=learner,online=[],arm=arm,seed=seed,folder=folder,interactions=0)
    source_families={r['initial_sha256'] for r in manifest['rows']}
    for round_ in range(cfg['online']['rounds']+1):
        if round_:
            for name,m in members.items():
                learner=m['learner'];r_cfg=cfg['online'];policy=learner.policy()
                for index in range(r_cfg['episodes_per_round']):
                    dump(out/'status.json',dict(state='ONLINE_COLLECTION',model=name,round=round_,episode=index+1,
                        total=r_cfg['episodes_per_round'],pid=os.getpid(),updated_unix=time.time()))
                    # Same fresh source families/noise stream across arms; each arm keeps its own replay.
                    seed=r_cfg['seed_start']+(round_-1)*r_cfg['episodes_per_round']+index
                    a,r=episode(policy,seed,cfg,out,deadline,r_cfg['exploration_std'])
                    assert r['initial_sha256'] not in source_families
                    store_episode(m['folder']/f'online_round{round_}',a,r,'online')
                    m['online'].append(a);m['interactions']+=len(a['state'])
                online=concat(m['online']);rng=np.random.default_rng([m['seed'],round_])
                for update in range(r_cfg['updates_per_round']):
                    stop(out,deadline);n=cfg['batch_size'];nd=int(n*cfg['replay_demo_fraction'])
                    batch=concat([sample(data,rng,nd),sample(online,rng,n-nd)])
                    bc=bc_batch(originals,rng,n)
                    metrics=learner.update(batch,bc,cfg['arms'][m['arm']]['bc_coefficient'])
                    # Log completed updates, including delayed actor updates.
                    # Zero-based 0,100,... captured only odd critic-only steps.
                    if update==0 or (update+1)%100==0 or update+1==r_cfg['updates_per_round']:
                        history.append(dict(model=name,round=round_,update=learner.updates,interactions=m['interactions'],**metrics))
                        dump(out/'status.json',dict(state='ONLINE_TRAINING',model=name,round=round_,step=learner.updates,
                            loss=metrics['critic_loss'],pid=os.getpid(),updated_unix=time.time()))
                learner.save(m['folder']/f'round{round_}.pth',dict(interactions=m['interactions']))
                dump(out/'history.json',history)
                dump(out/'status.json',dict(state='ONLINE_TRAINING',model=name,round=round_,step=learner.updates,
                    interactions=m['interactions'],pid=os.getpid(),updated_unix=time.time()))
        if round_ in cfg['evaluation']['rounds']:
            for name,m in members.items():
                results=[]
                for index in range(cfg['evaluation']['development_episodes']):
                    dump(out/'status.json',dict(state='DEVELOPMENT_EVALUATION',model=name,round=round_,episode=index+1,
                        total=cfg['evaluation']['development_episodes'],pid=os.getpid(),updated_unix=time.time()))
                    seed=cfg['evaluation']['development_seed_start']+index
                    a,r=episode(m['learner'].policy(),seed,cfg,out,deadline)
                    assert r['initial_sha256'] not in source_families
                    results.append(r)
                evaluations[f'{name}:round{round_}']=dict(successes=sum(r['success'] for r in results),attempts=len(results),
                    interactions=m['interactions'],critic_updates=m['learner'].updates,
                    offline_warmup_updates=m['learner'].warm_updates,rows=results)
                dump(out/'development.json',evaluations)
    frozen={}
    for name,m in members.items():
        path=m['folder']/f"round{cfg['online']['rounds']}.pth"
        frozen[name]=dict(path=str(path.resolve()),sha256=sha(path),fixed_last_round=True)
        expected=torch.load(parent(m['seed'])['path'],map_location=m['learner'].device,weights_only=False)['model']
        assert all(torch.equal(v,m['learner'].reference.state_dict()[k]) for k,v in expected.items()),'Completion reference drift'
    dump(out/'frozen_final.json',frozen)
    # Reserved final seeds are intentionally never evaluated by this setup command.


def smoke(out,cfg,deadline):
    model=native.historical.load(parent(1)['path']);rows=[]
    for split,seed in zip(('train','valid'),cfg['technical_seeds'][:2]):
        a,r=episode(model,seed,cfg,out,deadline)
        rows.append(store_episode(out/'technical_data',a,r,split))
    dump(out/'manifest.json',dict(complete=True,rows=rows,technical_only=True))
    data,valid,_=load_data(out)
    assert rows[0]['initial_sha256']!=rows[1]['initial_sha256']
    learner=init_learner(1,data,cfg);before=copy.deepcopy(learner.actor.state_dict())
    rng=np.random.default_rng(1)
    for _ in range(5):learner.warm(sample(data,rng,32))
    assert all(torch.equal(before[k],learner.actor.state_dict()[k]) for k in before)
    warm=copy.deepcopy(learner.critic.state_dict());original=original_bc();checks={}
    initial_hash=None
    for arm,ac in cfg['arms'].items():
        agent=init_learner(1,data,cfg)
        if ac['critic']=='warm':agent.critic.load_state_dict(warm);agent.target_critic.load_state_dict(warm)
        reference=copy.deepcopy(agent.reference.state_dict());metrics=[]
        for _ in range(6):metrics.append(agent.update(sample(data,rng,32),bc_batch(original,rng,32),ac['bc_coefficient']))
        assert any(not torch.equal(before[k],agent.actor.state_dict()[k]) for k in before),'Actor was not updated through critic'
        assert all(torch.equal(reference[k],agent.reference.state_dict()[k]) for k in reference)
        a,r=episode(agent.policy(),cfg['technical_seeds'][2],cfg,out,deadline)
        if initial_hash is None:initial_hash=r['initial_sha256']
        assert initial_hash==r['initial_sha256']
        store_episode(out/f'technical_{arm}',a,r,'technical_online')
        checks[arm]=dict(critic_updates=agent.updates,actor_updates=sum(m['actor_updated'] for m in metrics),
            bc_coefficient=ac['bc_coefficient'],finite_losses=True,completion_reference_unchanged=True,
            real_rollout_completed=True,success=r['success'])
    # Exercise the production data-loader, checkpoint restore, online replay mix,
    # delayed actor updates and evaluation in a bounded one-round workflow.
    mini=copy.deepcopy(cfg);mini['seeds']=[1];mini['batch_size']=32;mini['warmup_updates']=5
    mini['online'].update(rounds=1,episodes_per_round=1,updates_per_round=4,seed_start=cfg['technical_seeds'][3])
    mini['evaluation'].update(development_episodes=1,rounds=[0,1],development_seed_start=cfg['technical_seeds'][4])
    data_dir=out/'workflow_data';data_dir.mkdir();dump(data_dir/'config.json',mini)
    dump(data_dir/'manifest.json',dict(complete=True,technical_only=True,ready_for_training=False,rows=rows,
        controller_sha256=sha(controller.__file__)))
    warm_dir=out/'workflow_warm';warm_dir.mkdir()
    warmup(warm_dir,mini,data_dir,deadline,technical=True)
    train_dir=out/'workflow_train';train_dir.mkdir()
    train(train_dir,mini,data_dir,warm_dir,deadline,technical=True)
    assert len(json.loads((train_dir/'frozen_final.json').read_text()))==3
    logged=json.loads((train_dir/'history.json').read_text())
    for arm in mini['arms']:
        actor_rows=[r for r in logged if r['model']==f'{arm}_seed1' and r['actor_updated']]
        assert actor_rows,'Delayed actor updates must appear in the production history'
        assert all(np.isfinite(r[k]) for r in actor_rows for k in ('actor_loss','rl_loss','bc_loss'))
    assert any(r.get('bc_loss',0)>0 for r in logged if r['model']=='C_seed1')
    dump(out/'preflight.json',dict(passed=True,technical_only=True,scientific_training_started=False,
        warmup_keeps_actor_fixed=True,train_valid_families_disjoint=True,paired_online_starts=True,
        normalization_training_only=True,arms=checks,state_dim=data['state'].shape[1],
        warmup_validation=learner.validate(valid),
        bounded_workflow=dict(passed=True,seeds=1,arms=3,rounds=1,online_episodes_per_arm=1,
            critic_updates_per_arm=4,development_episodes_per_arm=2,checkpoint_restore_tested=True,
            total_critic_optimizer_updates=40,total_actor_optimizer_updates=15,
            actor_rl_bc_history_verified=True),
        note='Technical updates and a one-round mini workflow only; all technical families excluded from scientific runs; no efficacy claim'))


def main(args):
    cfg=json.loads(args.config.read_text());out=args.output.resolve()
    assert set(cfg['arms'])=={'A','B','C'}
    if args.command!='smoke':
        assert args.execute,'Explicit --execute is required for a long collection/training command'
        if args.command in ('warmup','train'):assert cfg['training_enabled'],'Enable a separate, reviewed config before scientific training'
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    seal(out,cfg,args.config);start=time.time();deadline=start+(600 if args.command=='smoke' else cfg['wall_clock_cap_seconds'])
    dump(out/'status.json',dict(state='STARTING',command=args.command,pid=os.getpid(),updated_unix=start))
    if args.command=='smoke':smoke(out,cfg,deadline)
    elif args.command=='prepare':prepare(out,cfg,deadline)
    elif args.command=='warmup':warmup(out,cfg,args.data.resolve(),deadline)
    elif args.command=='train':train(out,cfg,args.data.resolve(),args.warmup.resolve(),deadline)
    provenance=json.loads((out/'provenance.json').read_text())
    for p,h in provenance['source_hashes'].items():assert sha(p)==h
    for p in provenance['parent_checkpoints']:assert sha(p['path'])==p['sha256']
    assert sha(ARRAYS)==provenance['original_arrays_sha256']
    dump(out/'status.json',dict(state='COMPLETED',command=args.command,elapsed_seconds=time.time()-start,
        scientific_training_started=args.command in ('warmup','train'),inputs_unchanged=True,pid=os.getpid(),updated_unix=time.time()))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('smoke','prepare','warmup','train'))
    parser.add_argument('--config',type=Path,default=HERE/'config.json');parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data',type=Path);parser.add_argument('--warmup',type=Path);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:main(args)
    except Exception:
        if args.output.exists():dump(args.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time(),pid=os.getpid()))
        raise
