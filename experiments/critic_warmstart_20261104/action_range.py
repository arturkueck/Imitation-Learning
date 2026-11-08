"""Bounded, preregistered action-range ladder followed by fresh confirmation."""
from pathlib import Path
import argparse
import json
import os
import shutil
import time
import traceback
import numpy as np
import torch
from stability import run, constrain, drift, evaluate, fixed_inputs, load_checkpoint
from core import concat, sample

HERE=Path(__file__).resolve().parent


def plan():
    return dict(schema='action-range-ladder-v1', action_limits=[.05,.10,.20], seeds=[1,2,3],
        checkpoints=[10,50,100,500], development_seeds=list(range(2026112400,2026112406)),
        confirmation_seeds=list(range(2026112500,2026112520)),
        gate=dict(max_losses_per_parent=1,max_total_losses=1,min_baseline_successes=2),
        confirmation_gate=dict(max_losses_per_parent=2,max_total_losses=3,min_baseline_successes=10),
        ordering='Stop larger bounds after first failed level; select largest fully passed level before confirmation',
        fallback='No alternative selection if fresh confirmation fails; no automatic main training',
        unchanged='Same original parents, warm Critics, BC .01, LR, target smoothing and paired fixed replay as stability_002',
        source_replay='50% original training, 50% same-parent C online_round1; no new training data',
        baseline_reference_limit=.02, wall_clock_cap_seconds=3600, no_automatic_retry=True,
        reserved_final_data_enabled=False,
        interpretation='Development parameter selection. Confirmation is separate development, not a scientific endtest.')


def paired(base, current):
    assert len(base)==len(current)
    assert [r['initial_sha256'] for r in base]==[r['initial_sha256'] for r in current]
    return dict(successes=sum(r['success'] for r in current),
        baseline_successes=sum(r['success'] for r in base),
        paired_losses=sum(b['success'] and not e['success'] for b,e in zip(base,current)),
        paired_wins=sum(not b['success'] and e['success'] for b,e in zip(base,current)))


def passes(rows, gates, bound):
    return (len(rows)==3 and all(r['drift']['finite'] and r['drift']['max_abs_action_delta']<=bound+1e-6
        and r['paired_losses']<=gates['max_losses_per_parent'] for r in rows.values())
        and sum(r['paired_losses'] for r in rows.values())<=gates['max_total_losses'])


def main(source,out):
    planned=plan();cfg=json.loads((source/'config.json').read_text())
    inputs=fixed_inputs(source)
    inputs[str(Path(__file__).resolve())]=run.sha(Path(__file__))
    assert not out.exists()
    out.mkdir()
    run.dump(out/'protocol.json',dict(**planned,prepared_unix=time.time(),input_hashes=inputs))
    snap=out/'source_snapshot';snap.mkdir()
    for file in (Path(__file__),HERE/'stability.py',HERE/'core.py',HERE/'run.py'):
        shutil.copy2(file,snap/file.name)
    deadline=time.time()+planned['wall_clock_cap_seconds']
    torch.set_num_threads(4);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    data,_,manifest=run.load_data(source/'data');bc=run.original_bc()
    source_families={r['initial_sha256'] for r in manifest['rows']}
    ids=np.concatenate([np.flatnonzero(data['phase']==p)[np.linspace(0,(data['phase']==p).sum()-1,
                      min(64,(data['phase']==p).sum()),dtype=int)] for p in range(7)])
    probe={k:v[ids] for k,v in data.items()}
    baseline={};replay={};results={};history=[];passed_levels=[];selected=None
    for seed in planned['seeds']:
        baseline[str(seed)]=evaluate(run.native.historical.load(run.parent(seed)['path']),cfg,out,deadline,
                                    planned['development_seeds'],f'parent{seed}')
        assert all(r['initial_sha256'] not in source_families for r in baseline[str(seed)])
        parts=[]
        for path in sorted((source/f'train/C_seed{seed}/online_round1').glob('*.npz')):
            with np.load(path,allow_pickle=False) as arrays:
                parts.append({k:arrays[k].copy() for k in run.KEYS})
        replay[str(seed)]=concat(parts)
        run.dump(out/'baseline.json',baseline)
    if any(sum(r['success'] for r in rows)<planned['gate']['min_baseline_successes'] for rows in baseline.values()):
        run.dump(out/'status.json',dict(state='BASELINE_GATE_FAILED',updated_unix=time.time()));return
    for bound in planned['action_limits']:
        label=f'limit_{bound:.2f}'
        members={str(s):constrain(load_checkpoint(s,data,cfg,source),bound) for s in planned['seeds']}
        rng={str(s):np.random.default_rng([s,1]) for s in planned['seeds']}
        records=[];previous=0;level_passed=True
        for step in planned['checkpoints']:
            rows={}
            for seed,learner in members.items():
                for _ in range(previous,step):
                    run.stop(out,deadline)
                    batch=concat([sample(data,rng[seed],128),sample(replay[seed],rng[seed],128)])
                    metrics=learner.update(batch,run.bc_batch(bc,rng[seed],256),.01)
                    history.append(dict(bound=bound,seed=seed,step=learner.updates,**metrics))
                dm=drift(learner,probe)
                current=evaluate(learner.policy(),cfg,out,deadline,planned['development_seeds'],f'{label}:seed{seed}:step{step}')
                rows[seed]=dict(**paired(baseline[seed],current),drift=dm,episodes=current)
                folder=out/label/f'seed{seed}';folder.mkdir(parents=True,exist_ok=True)
                learner.save(folder/f'update{step}.pth',dict(action_limit=bound,development_only=True))
            previous=step;level_passed=passes(rows,planned['gate'],bound)
            records.append(dict(critic_updates=step,rows=rows,gate_passed=level_passed))
            results[label]=records
            run.dump(out/'results.json',results);run.dump(out/'history.json',history)
            if not level_passed:break
        if not level_passed:break
        passed_levels.append(bound);selected=members
    chosen=passed_levels[-1] if passed_levels else None
    run.dump(out/'selection.json',dict(selected_limit=chosen,passed_levels=passed_levels,
             selected_before_confirmation=True,selected_checkpoint=500))
    confirmed=False;confirmation={};confirmation_base={}
    if chosen is not None:
        for seed in planned['seeds']:
            confirmation_base[str(seed)]=evaluate(run.native.historical.load(run.parent(seed)['path']),cfg,out,deadline,
                planned['confirmation_seeds'],f'confirmation_parent{seed}')
            assert all(r['initial_sha256'] not in source_families and
                       r['initial_sha256'] not in {v['initial_sha256'] for rows in baseline.values() for v in rows}
                       for r in confirmation_base[str(seed)])
            run.dump(out/'confirmation_baseline.json',confirmation_base)
        base_ok=all(sum(r['success'] for r in rows)>=planned['confirmation_gate']['min_baseline_successes'] for rows in confirmation_base.values())
        if base_ok:
            for seed,learner in selected.items():
                current=evaluate(learner.policy(),cfg,out,deadline,planned['confirmation_seeds'],f'confirmation_limit{chosen}:seed{seed}')
                confirmation[seed]=dict(**paired(confirmation_base[seed],current),drift=drift(learner,probe),episodes=current)
                run.dump(out/'confirmation.json',confirmation)
            confirmed=passes(confirmation,planned['confirmation_gate'],chosen)
    for path,h in inputs.items():assert run.sha(path)==h, f'Changed input: {path}'
    decision=dict(selected_limit=chosen,confirmed=confirmed,passed_levels=passed_levels,
        next_test_ready=confirmed,improvement_established=False,input_hashes_unchanged=True,
        stop_reason='FIRST_FAILED_LEVEL' if len(results)<len(planned['action_limits']) or any(not v[-1]['gate_passed'] for v in results.values()) else 'LADDER_COMPLETED')
    run.dump(out/'decision.json',decision)
    run.dump(out/'status.json',dict(state='COMPLETED',updated_unix=time.time(),pid=os.getpid(),**decision))
    print(json.dumps(decision))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=HERE/'night_001')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:main(args.source.resolve(),args.output.resolve())
    except Exception:
        if args.output.exists():run.dump(args.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
