"""Evaluate a checkpoint on matched nominal / single-factor conditions."""
import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from robustness import CONDITIONS
from atomic_json import write_json

parser = argparse.ArgumentParser()
parser.add_argument('checkpoint',type=Path)
parser.add_argument('method')
parser.add_argument('--output-root',type=Path,required=True)
parser.add_argument('--episodes',type=int,default=20)
parser.add_argument('--horizon',type=int,default=400)
parser.add_argument('--seed',type=int,default=16000)
parser.add_argument('--video-episodes',type=int,default=3)
args = parser.parse_args()
out = args.output_root.resolve() / 'robustness' / args.method
out.mkdir(parents=True,exist_ok=True)
if (out / 'SUMMARY.json').exists(): raise RuntimeError('Existing suite results; choose a new output root')
status = {'state':'EVALUATING','conditions':{k:'PENDING' for k in CONDITIONS}}
def save():
    write_json(out/'status.json',status)
save()
results = []
try:
    nominal_states = None
    for condition in CONDITIONS:
        status['current_condition'] = condition; status['conditions'][condition] = 'EVALUATING'; save()
        with (out / f'{condition}.log').open('w') as log:
            subprocess.run([sys.executable,'-u',str(Path(__file__).with_name('evaluate.py')),
                str(args.checkpoint.resolve()),condition,'--output-root',str(out),
                '--episodes',str(args.episodes),'--horizon',str(args.horizon),'--seed',str(args.seed),
                '--condition',condition,'--video-episodes',str(args.video_episodes)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        result = json.loads((out/'evaluation'/condition/'evaluation_results.json').read_text())
        states = [(r['seed'],r['intervention']['initial_state_sha256']) for r in result['rollouts']]
        if nominal_states is None: nominal_states = states
        assert states == nominal_states, 'Initial states differ: cannot report a paired comparison'
        results.append(result)
        status['conditions'][condition] = 'COMPLETED'; save()
    nominal = results[0]
    rows = [{k:r[k] for k in ('condition','episodes','success_rate','sustained_success_rate',
        'object_drop_rate','avg_return','avg_episode_length')} for r in results]
    for row,result in zip(rows,results):
        n = row['episodes']; p = row['success_rate']; z = 1.95996398454
        denominator = 1+z*z/n
        center = (p+z*z/(2*n))/denominator
        margin = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
        row['success_ci95_low'] = max(0.,center-margin)
        row['success_ci95_high'] = min(1.,center+margin)
        row['success_drop_percentage_points'] = 100*(nominal['success_rate']-row['success_rate'])
        row['episodes_with_dynamic_intervention'] = sum(bool(r['intervention']['events']) for r in result['rollouts'])
    (out/'SUMMARY.json').write_text(json.dumps({'method':args.method,'checkpoint':str(args.checkpoint.resolve()),
        'paired_initial_states_verified':True,'seed_start':args.seed,'conditions':rows},indent=2))
    with (out/'SUMMARY.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    lines = ['# Measured robustness results','',
        '| Condition | Success | Sustained success | Drop from nominal (pp) | Object drop rate |',
        '|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['condition']} | {r['success_rate']:.3f} | {r['sustained_success_rate']:.3f} | {r['success_drop_percentage_points']:.1f} | {r['object_drop_rate']:.3f} |")
    (out/'RESULTS.md').write_text('\n'.join(lines))
    status['state'] = 'COMPLETED'; save()
except Exception as error:
    status['state'] = 'FAILED'; status['error'] = str(error); save(); raise
