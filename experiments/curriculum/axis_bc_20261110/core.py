"""Exposure-matched offline curriculum; historical policy and controller adapters."""
from pathlib import Path
import hashlib
import json
import os
import random
import sys
import time

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARRAYS = ROOT / 'experiments/self_imitation/stack_phased_8h_20261023/training_arrays.npz'
MANIFEST = ARRAYS.with_name('dataset_manifest.json')
DATA = ROOT / 'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'


def dump(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def backend():
    os.environ.setdefault('NUMBA_CACHE_DIR', str(HERE / 'runtime/numba_cache'))
    sys.path.insert(0, str(ROOT / 'experiments/self_imitation/retreat_gate_20261104'))
    import compare
    return compare


def load_data():
    with np.load(ARRAYS, allow_pickle=False) as archive:
        data = {s: tuple(archive[s + '_' + k].copy() for k in ('x', 'a', 'p', 'y'))
                for s in ('train', 'valid')}
    for x, a, p, y in data.values():
        n = len(x)
        if x.shape != (n, 10) or a.shape != (n, 4) or p.shape != (n,) or y.shape != (n,):
            raise ValueError('Unexpected dataset shapes')
        if not all(np.isfinite(v).all() for v in (x, a, p, y)):
            raise ValueError('Nonfinite dataset values')
        if not np.isin(p, range(7)).all() or not np.isin(y, (0, 1)).all() or np.abs(a).max() > 1.00001:
            raise ValueError('Invalid phase, completion, or action labels')
    manifest = json.loads(MANIFEST.read_text())
    if set(manifest['split_ids']['train']) & set(manifest['split_ids']['valid']):
        raise ValueError('Overlapping demonstration splits')
    return data


def pools(data, threshold):
    a = data[1]
    return {
        'X': np.flatnonzero((np.abs(a[:, 0]) > threshold) &
                            (np.max(np.abs(a[:, 1:3]), axis=1) <= threshold)),
        'XY': np.flatnonzero((np.max(np.abs(a[:, :2]), axis=1) > threshold) &
                             (np.abs(a[:, 2]) <= threshold)),
        'XYZ': np.arange(len(a)),
    }


def validate_config(cfg):
    ends = [s['end_update'] for s in cfg['stages']]
    if [s['name'] for s in cfg['stages']] != ['X', 'XY', 'XYZ']:
        raise ValueError('Expected X, XY, XYZ stages')
    if not (0 < ends[0] < ends[1] < ends[2] == cfg['updates']):
        raise ValueError('Invalid stage boundaries')
    if cfg['arms'] != ['mixed', 'curriculum'] or len(set(cfg['seeds'])) != len(cfg['seeds']):
        raise ValueError('Invalid paired experiment')
    if cfg['batch_size'] < 1 or not 0 < cfg['axis_threshold'] < 1:
        raise ValueError('Invalid sampling settings')
    if any(not 0 <= s['focus_fraction'] <= 1 for s in cfg['stages']):
        raise ValueError('Invalid focus fraction')
    if cfg['evaluation_updates'][-1] != cfg['updates'] or any(u < 1 or u > cfg['updates'] for u in cfg['evaluation_updates']):
        raise ValueError('Invalid evaluation updates')
    dev = set(range(cfg['development_seeds'][0], cfg['development_seeds'][1] + 1))
    final = set(range(cfg['final_seeds'][0], cfg['final_seeds'][1] + 1))
    if not dev or not final or dev & final or cfg['technical_seed'] in dev | final:
        raise ValueError('Overlapping or empty evaluation namespaces')


def schedule(data, cfg, seed):
    """Same complete minibatch multiset, globally permuted for the control arm."""
    groups = pools(data, cfg['axis_threshold'])
    if any(len(v) == 0 for v in groups.values()):
        raise ValueError('Empty curriculum pool; do not silently fall back')
    rng = np.random.default_rng(seed)
    n, b = cfg['updates'], cfg['batch_size']
    batches = np.empty((n, b), dtype=np.int32)
    phase_groups = {}
    for name, ids in groups.items():
        phase_groups[name] = [ids[data[2][ids] == p] for p in range(7)]
        phase_groups[name] = [v for v in phase_groups[name] if len(v)]

    def draw(name, count):
        # Uniform over supported phases, then over frames within that phase.
        g = phase_groups[name]
        chosen = rng.integers(len(g), size=count)
        result = np.empty(count, dtype=np.int32)
        for j, candidates in enumerate(g):
            mask = chosen == j
            result[mask] = rng.choice(candidates, size=int(mask.sum()))
        return result

    start = 0
    for stage in cfg['stages']:
        end = stage['end_update']
        focus = round(b * stage['focus_fraction'])
        block = batches[start:end]
        block[:, :focus] = draw(stage['name'], (end-start)*focus).reshape(end-start, focus)
        block[:, focus:] = draw('XYZ', (end-start)*(b-focus)).reshape(end-start, b-focus)
        start = end
    permutation = np.random.default_rng(seed + 100000).permutation(n)
    return batches, permutation


def configure(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)


def check_stop(out, deadline):
    if (out / 'STOP').exists():
        raise InterruptedError('STOP requested')
    if time.time() >= deadline:
        raise TimeoutError('Wall-clock budget exhausted')


def step(model, opt, data, ids, weights, cfg, update, device):
    x, a, p, y = [torch.as_tensor(v[ids], device=device) for v in data]
    pred, done = model(x, p)
    actor = (pred-a).square().mean()
    mask = p < 6
    completion = torch.nn.functional.binary_cross_entropy_with_logits(
        done[mask], y[mask], pos_weight=weights[p[mask]]) if mask.any() else done.sum()*0
    loss = actor + cfg['completion_coefficient']*completion
    if not torch.isfinite(loss):
        raise FloatingPointError('Nonfinite loss')
    for group in opt.param_groups:
        group['lr'] = cfg['lr'] * min(update / cfg['warmup_updates'], 1)
    opt.zero_grad(set_to_none=True)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['gradient_clip'])
    if not torch.isfinite(norm):
        raise FloatingPointError('Nonfinite gradient')
    opt.step()
    return dict(loss=float(loss.detach()), action_mse=float(actor.detach()),
                completion_bce=float(completion.detach()), gradient_norm=float(norm))


def positive_weights(data, device):
    p, y = data[2:]
    values = [min(50., max(1., float((1-y[p == k]).sum()) / max(float(y[p == k].sum()), 1))) for k in range(7)]
    return torch.tensor(values, device=device)


@torch.no_grad()
def offline(model, data, device, threshold):
    pred = []
    for start in range(0, len(data[0]), 512):
        a, _ = model(torch.as_tensor(data[0][start:start+512], device=device),
                     torch.as_tensor(data[2][start:start+512], device=device))
        pred.append(a.cpu().numpy())
    errors = (np.concatenate(pred)-data[1])**2
    groups = pools(data, threshold)
    return dict(action_mse=float(errors.mean()),
                axis_mse=errors[:, :3].mean(0).tolist(),
                pool_mse={k: float(errors[v].mean()) if len(v) else None for k, v in groups.items()})


class DevicePolicy:
    """Same historical phase policy, with explicit device selection."""
    def __init__(self, model, historical, threshold):
        self.model, self.historical, self.threshold = model, historical, threshold
        self.device = next(model.parameters()).device
        self.reset()

    def reset(self):
        self.phase, self.steps, self.anchor = 0, 0, None

    @torch.no_grad()
    def action(self, obs, target, source):
        if self.anchor is None:
            self.anchor = (source if self.phase < 4 else target).copy()
        x = self.historical.vector(obs, self.anchor, self.steps)
        a, z = self.model(torch.as_tensor(x[None], device=self.device),
                          torch.tensor([self.phase], device=self.device))
        probability = float(z.sigmoid()[0])
        action = np.zeros(7)
        action[[0, 1, 2, 6]] = a[0].cpu().numpy()
        if not np.isfinite(action).all():
            raise FloatingPointError('Nonfinite rollout action')
        phase = self.phase
        self.steps += 1
        if phase < 6 and probability >= self.threshold:
            self.phase += 1
            self.steps, self.anchor = 0, None
        return action, phase, probability


@torch.no_grad()
def evaluate(model, cfg, count, seeds, out, deadline, frame_cap=None):
    controller = backend()
    historical = controller.native.historical
    env = historical.make_env(count)
    rows = []
    try:
        model.eval()
        for seed in seeds:
            check_stop(out, deadline)
            random.seed(seed)
            np.random.seed(seed)
            env.reset()
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            initial = env.sim.get_state().flatten().copy()
            seq = controller.GuardedSequencer(model, count, controller.Clearance(env))
            seq.policy = DevicePolicy(model, historical, cfg['completion_threshold'])
            tail, first, grasped, lifted = 0, False, False, False
            horizon = 500*(count-1)
            for frame in range(min(horizon, frame_cap or horizon)):
                check_stop(out, deadline)
                positions = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                action, _, _ = seq.policy.action(obs, positions[seq.stage-1], positions[seq.stage])
                env.step(action)
                env.sim.forward()
                obs = env._get_observations(force_update=True)
                valid = [historical.old.prefix_valid(env, k) and
                         not any(controller.native.finger_contact(env, c) for c in env.cubes[:k])
                         for k in range(2, count+1)]
                grasped |= bool(env._check_grasp(env.robots[0].gripper, env.cubes[1].contact_geoms))
                lifted |= bool(env.sim.data.body_xpos[env.cube_ids[1]][2] > env.table_offset[2]+.05)
                seq.advance(valid[seq.stage-1], env.sim.data.body_xpos[env.cube_ids[seq.stage]])
                first |= bool(valid[0])
                tail = tail+1 if valid[-1] else 0
                if tail >= 50 or seq.timed_out:
                    break
            rows.append(dict(seed=seed, success=tail >= 50, frames=frame+1,
                             initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
                             first_pair_valid_seen=first, grasp_seen=grasped, lift_seen=lifted,
                             retreat_timeout=seq.timed_out, stable_tail_frames=tail))
    finally:
        env.close()
        model.train()
    return dict(count=count, complete=True, technical_only=frame_cap is not None,
                successes=sum(r['success'] for r in rows), n=len(rows), rows=rows)
