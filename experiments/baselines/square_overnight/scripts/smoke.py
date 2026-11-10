"""Verify real epoch-50 optimizer resume, checkpoint, and evaluator in isolation."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / 'experiments/baselines/square_overnight'
SHARED = ROOT / 'experiments/baselines/square/scripts'
TEST = EXP / 'smoke'
manifest = json.loads((EXP / 'manifest.json').read_text())
for method, info in manifest['models'].items():
    run = TEST / method / 'runs' / method / 'resume_test'
    run.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(info['source_checkpoint'],run / 'last.pth')
    cfg = json.loads((EXP / method / 'config.json').read_text())
    cfg['train'].update(num_epochs=51,output_dir=str(TEST / method / 'runs'))
    cfg['experiment'].update(epoch_every_n_steps=2,validation_epoch_every_n_steps=2)
    cfg['experiment']['save']['every_n_epochs'] = 1
    path = TEST / f'{method}.json'
    path.write_text(json.dumps(cfg,indent=2))
    with (TEST / f'{method}_train.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(SHARED / 'train_model.py'),str(path),'--resume'],
            stdout=log,stderr=subprocess.STDOUT,check=True)
    saved = torch.load(run / 'last.pth',map_location='cpu',weights_only=False)
    assert saved['variable_state']['epoch'] == 51
    del saved
    with (TEST / f'{method}_eval.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(SHARED / 'evaluate.py'),str(run / 'last.pth'),method,
            '--output-root',str(TEST),'--episodes','1','--horizon','3'],
            stdout=log,stderr=subprocess.STDOUT,check=True)
    result = json.loads((TEST / 'evaluation' / method / 'evaluation_results.json').read_text())
    assert result['episodes'] == 1 and result['rollouts'][0]['length'] <= 3
    import imageio.v2 as imageio
    with imageio.get_reader(str(TEST / 'videos' / method / 'rollout_00.mp4')) as reader:
        assert reader.get_data(0).shape == (768,768,3)
    print(f'SMOKE_OK {method}: optimizer resume epoch 51, evaluation JSON, MP4',flush=True)
