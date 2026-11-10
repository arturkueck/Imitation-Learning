from types import SimpleNamespace
import pytest
import pilot_watch
from prepare_exploratory import configuration
from new_test import performance_gate


def test_zero_successes_are_recorded_without_early_performance_abort():
    cfg=configuration()
    baseline={str(s):[dict(success=True) for _ in range(20)] for s in (1,2,3)}
    failed={str(s):[dict(success=False) for _ in range(20)] for s in (1,2,3)}
    passed,losses=performance_gate(baseline,failed,cfg)
    assert passed and sum(losses.values())==60
    assert cfg['temporary_regression_allowed'] and not cfg['performance_abort_enabled']
    assert cfg['fixed_checkpoint_round']==4 and cfg['wall_clock_cap_seconds']==10800


def test_supervisor_records_worker_failure_without_retry(tmp_path,monkeypatch):
    cfg=configuration();started=[]
    monkeypatch.setattr(pilot_watch,'verify',lambda out:(dict(worker_argv=['test']),cfg))
    monkeypatch.setattr(pilot_watch.ctypes,'windll',SimpleNamespace(kernel32=SimpleNamespace(SetThreadExecutionState=lambda flag:1)))
    def spawn(argv,**kwargs):
        started.append(argv);return SimpleNamespace(pid=123,returncode=1,poll=lambda:1)
    monkeypatch.setattr(pilot_watch.subprocess,'Popen',spawn)
    pilot_watch.write(tmp_path/'status.json',dict(state='ERROR'))
    pilot_watch.supervise(tmp_path)
    assert pilot_watch.read(tmp_path/'supervisor.json')['state']=='ERROR'
    assert len(started)==1
