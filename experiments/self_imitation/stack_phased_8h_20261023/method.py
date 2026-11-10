"""Phase-conditioned BC; learned Cartesian/gripper actions and phase completion."""
from pathlib import Path
import sys,json,hashlib,copy
from types import SimpleNamespace as NS
import h5py,numpy as np,torch
from torch import nn
OUT=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/self_imitation/stack_composition_20261023'))
import run as old
from task_extensions.stack_expert import StackExpert
DATA=ROOT/'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'
ACTIVE=[0,1,2,6]

def write(path,data):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(path)

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def vector(obs,anchor,steps):
    return np.r_[(np.asarray(obs['robot0_eef_pos'])-anchor)/.1,obs['robot0_eef_quat'],np.asarray(obs['robot0_gripper_qpos'])/.04,min(steps,100)/20].astype('float32')

def dataset():
    rows={s:[] for s in ['train','valid']};errors=[];ids={};counts={}
    with h5py.File(DATA,'r') as f:
        ids={s:[x.decode() for x in f['mask'][s][:]] for s in rows}
        assert not set(ids['train'])&set(ids['valid'])
        for split in rows:
            for name in sorted(ids[split]):
                d=f['data'][name];actions=d['actions'][:]
                raw=NS(cubes=[0,1],cube_ids=[0,1],sim=NS(data=NS(body_xpos=None)))
                expert=StackExpert(NS(base_env=raw));anchor=None
                for t,a in enumerate(actions):
                    ob={k:d['obs'][k][t] for k in ['object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']}
                    positions=ob['object'].reshape(2,3);raw.sim.data.body_xpos=positions
                    phase=expert.phase;assert phase<=6,(name,t,phase)
                    if expert.target is None:anchor=positions[1 if phase<4 else 0].copy()
                    x=vector(ob,anchor,expert.phase_steps)
                    label=expert(ob);errors.append(float(np.max(np.abs(label-a))))
                    rows[split].append((x,a[ACTIVE],phase,int(expert.phase!=phase)))
    assert max(errors)<1e-5,max(errors)
    result={}
    for s,r in rows.items():
        result[s]=(np.stack([x[0] for x in r]),np.stack([x[1] for x in r]).astype('float32'),np.array([x[2] for x in r]),np.array([x[3] for x in r],dtype='float32'))
        counts[s]={str(p):dict(frames=int((result[s][2]==p).sum()),transitions=int(result[s][3][result[s][2]==p].sum())) for p in range(7)}
    return result,dict(dataset_sha256=digest(DATA),split_ids=ids,phase_counts=counts,max_reconstructed_action_error=max(errors),features=10,
        anchor='source position cached at entry for phases0..3; target position cached at entry for phases4..6',
        phase_sequence='fixed expert order 0..6; completion0..5 learned; final completion uses physical stability gate',
        no_phase7='No complete retreat demonstration; no learned retreat claimed',rotations='identically zero in source; fixed zero outputs',new_demonstrations=0)

class PhaseNet(nn.Module):
    """Phasenabhaengige Policy pi_theta und separater Abschluss-Logit.

    x hat zehn Zustandsmerkmale. phase waehlt einen von sieben Koepfen.
    Die ersten vier Ausgaben sind die gelernten Aktionskomponenten
    [Translation x/y/z, Greifer]; tanh begrenzt sie auf [-1, 1].
    Die fuenfte Ausgabe trainiert den Phasenabschluss mit separatem BCE-Loss.
    """
    def __init__(self,width=128):
        super().__init__();self.heads=nn.ModuleList([nn.Sequential(nn.Linear(10,width),nn.SiLU(),nn.Linear(width,width),nn.SiLU(),nn.Linear(width,5)) for _ in range(7)])
    def forward(self,x,phase):
        out=torch.zeros((len(x),5),device=x.device)
        for p,h in enumerate(self.heads):
            mask=phase==p
            if mask.any():out[mask]=h(x[mask])
        # Erster Rueckgabewert = pi_theta(x_t) in den Imitations-Losstermen.
        # Der zweite ist kein Aktionswert und gehoert nicht in ||pi-a||^2.
        return out[:,:4].tanh(),out[:,4]

class Policy:
    def __init__(self,model,threshold=.8):self.model=model;self.threshold=threshold;self.reset()
    def reset(self):self.phase=0;self.steps=0;self.anchor=None
    @torch.no_grad()
    def action(self,obs,target,source):
        if self.anchor is None:self.anchor=(source if self.phase<4 else target).copy()
        x=torch.tensor(vector(obs,self.anchor,self.steps)[None],device='cuda')
        a,z=self.model(x,torch.tensor([self.phase],device='cuda'));prob=float(z.sigmoid()[0]);action=np.zeros(7);action[ACTIVE]=a[0].cpu().numpy()
        phase=self.phase;self.steps+=1
        if phase<6 and prob>=self.threshold:self.phase+=1;self.steps=0;self.anchor=None
        return action,phase,prob

@torch.no_grad()
def offline(model,data):
    x,a,p,y=data;se=np.zeros(7);n=np.zeros(7);tp=np.zeros(7);fp=np.zeros(7);fn=np.zeros(7)
    for i in range(0,len(x),512):
        pred,z=model(torch.tensor(x[i:i+512],device='cuda'),torch.tensor(p[i:i+512],device='cuda'))
        pred=pred.cpu().numpy();done=z.sigmoid().cpu().numpy()>=.8
        for k in range(7):
            m=p[i:i+512]==k;truth=y[i:i+512][m]>0
            n[k]+=m.sum();se[k]+=((pred[m]-a[i:i+512][m])**2).sum();tp[k]+=(done[m]&truth).sum();fp[k]+=(done[m]&~truth).sum();fn[k]+=(~done[m]&truth).sum()
    return dict(action_mse=(se/np.maximum(n*4,1)).tolist(),transition_tp=tp.tolist(),transition_fp=fp.tolist(),transition_fn=fn.tolist())

@torch.no_grad()
def evaluate(model,count,seeds,path,deadline,threshold=.8,retreat=False):
    import time,random
    env=old.make_env(count);rows=[];policy=Policy(model,threshold)
    try:
        for seed in seeds:
            if time.time()>deadline:break
            np.random.seed(seed);random.seed(seed);obs=env.reset();initial=env.sim.get_state().flatten().copy();policy.reset()
            stage=1;pair=0;tail=0;first=None;trace=[];retreat_active=False;retreat_done=False
            for t in range(500 if count==2 else 1000):
                if time.time()>deadline:break
                p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]);action,phase,prob=policy.action(obs,p[stage-1],p[stage])
                stage_before=stage;obs,_,_,_=env.step(action)
                p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]);held=[env._check_grasp(env.robots[0].gripper,c) for c in env.cubes]
                valid2=old.prefix_valid(env,2);valid=old.prefix_valid(env,count)
                trace.append(np.r_[t,stage_before,phase,prob,p.flatten(),obs['robot0_eef_pos'],action,held,valid2,valid,retreat_active])
                pair=pair+1 if valid2 else 0
                if first is None and pair>=10:first=t+1
                if retreat_active and policy.phase>0:
                    retreat_active=False;retreat_done=True;stage=2;policy.reset()
                elif count==3 and stage==1 and policy.phase==6 and pair>=10:
                    if retreat and not retreat_done:
                        # Reuse learned open-gripper approach head above the placed cube.
                        # Fixed orchestration change; no expert XYZ command or new label.
                        policy.reset();policy.anchor=p[1].copy();retreat_active=True
                    else:stage=2;policy.reset()
                tail=tail+1 if valid else 0
                if tail>=50:break
            complete=tail>=50 or t+1==(500 if count==2 else 1000)
            rows.append(dict(seed=seed,success=tail>=50,complete=complete,steps=t+1,first_stack_step=first,stage=stage,phase=policy.phase,
                initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest()))
            traces=path.parent/(path.stem+'_traces');traces.mkdir(exist_ok=True)
            np.savez_compressed(traces/f'{seed}.npz',trace=np.array(trace),initial=initial)
            write(path,dict(count=count,n=len(rows),successes=sum(r['success'] for r in rows),complete=len(rows)==len(seeds) and all(r['complete'] for r in rows),rows=rows))
    finally:env.close()
    return dict(n=len(rows),successes=sum(r['success'] for r in rows),complete=len(rows)==len(seeds) and all(r['complete'] for r in rows))
