"""Sequential train / matched evaluation blocks using upstream robomimic resume."""
import csv
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / 'experiments/baselines/square_overnight'
SHARED = ROOT / 'experiments/baselines/square/scripts'
METHODS = ('bc_rnn','bc_transformer')

def save(status):
    status['updated_at'] = datetime.now(timezone.utc).isoformat()
    temp = EXP / 'status.tmp'
    temp.write_text(json.dumps(status,indent=2)); temp.replace(EXP / 'status.json')

def command(script, args, log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as stream:
        subprocess.run([sys.executable,'-u',str(SHARED / script),*map(str,args)],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,check=True)

def summarize():
    rows = []
    for method in METHODS:
        for epoch in range(50,301,50):
            path = EXP / 'evaluation' / method / f'epoch_{epoch}' / 'evaluation_results.json'
            if path.exists():
                r = json.loads(path.read_text())
                rows.append({'algorithm':method,'epoch':epoch,**{k:r[k] for k in
                    ('success_rate','avg_return','avg_episode_length','successes','episodes')}})
    with (EXP / 'learning_curve.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (EXP / 'learning_curve.json').write_text(json.dumps(rows,indent=2))
    text = ['# Measured learning curve','',
        '| Algorithm | Epoch | Success Rate | Avg Return | Avg Length | Successes |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        text.append(f"| {r['algorithm']} | {r['epoch']} | {r['success_rate']:.3f} | {r['avg_return']:.3f} | {r['avg_episode_length']:.2f} | {r['successes']}/{r['episodes']} |")
    text += ['', 'Epoch 50 reuses measured baseline results. Later rows are written only after evaluation.',
        'New evaluations: seeds 6000-6049, 50 episodes; original reference: 20 episodes. Horizon 400; development evaluation only.']
    (EXP / 'RESULTS.md').write_text('\n'.join(text),encoding='utf-8')

def main():
    manifest = json.loads((EXP / 'manifest.json').read_text())
    status = {'state':'STARTING','pipeline_pid':os.getpid(),
        'models':{m:{'state':'PENDING','epoch':50} for m in METHODS}}
    method = None
    save(status)
    try:
        summarize()
        for method in METHODS:
            run = Path(manifest['models'][method]['run_directory'])
            for epoch in range(100,301,50):
                status['state'] = status['models'][method]['state'] = 'TRAINING'
                status['models'][method]['target_epoch'] = epoch; save(status)
                command('train_model.py',[EXP / method / f'config_epoch_{epoch}.json','--resume'],
                    EXP / 'logs' / f'{method}_to_epoch_{epoch}_training.log')
                matches = list((run / 'models').glob(f'model_epoch_{epoch}*.pth'))
                assert len(matches) == 1, f'Missing or ambiguous checkpoint for epoch {epoch}'
                checkpoint = matches[0]
                status['models'][method]['epoch'] = epoch
                status['state'] = status['models'][method]['state'] = 'EVALUATING'
                save(status)
                command('evaluate.py',[checkpoint,f'{method}/epoch_{epoch}','--output-root',EXP,'--episodes','50'],
                    EXP / 'logs' / f'{method}_epoch_{epoch}_evaluation.log')
                result = EXP / 'evaluation' / method / f'epoch_{epoch}' / 'evaluation_results.json'
                measured = json.loads(result.read_text())
                assert measured['episodes'] == 50
                videos = list((EXP / 'videos' / method / f'epoch_{epoch}').glob('*.mp4'))
                assert len(videos) == 50 and all(p.stat().st_size > 0 for p in videos)
                summarize()
                status['models'][method]['latest_success_rate'] = measured['success_rate']; save(status)
                if epoch == 300:
                    shutil.copyfile(checkpoint,EXP / method / 'final.pth')
                    best = max((run / 'models').glob('*best_validation*.pth'),key=lambda p:p.stat().st_mtime)
                    shutil.copyfile(best,EXP / method / 'best_validation.pth')
                    status['state'] = status['models'][method]['state'] = 'ROBUSTNESS_EVALUATION'
                    save(status)
                    command('robustness_suite.py',[checkpoint,method,'--output-root',EXP],
                        EXP / 'logs' / f'{method}_robustness.log')
            status['models'][method]['state'] = 'COMPLETED'; save(status)
        status['state'] = 'COMPLETED'; save(status)
    except Exception:
        status['state'] = 'FAILED'; status['error'] = traceback.format_exc()
        if method: status['models'][method]['state'] = 'FAILED'
        save(status); traceback.print_exc(); raise

if __name__ == '__main__':
    main()
