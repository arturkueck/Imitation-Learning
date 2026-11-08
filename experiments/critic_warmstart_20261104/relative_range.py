"""State-dependent action range: larger in motion, vanishing at IL equilibrium."""
from pathlib import Path
import argparse
import copy
import json
import shutil
import time
import traceback
import numpy as np
import torch
from torch import nn
import stability as base
from action_range import paired, passes

HERE=Path(__file__).resolve().parent
run=base.run


def widths(parent, cap, beta=.5, gripper=.02):
    xyz=torch.minimum(torch.full_like(parent[...,:3],cap),parent[...,:3].abs()*beta)
    return torch.cat([xyz,torch.full_like(parent[...,3:4],gripper)],dim=-1)


def project_relative(action,parent,cap=.2,beta=.5,gripper=.02):
    limit=widths(parent,cap,beta,gripper)
    return torch.maximum(torch.minimum(action,parent+limit),parent-limit).clamp(-1,1)


class RelativeMovement(nn.Module):
    def __init__(self,actor,parent,cap=.2,beta=.5,gripper=.02):
        super().__init__()
        assert 0<cap<=1 and 0<beta<1 and 0<gripper<=1
        self.actor=actor;self.parent=copy.deepcopy(parent).eval().requires_grad_(False)
        self.cap=cap;self.beta=beta;self.gripper=gripper

    def forward(self,x,phase):
        raw,done=self.actor(x,phase)
        with torch.no_grad():parent,_=self.parent(x,phase)
        limit=widths(parent,self.cap,self.beta,self.gripper)
        action=(parent+limit*torch.tanh((raw-parent)/limit.clamp_min(1e-8))).clamp(-1,1)
        return action,done

    @torch.no_grad()
    def project_action(self,action,x,phase):
        parent,_=self.parent(x,phase)
        return project_relative(action,parent,self.cap,self.beta,self.gripper)


def constrain(learner,cap=.2,beta=.5,gripper=.02,project_targets=True):
    assert not learner.actor_opt.state
    learner.actor=RelativeMovement(learner.actor,learner.reference,cap,beta,gripper)
    learner.target_actor=copy.deepcopy(learner.actor).eval().requires_grad_(False)
    learner.actor_opt=torch.optim.AdamW([p for p in learner.actor.parameters() if p.requires_grad],
        lr=learner.cfg['actor_lr'],weight_decay=learner.cfg['weight_decay'])
    learner.cfg=copy.deepcopy(learner.cfg)
    learner.cfg['target_action_projection']='actor_bounds_v1' if project_targets else 'legacy'
    return learner


class ExploringRelativePolicy(nn.Module):
    def __init__(self,policy,reference,seed,cap=.2,beta=.5,gripper=.02):
        super().__init__();self.policy=policy;self.reference=reference
        self.rng=np.random.default_rng(seed+177);self.cap=cap;self.beta=beta;self.gripper=gripper

    def forward(self,x,phase):
        action,done=self.policy(x,phase)
        with torch.no_grad():parent,_=self.reference(x,phase)
        noise=torch.as_tensor(self.rng.normal(size=tuple(action.shape))*np.array([.05,.05,.05,0.]),
                              device=action.device,dtype=action.dtype)
        return project_relative(action+noise,parent,self.cap,self.beta,self.gripper),done


def check(source,out):
    planned=base.protocol()
    planned.update(schema='relative-range-stability-v1',arms=['bounded_C'],action_limit=.2,
        target_action_projection='actor_bounds_v1',
        relative_beta=.5,gripper_limit=.02,development_seeds=list(range(2026112800,2026112806)),
        confirmation_seeds=list(range(2026112900,2026112920)),
        method='XYZ width=min(.2,.5*abs(parent XYZ)); gripper width .02; XYZ sign preserved',
        claim='A single targeted alternative after constant .05 failed, not a post-hoc relaxation of its gate.')
    planned['gate'].update(max_action_mse=.04,bounded_max_abs_delta=.200001)
    planned['confirmation_gate']=dict(max_losses_per_parent=2,max_total_losses=3,min_baseline_successes=10)
    original_inputs=base.fixed_inputs
    def inputs(folder):
        values=original_inputs(folder);values[str(Path(__file__).resolve())]=run.sha(Path(__file__))
        return values
    # Reuse the exact fixed-replay protocol; only policy constraint and seed panel differ.
    original_protocol,original_constrain=base.protocol,base.constrain
    try:
        base.protocol=lambda:copy.deepcopy(planned)
        base.constrain=constrain
        base.fixed_inputs=inputs
        base.main(source,out)
    finally:
        base.protocol=original_protocol;base.constrain=original_constrain;base.fixed_inputs=original_inputs
    shutil.copy2(Path(__file__),out/'source_snapshot/relative_range.py')
    decision=json.loads((out/'decision.json').read_text())
    decision.update(confirmed=False,selected_limit=.2,policy_constraint='relative',next_test_ready=False)
    if decision['candidate_passed_stability']:
        proto=json.loads((out/'protocol.json').read_text())
        deadline=proto['prepared_unix']+planned['total_cap_seconds']
        data,_,manifest=run.load_data(source/'data');baseline={};confirmation={}
        ids=np.concatenate([np.flatnonzero(data['phase']==p)[np.linspace(0,(data['phase']==p).sum()-1,
                          min(64,(data['phase']==p).sum()),dtype=int)] for p in range(7)])
        probe={k:v[ids] for k,v in data.items()}
        used_families={r['initial_sha256'] for r in manifest['rows']}
        used_families.update(r['initial_sha256'] for rows in json.loads((out/'baseline.json').read_text()).values() for r in rows)
        for seed in (1,2,3):
            baseline[str(seed)]=base.evaluate(run.native.historical.load(run.parent(seed)['path']),
                json.loads((source/'config.json').read_text()),out,deadline,planned['confirmation_seeds'],f'confirmation_parent{seed}')
            assert all(r['initial_sha256'] not in used_families for r in baseline[str(seed)])
            run.dump(out/'confirmation_baseline.json',baseline)
        if all(sum(r['success'] for r in rows)>=10 for rows in baseline.values()):
            for seed in (1,2,3):
                cfg=json.loads((source/'config.json').read_text())
                learner=constrain(base.load_checkpoint(seed,data,cfg,source),.2)
                ck=torch.load(out/f'bounded_C_seed{seed}/update500.pth',map_location='cuda',weights_only=False)
                learner.actor.load_state_dict(ck['actor'])
                learner.critic.load_state_dict(ck['critic'])
                rows=base.evaluate(learner.policy(),cfg,out,deadline,planned['confirmation_seeds'],f'confirmation_relative_seed{seed}')
                confirmation[str(seed)]=dict(**paired(baseline[str(seed)],rows),
                    drift=base.drift(learner,probe),episodes=rows)
                run.dump(out/'confirmation.json',confirmation)
            decision['confirmed']=passes(confirmation,planned['confirmation_gate'],.2)
            decision['next_test_ready']=decision['confirmed']
    for path,h in json.loads((out/'protocol.json').read_text())['input_hashes'].items():assert run.sha(path)==h
    run.dump(out/'decision.json',decision)
    run.dump(out/'status.json',dict(state='COMPLETED',updated_unix=time.time(),**decision))
    print(json.dumps(decision))


def prepare(source,study,out):
    decision=json.loads((study/'decision.json').read_text())
    assert decision['candidate_passed_stability'] and decision['confirmed'] and decision['next_test_ready']
    assert json.loads((study/'status.json').read_text())['state']=='COMPLETED'
    proto=json.loads((study/'protocol.json').read_text());inputs=dict(proto['input_hashes'])
    for path,h in inputs.items():assert run.sha(path)==h
    import new_test
    cfg=new_test.settings()
    cfg.update(schema='relative-range-online-pilot-v1',action_limit=.2,technical_only=False,
        target_action_projection='actor_bounds_v1',
        policy_constraint=dict(kind='relative',cap=.2,beta=.5,gripper=.02),
        exploration='XYZ noise std .05 projected to min(.2,.5*abs(parent XYZ)); gripper width .02',
        interpretation='Fresh online pilot of direction-preserving relative action changes, not unrestricted residual RL.')
    cfg['gate']['max_abs_action_delta']=.200001
    for file in (Path(__file__),HERE/'new_test.py',study/'results.json',study/'decision.json',
                 study/'confirmation.json',study/'confirmation_baseline.json'):
        inputs[str(file.resolve())]=run.sha(file)
    assert not out.exists();out.mkdir()
    run.dump(out/'config.json',cfg);inputs[str(out/'config.json')]=run.sha(out/'config.json')
    run.dump(out/'protocol.json',dict(source=str(source),stability=str(study),input_hashes=inputs,
        prepared_unix=time.time(),scientific_training_started=False,
        command=f'praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/relative_range.py run --execute --output "{out}"'))
    snap=out/'source_snapshot';snap.mkdir()
    for name in ('relative_range.py','new_test.py','stability.py','core.py','run.py'):
        shutil.copy2(HERE/name,snap/name)
    run.dump(out/'status.json',dict(state='READY',updated_unix=time.time()))
    print(json.dumps(dict(state='READY',action_limit=.2,kind='relative',started=False)))


def execute(out):
    import new_test
    cfg=json.loads((out/'config.json').read_text());method=cfg['policy_constraint']
    assert method['kind']=='relative'
    projection=cfg.get('target_action_projection','legacy')
    assert projection in ('legacy','actor_bounds_v1')
    new_test.constrain=lambda learner,limit:constrain(learner,limit,method['beta'],method['gripper'],
        project_targets=projection=='actor_bounds_v1')
    new_test.ExploringBoundedPolicy=lambda policy,reference,seed,limit:ExploringRelativePolicy(
        policy,reference,seed,limit,method['beta'],method['gripper'])
    new_test.execute(out)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['check','prepare','run'])
    p.add_argument('--source',type=Path,default=HERE/'night_001')
    p.add_argument('--study',type=Path,default=HERE/'relative_001')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    try:
        if a.command=='check':check(a.source.resolve(),a.output.resolve())
        elif a.command=='prepare':prepare(a.source.resolve(),a.study.resolve(),a.output.resolve())
        else:
            assert a.execute,'Explicit --execute required';execute(a.output.resolve())
    except Exception:
        if a.output.exists():run.dump(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
