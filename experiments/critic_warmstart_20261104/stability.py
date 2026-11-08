"""Preregistered fixed-replay stability experiment, isolated from night_001."""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import os
import sys
import time
import traceback
import numpy as np
import torch
from torch import nn
from core import concat, sample

HERE = Path(__file__).resolve().parent
# Historical method.py imports its own `run` module. Loading our CLI under that
# generic name would bind its legacy controller to the wrong module.
_spec = importlib.util.spec_from_file_location('critic_stability_runner', HERE/'run.py')
run = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = run
_spec.loader.exec_module(run)
assert callable(run.native.historical.old.prefix_valid)


class BoundedMovement(nn.Module):
    """Smoothly limit all four movement outputs around the fixed IL actor."""
    def __init__(self, actor, parent, limit):
        super().__init__()
        if not 0 < limit <= 1:
            raise ValueError('Action limit must be in (0,1]')
        self.actor = actor
        self.parent = copy.deepcopy(parent).eval().requires_grad_(False)
        self.limit = float(limit)

    def forward(self, x, phase):
        raw, done = self.actor(x, phase)
        with torch.no_grad():
            base, _ = self.parent(x, phase)
        action = (base+self.limit*torch.tanh((raw-base)/self.limit)).clamp(-1, 1)
        return action, done


def constrain(learner, limit):
    learner.actor = BoundedMovement(learner.actor, learner.reference, limit)
    learner.target_actor = copy.deepcopy(learner.actor).eval().requires_grad_(False)
    # Warmup never updates the actor, so its restored AdamW state must be empty.
    assert not learner.actor_opt.state
    learner.actor_opt = torch.optim.AdamW(
        [p for p in learner.actor.parameters() if p.requires_grad],
        lr=learner.cfg['actor_lr'], weight_decay=learner.cfg['weight_decay'])
    return learner


def protocol():
    return dict(schema='critic-stability-v1', seeds=[1, 2, 3],
        arms=['original_C', 'bounded_C'], checkpoints=[10, 50, 100, 500],
        action_limit=.02, bc_coefficient=.01, development_seeds=list(range(2026112000, 2026112006)),
        replay='50% night_001/data training; 50% same-parent C online_round1, fixed throughout',
        batch_pairing='Same np.random.default_rng([parentseed,1]) stream and original BC batches',
        probe='Up to 64 training frames per phase, evenly spaced; no validation or final data',
        gate=dict(max_abs_action_delta=.100001, max_action_mse=.01,
                  max_paired_losses_per_parent=1, max_total_paired_losses=1,
                  min_baseline_successes_per_parent=2, bounded_max_abs_delta=.020001),
        total_cap_seconds=3600, no_retries=True, no_automatic_resume=True,
        claim='Development stability only. No novelty, improvement, or generalization claim.',
        next_test_development_seeds=list(range(2026112100, 2026112120)),
        next_test_online_seeds=list(range(2026112200, 2026112220)))


@torch.no_grad()
def drift(learner, probe):
    x = learner.tensor(probe['x'], torch.float32)
    phase = learner.tensor(probe['phase'], torch.long)
    action, _ = learner.actor(x, phase)
    parent, _ = learner.reference(x, phase)
    q_old = learner.critic(learner.tensor(probe['state'], torch.float32), parent)[0]
    q_new = learner.critic(learner.tensor(probe['state'], torch.float32), action)[0]
    delta = action-parent
    return dict(action_mse=delta.square().mean().item(), max_abs_action_delta=delta.abs().max().item(),
        q1_gain=(q_new-q_old).mean().item(), finite=bool(torch.isfinite(action).all() and torch.isfinite(q_new).all()))


def gate(metrics, losses, planned, bounded):
    g = planned['gate']
    return bool(metrics['finite'] and metrics['action_mse'] <= g['max_action_mse']
                and metrics['max_abs_action_delta'] <= (g['bounded_max_abs_delta'] if bounded else g['max_abs_action_delta'])
                and losses <= g['max_paired_losses_per_parent'])


def evaluate(model, cfg, out, deadline, seeds, label):
    rows = []
    for i, seed in enumerate(seeds):
        run.dump(out/'status.json', dict(state='STABILITY_EVALUATION', model=label, episode=i+1,
                 total=len(seeds), updated_unix=time.time(), pid=os.getpid()))
        _, row = run.episode(model, seed, cfg, out, deadline)
        rows.append(row)
    return rows


def load_checkpoint(seed, data, cfg, source):
    return run.restore(seed, data, cfg, source/f'warm/seed{seed}/warm.pth')


def fixed_inputs(source):
    hashes = {}
    for phase in ('data', 'warm', 'train'):
        manifest = json.loads((source/phase/'provenance.json').read_text())
        for parent in manifest['parent_checkpoints']:
            hashes[parent['path']] = parent['sha256']
    for path in [source/'config.json', source/'data/manifest.json', source/'data/data_audit.json',
                 source/'warm/validation.json', HERE/'core.py', HERE/'run.py', Path(__file__)]:
        hashes[str(path)] = run.sha(path)
    for seed in (1, 2, 3):
        path = source/f'warm/seed{seed}/warm.pth'
        hashes[str(path)] = run.sha(path)
        for path in sorted((source/f'train/C_seed{seed}/online_round1').glob('*.npz')):
            hashes[str(path)] = run.sha(path)
    hashes[str(run.ARRAYS)] = run.sha(run.ARRAYS)
    return hashes


def main(source, out):
    planned = protocol()
    cfg = json.loads((source/'config.json').read_text())
    assert cfg['seeds'] == planned['seeds'] and cfg['arms']['C']['bc_coefficient'] == .01
    assert set(planned['development_seeds']).isdisjoint(range(2026111600, 2026111650))
    inputs = fixed_inputs(source)
    assert not out.exists()
    out.mkdir()
    run.dump(out/'protocol.json', {**planned, 'prepared_unix': time.time(), 'input_hashes': inputs})
    snapshot = out/'source_snapshot'
    snapshot.mkdir()
    import shutil
    for file in (Path(__file__), HERE/'core.py', HERE/'run.py'):
        shutil.copy2(file, snapshot/file.name)
    deadline = time.time()+planned['total_cap_seconds']
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    data, _, manifest = run.load_data(source/'data')
    assert manifest['ready_for_training'] and run.sha(source/'data/data_audit.json') == manifest['data_audit_sha256']
    bc = run.original_bc()
    ids = np.concatenate([np.flatnonzero(data['phase'] == phase)[np.linspace(0, (data['phase'] == phase).sum()-1,
                         min(64, (data['phase'] == phase).sum()), dtype=int)] for phase in range(7)])
    probe = {key: values[ids] for key, values in data.items()}
    baseline, results, histories = {}, {}, []
    source_families = {r['initial_sha256'] for r in manifest['rows']}
    for seed in planned['seeds']:
        baseline[str(seed)] = evaluate(run.native.historical.load(run.parent(seed)['path']), cfg, out,
                                      deadline, planned['development_seeds'], f'parent{seed}')
        assert all(r['initial_sha256'] not in source_families for r in baseline[str(seed)])
        run.dump(out/'baseline.json', baseline)
    baseline_ok = all(sum(r['success'] for r in rows) >= planned['gate']['min_baseline_successes_per_parent']
                      for rows in baseline.values())
    if not baseline_ok:
        run.dump(out/'status.json', dict(state='BASELINE_GATE_FAILED', updated_unix=time.time()))
        return
    for seed in planned['seeds']:
        parts = []
        for path in sorted((source/f'train/C_seed{seed}/online_round1').glob('*.npz')):
            with np.load(path, allow_pickle=False) as arrays:
                parts.append({k: arrays[k].copy() for k in run.KEYS})
        online = concat(parts)
        for arm in planned['arms']:
            learner = load_checkpoint(seed, data, cfg, source)
            if arm == 'bounded_C':
                constrain(learner, planned['action_limit'])
            assert drift(learner, probe)['max_abs_action_delta'] < 1e-6
            rng = np.random.default_rng([seed, 1])
            folder = out/f'{arm}_seed{seed}'
            folder.mkdir()
            rows = []
            previous = 0
            for step in planned['checkpoints']:
                for _ in range(previous, step):
                    run.stop(out, deadline)
                    batch = concat([sample(data, rng, 128), sample(online, rng, 128)])
                    metrics = learner.update(batch, run.bc_batch(bc, rng, 256), .01)
                    histories.append(dict(model=f'{arm}_seed{seed}', step=learner.updates, **metrics))
                previous = step
                dm = drift(learner, probe)
                ev = evaluate(learner.policy(), cfg, out, deadline, planned['development_seeds'], f'{arm}_seed{seed}:step{step}')
                base = baseline[str(seed)]
                assert [r['initial_sha256'] for r in ev] == [r['initial_sha256'] for r in base]
                losses = sum(b['success'] and not e['success'] for b, e in zip(base, ev))
                wins = sum(not b['success'] and e['success'] for b, e in zip(base, ev))
                passed = gate(dm, losses, planned, arm == 'bounded_C')
                rows.append(dict(critic_updates=step, actor_updates=step//2, baseline_successes=sum(r['success'] for r in base),
                                 successes=sum(r['success'] for r in ev), paired_losses=losses, paired_wins=wins,
                                 drift=dm, gate_passed=passed, episodes=ev))
                learner.save(folder/f'update{step}.pth', dict(development_only=True, stability_gate_passed=passed))
                results[f'{arm}_seed{seed}'] = rows
                run.dump(out/'results.json', results)
                run.dump(out/'history.json', histories)
                if not passed:
                    break
    candidate = [results[f'bounded_C_seed{s}'] for s in planned['seeds']]
    passed = all(len(rows) == len(planned['checkpoints']) and all(row['gate_passed'] for row in rows) for rows in candidate)
    for i in range(len(planned['checkpoints'])):
        if all(len(rows) > i for rows in candidate):
            passed = passed and sum(rows[i]['paired_losses'] for rows in candidate) <= planned['gate']['max_total_paired_losses']
        else:
            passed = False
    for path, expected in inputs.items():
        assert run.sha(path) == expected, f'Changed input: {path}'
    run.dump(out/'decision.json', dict(candidate_passed_stability=passed,
             next_test='PREPARE_FRESH_ONLINE_PILOT' if passed else 'BLOCKED_BY_STABILITY_GATE',
             improvement_established=False, source_inputs_unchanged=True, evaluated_seeds=planned['development_seeds']))
    run.dump(out/'status.json', dict(state='COMPLETED', candidate_passed_stability=passed, updated_unix=time.time(), pid=os.getpid()))
    print(json.dumps(dict(state='COMPLETED', candidate_passed_stability=passed)))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=HERE/'night_001')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        main(args.source.resolve(), args.output.resolve())
    except Exception:
        if args.output.exists():
            run.dump(args.output/'status.json', dict(state='ERROR', error=traceback.format_exc(), updated_unix=time.time()))
        raise
