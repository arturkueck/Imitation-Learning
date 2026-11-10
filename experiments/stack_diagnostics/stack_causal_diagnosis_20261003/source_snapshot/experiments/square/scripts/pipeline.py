import runtime
import csv
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

EXP = runtime.ROOT / 'experiments/square'
SCRIPTS = EXP / 'scripts'
METHODS = ('bc','bc_rnn','bc_transformer')
LOGS = EXP / 'logs'
LOGS.mkdir(parents=True, exist_ok=True)
status = {'pipeline_pid':os.getpid(),'state':'PENDING',
    'models':{m:{'state':'PENDING'} for m in METHODS}}

def save_status():
    status['updated_at'] = datetime.now(timezone.utc).isoformat()
    temporary = EXP / 'status.tmp'
    temporary.write_text(json.dumps(status,indent=2))
    temporary.replace(EXP / 'status.json')

def run(script, args, log):
    with log.open('w',encoding='utf-8') as stream:
        subprocess.run([sys.executable,'-u',str(SCRIPTS / script),*map(str,args)],
            cwd=str(runtime.ROOT),stdout=stream,stderr=subprocess.STDOUT,check=True)

if __name__ == '__main__':
    if list((EXP / 'bc/runs').glob('**/*.pth')):
        raise RuntimeError('Existing checkpoints: use a new experiment directory to avoid overwrites.')
    save_status()
    current = None
    try:
        assert (EXP / 'dataset_info.json').exists(), 'Run prepare.py first'
        for current in METHODS:
            status['state'] = status['models'][current]['state'] = 'TRAINING'
            save_status()
            run('train_model.py',[EXP / current / 'config.json'],LOGS / f'{current}_training.log')
            checkpoints = sorted((EXP / current / 'runs').glob('**/models/model_epoch_50*.pth'))
            assert len(checkpoints) == 1, 'Final epoch checkpoint absent or ambiguous'
            final = EXP / current / 'final.pth'
            shutil.copyfile(checkpoints[0], final)
            candidates = list((EXP / current / 'runs').glob('**/models/*best_validation*.pth'))
            if candidates:
                best = max(candidates,key=lambda p:p.stat().st_mtime)
                shutil.copyfile(best,EXP / current / 'best_validation.pth')
            # Evaluate the final checkpoint consistently for every method.
            status['models'][current]['checkpoint'] = str(final)
            status['state'] = status['models'][current]['state'] = 'EVALUATING'
            status['models'][current]['video_generation'] = 'GENERATING_VIDEO (during evaluation)'
            save_status()
            run('evaluate.py',[final,current],LOGS / f'{current}_evaluation.log')
            status['models'][current]['state'] = 'GENERATING_VIDEO'
            status['state'] = 'GENERATING_VIDEO'; save_status()
            files = list((EXP / 'videos' / current).glob('*.mp4'))
            assert len(files) >= 3 and all(p.stat().st_size > 0 for p in files)
            status['models'][current]['state'] = 'ROBUSTNESS_EVALUATION'
            status['state'] = 'ROBUSTNESS_EVALUATION'; save_status()
            run('robustness_suite.py',[final,current,'--output-root',EXP],LOGS / f'{current}_robustness.log')
            status['models'][current]['state'] = 'COMPLETED'; save_status()
        results = [json.loads((EXP / 'evaluation' / m / 'evaluation_results.json').read_text()) for m in METHODS]
        columns = ['algorithm','success_rate','avg_return','avg_episode_length','successes','episodes']
        with (EXP / 'evaluation_results.csv').open('w',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=columns); writer.writeheader()
            writer.writerows({k:r[k] for k in columns} for r in results)
        (EXP / 'evaluation_results.json').write_text(json.dumps(results,indent=2))
        lines = ['# Measured results','', '| Algorithm | Success Rate | Avg Return | Avg Episode Length | Successes |',
                 '|---|---:|---:|---:|---:|']
        for r in results:
            lines.append(f"| {r['algorithm']} | {r['success_rate']:.3f} | {r['avg_return']:.3f} | {r['avg_episode_length']:.2f} | {r['successes']}/20 |")
        lines += ['', 'Final checkpoints; identical rollout seeds 6000–6019; horizon 400. No interpretation added.']
        (EXP / 'RESULTS.md').write_text('\n'.join(lines))
        status['state'] = 'COMPLETED'; save_status()
    except Exception:
        status['state'] = 'FAILED'
        status['error'] = traceback.format_exc()
        if current: status['models'][current]['state'] = 'FAILED'
        save_status()
        traceback.print_exc()
        sys.exit(1)
