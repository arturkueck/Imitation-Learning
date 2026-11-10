from pathlib import Path
import sys,json,time,copy,random,hashlib,traceback,shutil,os
from collections import defaultdict
import numpy as np
import torch
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'experiments/stack_self_imitation_20261023'))
import pipeline as prior
from pipeline import PhaseNet,Policy,vector,write,digest,offline,old,ACTIVE,DATA,EpisodePool,audit_episode,observation
from task_extensions.environments import StackFour,ManipulationEnv,TableArena,BoxObject,ManipulationTask,UniformRandomSampler

class CurriculumStack(StackFour):
    def __init__(self,*args,cube_count=5,**kwargs):
        self.cube_count=cube_count;super().__init__(*args,**kwargs)
    def _load_model(self):
        ManipulationEnv._load_model(self)
        self.robots[0].robot_model.set_base_xpos(self.robots[0].robot_model.base_xpos_offset['table'](self.table_full_size[0]))
        arena=TableArena(table_full_size=self.table_full_size,table_friction=self.table_friction,table_offset=self.table_offset);arena.set_origin([0,0,0])
        colors=[[.85,.15,.15,1],[.15,.75,.2,1],[.15,.3,.9,1],[.95,.75,.1,1],[.8,.2,.8,1]]
        self.cubes=[BoxObject(name='cube'+letter,size=[.02]*3,rgba=color,density=500,friction=[1,.005,.0001]) for letter,color in list(zip('ABCDE',colors))[:self.cube_count]]
        for letter,cube in zip('ABCDE',self.cubes):setattr(self,'cube'+letter,cube)
        self.placement_initializer=UniformRandomSampler(name='CurriculumSampler',mujoco_objects=self.cubes,x_range=[-.16,.16],y_range=[-.16,.16],rotation=0,ensure_valid_placement=True,ensure_object_boundary_in_range=True,reference_pos=self.table_offset,z_offset=.01)
        self.model=ManipulationTask(mujoco_arena=arena,mujoco_robots=[r.robot_model for r in self.robots],mujoco_objects=self.cubes)

def make_env(count):
    meta=json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text());kw=copy.deepcopy(meta['environment']['env_kwargs'])
    kw.update(has_offscreen_renderer=False,use_camera_obs=False,has_renderer=False,horizon=500*(count-1),hard_reset=False)
    env=CurriculumStack(cube_count=count,**kw);assert len(env.cubes)==count and len(set(env.cube_ids))==count
    return env

def bound(deadline):
    if time.time()>=deadline or (OUT/'STOP').exists():raise TimeoutError('Fixed deadline or session STOP')

class Sequencer:
    def __init__(self,model,count):
        self.policy=Policy(model);self.count=count;self.stage=1;self.pair=0;self.retreat=False
    def advance(self,valid,placed_position):
        self.pair=self.pair+1 if valid else 0
        if self.retreat and self.policy.phase>0:
            self.retreat=False;self.stage+=1;self.pair=0;self.policy.reset();return 2
        if not self.retreat and self.stage<self.count-1 and self.policy.phase==6 and self.pair>=10:
            self.policy.reset();self.policy.anchor=placed_position.copy();self.retreat=True;self.pair=0;return 1
        return 0

@torch.no_grad()
def episode(env,model,count,seed,deadline):
    bound(deadline);np.random.seed(seed);random.seed(seed);obs=env.reset();initial=env.sim.get_state().flatten().copy()
    seq=Sequencer(model,count);records=defaultdict(list);tail=0;prefix_max=[0]*(count-1);prefix_runs=[0]*(count-1)
    for t in range(500*(count-1)):
        bound(deadline);policy=seq.policy;stage=seq.stage;positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]);phase=policy.phase;steps=policy.steps
        anchor=positions[stage if phase<4 else stage-1].copy() if policy.anchor is None else policy.anchor.copy()
        x=vector(obs,anchor,steps);pre=observation(env,obs);state=env.sim.get_state().flatten().copy()
        action,actual_phase,prob=policy.action(obs,positions[stage-1],positions[stage]);assert phase==actual_phase
        done=int(policy.phase!=phase);next_obs,_,_,_=env.step(action);post=observation(env,next_obs)
        prefixes=[old.prefix_valid(env,k) for k in range(2,count+1)];valid=prefixes[-1]
        for j,v in enumerate(prefixes):prefix_runs[j]=prefix_runs[j]+1 if v else 0;prefix_max[j]=max(prefix_max[j],prefix_runs[j])
        row=dict(x=x,a=action,p=phase,y=done,phase_steps=steps,anchor=anchor,stage=stage,retreat=seq.retreat,pre_obs=pre,post_obs=post,pre_state=state,prob=prob,valid2=prefixes[0],valid=valid,prefix_valid=prefixes,
          velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes]),contacts=[env.check_contact(env.cubes[i],env.cubes[i+1]) for i in range(count-1)],fingers=[env.check_contact(env.robots[0].gripper,c) for c in env.cubes])
        row['controller_event']=seq.advance(prefixes[stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        for k,v in row.items():records[k].append(v)
        obs=next_obs;tail=tail+1 if valid else 0
        if tail>=50:break
    a={k:np.asarray(v) for k,v in records.items()};a['initial']=initial
    return a,dict(seed=seed,count=count,success=tail>=50,frames=t+1,initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),prefix_max_run=prefix_max,last_stage=seq.stage,phase=int(seq.policy.phase),pair_switches=int(np.sum(a['controller_event']==2)))

def load(path):
    m=PhaseNet().cuda().eval();m.load_state_dict(torch.load(path,map_location='cpu',weights_only=False)['model']);return m

def status(**kw):write(OUT/'status.json',dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw))

def evaluate(path,count,seeds,folder,deadline,save=2):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);m=load(path);env=make_env(count);rows=[]
    try:
        for i,seed in enumerate(seeds):
            a,r=episode(env,m,count,seed,deadline);rows.append(r)
            if i<save:np.savez_compressed(folder/f'{seed}.npz',**a)
            write(folder/'result.json',dict(complete=i+1==len(seeds),successes=sum(r['success'] for r in rows),attempts=len(rows),rows=rows))
    finally:env.close()
    return sum(r['success'] for r in rows)

def collect(paths,count,cycle,arm,deadline,attempts=120):
    folder=OUT/'datasets'/f'{arm}_n{count}_cycle{cycle}';folder.mkdir(parents=True,exist_ok=False)
    models=[load(p) for p in paths];env=make_env(count);rows=[]
    # Separate namespaces by arm, height, cycle and split, fixed before outcomes.
    base=200000+(0 if arm=='curriculum' else 50000)+count*5000+cycle*1000
    try:
        (folder/'model.xml').write_text(env.model.get_xml(),encoding='utf-8')
        for i in range(attempts):
            ti=i%len(models);a,r=episode(env,models[ti],count,base+i,deadline);assert audit_episode(a,models[ti],count)==r['success']
            r.update(teacher=str(paths[ti]),teacher_sha256=digest(paths[ti]),split='train' if i<100 else 'valid',path=str(folder/f'{base+i}.npz'))
            np.savez_compressed(r['path'],**a);rows.append(r);write(folder/'manifest.json',dict(complete=i+1==attempts,rows=rows))
            status(state='COLLECTING',arm=arm,height=count,cycle=cycle,attempt=i+1,successes=sum(x['success'] for x in rows))
    finally:env.close()
    assert not {r['initial_sha256'] for r in rows if r['split']=='train'} & {r['initial_sha256'] for r in rows if r['split']=='valid'}
    return rows

class ReplayPool:
    def __init__(self,rows):
        self.pools=[EpisodePool(rows,n) for n in sorted({r['count'] for r in rows if r['success'] and r['split']=='train'})]
        assert self.pools
    def sample(self,rng,n):
        samples=[self.pools[int(rng.integers(len(self.pools)))].sample(rng,1) for _ in range(n)]
        return tuple(np.concatenate([v[k] for v in samples]) for k in range(3))

def train(parent,seed,arm,count,cycle,rows,earlier,steps,deadline,smoke=False):
    folder=OUT/'training'/f'{arm}_n{count}_c{cycle}_seed{seed}';folder.mkdir(parents=True,exist_ok=False)
    data=np.load(prior.BASE/'training_arrays.npz');x,a,p,y=[data['train_'+k] for k in ['x','a','p','y']];valid=tuple(data['valid_'+k] for k in ['x','a','p','y'])
    groups=[np.flatnonzero(p==k) for k in range(7)];pw=torch.tensor([min(50.,max(1.,(1-y[j]).sum()/max(y[j].sum(),1))) for j in groups],device='cuda')
    new=EpisodePool(rows,count);replay=ReplayPool(earlier);m=load(parent);opt=torch.optim.AdamW(m.parameters(),lr=3e-5,weight_decay=1e-6)
    rng=np.random.default_rng(seed+cycle*100);extra=np.random.default_rng(seed+cycle*100+10000);curve=[];best=-1;selected=Path(parent)
    write(folder/'config.json',dict(parent=str(parent),parent_sha256=digest(parent),seed=seed,arm=arm,height=count,cycle=cycle,planned_updates=steps,batch=64,lr=3e-5,mixture='32 original +16 earlier heights +16 new height',completion_loss='original only',sampler='phase/episode/frame',architecture='unchanged PhaseNet 10 inputs'))
    for u in range(1,steps+1):
        bound(deadline);ids=np.array([rng.choice(groups[k]) for k in rng.integers(7,size=32)]);xx,aa,pp=new.sample(extra,16);rx,ra,rp=replay.sample(extra,16)
        bx=np.r_[x[ids],rx,xx];ba=np.r_[a[ids],ra,aa];bp=np.r_[p[ids],rp,pp]
        pred,z=m(torch.tensor(bx,device='cuda'),torch.tensor(bp,device='cuda'));actor=(pred-torch.tensor(ba,device='cuda')).square().mean()
        mask=torch.tensor(p[ids]<6,device='cuda');labels=torch.tensor(y[ids],device='cuda');bce=torch.nn.functional.binary_cross_entropy_with_logits(z[:32][mask],labels[mask],pos_weight=pw[torch.tensor(p[ids],device='cuda')][mask]);loss=actor+.1*bce;assert torch.isfinite(loss)
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),10);opt.step()
        if u%1000==0 or u==steps:
            ck=dict(model=m.state_dict(),optimizer=opt.state_dict(),update=u,parent=str(parent));tmp=folder/'latest.tmp';torch.save(ck,tmp);tmp.replace(folder/'latest.pth');write(folder/'status.json',dict(update=u,state='TRAINING'));status(state='TRAINING',arm=arm,height=count,seed=seed,cycle=cycle,update=u,actor_loss=float(actor.detach()))
        if u in [10000,30000,60000] or u==steps:
            metric=dict(update=u,actor_loss=float(actor.detach()),completion_loss=float(bce.detach()),original_valid=offline(m,valid));curve.append(metric);write(folder/'learning_curve.json',curve)
    # One shared fixed development block per height, no selection on held-out tests.
    score=0 if smoke else evaluate(folder/'latest.pth',count,list(range(310000+count*1000,310050+count*1000)),folder/'development',deadline)
    torch.save(ck,folder/'best.pth');write(folder/'best.json',dict(update=steps,dev_successes=score,dev_attempts=50,selection='only completed checkpoint; compare to parent gate before replacement'))
    write(folder/'status.json',dict(state='TRAINING_COMPLETE',update=steps));return folder/'best.pth',score

def gate(paths,count,tag,deadline):
    result=[]
    for i,path in enumerate(paths):
        status(state='GATE',height=count,seed=i+1,tag=tag)
        first=evaluate(path,count,list(range(310000+count*1000,310050+count*1000)),OUT/'gates'/f'{tag}_seed{i+1}_first',deadline)
        second=None
        if first>=30:second=evaluate(path,count,list(range(320000+count*1000,320050+count*1000)),OUT/'gates'/f'{tag}_seed{i+1}_confirm',deadline)
        result.append(dict(path=str(path),seed=i+1,first=first,confirm=second,passed=first>=30 and second is not None and second>=30))
        write(OUT/f'{tag}_gates.json',result)
    return result

def preflight():
    torch.set_num_threads(4);m=load(json.loads((OUT/'protocol.json').read_text())['parents'][0]['path']);checks={}
    for n in [2,3,4,5]:
        env=make_env(n);obs=env.reset();assert len(env.cube_ids)==n;assert not old.prefix_valid(env,n)
        # Prepared poses only validate the metric, never collection or success statistics.
        for i,c in enumerate(env.cubes):env.sim.data.set_joint_qpos(c.joints[0],np.r_[[0,0,env.table_offset[2]+.02+.04*i],[1,0,0,0]]);env.sim.data.set_joint_qvel(c.joints[0],np.zeros(6))
        env.sim.forward()
        for _ in range(250):env.sim.step()
        env.sim.forward();positive=old.prefix_valid(env,n);assert positive,('prepared metric positive',n)
        last=env.cubes[-1];q=env.sim.data.get_joint_qpos(last.joints[0]).copy();q[0]+=.04;env.sim.data.set_joint_qpos(last.joints[0],q);env.sim.forward();assert not old.prefix_valid(env,n)
        checks[str(n)]=dict(objects=len(env.cubes),ids=env.cube_ids,positive_metric=positive,negative_metric=True);env.close()
    seq=Sequencer(m,5)
    for expected in [2,3,4]:
        seq.policy.phase=6;seq.pair=9;assert seq.advance(True,np.zeros(3))==1;seq.policy.phase=1;assert seq.advance(False,np.zeros(3))==2;assert seq.stage==expected
    env=make_env(5)
    try:a,r=episode(env,m,5,399001,time.time()+180);assert audit_episode(a,m,5)==r['success'];np.savez_compressed(OUT/'preflight_episode.npz',**a)
    finally:env.close()
    legacy=json.loads((prior.OUT/'dataset_manifest.json').read_text())['rows']
    train(Path(json.loads((OUT/'protocol.json').read_text())['parents'][0]['path']),99,'technical_smoke',3,0,legacy,legacy,5,time.time()+120,smoke=True)
    corrupted={k:v.copy() for k,v in a.items()};corrupted['a'][0,0]+=.1
    try:audit_episode(corrupted,m,5)
    except AssertionError:pass
    else:raise AssertionError('Corruption audit failed to reject')
    write(OUT/'preflight.json',dict(state='PASSED',checks=checks,all_three_pair_switches=True,pre_action_audit=True,real_episode=r))

def report(state,error=None):
    tests={str(p.relative_to(OUT)):json.loads(p.read_text()) for p in (OUT/'final_test').glob('*/result.json')} if (OUT/'final_test').exists() else {}
    text=['# Five-cube curriculum pilot',f'State: {state}', 'Only observed results are reported. Missing evaluations are not failures.',f'Error: {error}' if error else '', '## Held-out complete stable towers']
    for name,r in tests.items():text.append(f"- {name}: {r['successes']}/{r['attempts']}, complete={r['complete']}")
    text+=['## Actual optimizer updates']
    for p in (OUT/'training').glob('*/status.json'):
        if 'technical_smoke' not in str(p):text.append(f'- {p.parent.name}: {json.loads(p.read_text())}')
    text+=['## Collected dataset counts']
    for p in (OUT/'datasets').glob('*/manifest.json'):
        d=json.loads(p.read_text());rr=d['rows'];text.append(f"- {p.parent.name}: {len(rr)} attempts, {sum(r['success'] and r['split']=='train' for r in rr)} training successes, {sum(r['success'] and r['split']=='valid' for r in rr)} validation successes; complete={d['complete']}")
    if (OUT/'decisions.json').exists():text+=['## Gates and decisions', '```json', (OUT/'decisions.json').read_text(), '```']
    text+=['## Interpretation','Three-cube and higher successful self-generated actions are training data. This is not zero-shot transfer from two-cube demonstrations.','Fixed phase BC actions/completion, geometric prefix stability gate and learned phase-0 retreat reused between each pair. The external sequencer chooses the next pair; it is not learned.','At least 90/100 complete stable five-cube towers on EACH of three seeds is required for the 90% point target. A skipped stage or missing test is unproven, not 0/100.','See protocol.json, gate records, dataset manifests and learning curves for actual costs and decisions. A full agent-written analysis is due at the next hourly check.']
    (OUT/'RESULTS.md').write_text('\n\n'.join(text),encoding='utf-8')

def main():
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    if '--preflight' in sys.argv:preflight();return
    plan=json.loads((OUT/'protocol.json').read_text());assert json.loads((OUT/'preflight.json').read_text())['state']=='PASSED'
    for source,expected in json.loads((OUT/'source_hashes.json').read_text()).items():assert digest(source)==expected,source
    paths=[Path(p['path']) for p in plan['parents']]
    for p,info in zip(paths,plan['parents']):assert digest(p)==info['sha256']
    assert digest(DATA)==plan['original_sha256'];earlier=json.loads((prior.OUT/'dataset_manifest.json').read_text())['rows'];selected={};decisions=[]
    for i,p in enumerate(paths):selected[f'curriculum_seed{i+1}']=p;selected[f'direct_seed{i+1}']=p
    try:
        gates=gate(paths,3,'initial3',plan['training_deadline']);ready=[Path(r['path']) for r in gates if r['passed']]
        # Three-cube refinement is allowed even before the 60% collection gate.
        for n in [3,4,5]:
            cutoff=min(plan['training_deadline'],plan['start']+({3:3,4:5,5:10}[n])*3600)
            if time.time()>=cutoff:decisions.append(dict(height=n,reason='stage time cap'));break
            if n>3 and not ready:decisions.append(dict(height=n,reason='no teacher confirmed previous-height 60% gate'));break
            donors=ready if n>3 else paths
            rows=collect(donors,n,0,'curriculum',cutoff)
            if sum(r['success'] and r['split']=='train' for r in rows)<20 or sum(r['success'] and r['split']=='valid' for r in rows)<3:
                decisions.append(dict(height=n,reason='insufficient successful data: train minimum20, valid3'));break
            newpaths=[]
            for i,p in enumerate(paths):
                candidate,score=train(p,i+1,'curriculum',n,0,rows,earlier,30000 if n<5 else 120000,cutoff)
                parent_score=evaluate(p,n,list(range(310000+n*1000,310050+n*1000)),OUT/'gates'/f'parent_n{n}_seed{i+1}',cutoff)
                chosen=candidate if score>parent_score else p;newpaths.append(chosen);selected[f'curriculum_seed{i+1}']=chosen
            paths=newpaths;gates=gate(paths,n,f'post{n}',cutoff);ready=[Path(r['path']) for r in gates if r['passed']]
            decisions.append(dict(height=n,gates=gates));write(OUT/'decisions.json',decisions)
            earlier=earlier+rows
        # Direct five-cube self-IL control: same original parents and no new intermediate data.
        if time.time()<plan['training_deadline']:
            direct=[Path(p['path']) for p in plan['parents']];rows=collect(direct,5,0,'direct',plan['training_deadline'])
            if sum(r['success'] and r['split']=='train' for r in rows)>=20 and sum(r['success'] and r['split']=='valid' for r in rows)>=3:
                for i,p in enumerate(direct):
                    candidate,score=train(p,i+1,'direct',5,0,rows,json.loads((prior.OUT/'dataset_manifest.json').read_text())['rows'],180000,plan['training_deadline'])
                    parent_score=evaluate(p,5,list(range(315000,315050)),OUT/'gates'/f'direct_parent_seed{i+1}',plan['training_deadline'])
                    selected[f'direct_seed{i+1}']=candidate if score>parent_score else p
            else:decisions.append(dict(arm='direct',height=5,reason='insufficient successful five-cube data; control remains unchanged parent'))
    except TimeoutError as e:decisions.append(dict(reason=str(e),state='TRAINING_TIME_CAP'))
    write(OUT/'decisions.json',decisions)
    final=OUT/'final_test';final.mkdir(exist_ok=False);frozen={}
    for name,p in selected.items():dst=final/(name+'.pth');shutil.copy2(p,dst);frozen[name]=dict(path=str(dst),source=str(p),sha256=digest(dst))
    write(final/'selection.json',frozen)
    try:
        # Five-cube target first, with all replicates/arms interleaved; regression only if time remains.
        for n,number in [(5,100),(3,50),(2,50),(4,50)]:
            for name,info in frozen.items():
                status(state='FINAL_TEST',model=name,height=n);evaluate(info['path'],n,list(range(360000+n*1000,360000+n*1000+number)),final/f'{name}_n{n}',plan['deadline']-120)
        assert digest(DATA)==plan['original_sha256'];status(state='COMPLETED',original_hash_unchanged=True);report('COMPLETED')
    except TimeoutError as e:status(state='PARTIAL_TIME_LIMIT');report('PARTIAL_TIME_LIMIT',str(e))

if __name__=='__main__':
    try:main()
    except Exception:
        error=traceback.format_exc();status(state='FAILED',error=error);report('FAILED',error);raise
