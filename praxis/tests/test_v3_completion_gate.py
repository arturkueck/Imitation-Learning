"""Completion/handoff must not fire on pauses, live workers or damaged outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path

import psutil
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('v3_completion_gate', ROOT / 'experiments/visual_active_v3_20261101/completion_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def setup_run(tmp_path):
    gate.save(tmp_path / 'monitor_state.json', {'phase': 'waiting', 'followup_claimed': False, 'run_directory': None})
    run = tmp_path / 'run_001'
    run.mkdir()
    gate.mutate('arm', tmp_path, run='run_001')
    worker = psutil.Process()
    result = dict(schema_version=1, run_id='run_001', status='completed', training_complete=True,
                  validation_complete=True, workers=[{'pid': worker.pid, 'create_time': worker.create_time()}], artifacts={})
    for key in ['metrics', 'curves', 'checkpoint_manifest']:
        path = run / (key + '.txt')
        path.write_bytes(b'verifiable test artifact')
        result['artifacts'][key] = {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    gate.save(run / 'handoff_result.json', result)
    return run, result


def mark_worker_ended(monkeypatch):
    def ended(pid):
        raise psutil.NoSuchProcess(pid)
    monkeypatch.setattr(gate.psutil, 'Process', ended)


def test_unregistered_is_not_complete(tmp_path):
    gate.save(tmp_path / 'monitor_state.json', {'phase': 'waiting', 'followup_claimed': False})
    assert gate.check(tmp_path)['status'] == 'awaiting_training_registration'
    with pytest.raises(ValueError):
        gate.mutate('claim', tmp_path)


def test_live_worker_prevents_handoff(tmp_path):
    setup_run(tmp_path)
    assert gate.check(tmp_path)['status'] == 'waiting_for_worker_exit'
    with pytest.raises(ValueError):
        gate.mutate('claim', tmp_path)


def test_ready_claim_is_once_only(tmp_path, monkeypatch):
    setup_run(tmp_path)
    mark_worker_ended(monkeypatch)
    assert gate.check(tmp_path)['status'] == 'ready'
    gate.mutate('claim', tmp_path)
    assert gate.check(tmp_path)['status'] == 'already_claimed'
    with pytest.raises(ValueError):
        gate.mutate('claim', tmp_path)
    gate.mutate('finish', tmp_path, outcome='active_view_validated')
    assert gate.read(tmp_path / 'monitor_state.json')['phase'] == 'finished'


def test_corruption_and_missing_validation_block(tmp_path, monkeypatch):
    run, result = setup_run(tmp_path)
    mark_worker_ended(monkeypatch)
    (run / 'metrics.txt').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        gate.check(tmp_path)
    result['validation_complete'] = False
    gate.save(run / 'handoff_result.json', result)
    with pytest.raises(ValueError, match='both be complete'):
        gate.check(tmp_path)


def test_path_escape_and_existing_lock_rejected(tmp_path):
    setup_run(tmp_path)
    with pytest.raises(ValueError):
        gate.contained(tmp_path, '../elsewhere')
    (tmp_path / 'monitor_state.lock').write_text('another writer')
    with pytest.raises(FileExistsError):
        gate.mutate('claim', tmp_path)
    assert (tmp_path / 'monitor_state.lock').exists()


def test_failure_and_validation_pause(tmp_path):
    run, result = setup_run(tmp_path)
    result['status'] = 'validating'
    gate.save(run / 'handoff_result.json', result)
    assert gate.check(tmp_path)['status'] == 'validating'
    result['status'] = 'failed'
    result['error'] = 'CUDA OOM'
    gate.save(run / 'handoff_result.json', result)
    assert gate.check(tmp_path) == {'status': 'error', 'reason': 'CUDA OOM'}


def test_ended_without_result_is_error(tmp_path, monkeypatch):
    run, result = setup_run(tmp_path)
    result['status'] = 'running'
    gate.save(run / 'handoff_result.json', result)
    mark_worker_ended(monkeypatch)
    assert gate.check(tmp_path)['status'] == 'error'
