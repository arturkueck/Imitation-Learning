"""Train only after a complete, successful demonstration collection is present."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import h5py

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--task',choices=['stack_four','cube_handover'],required=True)
parser.add_argument('--methods',nargs='+',choices=['bc','bc_rnn','bc_transformer'],
    default=['bc_rnn','bc_transformer'])
args = parser.parse_args()
folder = ROOT / 'experiments/additional_tasks' / args.task
info = json.loads((folder / 'task_info.json').read_text())
report_path = folder / 'collection_report.json'
if not report_path.exists():
    raise RuntimeError('No validated demonstration dataset. Collect successful expert rollouts first.')
report = json.loads(report_path.read_text())
assert report['ready_for_baseline'] and report['accepted'] >= 100, 'Need >=100 validated demos'
with h5py.File(info['dataset']) as f:
    assert len(f['data']) == report['accepted']
    train,valid = set(f['mask/train'][:]),set(f['mask/valid'][:])
    assert train and valid and not train & valid
    assert len(train | valid) == len(f['data'])
    for demo in f['data'].values():
        assert demo['actions'].shape[-1] == info['action_dimension']
        for key in info['camera_keys']+info['proprioception_keys']:
            assert key in demo['obs']
shared = ROOT / 'experiments/square/scripts'
def progress(method,state):
    (folder / 'training_status.json').write_text(json.dumps({'algorithm':method,'state':state},indent=2))
for method in args.methods:
    if list((folder / method / 'runs').glob('**/*.pth')):
        raise RuntimeError('Existing training run: refusing to overwrite checkpoints')
    logs = folder / 'logs'; logs.mkdir(exist_ok=True)
    progress(method,'TRAINING')
    with (logs / f'{method}_training.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(shared/'train_model.py'),str(folder/method/'config.json')],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    matches = list((folder/method/'runs').glob('**/models/model_epoch_1000*.pth'))
    assert len(matches) == 1
    progress(method,'EVALUATING_AND_GENERATING_VIDEOS')
    with (logs / f'{method}_evaluation.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(shared/'evaluate.py'),str(matches[0]),method,
            '--output-root',str(folder),'--episodes','50','--horizon','1000'],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    progress(method,'ROBUSTNESS_EVALUATION')
    with (logs / f'{method}_robustness.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(shared/'robustness_suite.py'),str(matches[0]),method,
            '--output-root',str(folder),'--horizon','1000'],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    progress(method,'COMPLETED')
