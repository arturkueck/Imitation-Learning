"""Prepare, smoke, run, test and inspect a bounded curriculum comparison."""
from pathlib import Path
import argparse
import copy
import importlib.metadata
import json
import os
import shutil
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify(out):
    import core
    proof = read(out / 'provenance.json')
    for path, expected in proof['input_hashes'].items():
        if core.sha(ROOT / path) != expected:
            raise ValueError('Prepared input changed: ' + path)
    for path, expected in proof.get('library_source_hashes', {}).items():
        if core.sha(path) != expected:
            raise ValueError('Simulator dependency changed: ' + path)
    for name, expected in proof['versions'].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError('Library version changed: ' + name)


def prepare(out):
    import core
    import numpy as np
    cfg = read(HERE / 'config.json')
    core.validate_config(cfg)
    data = core.load_data()
    controller = core.backend()
    # Reconstruct the cached labels from whole source trajectories once, before
    # freezing inputs. Training never reconstructs labels or reads test results.
    import method
    rebuilt, manifest = method.dataset()
    if any(not np.array_equal(left, right) for split in data
           for left, right in zip(data[split], rebuilt[split])):
        raise ValueError('Cached training arrays differ from original demonstrations')
    if core.sha(core.DATA) != manifest['dataset_sha256']:
        raise ValueError('Demonstration hash mismatch')
    # Include loaded project dependencies and their snapshots, plus experiment code.
    sources = set(HERE.glob('*.py')) | {HERE / 'config.json', core.MANIFEST, core.ARRAYS, core.DATA,
        ROOT / 'experiments/baselines/additional_tasks/stack_two/task_info.json'}
    library_sources = {}
    for name, module in list(sys.modules.items()):
        location = getattr(module, '__file__', None)
        if not location:
            continue
        path = Path(location).resolve()
        if not path.is_file():
            continue  # Some libraries expose synthetic __file__ values.
        if name == 'robosuite' or name.startswith('robosuite.'):
            library_sources[str(path)] = core.sha(path)
        if path.suffix == '.py' and path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / 'praxis/.venv'):
            sources.add(path)
    hashes = {str(p.relative_to(ROOT)): core.sha(p) for p in sorted(sources)}
    audit = {}
    for split in data:
        groups = core.pools(data[split], cfg['axis_threshold'])
        if any(not len(v) for v in groups.values()):
            raise ValueError('Empty curriculum pool in ' + split)
        audit[split] = {name: dict(frames=len(ids), phase_counts=np.bincount(data[split][2][ids], minlength=7).tolist())
                        for name, ids in groups.items()}
    versions = {name: importlib.metadata.version(name) for name in ('torch', 'numpy', 'robosuite', 'mujoco', 'h5py')}
    out.mkdir(parents=True, exist_ok=False)
    core.dump(out / 'config.json', cfg)
    hashes[str((out / 'config.json').resolve().relative_to(ROOT))] = core.sha(out / 'config.json')
    core.dump(out / 'data_audit.json', dict(pools=audit, split_ids=manifest['split_ids'],
        reconstructed_arrays_exact=True, source_sha256=manifest['dataset_sha256'],
        features=10, learned_actions=['x', 'y', 'z', 'gripper'], rotations='fixed zero as in original demos'))
    for path in sources:
        if path.suffix in ('.py', '.json'):
            target = out / 'source_snapshot' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    core.dump(out / 'provenance.json', dict(input_hashes=hashes, versions=versions, library_source_hashes=library_sources,
        python=sys.version, prepared_unix=time.time(), data_reconstructed_exactly=True))
    core.dump(out / 'status.json', dict(state='READY', training_started=False, updated_unix=time.time()))
    print(json.dumps(dict(state='READY', output=str(out), pools=audit)))


def checkpoint(out, member, cfg, technical):
    import core
    import torch
    folder = out / member['name']
    state = dict(model=member['model'].state_dict(), optimizer=member['opt'].state_dict(),
        update=member['update'], config=cfg, seed=member['seed'], arm=member['arm'],
        technical_only=technical, torch_rng=torch.get_rng_state(),
        cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        schedule_sha256=member['schedule_sha256'], permutation_sha256=member['permutation_sha256'])
    tmp = folder / 'latest.tmp'
    torch.save(state, tmp)
    tmp.replace(folder / 'latest.pth')


def run(out, device, technical=False, prepared=None):
    import core
    import hashlib
    import numpy as np
    import torch
    verify(prepared or out)
    cfg = copy.deepcopy(read((prepared or out) / 'config.json'))
    if technical:
        cfg.update(seeds=[99], updates=6, evaluation_updates=[6], wall_clock_cap_seconds=300)
        for stage, end in zip(cfg['stages'], (2, 4, 6)):
            stage['end_update'] = end
        out.mkdir(parents=True, exist_ok=False)
        core.dump(out / 'config.json', cfg)
        shutil.copy2(prepared / 'provenance.json', out / 'parent_provenance.json')
    elif read(out / 'status.json')['state'] != 'READY':
        raise ValueError('Run is not READY; use a new output directory, no automatic resume')
    core.validate_config(cfg)
    with (out / 'launch.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time(), technical_only=technical), stream)
    start = time.time()
    deadline = start + cfg['wall_clock_cap_seconds']
    members = []
    status = dict(state='INITIALIZING', pid=os.getpid(), started_unix=start, deadline=deadline,
                  technical_only=technical, completed_round=0, updates={}, updated_unix=start)
    core.dump(out / 'status.json', status)
    try:
        core.configure(cfg['seeds'][0])
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested but unavailable')
        controller = core.backend()
        historical = controller.native.historical
        data = core.load_data()
        weights = core.positive_weights(data['train'], device)
        schedules = {}
        for seed in cfg['seeds']:
            batches, permutation = core.schedule(data['train'], cfg, seed)
            schedules[seed] = (batches, permutation)
            schedule_hash = hashlib.sha256(batches.tobytes()).hexdigest()
            permutation_hash = hashlib.sha256(permutation.tobytes()).hexdigest()
            np.savez_compressed(out / f'schedule_seed{seed}.npz', batches=batches, permutation=permutation)
            core.configure(seed)
            initial = historical.PhaseNet(cfg['width']).state_dict()
            for arm in cfg['arms']:
                name = f'{arm}_seed{seed}'
                (out / name).mkdir()
                model = historical.PhaseNet(cfg['width']).to(device)
                model.load_state_dict(initial)
                opt = torch.optim.AdamW(model.parameters(), lr=cfg['lr'], weight_decay=cfg['weight_decay'])
                member = dict(name=name, model=model, opt=opt, seed=seed, arm=arm, update=0,
                              schedule_sha256=schedule_hash, permutation_sha256=permutation_hash)
                members.append(member)
                checkpoint(out, member, cfg, technical)
                shutil.copy2(out / name / 'latest.pth', out / name / 'initial.pth')
        for update in range(1, cfg['updates']+1):
            core.check_stop(out, deadline)
            for member in members:
                batches, permutation = schedules[member['seed']]
                batch_id = update-1 if member['arm'] == 'curriculum' else int(permutation[update-1])
                metrics = core.step(member['model'], member['opt'], data['train'], batches[batch_id],
                                    weights, cfg, update, device)
                member['update'] = update
                if update % 100 == 0 or update in cfg['evaluation_updates']:
                    with (out / 'metrics.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(dict(model=member['name'], update=update, **metrics))+'\n')
            status.update(state='TRAINING', completed_round=update,
                          updates={m['name']: m['update'] for m in members},
                          last_metrics=metrics, updated_unix=time.time())
            if update % 100 == 0 or update in cfg['evaluation_updates']:
                core.dump(out / 'status.json', status)
            if update % 1000 == 0 or update in cfg['evaluation_updates']:
                for member in members:
                    checkpoint(out, member, cfg, technical)
            if update in cfg['evaluation_updates']:
                panel = {}
                reference_hashes = {}
                status.update(state='EVALUATING', updated_unix=time.time())
                core.dump(out / 'status.json', status)
                for member in members:
                    folder = out / member['name']
                    metric = core.offline(member['model'], data['valid'], device, cfg['axis_threshold'])
                    seeds = ([cfg['technical_seed']] if technical else
                             range(cfg['development_seeds'][0], cfg['development_seeds'][1]+1))
                    for count in (2, 3):
                        status.update(evaluating=member['name'], count=count, updated_unix=time.time())
                        core.dump(out / 'status.json', status)
                        result = core.evaluate(member['model'], cfg, count, seeds, out, deadline,
                                               frame_cap=20 if technical else None)
                        hashes = [r['initial_sha256'] for r in result['rows']]
                        if count in reference_hashes and hashes != reference_hashes[count]:
                            raise ValueError('Evaluation starts differ between arms/seeds')
                        reference_hashes[count] = hashes
                        core.dump(folder / f'dev{count}_u{update}.json', result)
                        metric[f'dev{count}'] = {k: v for k, v in result.items() if k != 'rows'}
                    metric.update(update=update, sampled_frame_equivalents=update*cfg['batch_size']/len(data['train'][0]))
                    core.dump(folder / f'metrics_u{update}.json', metric)
                    panel[member['name']] = metric
                # Only complete panels enter the comparison summary.
                core.dump(out / f'panel_u{update}.json', panel)
                core.dump(out / 'latest_panel.json', dict(update=update, models=panel))
        status['state'] = 'SMOKE_COMPLETE' if technical else 'TRAINING_COMPLETE'
    except InterruptedError as exc:
        status.update(state='STOPPED', reason=str(exc))
    except TimeoutError as exc:
        status.update(state='PARTIAL_TIME_CAP', reason=str(exc))
    except BaseException as exc:
        status.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        for member in members:
            checkpoint(out, member, cfg, technical)
        status.update(updates={m['name']: m['update'] for m in members}, updated_unix=time.time())
        core.dump(out / 'status.json', status)
    print(json.dumps(dict(state=status['state'], updates=status['updates'], output=str(out))))


def final_test(out, device):
    import core
    import torch
    verify(out)
    cfg = read(out / 'config.json')
    if read(out / 'status.json')['state'] != 'TRAINING_COMPLETE':
        raise ValueError('Final testing requires all planned updates')
    core.configure(cfg['seeds'][0])
    controller = core.backend()
    folder = out / 'final_test'
    folder.mkdir(exist_ok=False)  # Never repeat or overwrite the held-out panel.
    frozen = {}
    # Freeze EVERY model before observing ANY final outcome.
    for seed in cfg['seeds']:
        for arm in cfg['arms']:
            name = f'{arm}_seed{seed}'
            source = out / name / 'latest.pth'
            ck = torch.load(source, map_location='cpu', weights_only=False)
            if ck['update'] != cfg['updates'] or ck['technical_only']:
                raise ValueError('Incomplete or technical checkpoint')
            shutil.copy2(source, folder / f'{name}.pth')
            frozen[name] = core.sha(folder / f'{name}.pth')
    core.dump(folder / 'frozen.json', frozen)
    deadline = time.time()+cfg['wall_clock_cap_seconds']
    seeds = range(cfg['final_seeds'][0], cfg['final_seeds'][1]+1)
    results, reference_hashes = {}, {}
    for name, expected in frozen.items():
        path = folder / f'{name}.pth'
        if core.sha(path) != expected:
            raise ValueError('Frozen checkpoint changed')
        ck = torch.load(path, map_location='cpu', weights_only=False)
        model = controller.native.historical.PhaseNet(cfg['width']).to(device)
        model.load_state_dict(ck['model'])
        results[name] = {}
        for count in (2, 3):
            result = core.evaluate(model, cfg, count, seeds, out, deadline)
            hashes = [r['initial_sha256'] for r in result['rows']]
            if count in reference_hashes and hashes != reference_hashes[count]:
                raise ValueError('Final starts differ between models')
            reference_hashes[count] = hashes
            results[name][str(count)] = result
            core.dump(folder / f'{name}_count{count}.json', result)
    core.dump(folder / 'results.json', results)
    print(json.dumps(dict(state='FINAL_TEST_COMPLETE', models=len(results))))


def status(out):
    """Read two small files, plus process identity; never import ML libraries."""
    state = read(out / 'status.json')
    pid = state.get('pid')
    alive = False
    if pid and os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p]*4
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if handle:
            code = ctypes.c_ulong()
            times = [ctypes.c_ulonglong() for _ in range(4)]
            if kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
                created = times[0].value / 10000000 - 11644473600
                alive = code.value == 259 and 0 <= state['started_unix']-created < 120
            kernel.CloseHandle(handle)
    monitor_path = out / 'monitor_state.json'
    previous = read(monitor_path) if monitor_path.exists() else {}
    active = state['state'] in ('TRAINING', 'INITIALIZING', 'EVALUATING')
    age = time.time()-state['updated_unix']
    label = 'ERROR' if state['state'] == 'FAILED' or (active and not alive) else 'OK'
    if active and alive and age > 900:
        label = 'WARNING'
    progressed = state.get('completed_round') != previous.get('completed_round')
    metric_path = out / 'metrics.jsonl'
    offset = previous.get('log_offset', metric_path.stat().st_size if metric_path.exists() else 0)
    errors = []
    if metric_path.exists():
        size = metric_path.stat().st_size
        if offset > size:
            offset = 0
        with metric_path.open('rb') as stream:
            stream.seek(offset)
            for line in stream:
                try:
                    row = json.loads(line)
                    if not all(isinstance(row[k], (int, float)) and __import__('math').isfinite(row[k])
                               for k in ('loss', 'gradient_norm')):
                        errors.append('Nonfinite metric')
                except (ValueError, KeyError):
                    errors.append('Invalid metrics record')
            offset = stream.tell()
    if errors:
        label = 'ERROR'
    current = dict(checked_unix=time.time(), completed_round=state.get('completed_round'),
                   log_offset=offset, state=state['state'], process_alive=alive,
                   last_metrics=state.get('last_metrics'), issues=errors)
    tmp = monitor_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(current), encoding='utf-8')
    tmp.replace(monitor_path)
    print(json.dumps(dict(level=label, state=state['state'], process_alive=alive,
                         step=state.get('completed_round', 0), progress_since_last_check=progressed,
                         status_age_seconds=round(age), loss=state.get('last_metrics', {}).get('loss'),
                         new_errors=len(errors), action='none'), ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'smoke', 'run', 'test', 'status'])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prepared', type=Path)
    p.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    args = p.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        p.error('Output must be inside the project workspace')
    if args.command == 'status':
        status(out)
    elif args.command == 'prepare':
        prepare(out)
    elif args.command == 'smoke':
        if args.prepared is None:
            p.error('smoke needs --prepared with a READY experiment')
        run(out, args.device, technical=True, prepared=args.prepared.resolve())
    elif args.command == 'run':
        run(out, args.device)
    else:
        final_test(out, args.device)


if __name__ == '__main__':
    main()
