"""Launch the frozen pipeline with an additional absolute stop time."""
from pathlib import Path
from datetime import datetime
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

import pipeline


def limits(started, requested, plan):
    if requested <= started:
        raise ValueError('Requested end time is already past')
    hard = min(requested, started+plan['wall_clock_cap_seconds'])
    deadline = hard-plan['shutdown_reserve_seconds']
    if deadline <= time.time():
        raise ValueError('Insufficient time for the shutdown reserve')
    return deadline, hard


def launch(out, requested, requested_iso, device):
    started = time.time()
    pipeline.verify(out)
    if pipeline.read(out/'status.json')['state'] != 'READY' or any((out/name).exists() for name in ('STOP','launch.json','supervisor_launch.json')):
        raise ValueError('Run is not fresh READY; no duplicate start permitted')
    plan = pipeline.read(out/'plan.json')
    deadline, hard = limits(started, requested, plan)
    with (out/'supervisor_launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=started, requested_end=requested_iso,
                       launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), stream)
    state = dict(state='STARTING', pid=os.getpid(), started_unix=started, deadline=deadline,
                 hard_deadline=hard, requested_end=requested_iso)
    worker, awake = None, False
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        worker = subprocess.Popen([sys.executable, '-u', str(Path(pipeline.__file__).resolve()), 'run',
            '--output', str(out), '--device', device, '--deadline', str(deadline)], cwd=pipeline.ROOT)
        state.update(state='VALIDATING', worker_pid=worker.pid, sleep_prevention_active=awake, updated_unix=time.time())
        pipeline.write(out/'supervisor_status.json', state)
        try:
            code = worker.wait(timeout=max(.001, hard-time.time()))
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
            state.update(state='PARTIAL_TIME_CAP', reason='Requested absolute end time reached')
            return
        if code:
            raise RuntimeError('Validation failed with exit code '+str(code))
        state['state'] = pipeline.read(out/'status.json')['state']
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
        pipeline.write(out/'supervisor_status.json', state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--until', required=True, help='ISO datetime with timezone offset')
    parser.add_argument('--device', choices=('cpu','cuda'), default='cuda')
    args = parser.parse_args()
    end = datetime.fromisoformat(args.until)
    if end.tzinfo is None:
        parser.error('--until requires an explicit timezone offset')
    out = args.output.resolve()
    if not out.is_relative_to(pipeline.ROOT):
        parser.error('Output must stay inside workspace')
    launch(out, end.timestamp(), args.until, args.device)


if __name__ == '__main__':
    main()
