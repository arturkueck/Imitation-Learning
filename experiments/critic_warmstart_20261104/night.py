"""Prepare or explicitly launch one bounded, sequential overnight experiment."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT = HERE / 'night_001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def commands(out, python):
    base = [python, '-u', str(HERE / 'run.py')]
    common = ['--execute', '--config', str(out / 'config.json')]
    data, warm, train = (out / name for name in ('data', 'warm', 'train'))
    return [
        ('prepare', base + ['prepare', *common, '--output', str(data)]),
        ('warmup', base + ['warmup', *common, '--data', str(data), '--output', str(warm)]),
        ('train', base + ['train', *common, '--data', str(data), '--warmup', str(warm), '--output', str(train)]),
    ]


def prepare(out, smoke):
    # Import the actual simulator stack only during explicit preparation.
    import run
    import torch
    import psutil
    assert not out.exists(), 'Never overwrite a prepared or started experiment'
    assert torch.cuda.is_available(), 'CUDA required'
    assert psutil.disk_usage(str(ROOT)).free > 20 * 1024**3, 'Need at least 20 GiB free'
    proof = read(smoke / 'preflight.json')
    assert proof['passed'] and proof['bounded_workflow']['passed']
    assert read(smoke / 'status.json')['state'] == 'COMPLETED'
    provenance = read(smoke / 'provenance.json')
    inputs = dict(provenance['source_hashes'])
    inputs.update({p['path']: p['sha256'] for p in provenance['parent_checkpoints']})
    inputs[str(run.ARRAYS)] = provenance['original_arrays_sha256']
    for path, expected in inputs.items():
        assert sha(path) == expected, f'Input changed since smoke: {path}'
    assert read(smoke / 'config.json') == read(HERE / 'config.json')
    cfg = read(HERE / 'config.json')
    cfg['training_enabled'] = True
    cfg['scope'] = 'Prepared overnight A/B/C experiment; execution requires night.py launch'
    for path in (Path(__file__), HERE / 'monitor.py', HERE / 'config.json', smoke / 'preflight.json'):
        inputs[str(path.resolve())] = sha(path)
    out.mkdir()
    write(out / 'config.json', cfg)
    inputs[str(out / 'config.json')] = sha(out / 'config.json')
    protocol = dict(schema='critic-night-v1', state='READY', prepared_unix=time.time(),
        python=sys.executable, smoke=str(smoke), input_hashes=inputs,
        phase_cap_seconds=cfg['wall_clock_cap_seconds'],
        total_cap_seconds=3 * cfg['wall_clock_cap_seconds'],
        phases=commands(out, sys.executable), no_retries=True, no_automatic_resume=True,
        reserved_final_tests=False, scientific_training_started=False,
        resources=dict(cuda_device=torch.cuda.get_device_name(0),
                       available_ram_bytes=psutil.virtual_memory().available,
                       free_disk_bytes=psutil.disk_usage(str(ROOT)).free))
    write(out / 'protocol.json', protocol)
    write(out / 'status.json', dict(state='READY', updated_unix=time.time(), scientific_training_started=False))
    print(f'READY | {out} | Hauptlauf nicht gestartet')


def verify(out):
    protocol = read(out / 'protocol.json')
    for path, expected in protocol['input_hashes'].items():
        assert sha(path) == expected, f'Prepared input changed: {path}; prepare a new run'
    assert protocol['phases'] == [[name, cmd] for name, cmd in commands(out, protocol['python'])]
    assert not (out / 'STOP').exists(), 'STOP already present'
    assert all(not (out / name).exists() for name in ('data', 'warm', 'train')), 'No resume or overwrite'
    return protocol


def phase_ok(out, phase, returncode):
    folder = out / {'prepare': 'data', 'warmup': 'warm', 'train': 'train'}[phase]
    if returncode != 0 or read(folder / 'status.json')['state'] != 'COMPLETED':
        raise RuntimeError(f'{phase} failed; exit={returncode}; see {folder} and worker.log')
    if phase == 'prepare':
        manifest = read(folder / 'manifest.json')
        assert manifest['complete'] and manifest['ready_for_training'] and not manifest['technical_only']
        assert sha(folder / 'data_audit.json') == manifest['data_audit_sha256']
    elif phase == 'warmup':
        scores = read(folder / 'validation.json')
        assert set(scores) == {'1', '2', '3'}
        assert all(s['finite'] and s['beats_constant'] for s in scores.values()), 'Critic validation gate failed; stop without retry'
    else:
        frozen = read(folder / 'frozen_final.json')
        assert len(frozen) == 9
        assert all(row['fixed_last_round'] and sha(row['path']) == row['sha256'] for row in frozen.values())


def terminate(worker, folder):
    folder.mkdir(exist_ok=True)
    (folder / 'STOP').touch(exist_ok=True)
    try:
        worker.wait(timeout=30)
    except subprocess.TimeoutExpired:
        # Windows venv executables can be launchers. Include their owned child
        # interpreters so the fallback cannot leave training running unattended.
        import psutil
        try:
            children = psutil.Process(worker.pid).children(recursive=True)
        except psutil.NoSuchProcess:
            children = []
        for child in reversed(children):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        worker.kill()
        worker.wait(timeout=10)


def supervise(out):
    worker = None
    info = dict(state='STARTING', pid=os.getpid(), started_unix=time.time())
    kernel = ctypes.windll.kernel32
    info['keepawake_enabled'] = bool(kernel.SetThreadExecutionState(0x80000001))
    try:
        protocol = verify(out)
        deadline = time.time() + protocol['total_cap_seconds']
        info['deadline_unix'] = deadline
        with (out / 'worker.log').open('xb', buffering=0) as log:
            for phase, cmd in protocol['phases']:
                for path, expected in protocol['input_hashes'].items():
                    assert sha(path) == expected, f'Prepared input changed: {path}'
                assert not (out / 'STOP').exists(), 'STOP requested'
                assert time.time() < deadline, 'Total deadline reached'
                folder = out / {'prepare': 'data', 'warmup': 'warm', 'train': 'train'}[phase]
                worker = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                phase_deadline = min(deadline, time.time() + protocol['phase_cap_seconds'])
                info.update(state='RUNNING', phase=phase, worker_pid=worker.pid,
                            phase_started_unix=time.time(), phase_deadline_unix=phase_deadline)
                while worker.poll() is None:
                    info['last_check_unix'] = time.time()
                    write(out / 'supervisor.json', info)
                    if (out / 'STOP').exists() or time.time() >= phase_deadline:
                        terminate(worker, folder)
                        info.update(state='STOPPED' if (out / 'STOP').exists() else 'TIME_LIMIT', returncode=worker.returncode)
                        return
                    time.sleep(5)
                phase_ok(out, phase, worker.returncode)
                info['returncode'] = worker.returncode
        info['state'] = 'COMPLETED'
    except Exception:
        info.update(state='ERROR', error=traceback.format_exc())
        if worker is not None and worker.poll() is None:
            terminate(worker, folder)
    finally:
        kernel.SetThreadExecutionState(0x80000000)
        info['ended_unix'] = time.time()
        write(out / 'supervisor.json', info)
        write(out / 'status.json', dict(state=info['state'], phase=info.get('phase'), updated_unix=time.time()))


def launch(out):
    protocol = verify(out)
    assert read(out / 'status.json')['state'] == 'READY'
    # Exclusive persistent lock also prevents retrying a failed launch accidentally.
    with (out / 'launch.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(launched_unix=time.time(), no_retry=True), stream)
    with (out / 'supervisor.log').open('xb', buffering=0) as log:
        proc = subprocess.Popen([protocol['python'], '-u', str(Path(__file__).resolve()), '_worker', '--output', str(out)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(supervisor_pid=proc.pid, output=str(out))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'launch', '_worker'])
    parser.add_argument('--output', type=Path, default=DEFAULT)
    parser.add_argument('--smoke', type=Path, default=HERE / 'smoke_night_001')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.command == 'prepare':
        prepare(output, args.smoke.resolve())
    elif args.command == 'launch':
        launch(output)
    else:
        supervise(output)
