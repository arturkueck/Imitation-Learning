"""Prepare isolated continuation runs, preserving existing weights and Adam state."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / 'experiments/baselines/square_overnight'
BASE = ROOT / 'experiments/baselines/square'
METHODS = ('bc_rnn','bc_transformer')
if (EXP / 'manifest.json').exists():
    raise RuntimeError('Already configured; do not overwrite continuation checkpoints.')
import torch
manifest = {'total_epochs':300,'initial_epoch':50,'evaluation_interval':50,
    'train_seed':1,'rollout_seeds':list(range(6000,6020)), 'models':{}}
for method in METHODS:
    source_runs = list((BASE / method / 'runs').glob('*/*/last.pth'))
    assert len(source_runs) == 1, f'Expected exactly one source run for {method}'
    source = source_runs[0]
    saved = torch.load(source, map_location='cpu', weights_only=False)
    assert saved['variable_state']['epoch'] == 50
    assert 'optimizers' in saved['model'], 'Optimizer state is required for continuation'
    del saved
    folder = EXP / method
    run = folder / 'runs' / method / 'continued_from_epoch50'
    run.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,run / 'last.pth')
    shutil.copyfile(source,run / 'last_bak.pth')
    models = run / 'models'
    models.mkdir(exist_ok=True)
    best = max((source.parent / 'models').glob('*best_validation*.pth'),key=lambda p:p.stat().st_mtime)
    shutil.copyfile(best,models / best.name)
    cfg = json.loads((BASE / method / 'config.json').read_text())
    cfg['train']['output_dir'] = str(folder / 'runs')
    cfg['train']['num_epochs'] = 300
    cfg['experiment']['save']['every_n_epochs'] = 50
    cfg['experiment']['rollout']['enabled'] = False
    folder.mkdir(exist_ok=True)
    (folder / 'config.json').write_text(json.dumps(cfg,indent=2))
    for epoch in range(100,301,50):
        cfg['train']['num_epochs'] = epoch
        (folder / f'config_epoch_{epoch}.json').write_text(json.dumps(cfg,indent=2))
    # Store measured epoch-50 results as the unchanged reference point.
    result = json.loads((BASE / 'evaluation' / method / 'evaluation_results.json').read_text())
    dest = EXP / 'evaluation' / method / 'epoch_50'
    dest.mkdir(parents=True,exist_ok=True)
    (dest / 'evaluation_results.json').write_text(json.dumps(result,indent=2))
    manifest['models'][method] = {'source_checkpoint':str(source),'source_sha256':
        hashlib.file_digest(source.open('rb'),'sha256').hexdigest(), 'run_directory':str(run)}
(EXP / 'manifest.json').write_text(json.dumps(manifest,indent=2))
(EXP / 'status.json').write_text(json.dumps({'state':'READY','pipeline_pid':None,
    'models':{m:{'state':'PENDING','epoch':50} for m in METHODS}},indent=2))
print('READY: continuation from epoch 50 to 300, not started')
