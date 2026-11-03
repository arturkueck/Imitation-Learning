"""Cheap, fail-closed completion gate. Never starts training or robot motion."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import psutil

HERE = Path(__file__).resolve().parent


def contained(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or path == base.resolve():
        raise ValueError('Path must stay inside the experiment/run directory')
    return path


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, obj):
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(obj, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def check(base=HERE):
    state = read(base / 'monitor_state.json')
    if state.get('followup_claimed'):
        return {'status': 'already_claimed', 'phase': state['phase']}
    if not state.get('run_directory'):
        return {'status': 'awaiting_training_registration'}
    run = contained(base, state['run_directory'])
    result_path = run / 'handoff_result.json'
    if not result_path.exists():
        return {'status': 'waiting_for_result', 'run': state['run_directory']}
    result = read(result_path)
    if result.get('schema_version') != 1 or result.get('run_id') != run.name:
        raise ValueError('Wrong result schema or run identity')
    if result.get('status') == 'failed':
        return {'status': 'error', 'reason': result.get('error', 'Training failed')}
    in_progress = result.get('status') in ('running', 'validating', 'checkpointing')
    if not in_progress and result.get('status') != 'completed':
        raise ValueError('Unknown training status')
    if not in_progress and (result.get('training_complete') is not True or result.get('validation_complete') is not True):
        raise ValueError('Training and validation must both be complete')
    workers = result.get('workers')
    if not isinstance(workers, list) or not workers:
        raise ValueError('Explicit worker process identities are required')
    active_pids = []
    for worker in workers:
        pid, created = worker['pid'], worker['create_time']
        if type(pid) is not int or pid <= 0 or not isinstance(created, (int, float)) or created <= 0:
            raise ValueError('Invalid worker process identity')
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - created) < .01 and process.is_running():
                active_pids.append(pid)
        except psutil.NoSuchProcess:
            pass
        # AccessDenied is intentionally not swallowed: inability to verify is not completion.
    if in_progress:
        return ({'status': result['status'], 'active_pids': active_pids} if active_pids else
                {'status': 'error', 'reason': 'Workers ended without a completed result'})
    if active_pids:
        return {'status': 'waiting_for_worker_exit', 'pid': active_pids[0]}
    artifacts = result.get('artifacts', {})
    for key in ('metrics', 'curves', 'checkpoint_manifest'):
        item = artifacts[key]
        path = contained(run, item['path'])
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing/empty artifact: {key}')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item['sha256']:
            raise ValueError(f'Artifact hash mismatch: {key}')
    return {'status': 'ready', 'run': state['run_directory'],
            'result_sha256': hashlib.sha256(result_path.read_bytes()).hexdigest()}


def mutate(action, base=HERE, run=None, outcome=None):
    lock = base / 'monitor_state.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        state = read(base / 'monitor_state.json')
        if action == 'arm':
            if state.get('run_directory') or state.get('followup_claimed'):
                raise ValueError('Already armed/claimed; preserve existing handoff')
            directory = contained(base, run)
            if not directory.is_dir():
                raise ValueError('Run directory must exist')
            state.update(run_directory=directory.relative_to(base.resolve()).as_posix(), phase='waiting_for_training_completion')
            state.pop('training_started',None) # Optimizer activity belongs in the actual run status.
        elif action == 'claim':
            result = check(base)
            if result['status'] != 'ready':
                raise ValueError(f'Cannot claim: {result["status"]}')
            state.update(followup_claimed=True, phase='followup_running', completion=result)
        elif action == 'finish':
            if state.get('phase') != 'followup_running':
                raise ValueError('No active followup claim')
            state.update(phase='finished', outcome=outcome)
        state['updated_unix'] = time.time()
        save(base / 'monitor_state.json', state)
        return state
    finally:
        os.close(descriptor)
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'arm', 'claim', 'finish'])
    parser.add_argument('--run')
    parser.add_argument('--outcome', choices=['review_only', 'continued_then_reviewed', 'active_view_validated', 'blocked', 'failed'])
    args = parser.parse_args()
    if args.action == 'arm' and not args.run:
        parser.error('--run required')
    if args.action == 'finish' and not args.outcome:
        parser.error('--outcome required')
    try:
        result = check() if args.action == 'check' else mutate(args.action, run=args.run, outcome=args.outcome)
        print(json.dumps(result))
        return 2 if result.get('status') == 'error' else 0
    except Exception as error:
        print(json.dumps({'status': 'error', 'reason': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
