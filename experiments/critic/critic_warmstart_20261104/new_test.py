"""Prepare a fresh, gated online pilot after the fixed-replay stability gate."""
from pathlib import Path
import argparse
import json
import os
import time
import traceback
import numpy as np
import torch
from torch import nn
from stability import run, constrain, drift, evaluate, fixed_inputs
from core import concat, sample

HERE = Path(__file__).resolve().parent


class ExploringBoundedPolicy(nn.Module):
    """Exploration is projected too; executed actions retain the same IL bound."""
    def __init__(self, policy, reference, seed, limit=.02):
        super().__init__()
        self.policy = policy
        self.reference = reference
        self.rng = np.random.default_rng(seed+177)
        self.limit = limit

    def forward(self, x, phase):
        action, done = self.policy(x, phase)
        with torch.no_grad():
            base, _ = self.reference(x, phase)
        noise = torch.as_tensor(self.rng.normal(size=tuple(action.shape))*np.array([.05,.05,.05,0.]),
                                device=action.device, dtype=action.dtype)
        return torch.maximum(torch.minimum(action+noise, base+self.limit), base-self.limit).clamp(-1,1), done


def settings():
    return dict(schema='bounded-online-pilot-v1', action_limit=.02, seeds=[1,2,3],
        rounds=4, episodes_per_round=5, critic_updates_per_round=500,
        evaluation_rounds=[0,1,2,4], development_seeds=list(range(2026112100,2026112120)),
        online_seed_start=2026112200, development_only=True, final_tests_enabled=False,
        actor_bc_coefficient=.01, replay_demo_fraction=.5,
        source='Same original IL parents and prewarmed Critics as night_001, fresh actor optimizer; no collapsed actors',
        exploration='Original XYZ noise std .05, then project executed action to IL-parent +/- .02; gripper noise zero',
        target_smoothing='Same TD3 target smoothing as stability test; noisy critic target actions are not certified by the executed-action bound',
        gate=dict(min_parent_successes_per_seed=10, max_paired_losses_per_seed=2,
                  max_paired_losses_total=3, max_abs_action_delta=.020001),
        wall_clock_cap_seconds=3600, no_automatic_retry=True, fixed_checkpoint_round=4,
        interpretation='Fresh online development pilot. Stability is prerequisite, not proof of improvement or novelty.')


def prepare(source, stability, out, technical=False):
    decision=json.loads((stability/'decision.json').read_text())
    assert decision['candidate_passed_stability'], 'Do not prepare a new pilot after a failed stability gate'
    assert json.loads((stability/'status.json').read_text())['state']=='COMPLETED'
    stability_protocol=json.loads((stability/'protocol.json').read_text())
    for path,expected in stability_protocol['input_hashes'].items():
        assert run.sha(path)==expected, f'Stability input changed: {path}'
    results=json.loads((stability/'results.json').read_text())
    for seed in (1,2,3):
        rows=results[f'bounded_C_seed{seed}']
        assert [r['critic_updates'] for r in rows]==[10,50,100,500] and all(r['gate_passed'] for r in rows)
    cfg=settings()
    cfg['technical_only']=technical
    if technical:
        cfg.update(seeds=[1], rounds=1, episodes_per_round=1, critic_updates_per_round=4,
                   evaluation_rounds=[0,1], development_seeds=[2026112050],
                   online_seed_start=2026112051, fixed_checkpoint_round=1, wall_clock_cap_seconds=600)
        cfg['gate'].update(min_parent_successes_per_seed=0, max_paired_losses_per_seed=0, max_paired_losses_total=0)
    assert len(set(cfg['development_seeds']) & set(range(2026111600,2026111650)))==0
    hashes=fixed_inputs(source)
    for path in (Path(__file__), stability/'protocol.json', stability/'decision.json', stability/'results.json'):
        hashes[str(path.resolve())]=run.sha(path)
    assert not out.exists()
    out.mkdir()
    run.dump(out/'config.json',cfg)
    hashes[str(out/'config.json')]=run.sha(out/'config.json')
    run.dump(out/'protocol.json',dict(source=str(source), stability=str(stability), input_hashes=hashes,
             prepared_unix=time.time(), scientific_training_started=False,
             command=f'praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/new_test.py run --execute --output "{out}"'))
    run.dump(out/'status.json',dict(state='READY',updated_unix=time.time()))
    print(json.dumps(dict(state='READY',output=str(out),started=False)))


def performance_gate(baseline, rows, cfg):
    assert set(rows)==set(baseline)
    assert all(len(rows[s])==len(baseline[s])==len(cfg['development_seeds']) for s in baseline)
    losses={seed:sum(b['success'] and not e['success'] for b,e in zip(baseline[seed],rows[seed])) for seed in baseline}
    return all(v<=cfg['gate']['max_paired_losses_per_seed'] for v in losses.values()) and sum(losses.values())<=cfg['gate']['max_paired_losses_total'],losses


def execute(out):
    cfg=json.loads((out/'config.json').read_text())
    proof=json.loads((out/'protocol.json').read_text())
    for path,h in proof['input_hashes'].items():
        assert run.sha(path)==h, f'Prepared input changed: {path}'
    assert json.loads((out/'status.json').read_text())['state']=='READY'
    assert not (out/'STOP').exists()
    with (out/'launch.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(started_unix=time.time(),pid=os.getpid(),no_resume=True),stream)
    source=Path(proof['source'])
    old_cfg=json.loads((source/'config.json').read_text())
    deadline=time.time()+cfg['wall_clock_cap_seconds']
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    data,_,manifest=run.load_data(source/'data')
    bc=run.original_bc()
    ids=np.concatenate([np.flatnonzero(data['phase']==p)[::max(1,(data['phase']==p).sum()//64)][:64] for p in range(7)])
    probe={k:v[ids] for k,v in data.items()}
    members={};baseline={};evaluation={};history=[];episodes=[];online_families={}
    source_families={v['initial_sha256'] for v in manifest['rows']}
    for seed in cfg['seeds']:
        learner=run.restore(seed,data,old_cfg,source/f'warm/seed{seed}/warm.pth')
        constrain(learner,cfg['action_limit'])
        baseline[str(seed)]=evaluate(learner.policy(),old_cfg,out,deadline,cfg['development_seeds'],f'parent{seed}')
        assert all(r['initial_sha256'] not in source_families for r in baseline[str(seed)])
        members[str(seed)]=dict(learner=learner,online=[],interactions=0)
        run.dump(out/'baseline.json',baseline)
    if any(sum(r['success'] for r in rows)<cfg['gate']['min_parent_successes_per_seed'] for rows in baseline.values()):
        run.dump(out/'status.json',dict(state='BASELINE_GATE_FAILED',updated_unix=time.time()))
        return
    for round_ in range(1,cfg['rounds']+1):
        for seed,m in members.items():
            learner=m['learner']
            for i in range(cfg['episodes_per_round']):
                run.dump(out/'status.json',dict(state='ONLINE_COLLECTION',seed=seed,round=round_,episode=i+1,updated_unix=time.time()))
                start=cfg['online_seed_start']+(round_-1)*cfg['episodes_per_round']+i
                model=ExploringBoundedPolicy(learner.policy(),learner.reference,start,cfg['action_limit'])
                arrays,row=run.episode(model,start,old_cfg,out,deadline)
                assert row['initial_sha256'] not in source_families
                assert row['initial_sha256'] not in {r['initial_sha256'] for rows in baseline.values() for r in rows}
                assert online_families.setdefault(start,row['initial_sha256'])==row['initial_sha256']
                episodes.append(run.store_episode(out/f'online/seed{seed}/round{round_}',arrays,row,'online'))
                run.dump(out/'online_manifest.json',dict(complete=False,rows=episodes))
                m['online'].append(arrays);m['interactions']+=len(arrays['x'])
            replay=concat(m['online']);rng=np.random.default_rng([int(seed),round_])
            for i in range(cfg['critic_updates_per_round']):
                run.stop(out,deadline)
                batch=concat([sample(data,rng,128),sample(replay,rng,128)])
                metrics=learner.update(batch,run.bc_batch(bc,rng,256),cfg['actor_bc_coefficient'])
                if i==0 or (i+1)%50==0 or i+1==cfg['critic_updates_per_round']:
                    dm=drift(learner,probe)
                    assert dm['finite'] and dm['max_abs_action_delta']<=cfg['gate']['max_abs_action_delta']
                    history.append(dict(seed=seed,round=round_,step=learner.updates,interactions=m['interactions'],drift=dm,**metrics))
                    run.dump(out/'history.json',history)
                    run.dump(out/'status.json',dict(state='TRAINING',seed=seed,round=round_,step=learner.updates,updated_unix=time.time()))
            folder=out/f'seed{seed}';folder.mkdir(exist_ok=True)
            learner.save(folder/f'round{round_}.pth',dict(action_limit=cfg['action_limit'],bounded_actor=True,interactions=m['interactions']))
        if round_ in cfg['evaluation_rounds']:
            current={}
            for seed,m in members.items():
                current[seed]=evaluate(m['learner'].policy(),old_cfg,out,deadline,cfg['development_seeds'],f'seed{seed}:round{round_}')
                assert [r['initial_sha256'] for r in current[seed]]==[r['initial_sha256'] for r in baseline[seed]]
            passed,losses=performance_gate(baseline,current,cfg)
            evaluation[str(round_)]=dict(rows=current,paired_losses=losses,gate_passed=passed)
            run.dump(out/'development.json',evaluation)
            if not passed:
                run.dump(out/'status.json',dict(state='PERFORMANCE_GATE_FAILED',round=round_,paired_losses=losses,updated_unix=time.time()))
                return
    frozen={}
    for seed in members:
        path=out/f"seed{seed}/round{cfg['fixed_checkpoint_round']}.pth"
        frozen[seed]=dict(path=str(path),sha256=run.sha(path),fixed_last_round=True)
    run.dump(out/'frozen_final.json',frozen)
    run.dump(out/'online_manifest.json',dict(complete=True,rows=episodes))
    for path,h in proof['input_hashes'].items():
        assert run.sha(path)==h
    run.dump(out/'status.json',dict(state='COMPLETED',updated_unix=time.time()))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['prepare','run','smoke'])
    p.add_argument('--source',type=Path,default=HERE/'night_001')
    p.add_argument('--stability',type=Path,default=HERE/'stability_002')
    p.add_argument('--output',type=Path,default=HERE/'pilot_001')
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.command in ('prepare','smoke'):
        prepare(args.source.resolve(),args.stability.resolve(),args.output.resolve(),technical=args.command=='smoke')
        if args.command=='smoke':
            execute(args.output.resolve())
    else:
        assert args.execute,'Explicit --execute required'
        try:
            execute(args.output.resolve())
        except Exception:
            if (args.output/'launch.json').exists():
                run.dump(args.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
            raise
