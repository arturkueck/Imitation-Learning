"""Prepare a declared learning experiment that permits temporary task regressions."""
from pathlib import Path
import argparse
import json
import shutil
import sys
import time
from new_test import settings,run

HERE=Path(__file__).resolve().parent


def configuration():
    cfg=settings()
    cfg.update(schema='relative-exploratory-online-v2',action_limit=.2,technical_only=False,
        target_action_projection='actor_bounds_v1',
        target_smoothing='Original noise std/clip, then project at NEXT input/phase into the same frozen-parent relative bounds as actor and exploration',
        policy_constraint=dict(kind='relative',cap=.2,beta=.5,gripper=.02),
        exploration='XYZ std .05 projected to min(.2,.5*abs(parent XYZ)); gripper width .02',
        performance_abort_enabled=False,temporary_regression_allowed=True,
        wall_clock_cap_seconds=10800,absolute_deadline_utc='2026-11-05T14:00:00+00:00',
        interpretation='Exploratory fixed-budget online learning after failed stability gates; no prior stability or efficacy claim.',
        checkpoint_selection='Fixed last round4, never best development checkpoint')
    # The production runner still computes paired losses. These explicit limits
    # disable early performance rejection while retaining all observations.
    cfg['gate'].update(max_paired_losses_per_seed=20,max_paired_losses_total=60,max_abs_action_delta=.200001)
    return cfg


def prepare(source,study,out):
    assert json.loads((study/'status.json').read_text())['state']=='COMPLETED'
    decision=json.loads((study/'decision.json').read_text())
    assert decision['policy_constraint']=='relative'
    proto=json.loads((study/'protocol.json').read_text());inputs=dict(proto['input_hashes']);source_changes={}
    declared_changes={str((HERE/name).resolve()) for name in ('core.py','relative_range.py')}
    for path,h in list(inputs.items()):
        current=run.sha(path)
        if current!=h:
            assert str(Path(path).resolve()) in declared_changes, f'Undeclared study input change: {path}'
            snapshot=study/'source_snapshot'/Path(path).name
            assert snapshot.exists() and run.sha(snapshot)==h, f'Historical source snapshot missing: {path}'
            source_changes[path]=dict(previous_sha256=h,new_sha256=current,historical_snapshot=str(snapshot),
                                      reason='Declared target-action projection correction; prior stability results not reused as proof')
            inputs[path]=current
    cfg=configuration()
    assert cfg['temporary_regression_allowed'] and not cfg['performance_abort_enabled']
    for path in (Path(__file__),HERE/'new_test.py',HERE/'relative_range.py',HERE/'pilot_watch.py',
                 study/'decision.json',study/'results.json'):
        inputs[str(path.resolve())]=run.sha(path)
    assert not out.exists();out.mkdir()
    run.dump(out/'config.json',cfg);inputs[str(out/'config.json')]=run.sha(out/'config.json')
    argv=[sys.executable,'-u',str(HERE/'relative_range.py'),'run','--execute','--output',str(out)]
    run.dump(out/'protocol.json',dict(source=str(source),prior_study=str(study),input_hashes=inputs,
        prior_stability_passed=decision['candidate_passed_stability'],
        declared_source_changes=source_changes,
        prepared_unix=time.time(),scientific_training_started=False,worker_argv=argv,
        decision='Separate research run permits temporary regression; historical failed gates remain unchanged'))
    snap=out/'source_snapshot';snap.mkdir()
    for name in ('prepare_exploratory.py','pilot_watch.py','relative_range.py','new_test.py','stability.py','core.py','run.py'):
        shutil.copy2(HERE/name,snap/name)
    run.dump(out/'status.json',dict(state='READY',updated_unix=time.time()))
    print(json.dumps(dict(state='READY',output=str(out),started=False,temporary_regression_allowed=True)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=HERE/'night_001')
    p.add_argument('--study',type=Path,default=HERE/'relative_002')
    p.add_argument('--output',type=Path,default=HERE/'pilot_002');a=p.parse_args()
    prepare(a.source.resolve(),a.study.resolve(),a.output.resolve())
