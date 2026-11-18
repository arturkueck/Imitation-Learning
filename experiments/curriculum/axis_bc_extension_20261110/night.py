"""Prepare and run a bounded continuation of six completed BC models."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.with_name('axis_bc_20261110')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def libraries():
    sys.path.insert(0, str(BASE))
    import core
    import torch
    import numpy as np
    return core, torch, np


def verify(out):
    base, _, _ = libraries()
    proof = read(out/'provenance.json')
    for key in ('input_hashes', 'library_source_hashes'):
        for path, expected in proof[key].items():
            if base.sha(ROOT/path) != expected:
                raise ValueError('Frozen input changed: '+path)
    for name, expected in proof['versions'].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError('Library changed: '+name)


def validate(plan, cfg):
    end = plan['start_update']+plan['additional_updates']
    if plan['start_update'] != cfg['updates'] or plan['additional_updates'] <= 0:
        raise ValueError('Invalid continuation boundaries')
    if plan['evaluation_updates'] != sorted(set(plan['evaluation_updates'])) or plan['evaluation_updates'][-1] != end:
        raise ValueError('Invalid evaluation schedule')
    if any(u <= plan['start_update'] or u > end for u in plan['evaluation_updates']):
        raise ValueError('Evaluation outside continuation')
    namespaces = [set(range(*[r[0], r[1]+1])) for r in
                  (cfg['development_seeds'], cfg['final_seeds'], plan['confirmation_seeds'], plan['technical_seeds'])]
    if any(not s for s in namespaces) or any(a & b for i, a in enumerate(namespaces) for b in namespaces[i+1:]):
        raise ValueError('Evaluation namespaces overlap or are empty')


def common_batches(data, count, batch_size, seed):
    _, _, np = libraries()
    rng = np.random.default_rng(seed)
    phases = rng.integers(7, size=(count, batch_size))
    batches = np.empty((count, batch_size), dtype=np.int32)
    for phase in range(7):
        candidates = np.flatnonzero(data[2] == phase)
        if not len(candidates):
            raise ValueError('Missing training phase')
        mask = phases == phase
        batches[mask] = rng.choice(candidates, size=int(mask.sum()))
    return batches


def restore(checkpoint, cfg, device):
    base, torch, _ = libraries()
    model = base.backend().native.historical.PhaseNet(cfg['width']).to(device)
    model.load_state_dict(checkpoint['model'])
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['lr'], weight_decay=cfg['weight_decay'])
    optimizer.load_state_dict(checkpoint['optimizer'])
    return model, optimizer


def prepare(out):
    base, torch, _ = libraries()
    if out.exists():
        raise FileExistsError('Use a new output directory')
    plan = read(HERE/'config.json')
    parent = ROOT/plan['parent']
    cfg = read(parent/'config.json')
    validate(plan, cfg)
    from train import verify as verify_parent
    verify_parent(parent)
    if read(parent/'status.json')['state'] != 'TRAINING_COMPLETE':
        raise ValueError('Parent training is incomplete')
    frozen = read(parent/'final_test/frozen.json')
    parents = {}
    proof = read(parent/'provenance.json')
    inputs = dict(proof['input_hashes'])
    for seed in cfg['seeds']:
        for arm in cfg['arms']:
            name = f'{arm}_seed{seed}'
            path = parent/name/'latest.pth'
            digest = base.sha(path)
            if digest != frozen[name]:
                raise ValueError('Parent differs from previously frozen model: '+name)
            ck = torch.load(path, map_location='cpu', weights_only=False)
            if ck['update'] != plan['start_update'] or ck['technical_only'] or ck['config'] != cfg:
                raise ValueError('Invalid parent checkpoint: '+name)
            if not ck['optimizer']['state']:
                raise ValueError('Missing optimizer state')
            parents[name] = dict(path=str(path.relative_to(ROOT)), sha256=digest, seed=seed, arm=arm)
            inputs[str(path.relative_to(ROOT))] = digest
    sources = list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+[HERE/'config.json']
    for path in sources:
        inputs[str(path.relative_to(ROOT))] = base.sha(path)
    out.mkdir(parents=True)
    write(out/'plan.json', plan)
    write(out/'base_config.json', cfg)
    write(out/'parents.json', parents)
    for name in ('plan.json', 'base_config.json', 'parents.json'):
        inputs[str((out/name).relative_to(ROOT))] = base.sha(out/name)
    for path in sources:
        target = out/'source_snapshot'/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
    write(out/'provenance.json', dict(input_hashes=inputs,
          library_source_hashes=proof['library_source_hashes'], versions=proof['versions'],
          prepared_unix=time.time(), parent_provenance_sha256=base.sha(parent/'provenance.json')))
    write(out/'status.json', dict(state='READY', completed_round=plan['start_update'],
          updated_unix=time.time(), training_started=False))
    print(json.dumps(dict(state='READY', models=len(parents), additional_updates=plan['additional_updates'],
                         total_wall_clock_cap_seconds=plan['wall_clock_cap_seconds'], output=str(out))))


def completion_metrics(model, data, cfg, device, weights):
    """Teacher-forced frame classification, not measured online switch timing."""
    _, torch, np = libraries()
    logits = []
    with torch.no_grad():
        for start in range(0, len(data[0]), 512):
            _, z = model(torch.as_tensor(data[0][start:start+512], device=device),
                         torch.as_tensor(data[2][start:start+512], device=device))
            logits.append(z.cpu())
    z = torch.cat(logits)
    phase = torch.as_tensor(data[2])
    y = torch.as_tensor(data[3])
    w = weights.detach().cpu()
    probability = z.sigmoid()
    prediction = probability >= cfg['completion_threshold']
    truth = y.bool()
    mask = phase < 6
    total_bce = float(torch.nn.functional.binary_cross_entropy_with_logits(z[mask], y[mask], pos_weight=w[phase[mask]]))
    result = dict(weighted_bce=total_bce, threshold=cfg['completion_threshold'], phases={})
    for p in range(6):
        m = phase == p
        tp = int((prediction[m] & truth[m]).sum())
        fp = int((prediction[m] & ~truth[m]).sum())
        fn = int((~prediction[m] & truth[m]).sum())
        precision = tp/(tp+fp) if tp+fp else None
        recall = tp/(tp+fn) if tp+fn else None
        result['phases'][p] = dict(frames=int(m.sum()), positives=int(truth[m].sum()),
            tp=tp, fp=fp, fn=fn, precision=precision, recall=recall,
            f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            weighted_bce=float(torch.nn.functional.binary_cross_entropy_with_logits(z[m], y[m], pos_weight=w[p])))
    return result


def offline(model, data, cfg, device, weights):
    base, _, _ = libraries()
    model.eval()
    result = base.offline(model, data, device, cfg['axis_threshold'])
    result['completion'] = completion_metrics(model, data, cfg, device, weights)
    result['total_validation_loss'] = result['action_mse']+cfg['completion_coefficient']*result['completion']['weighted_bce']
    model.train()
    return result


def save_member(out, member, plan, cfg, technical):
    _, torch, _ = libraries()
    state = dict(model=member['model'].state_dict(), optimizer=member['optimizer'].state_dict(),
        update=member['update'], config=cfg, extension_plan=plan, technical_only=technical,
        parent=member['parent'], seed=member['seed'], arm=member['arm'],
        sampler_sha256=member['sampler_sha256'], next_batch=member['update']-plan['start_update'],
        torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])
    path = out/member['name']/'latest.pth'
    tmp = path.with_suffix('.tmp')
    torch.save(state, tmp)
    tmp.replace(path)


def run(out, device, deadline=None, prepared=None):
    base, torch, np = libraries()
    technical = prepared is not None
    verify(prepared or out)
    plan = copy.deepcopy(read((prepared or out)/'plan.json'))
    cfg = read((prepared or out)/'base_config.json')
    parents = read((prepared or out)/'parents.json')
    if technical:
        plan.update(additional_updates=3, evaluation_updates=[plan['start_update']+3], wall_clock_cap_seconds=600)
        parents = {k: v for k, v in parents.items() if v['seed'] == cfg['seeds'][0]}
        out.mkdir(parents=True, exist_ok=False)
        write(out/'plan.json', plan)
        write(out/'base_config.json', cfg)
    elif read(out/'status.json')['state'] != 'READY':
        raise ValueError('Expected READY; no automatic resume')
    if (out/'STOP').exists():
        raise InterruptedError('STOP requested before launch')
    with (out/'launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time(), technical_only=technical), stream)
    started = time.time()
    deadline = deadline or started+plan['wall_clock_cap_seconds']
    state = dict(state='INITIALIZING', pid=os.getpid(), started_unix=started, deadline=deadline,
                 technical_only=technical, completed_round=plan['start_update'], updated_unix=started)
    write(out/'status.json', state)
    members, schedules = [], {}
    try:
        base.configure(cfg['seeds'][0])
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable')
        data = base.load_data()
        weights = base.positive_weights(data['train'], device)
        for name, parent in parents.items():
            base.check_stop(out, deadline)
            seed = parent['seed']
            if seed not in schedules:
                schedules[seed] = common_batches(data['train'], plan['additional_updates'],
                    cfg['batch_size'], seed+plan['sampler_seed_offset'])
                np.savez_compressed(out/f'schedule_seed{seed}.npz', batches=schedules[seed])
            ck = torch.load(ROOT/parent['path'], map_location='cpu', weights_only=False)
            model, optimizer = restore(ck, cfg, device)
            folder = out/name
            folder.mkdir()
            member = dict(name=name, model=model, optimizer=optimizer, seed=seed, arm=parent['arm'],
                          update=plan['start_update'], parent=parent,
                          sampler_sha256=hashlib.sha256(schedules[seed].tobytes()).hexdigest())
            members.append(member)
            write(folder/'offline_u30000.json', offline(model, data['valid'], cfg, device, weights))
            save_member(out, member, plan, cfg, technical)
        for extra in range(1, plan['additional_updates']+1):
            base.check_stop(out, deadline)
            update = plan['start_update']+extra
            for member in members:
                metrics = base.step(member['model'], member['optimizer'], data['train'],
                    schedules[member['seed']][extra-1], weights, cfg, update, device)
                member['update'] = update
                if extra % 100 == 0 or update in plan['evaluation_updates']:
                    with (out/'metrics.jsonl').open('a') as stream:
                        stream.write(json.dumps(dict(model=member['name'], update=update, **metrics))+'\n')
            state.update(state='TRAINING', completed_round=update, last_metrics=metrics,
                         updates={m['name']: m['update'] for m in members}, updated_unix=time.time())
            if extra % 100 == 0 or update in plan['evaluation_updates']:
                write(out/'status.json', state)
            if extra % 1000 == 0 or update in plan['evaluation_updates']:
                for member in members:
                    save_member(out, member, plan, cfg, technical)
            if update in plan['evaluation_updates']:
                panel, hashes = {}, {}
                for member in members:
                    result = offline(member['model'], data['valid'], cfg, device, weights)
                    seeds = [plan['technical_seeds'][0]] if technical else range(cfg['development_seeds'][0], cfg['development_seeds'][1]+1)
                    for count in (2, 3):
                        state.update(state='EVALUATING', evaluating=member['name'], count=count, updated_unix=time.time())
                        write(out/'status.json', state)
                        rollout = base.evaluate(member['model'], cfg, count, seeds, out, deadline, frame_cap=20 if technical else None)
                        check_pairing(hashes, count, rollout)
                        write(out/member['name']/f'dev{count}_u{update}.json', rollout)
                        result[f'dev{count}'] = {k: v for k, v in rollout.items() if k != 'rows'}
                    panel[member['name']] = result
                    write(out/member['name']/f'offline_u{update}.json', result)
                write(out/f'panel_u{update}.json', panel)
                write(out/'latest_panel.json', dict(update=update, models=panel))
        state['state'] = 'SMOKE_COMPLETE' if technical else 'TRAINING_COMPLETE'
    except (TimeoutError, InterruptedError) as exc:
        state.update(state='PARTIAL_TIME_CAP' if isinstance(exc, TimeoutError) else 'STOPPED', reason=str(exc))
    except BaseException as exc:
        state.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        for member in members:
            save_member(out, member, plan, cfg, technical)
        state.update(updated_unix=time.time(), updates={m['name']: m['update'] for m in members})
        write(out/'status.json', state)
    print(json.dumps(dict(state=state['state'], updates=state['updates'])))


def check_pairing(hashes, count, result):
    observed = [r['initial_sha256'] for r in result['rows']]
    if count in hashes and hashes[count] != observed:
        raise ValueError('Paired initial states differ')
    hashes[count] = observed


def confirmation(out, device, deadline):
    base, torch, _ = libraries()
    verify(out)
    if read(out/'status.json')['state'] != 'TRAINING_COMPLETE':
        raise ValueError('Confirmation needs complete training')
    plan, cfg, parents = read(out/'plan.json'), read(out/'base_config.json'), read(out/'parents.json')
    base.configure(cfg['seeds'][0])
    folder = out/'confirmation'
    folder.mkdir(exist_ok=False)
    frozen = {}
    # Freeze both generations BEFORE observing any fresh confirmation outcome.
    for name, parent in parents.items():
        for tag, source, expected_update in (
            ('parent', ROOT/parent['path'], plan['start_update']),
            ('extended', out/name/'latest.pth', plan['start_update']+plan['additional_updates'])):
            ck = torch.load(source, map_location='cpu', weights_only=False)
            if ck['update'] != expected_update or ck['technical_only']:
                raise ValueError('Invalid confirmation checkpoint')
            target = folder/f'{name}_{tag}.pth'
            shutil.copy2(source, target)
            frozen[f'{name}_{tag}'] = dict(path=str(target), sha256=base.sha(target))
    write(folder/'frozen.json', frozen)
    result, hashes = {}, {}
    seeds = range(plan['confirmation_seeds'][0], plan['confirmation_seeds'][1]+1)
    start = time.time()
    for name, frozen_model in frozen.items():
        if base.sha(frozen_model['path']) != frozen_model['sha256']:
            raise ValueError('Frozen model changed')
        ck = torch.load(frozen_model['path'], map_location='cpu', weights_only=False)
        model, _ = restore(ck, cfg, device)
        result[name] = {}
        for count in (2, 3):
            write(out/'status.json', dict(state='FINAL_TEST', pid=os.getpid(), started_unix=start,
                  completed_round=plan['start_update']+plan['additional_updates'],
                  evaluating=name, count=count, deadline=deadline, updated_unix=time.time()))
            rollout = base.evaluate(model, cfg, count, seeds, out, deadline)
            check_pairing(hashes, count, rollout)
            write(folder/f'{name}_count{count}.json', rollout)
            result[name][str(count)] = rollout
    write(folder/'results.json', result)
    summary = {name: {count: dict(successes=r['successes'], n=r['n']) for count, r in counts.items()}
               for name, counts in result.items()}
    paired = {}
    for name in parents:
        paired[name] = {}
        for count in ('2', '3'):
            before = result[name+'_parent'][count]['rows']
            after = result[name+'_extended'][count]['rows']
            paired[name][count] = dict(gains=sum(not a['success'] and b['success'] for a, b in zip(before, after)),
                losses=sum(a['success'] and not b['success'] for a, b in zip(before, after)))
    write(out/'result_summary.json', dict(models=summary, paired_extension_changes=paired,
          interpretation='Descriptive paired results per training seed; no pooled-scene significance claim'))
    write(out/'status.json', dict(state='COMPLETE', completed_round=plan['start_update']+plan['additional_updates'], updated_unix=time.time()))


def supervise(out, device):
    verify(out)
    if read(out/'status.json')['state'] != 'READY' or (out/'STOP').exists():
        raise ValueError('Expected READY without STOP')
    with (out/'supervisor_launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time()), stream)
    plan = read(out/'plan.json')
    start = time.time()
    deadline = start+plan['wall_clock_cap_seconds']
    state = dict(state='STARTING', pid=os.getpid(), started_unix=start, deadline=deadline)
    awake, worker = False, None
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        for command in ('run', 'test'):
            if command == 'test' and read(out/'status.json')['state'] != 'TRAINING_COMPLETE':
                state['state'] = 'INCOMPLETE'
                return
            if (out/'STOP').exists() or time.time() >= deadline:
                state['state'] = 'STOPPED_OR_TIME_CAP'
                return
            worker = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), command,
                 '--output', str(out), '--device', device, '--deadline', str(deadline)], cwd=ROOT)
            state.update(state=command.upper(), worker_pid=worker.pid, sleep_prevention_active=awake, updated_unix=time.time())
            write(out/'supervisor_status.json', state)
            try:
                code = worker.wait(timeout=max(1, deadline-time.time())+120)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
                raise TimeoutError('Global time cap plus shutdown allowance exhausted')
            if code:
                raise RuntimeError(command+' failed with exit code '+str(code))
        state['state'] = read(out/'status.json')['state']
    except BaseException as exc:
        state.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        if worker is not None and worker.poll() is None:
            worker.kill()
            worker.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(), sleep_prevention_active=False)
        write(out/'supervisor_status.json', state)


def status(out):
    state = read(out/'status.json')
    supervisor = read(out/'supervisor_status.json') if (out/'supervisor_status.json').exists() else {}
    previous_path = out/'monitor_state.json'
    previous = read(previous_path) if previous_path.exists() else {}
    active = state['state'] in ('INITIALIZING', 'TRAINING', 'EVALUATING', 'FINAL_TEST')
    alive = None
    if active and os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p]*5
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        handle = kernel.OpenProcess(0x1000, False, state['pid'])
        if handle:
            times = [ctypes.c_ulonglong() for _ in range(4)]
            code = ctypes.c_ulong()
            if kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
                birth = times[0].value/10000000-11644473600
                alive = code.value == 259 and 0 <= state['started_unix']-birth < 120
            kernel.CloseHandle(handle)
        elif ctypes.get_last_error() == 87:
            alive = False
    log = out/'metrics.jsonl'
    offset, errors, identity = 0, [], None
    if log.exists():
        info = log.stat()
        identity = [info.st_ino, info.st_ctime_ns]
        offset = previous.get('offset', info.st_size) if previous.get('log_identity') == identity else (0 if previous else info.st_size)
        if offset > info.st_size:
            offset = 0
        with log.open('rb') as stream:
            stream.seek(offset)
            while line := stream.readline():
                if not line.endswith(b'\n'):
                    break  # Retry a partial append next time.
                try:
                    row = json.loads(line)
                    if not all(math.isfinite(row[k]) for k in ('loss', 'gradient_norm')):
                        errors.append('Nonfinite metrics')
                except (ValueError, KeyError, TypeError):
                    errors.append('Invalid metrics record')
                offset = stream.tell()
    age = time.time()-state['updated_unix']
    level = 'ERROR' if errors or state['state'] == 'FAILED' or supervisor.get('state') == 'FAILED' or (active and alive is False) else 'OK'
    if level == 'OK' and active and (alive is None or age > 900):
        level = 'WARNING'
    write(previous_path, dict(checked_unix=time.time(), offset=offset, log_identity=identity,
          step=state.get('completed_round'), process_alive=alive, metrics=state.get('last_metrics'), issues=errors))
    print(json.dumps(dict(level=level, state=state['state'], supervisor=supervisor.get('state'),
          step=state.get('completed_round'), process_alive=alive, status_age_seconds=round(age),
          loss=state.get('last_metrics', {}).get('loss'), new_errors=len(errors), action='none')))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare', 'smoke', 'run', 'test', 'supervise', 'status', 'preflight'))
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--prepared', type=Path)
    p.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    p.add_argument('--deadline', type=float)
    args = p.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        p.error('Output must stay in the project workspace')
    if args.command == 'prepare':
        prepare(out)
    elif args.command == 'smoke':
        if args.prepared is None:
            p.error('--prepared required')
        run(out, args.device, prepared=args.prepared.resolve())
    elif args.command == 'run':
        run(out, args.device, deadline=args.deadline)
    elif args.command == 'test':
        if args.deadline is None:
            p.error('Shared --deadline required; normally use supervise')
        try:
            confirmation(out, args.device, args.deadline)
        except (TimeoutError, InterruptedError) as exc:
            state = read(out/'status.json')
            state.update(state='PARTIAL_TIME_CAP' if isinstance(exc, TimeoutError) else 'STOPPED',
                         reason=str(exc), updated_unix=time.time())
            write(out/'status.json', state)
    elif args.command == 'supervise':
        supervise(out, args.device)
    elif args.command == 'preflight':
        verify(out)
        if read(out/'status.json')['state'] != 'READY' or (out/'supervisor_launch.json').exists() or (out/'launch.json').exists() or (out/'STOP').exists():
            raise ValueError('Run not startable; no restart or overwrite permitted')
        print(json.dumps(dict(state='READY', input_hashes_verified=True)))
    else:
        status(out)


if __name__ == '__main__':
    main()
