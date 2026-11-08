"""Incremental night-run check. No model, data, CUDA or source-code imports."""
from pathlib import Path
import argparse
import json
import re
import time
from night import read, write

HERE = Path(__file__).resolve().parent
EXPECTED_STARTUP = ('No private macro file found!', 'It is recommended to use a private macro file',
                    'To setup, run:', 'Could not import robosuite_models.',
                    'Could not load the mink-based whole-body IK.')


def check(out):
    now = time.time()
    if not (out / 'supervisor.json').exists():
        state = read(out / 'status.json')['state']
        if state == 'READY' and not (out / 'launch.json').exists():
            print('READY | Nachtlauf vorbereitet | Training nicht gestartet | Aktion: keine')
            return 'READY'
        print('ERROR | Kein Supervisor-Heartbeat nach Start | Aktion: Startprotokoll prüfen')
        return 'ERROR'
    supervisor = read(out / 'supervisor.json')
    monitor = out / 'monitor'
    monitor.mkdir(exist_ok=True)
    prev = read(monitor / 'state.json') if (monitor / 'state.json').exists() else {}
    phase = supervisor.get('phase')
    folder = out / {'prepare': 'data', 'warmup': 'warm', 'train': 'train'}.get(phase, 'data')
    status = read(folder / 'status.json') if (folder / 'status.json').exists() else {}
    log = out / 'worker.log'
    errors, warnings = [], []
    offset, identity = 0, None
    if log.exists():
        stat = log.stat()
        identity = [stat.st_ino, stat.st_ctime_ns]
        offset = prev.get('offset', max(0, stat.st_size - 65536))
        if prev.get('log_identity', identity) != identity or offset > stat.st_size:
            offset = 0
        with log.open('rb') as stream:
            stream.seek(offset)
            for line in stream:
                text = line.decode('utf-8', errors='replace').strip()
                if re.search(r'Traceback|CUDA out of memory|AssertionError|RuntimeError|FloatingPointError|\b(?:NaN|Inf)\b', text, re.I):
                    errors.append(text[:300])
                elif re.search(r'\b(?:[A-Za-z]*Warning)\b', text, re.I):
                    if not ('[robosuite WARNING]' in text and any(message in text for message in EXPECTED_STARTUP)):
                        warnings.append(text[:300])
            offset = stream.tell()
    alive = supervisor['state'] == 'RUNNING' and now - supervisor.get('last_check_unix', 0) < 20
    progress = {k: status[k] for k in ('state', 'model', 'seed', 'split', 'episode', 'total', 'round', 'step') if k in status}
    changed = progress != prev.get('progress')
    last_progress = now if changed else prev.get('last_progress_unix', now)
    level = 'OK'
    if supervisor['state'] in ('ERROR', 'TIME_LIMIT', 'STOPPED') or status.get('state') == 'ERROR' or errors:
        level = 'ERROR' if supervisor['state'] != 'STOPPED' else 'WARNING'
    elif supervisor['state'] != 'COMPLETED' and not alive:
        level = 'ERROR'
    elif alive and (now - last_progress > 600 or warnings):
        level = 'WARNING'
    write(monitor / 'state.json', dict(last_check_unix=now,
        last_successful_check_unix=now if level == 'OK' else prev.get('last_successful_check_unix'),
        offset=offset, log_identity=identity, worker_pid=supervisor.get('worker_pid'),
        process_alive=alive, process_observation='supervisor worker.poll heartbeat',
        progress=progress, last_progress_unix=last_progress, loss=status.get('loss'),
        new_errors=errors, new_warnings=warnings, handled_problems=prev.get('handled_problems', [])))
    step = status.get('step', status.get('episode', '-'))
    print(f"{level} | {supervisor['state']} | Phase: {phase} | Step: {step} | Loss: {status.get('loss', '-')} | Neue Fehler: {len(errors)} | Aktion: keine")
    if level != 'OK':
        print(json.dumps(dict(error=supervisor.get('error'), worker_error=status.get('error'), new_errors=errors, new_warnings=warnings)))
    return level


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE / 'night_001')
    args = parser.parse_args()
    check(args.output.resolve())
