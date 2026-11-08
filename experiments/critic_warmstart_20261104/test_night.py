"""Failure-path tests: no real training subprocesses or model loads."""
import time
from types import SimpleNamespace
import pytest
import night
import monitor


def test_phase_failure_never_passes(tmp_path):
    folder = tmp_path / 'data'
    folder.mkdir()
    night.write(folder / 'status.json', {'state': 'ERROR'})
    with pytest.raises(RuntimeError):
        night.phase_ok(tmp_path, 'prepare', 1)


def test_warmup_gate_rejects_any_bad_seed(tmp_path):
    folder = tmp_path / 'warm'
    folder.mkdir()
    night.write(folder / 'status.json', {'state': 'COMPLETED'})
    scores = {str(seed): {'finite': True, 'beats_constant': True} for seed in (1, 2, 3)}
    scores['2']['beats_constant'] = False
    night.write(folder / 'validation.json', scores)
    with pytest.raises(AssertionError, match='validation gate'):
        night.phase_ok(tmp_path, 'warmup', 0)


def test_verify_rejects_changed_config_and_existing_outputs(tmp_path):
    config = tmp_path / 'config.json'
    night.write(config, {'training_enabled': True})
    protocol = dict(input_hashes={str(config): night.sha(config)}, python='python',
                    phases=night.commands(tmp_path, 'python'))
    night.write(tmp_path / 'protocol.json', protocol)
    night.verify(tmp_path)
    night.write(config, {'training_enabled': False})
    with pytest.raises(AssertionError, match='input changed'):
        night.verify(tmp_path)
    night.write(config, {'training_enabled': True})
    (tmp_path / 'data').mkdir()
    with pytest.raises(AssertionError, match='No resume'):
        night.verify(tmp_path)


def setup_monitor(out):
    (out / 'train').mkdir()
    night.write(out / 'supervisor.json', dict(state='RUNNING', phase='train', last_check_unix=time.time(), worker_pid=123))
    night.write(out / 'train/status.json', dict(state='ONLINE_TRAINING', step=100, loss=0.2))
    (out / 'worker.log').write_text('normal\n')


def test_monitor_reads_only_new_errors_and_handles_rotation(tmp_path, capsys):
    setup_monitor(tmp_path)
    assert monitor.check(tmp_path) == 'OK'
    with (tmp_path / 'worker.log').open('a') as stream:
        stream.write('RuntimeError: technical test\n')
    assert monitor.check(tmp_path) == 'ERROR'
    assert monitor.check(tmp_path) == 'OK'
    (tmp_path / 'worker.log').write_text('NaN\n')
    assert monitor.check(tmp_path) == 'ERROR'


def test_monitor_rejects_stale_supervisor_and_accepts_ready(tmp_path):
    night.write(tmp_path / 'status.json', dict(state='READY'))
    assert monitor.check(tmp_path) == 'READY'
    setup_monitor(tmp_path)
    night.write(tmp_path / 'supervisor.json', dict(state='RUNNING', phase='train', last_check_unix=time.time()-60))
    assert monitor.check(tmp_path) == 'ERROR'


def test_monitor_warns_on_missing_progress(tmp_path):
    setup_monitor(tmp_path)
    assert monitor.check(tmp_path) == 'OK'
    path = tmp_path / 'monitor/state.json'
    state = night.read(path)
    state['last_progress_unix'] = time.time()-601
    night.write(path, state)
    assert monitor.check(tmp_path) == 'WARNING'


def test_monitor_ignores_known_optional_startup_but_reports_runtime_warning(tmp_path):
    setup_monitor(tmp_path)
    with (tmp_path / 'worker.log').open('a') as stream:
        stream.write('[robosuite WARNING] No private macro file found!\n')
    assert monitor.check(tmp_path) == 'OK'
    with (tmp_path / 'worker.log').open('a') as stream:
        stream.write('RuntimeWarning: overflow encountered\n')
    assert monitor.check(tmp_path) == 'WARNING'


@pytest.mark.parametrize('fail_phase, expected', [(None, 'COMPLETED'), ('warmup', 'ERROR')])
def test_supervisor_sequences_once_and_stops_at_failed_gate(tmp_path, monkeypatch, fail_phase, expected):
    started, checked = [], []
    protocol = dict(total_cap_seconds=100, phase_cap_seconds=30, input_hashes={},
                    phases=[(phase, [phase]) for phase in ('prepare', 'warmup', 'train')])
    monkeypatch.setattr(night, 'verify', lambda out: protocol)
    monkeypatch.setattr(night.ctypes, 'windll', SimpleNamespace(kernel32=SimpleNamespace(SetThreadExecutionState=lambda flag: 1)))

    def spawn(cmd, **kwargs):
        started.append(cmd[0])
        return SimpleNamespace(pid=123, returncode=0, poll=lambda: 0)

    def gate(out, phase, code):
        checked.append(phase)
        if phase == fail_phase:
            raise AssertionError('Simulated gate failure')

    monkeypatch.setattr(night.subprocess, 'Popen', spawn)
    monkeypatch.setattr(night, 'phase_ok', gate)
    night.supervise(tmp_path)
    assert started == checked == (['prepare', 'warmup'] if fail_phase else ['prepare', 'warmup', 'train'])
    assert night.read(tmp_path / 'supervisor.json')['state'] == expected
