"""Small deterministic actor-critic core; no simulator or data access on import."""
import copy
import numpy as np
import torch
from torch import nn


def returns(rewards, terminal, gamma):
    assert len(rewards)==len(terminal) and terminal[-1]
    out=np.zeros(len(rewards),np.float32);value=0.
    for j in range(len(rewards)-1,-1,-1):
        value=float(rewards[j])+gamma*value*(not bool(terminal[j]));out[j]=value
    return out


class FixedCompletion(nn.Module):
    """Actor updates cannot silently change the phase-completion decision."""
    def __init__(self,actor,reference):
        super().__init__();self.actor=actor;self.reference=reference
    def forward(self,x,phase):
        action,_=self.actor(x,phase)
        with torch.no_grad():_,done=self.reference(x,phase)
        return action,done


class TwinQ(nn.Module):
    def __init__(self,mean,std,width):
        super().__init__()
        self.register_buffer('mean',torch.as_tensor(mean,dtype=torch.float32))
        self.register_buffer('std',torch.as_tensor(std,dtype=torch.float32).clamp_min(.001))
        n=len(mean)+4
        def net():return nn.Sequential(nn.Linear(n,width),nn.SiLU(),nn.Linear(width,width),nn.SiLU(),nn.Linear(width,1))
        self.q1=net();self.q2=net()
    def forward(self,state,action):
        inp=torch.cat((((state-self.mean)/self.std).clamp(-10,10),action),dim=-1)
        return self.q1(inp).squeeze(-1),self.q2(inp).squeeze(-1)


class Learner:
    def __init__(self,actor,mean,std,config,seed=1,device='cuda'):
        self.cfg=config;self.device=device;self.seed=seed;self.updates=0;self.warm_updates=0
        torch.manual_seed(seed)
        self.actor=copy.deepcopy(actor).to(device)
        self.reference=copy.deepcopy(actor).to(device).eval().requires_grad_(False)
        self.target_actor=copy.deepcopy(self.actor).eval().requires_grad_(False)
        self.critic=TwinQ(mean,std,config['critic_width']).to(device)
        self.target_critic=copy.deepcopy(self.critic).eval().requires_grad_(False)
        self.actor_opt=torch.optim.AdamW(self.actor.parameters(),lr=config['actor_lr'],weight_decay=config['weight_decay'])
        self.critic_opt=torch.optim.AdamW(self.critic.parameters(),lr=config['critic_lr'],weight_decay=config['weight_decay'])
        self.generator=torch.Generator(device=device).manual_seed(seed+9000)
    def tensor(self,value,dtype=None):return torch.as_tensor(value,device=self.device,dtype=dtype)
    def policy(self):return FixedCompletion(self.actor,self.reference)
    def warm(self,batch):
        s,a,y=[self.tensor(batch[k],torch.float32) for k in ('state','action','return')]
        q1,q2=self.critic(s,a);loss=(q1-y).square().mean()+(q2-y).square().mean()
        self._critic_step(loss);self.warm_updates+=1
        self.target_critic.load_state_dict(self.critic.state_dict())
        return float(loss.detach())
    def _critic_step(self,loss):
        assert torch.isfinite(loss)
        self.critic_opt.zero_grad(set_to_none=True);loss.backward()
        norm=nn.utils.clip_grad_norm_(self.critic.parameters(),self.cfg['gradient_clip']);assert torch.isfinite(norm)
        self.critic_opt.step()
    @torch.no_grad()
    def target_actions(self,next_x,next_phase):
        c=self.cfg
        action,_=self.target_actor(next_x,next_phase)
        noise=torch.randn(action.shape,device=self.device,generator=self.generator)*self.tensor(c['target_noise_std'])
        noisy=(action+noise.clamp(-c['target_noise_clip'],c['target_noise_clip'])).clamp(-1,1)
        mode=c.get('target_action_projection','legacy')
        if mode=='actor_bounds_v1':
            project=getattr(self.target_actor,'project_action',None)
            if not callable(project):raise ValueError('Target projection requires an actor with project_action')
            projected=project(noisy,next_x,next_phase)
        elif mode=='legacy':projected=noisy
        else:raise ValueError(f'Unknown target action projection: {mode}')
        delta=(projected-noisy).abs()
        return projected,dict(target_action_projection=mode,
            target_projection_changed_fraction=float((delta.amax(-1)>1e-7).float().mean()),
            target_projection_max_abs_change=float(delta.max()))
    def update(self,batch,bc=None,bc_coefficient=0.):
        c=self.cfg
        s,a,r,ns,t=[self.tensor(batch[k],torch.float32) for k in ('state','action','reward','next_state','terminal')]
        nx=self.tensor(batch['next_x'],torch.float32);np_=self.tensor(batch['next_phase'],torch.long)
        with torch.no_grad():
            na,projection_metrics=self.target_actions(nx,np_)
            q1,q2=self.target_critic(ns,na)
            target=(r+c['gamma']*(1-t)*torch.minimum(q1,q2)).clamp(0,1)
        q1,q2=self.critic(s,a);critic_loss=(q1-target).square().mean()+(q2-target).square().mean()
        self._critic_step(critic_loss);self.updates+=1
        metrics=dict(critic_loss=float(critic_loss.detach()),actor_updated=False,bc_coefficient=bc_coefficient,
                     target_mean=float(target.mean()),target_min=float(target.min()),target_max=float(target.max()),
                     **projection_metrics)
        if self.updates%c['policy_delay']==0:
            self.critic.requires_grad_(False)
            pred,_=self.actor(self.tensor(batch['x'],torch.float32),self.tensor(batch['phase'],torch.long))
            q,_=self.critic(s,pred);rl=-q.mean();bc_loss=torch.zeros((),device=self.device)
            if bc_coefficient:
                assert bc is not None,'BC samples required for nonzero coefficient'
                bp,_=self.actor(self.tensor(bc['x'],torch.float32),self.tensor(bc['phase'],torch.long))
                bc_loss=(bp-self.tensor(bc['action'],torch.float32)).square().mean()
            actor_loss=rl+bc_coefficient*bc_loss;assert torch.isfinite(actor_loss)
            self.actor_opt.zero_grad(set_to_none=True);actor_loss.backward()
            norm=nn.utils.clip_grad_norm_(self.actor.parameters(),c['gradient_clip']);assert torch.isfinite(norm)
            self.actor_opt.step();self.critic.requires_grad_(True)
            with torch.no_grad():
                for target_net,source in ((self.target_actor,self.actor),(self.target_critic,self.critic)):
                    for target_p,p in zip(target_net.parameters(),source.parameters()):target_p.lerp_(p,c['target_tau'])
            metrics.update(actor_updated=True,actor_loss=float(actor_loss.detach()),rl_loss=float(rl.detach()),bc_loss=float(bc_loss.detach()))
        return metrics
    @torch.no_grad()
    def validate(self,data):
        predictions=[]
        for j in range(0,len(data['state']),512):
            q1,q2=self.critic(self.tensor(data['state'][j:j+512],torch.float32),self.tensor(data['action'][j:j+512],torch.float32))
            predictions.extend(torch.minimum(q1,q2).cpu().numpy().tolist())
        q=np.array(predictions);y=data['return']
        return dict(return_mse=float(np.mean((q-y)**2)),prediction_min=float(q.min()),prediction_max=float(q.max()),
                    n=len(q),finite=bool(np.isfinite(q).all()))
    def save(self,path,extra=None):
        checkpoint=dict(actor=self.actor.state_dict(),reference=self.reference.state_dict(),critic=self.critic.state_dict(),
            target_actor=self.target_actor.state_dict(),target_critic=self.target_critic.state_dict(),
            actor_optimizer=self.actor_opt.state_dict(),critic_optimizer=self.critic_opt.state_dict(),
            updates=self.updates,warm_updates=self.warm_updates,seed=self.seed,config=self.cfg,
            sampler_generator=self.generator.get_state(),extra=extra or {})
        torch.save(checkpoint,path)


def sample(data,rng,n):
    ids=rng.integers(len(data['state']),size=n)
    return {k:v[ids] for k,v in data.items()}


def concat(parts):
    assert parts
    return {k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
