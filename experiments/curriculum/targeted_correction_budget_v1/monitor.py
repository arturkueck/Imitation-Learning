"""Small incremental monitor; no training imports or scientific changes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import time


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {} if default is None else default


def identity(pid, created):
    if pid <= 0:
        return None
    if os.name == 'nt':
        # Direct limited-information handles avoid filtered process enumeration
        # being misreported by psutil as NoSuchProcess in restricted shells.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = wintypes.DWORD()
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in times)):
                return None
            start = ((times[0].dwHighDateTime << 32)+times[0].dwLowDateTime)/10000000-11644473600
            return code.value == 259 and abs(start-created) <= 1
        finally:
            kernel.CloseHandle(handle)
    import psutil
    try:
        process = psutil.Process(pid)
        if not process.is_running() or abs(process.create_time()-created) > 1:
            return False
        return True
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return None


def new_errors(path, state):
    if not path.exists():
        return []
    stat = path.stat()
    token = [stat.st_ino, stat.st_ctime_ns]
    offset = state.get('offset', 0) if state.get('file_identity') == token else 0
    if stat.st_size < offset:
        offset = 0
    with path.open('rb') as stream:
        stream.seek(offset)
        chunk = stream.read(65536)
    # Preserve incomplete lines for the next check.
    boundary = chunk.rfind(b'\n')+1
    if not boundary and len(chunk) == 65536:
        boundary = len(chunk)
    state.update(offset=offset+boundary, file_identity=token)
    messages = chunk[:boundary].decode('utf-8', errors='replace').splitlines()
    pattern = re.compile(r'Traceback|CUDA.*out of memory|(?:FloatingPoint|Runtime|Value|Permission|Memory)Error|nonfinite|\bNaN\b|\bloss.*\binf\b', re.I)
    seen = set(state.get('known_errors', []))
    errors = []
    for line in messages:
        digest = hashlib.sha256(line.encode()).hexdigest()
        if pattern.search(line) and digest not in seen:
            errors.append(line[:400])
            seen.add(digest)
    state['known_errors'] = sorted(seen)
    return errors


def check(out):
    state_path = out/'monitor_state.json'
    previous = read(state_path)
    current = read(out/'status.json')
    supervisor = read(out/'supervisor_status.json')
    plan = read(out/'plan.json')
    errors = new_errors(out/'worker.log', previous)
    now = time.time()
    name = current.get('state', 'MISSING')
    if name == 'READY' and supervisor.get('state') == 'RUNNING':
        name = 'STARTING'
    level, detail = 'OK', name
    if supervisor.get('state') == 'FAILED':
        level, detail = 'ERROR', supervisor.get('error', 'Supervisor meldet Fehler')
    elif name == 'READY':
        detail = 'Startbereit | Training nicht gestartet'
    elif name == 'COMPLETE':
        detail = 'Abgeschlossen | Komponenten: '+str(current.get('components_completed'))
        if supervisor.get('state') == 'RUNNING':
            level, detail = 'WARNING', 'Worker fertig, Supervisor-Abschluss noch ausstehend'
    elif name in ('FAILED', 'MISSING'):
        level, detail = 'ERROR', current.get('error', name)
    elif name in ('STOPPED', 'PARTIAL_TIME_CAP'):
        level, detail = 'WARNING', current.get('error', name)
    else:
        alive = identity(supervisor.get('worker_pid', -1), supervisor.get('worker_created', -100))
        if alive is False:
            level, detail = 'ERROR', 'Erwarteter Worker nicht aktiv'
        elif alive is None:
            level, detail = 'WARNING', 'Prozessidentität wegen Zugriffsrechten nicht prüfbar'
        elif now-supervisor.get('heartbeat_unix', 0) > 60:
            level, detail = 'WARNING', 'Supervisor-Heartbeat älter als 60 s'
        branch = read(out/current['component_output']/'status.json') if current.get('component_output') else {}
        key = {k:current.get(k) for k in ('state', 'block', 'model', 'source', 'kind', 'split', 'seed', 'policy', 'panel')}
        key['update'] = branch.get('update')
        if previous.get('progress_key') != key:
            previous['last_progress_unix'] = now
        elif now-previous.get('last_progress_unix', now) > plan.get('stagnation_seconds', 1200) and level == 'OK':
            level, detail = 'WARNING', 'Kein neuer Fortschritt seit mehr als 20 Minuten'
        previous['progress_key'] = key
        if level == 'OK':
            detail = 'Training aktiv | '+name+' | '+str(current.get('block', ''))
            if branch:
                loss_path = out/current['component_output']/f"{current['model']}_{'replay' if current['source'] == 'replay' else 'correction'}_{current['kind']}"/'loss.json'
                losses = read(loss_path, [])
                latest = losses[-1] if losses else {}
                detail += f" | Step: {branch.get('update', 0)} | Loss: {latest.get('loss', 'noch kein Messpunkt')}"
            else:
                detail += ' | Szene: '+str(current.get('seed', '-'))
    if errors:
        level = 'ERROR'
    previous.update(last_check_unix=now, process_state=name, last_metrics=current, latest_errors=errors)
    if level == 'OK':
        previous['last_successful_check_unix'] = now
    temp = state_path.with_suffix('.tmp')
    temp.write_text(json.dumps(previous, indent=2), encoding='utf-8')
    temp.replace(state_path)
    print(f"{level} | {detail} | Neue Fehler: {len(errors)} | Aktion: keine")
    for error in errors[:5]:
        print(error)
    return 2 if level == 'ERROR' else (1 if level == 'WARNING' else 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(check(args.output.resolve()))
