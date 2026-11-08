"""Prepare a separate online pilot only after fresh range confirmation."""
from pathlib import Path
import argparse
import json
import shutil
import time
from new_test import settings, run

HERE=Path(__file__).resolve().parent


def prepare(source, experiment, out):
    decision=json.loads((experiment/'decision.json').read_text())
    assert decision['confirmed'] and decision['next_test_ready'], 'Action-range confirmation did not pass'
    assert json.loads((experiment/'status.json').read_text())['state']=='COMPLETED'
    bound=decision['selected_limit']
    planned=json.loads((experiment/'protocol.json').read_text())
    assert bound in planned['action_limits'] and bound in decision['passed_levels']
    for path,h in planned['input_hashes'].items():
        assert run.sha(path)==h, f'Range-test input changed: {path}'
    result=json.loads((experiment/'results.json').read_text())[f'limit_{bound:.2f}']
    assert [r['critic_updates'] for r in result]==[10,50,100,500] and all(r['gate_passed'] for r in result)
    confirmation=json.loads((experiment/'confirmation.json').read_text())
    assert set(confirmation)=={'1','2','3'}
    assert all(r['paired_losses']<=2 and r['drift']['finite'] for r in confirmation.values())
    assert sum(r['paired_losses'] for r in confirmation.values())<=3
    cfg=settings()
    cfg.update(schema='bounded-online-pilot-range-v1',action_limit=bound,technical_only=False)
    cfg['gate']['max_abs_action_delta']=bound+1e-6
    cfg['exploration']=f'XYZ std .05, then project executed actions to IL-parent +/- {bound}; gripper noise zero'
    cfg['parameter_selection']=dict(source=str(experiment),limit_chosen_before_confirmation=True,
                                   final_endtest_used=False)
    inputs=dict(planned['input_hashes'])
    for file in (Path(__file__),HERE/'new_test.py',experiment/'decision.json',experiment/'selection.json',
                 experiment/'results.json',experiment/'confirmation.json',experiment/'confirmation_baseline.json'):
        inputs[str(file.resolve())]=run.sha(file)
    assert not out.exists()
    out.mkdir()
    run.dump(out/'config.json',cfg)
    inputs[str(out/'config.json')]=run.sha(out/'config.json')
    command=f'praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/new_test.py run --execute --output "{out}"'
    run.dump(out/'protocol.json',dict(source=str(source),range_experiment=str(experiment),input_hashes=inputs,
             prepared_unix=time.time(),scientific_training_started=False,command=command))
    snap=out/'source_snapshot';snap.mkdir()
    for name in ('new_test.py','stability.py','action_range.py','prepare_range_pilot.py','core.py','run.py'):
        shutil.copy2(HERE/name,snap/name)
    run.dump(out/'status.json',dict(state='READY',action_limit=bound,updated_unix=time.time()))
    print(json.dumps(dict(state='READY',action_limit=bound,output=str(out),started=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=HERE/'night_001')
    p.add_argument('--experiment',type=Path,default=HERE/'range_001')
    p.add_argument('--output',type=Path,default=HERE/'pilot_002');args=p.parse_args()
    prepare(args.source.resolve(),args.experiment.resolve(),args.output.resolve())
