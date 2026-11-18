"""One-shot supervisor for the prepared training and its held-out tests."""
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


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    out = args.run.resolve()
    if read(out/'status.json')['state'] != 'READY' or (out/'launch.json').exists():
        raise RuntimeError('Expected a fresh READY run')
    if (out/'STOP').exists():
        raise RuntimeError('STOP already requested')
    with (out/'supervisor_launch.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time(), executable=sys.executable,
                       source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), stream)
    status = dict(state='STARTING', pid=os.getpid(), started_unix=time.time())
    awake = False
    worker = None
    cap = read(out/'config.json')['wall_clock_cap_seconds']

    def save():
        status['updated_unix'] = time.time()
        write(out/'supervisor_status.json', status)

    def execute(command):
        nonlocal worker
        status['state'] = 'TRAINING' if command == 'run' else 'FINAL_TEST'
        worker = subprocess.Popen([sys.executable, '-u', str(HERE/'train.py'), command,
                                   '--output', str(out), '--device', 'cuda'],
                                  cwd=HERE.parents[2])
        status['worker_pid'] = worker.pid
        status['phase_started_unix'] = time.time()
        save()
        try:
            result = worker.wait(timeout=cap+120)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
            raise TimeoutError(command+' exceeded its wall-clock cap plus shutdown allowance')
        if result != 0:
            raise RuntimeError(command+' failed with exit code '+str(result))

    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        status['sleep_prevention_active'] = awake
        save()
        execute('run')
        training = read(out/'status.json')
        if training['state'] != 'TRAINING_COMPLETE' or (out/'STOP').exists():
            status.update(state='INCOMPLETE', training_state=training['state'])
            return
        execute('test')
        results = read(out/'final_test/results.json')
        summary = {}
        for name, counts in results.items():
            summary[name] = {count: dict(successes=r['successes'], n=r['n'],
                                         success_rate=r['successes']/r['n'])
                             for count, r in counts.items()}
        write(out/'result_summary.json', dict(models=summary,
              interpretation='Report each training seed; full three-cube tower is primary. No superiority claim from pooled scenes alone.'))
        status.update(state='COMPLETE', summary=str(out/'result_summary.json'))
    except BaseException as exc:
        status.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        if worker is not None and worker.poll() is None:
            worker.kill()
            worker.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        save()


if __name__ == '__main__':
    main()
