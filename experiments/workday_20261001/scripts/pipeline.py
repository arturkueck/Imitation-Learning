"""Bounded unattended training, matched evaluation, and incremental reporting."""
import ctypes
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/workday_20261001'
SHARED=ROOT/'experiments/square/scripts'
LOGS=EXP/'logs'; LOGS.mkdir(exist_ok=True)
manifest=json.loads((EXP/'manifest.json').read_text())
started=time.monotonic(); deadline=started+manifest['deadline_hours']*3600
status=dict(state='STARTING',pid=os.getpid(),jobs={},errors=[],results=[],
    deadline_hours=manifest['deadline_hours'],started_at=datetime.now(timezone.utc).isoformat())

def save():
    status['updated_at']=datetime.now(timezone.utc).isoformat()
    status['elapsed_minutes']=round((time.monotonic()-started)/60,1)
    temp=EXP/'status.tmp'; temp.write_text(json.dumps(status,indent=2)); temp.replace(EXP/'status.json')
    report()

def report():
    lines=['# Ergebnisse des Arbeitstags-Laufs','',f"Status: {status['state']}; Laufzeit {status.get('elapsed_minutes',0)} Minuten.",'',
        'Alle neuen Videos: vier Perspektiven, anschließend zwei Sekunden Fortsetzung. Alte Experimente bleiben erhalten.',
        'Modellauswahl: 15 Entwicklungsepisoden ab Seed 6000; unabhängiger Abschlusstest: 50 Episoden ab Seed 26000.',
        'Robustheit: 10 gepaarte Episoden je Bedingung ab Seed 36000. Kleine Stichproben liefern Hinweise, keine sicheren Rangfolgen.','',
        '| Modell / Checkpoint | Split | Erfolg | B gegriffen | B angehoben | Zweierstapel abgelegt | Basis angehoben |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in status['results']:
        stage=r.get('stages',{})
        fmt=lambda key: f"{stage[key]:.0%}" if key in stage else '–'
        lines.append(f"| {r['name']} | {r['split']} ({r['episodes']}) | {r['success_rate']:.0%} | {fmt('grasp_B')} | {fmt('lift_B')} | {fmt('placed_pair')} | {fmt('base_lifted')} |")
    lines+=['','## Interpretation','',
        'Die Objektpositions-Variante verwendet privilegierte Simulatorinformationen. Sie dient zur Diagnose und ist nicht direkt als visuelle Roboter-Policy vergleichbar.',
        'Kurz/Lang-Vision nutzen dieselben Daten, Eingaben und 80 Bild-Zeitschritte pro Trainingsbatch (16×5 bzw. 4×20). Sequenzlänge, RNN-Zustandsdauer und Anzahl unterschiedlicher Sequenzen pro Batch ändern sich gemeinsam.',
        'Square-GMM verändert gegenüber dem bisherigen RNN die Aktionsverteilung (Mischmodell statt MSE-Punktvorhersage). Seine Trainingsverluste sind deshalb nicht numerisch mit MSE-Loss vergleichbar.','']
    selected=[r for r in status['results'] if r['split']=='test' and r['name'].startswith('stack_two')]
    state=next((r for r in selected if r['name']=='stack_two_state_long'),None)
    vision=[r for r in selected if 'vision' in r['name']]
    if state and vision:
        gap=state['success_rate']-max(r['success_rate'] for r in vision)
        if gap >= .2:
            lines.append('Die Objektpositions-Policy liegt deutlich vor den visuellen Varianten. Das unterstützt einen Engpass bei der visuellen Zustandsabschätzung; eine einzelne Trainingsinitialisierung beweist die Ursache nicht.')
        elif max(r['success_rate'] for r in selected)<.2:
            lines.append('Auch mit Objektpositionen bleibt die Leistung niedrig. Phasensteuerung, Demonstrationsabdeckung und Aktionsmodell sollten vor weiterer Skalierung untersucht werden.')
        else:
            lines.append('Die gemessenen Varianten zeigen Unterschiede; Erfolg, Teilstufen und Videos gemeinsam beurteilen. Erst einen zuverlässigen Zweierstapel erreichen, bevor vier Würfel wieder trainiert werden.')
    short=next((r for r in selected if r['name']=='stack_two_vision_short'),None)
    long=next((r for r in selected if r['name']=='stack_two_vision_long'),None)
    if short and long:
        lines.append(f"Vision mit längerem Kontext: {long['success_rate']:.0%}; kurzer Kontext: {short['success_rate']:.0%}. Ein Unterschied gilt zunächst für diese Trainingsinitialisierung und Teststichprobe.")
    square=[r for r in status['results'] if r['split']=='test' and r['name'].startswith('square')]
    gmm=next((r for r in square if r['name']=='square_rnn_gmm'),None)
    reference=next((r for r in square if r['name']=='square_old_rnn'),None)
    if gmm and reference:
        lines.append(f"Square-GMM: {gmm['success_rate']:.0%}; bisheriges RNN: {reference['success_rate']:.0%} auf denselben 50 neuen Seeds. Unterschiede in Trainingsdauer und Initialisierung verhindern eine reine Aussage über den GMM-Kopf allein.")
    summaries=list((EXP/'robustness').glob('*/SUMMARY.json'))
    if summaries:
        lines+=['','## Robustheit','',
            '| Modell | Bedingung | Erfolg | Abfall gegenüber nominal (Prozentpunkte) |',
            '|---|---|---:|---:|']
        for path in summaries:
            data=json.loads(path.read_text())
            for row in data['conditions']:
                lines.append(f"| {data['method']} | {row['condition']} | {row['success_rate']:.0%} | {row['success_drop_percentage_points']:.1f} |")
    lines+=['','## Fehler / ausgelassene Schritte','']
    lines += [f"- {e}" for e in status['errors']] or ['Keine bisher.']
    lines+=['','Übergabeaufgabe: geprüft, aber kein Demonstrationsdatensatz / validierter Expert vorhanden. Kein blindes Training eingeplant.',
        'Vierer-Stapel: frühere beste Validierungs-Checkpoints werden geprüft; unverändertes Weitertraining ist ausgesetzt.',
        'Robustheitsdetails stehen in den Unterordnern `robustness/`, Rohdaten in `evaluation/`, Videos in `videos/`.']
    (EXP/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')

def run(script,args,tag,minutes):
    remaining=deadline-time.monotonic()
    if remaining<120: raise TimeoutError('Global time budget exhausted')
    status['current_step']=tag; save()
    with (LOGS/f'{tag}.log').open('w',encoding='utf-8') as log:
        child=subprocess.Popen([sys.executable,'-u',str(SHARED/script),*map(str,args)],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        status['child_pid']=child.pid; save()
        try:
            code=child.wait(timeout=min(minutes*60,remaining-60))
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            child.wait(timeout=30)
            raise TimeoutError(f'{tag}: time limit; checkpoints preserved')
        finally:
            status.pop('child_pid',None)
    if code: raise RuntimeError(f'{tag}: exit {code}, see logs/{tag}.log')

def evaluate(checkpoint,name,split,horizon,episodes,seed,videos=0):
    label=f'{split}/{name}'
    status['state']='EVALUATING'; save()
    run('evaluate.py',[checkpoint,label,'--output-root',EXP,'--episodes',episodes,
        '--horizon',horizon,'--seed',seed,'--video-episodes',videos],
        f"evaluate_{split}_{name}",25)
    path=EXP/'evaluation'/label/'evaluation_results.json'
    result=json.loads(path.read_text())
    row=dict(name=name,split=split,checkpoint=str(checkpoint),horizon=horizon,
        episodes=result['episodes'],success_rate=result['success_rate'],
        sustained_success_rate=result['sustained_success_rate'],path=str(path))
    stages=[r['stack_progress'] for r in result['rollouts'] if 'stack_progress' in r]
    if stages:
        row['stages']=dict(grasp_B=sum(1 in r['grasped_cube_indices'] for r in stages)/len(stages),
            lift_B=sum(1 in r['lifted_cube_indices'] for r in stages)/len(stages),
            placed_pair=sum(r['released_correct_pair_steps'][0]>0 for r in stages)/len(stages),
            base_lifted=sum(r['base_lifted'] for r in stages)/len(stages))
    status['results'].append(row); save()
    return row

def attempt(action,label):
    try: return action()
    except Exception as error:
        status['errors'].append(f'{label}: {error}')
        print(traceback.format_exc(),flush=True); save()
        return None

def best_loss(folder):
    files=list(folder.glob('**/models/*best_validation*.pth'))
    if files: return min(files,key=lambda p:float(p.stem.split('best_validation_')[-1]))
    # New runs save every 50 epochs to avoid hundreds of 140-MB files.
    log=LOGS/f'train_{folder.name}.log'
    if not log.exists(): return None
    values={int(e):json.loads(v)['Loss'] for e,v in re.findall(
        r'Validation Epoch (\d+)\s*(\{.*?\})',log.read_text(errors='replace'),re.S)}
    files=[p for p in folder.glob('**/models/model_epoch_*.pth')
        if int(p.stem.split('_')[2]) in values]
    return min(files,key=lambda p:values[int(p.stem.split('_')[2])]) if files else None

def main():
    import h5py
    info=json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())
    collection=json.loads((ROOT/'experiments/additional_tasks/stack_two/collection_report.json').read_text())
    assert collection['ready_for_baseline'] and collection['accepted']==200
    with h5py.File(info['dataset'],'r') as f:
        assert len(f['data'])==200 and len(f['mask/train'])==180 and len(f['mask/valid'])==20
        assert all(d['rewards'][-1]>0 and 'object' in d['obs'] for d in f['data'].values())
    # First long-running step is training, not collection or historical evaluation.
    selections=[]
    for job in manifest['jobs']:
        name=job['name']; folder=EXP/name
        if list(folder.glob('runs/**/*.pth')): raise RuntimeError(f'Existing run: {name}')
        status['state']='TRAINING'; status['jobs'][name]='TRAINING'; save()
        attempt(lambda:run('train_model.py',[job['config']],f'train_{name}',75),name)
        final=sorted(folder.glob('runs/**/models/model_epoch_*.pth'),
            key=lambda p:int(p.stem.split('_')[2]))
        if not final:
            status['jobs'][name]='FAILED'; save(); continue
        last=final[-1]; best=best_loss(folder)
        candidates=[('best_validation',best),('last',last)] if best!=last else [('last',last)]
        measured=[]
        for label,path in candidates:
            if path:
                row=attempt(lambda p=path,l=label:evaluate(p,name+'_'+l,'development',job['horizon'],15,6000),name+'_'+label)
                if row: measured.append(row)
        if measured:
            chosen=max(measured,key=lambda r:(r['success_rate'],r['sustained_success_rate'],
                r.get('stages',{}).get('placed_pair',0),r.get('stages',{}).get('lift_B',0)))
            selections.append(dict(name=name,checkpoint=chosen['checkpoint'],horizon=job['horizon'],
                development_success=chosen['success_rate'],kind=job['kind']))
            attempt(lambda:evaluate(chosen['checkpoint'],name,'test',job['horizon'],50,26000,8),name+' test')
            status['jobs'][name]='COMPLETED'; save()
    # Compare the existing algorithms without spending time on unchanged training.
    old=ROOT/'experiments/square_overnight'
    historical=[('square_old_bc',ROOT/'experiments/square/bc/final.pth',400,'Square'),
        ('square_old_rnn',old/'bc_rnn/final.pth',400,'Square'),
        ('square_old_transformer_epoch200',next((old/'bc_transformer/runs').glob('**/model_epoch_200.pth')),400,'Square')]
    for method in ('bc_rnn','bc_transformer'):
        path=best_loss(ROOT/'experiments/additional_tasks/stack_four'/method)
        if path: historical.append(('stack_four_'+method+'_best_validation',path,1000,'StackFour'))
    for name,path,horizon,kind in historical:
        if path.exists():
            row=attempt(lambda:evaluate(path,name,'development',horizon,15,6000,2),name)
            if row and kind=='Square':
                selections.append(dict(name=name,checkpoint=str(path),horizon=horizon,
                    development_success=row['success_rate'],kind=kind))
                attempt(lambda:evaluate(path,name,'test',horizon,50,26000,5),name+' test')
    # Verify paired starts across same-task held-out comparisons.
    for kind,prefix in [('StackTwo','stack_two'),('Square','square')]:
        rows=[r for r in status['results'] if r['split']=='test' and r['name'].startswith(prefix)]
        states=[]
        for row in rows:
            data=json.loads(Path(row['path']).read_text())
            states.append([(r['seed'],r['intervention']['initial_state_sha256']) for r in data['rollouts']])
        if states:
            status.setdefault('paired_test_starts',{})[kind]=all(s==states[0] for s in states)
            if not status['paired_test_starts'][kind]: status['errors'].append(f'{kind}: paired starts differ')
    # Robustness is meaningful for deployable visual models; exclude the oracle.
    for kind in ('StackTwo','Square'):
        options=[s for s in selections if s['kind']==kind and 'state_long' not in s['name']]
        if not options: continue
        winner=max(options,key=lambda r:r['development_success'])
        status['state']='ROBUSTNESS'; save()
        attempt(lambda:run('robustness_suite.py',[winner['checkpoint'],winner['name'],
            '--output-root',EXP,'--horizon',winner['horizon'],'--episodes',10,
            '--seed',36000,'--video-episodes',2],f"robustness_{winner['name']}",50),kind+' robustness')
    status['selections']=selections
    status['state']='COMPLETED_WITH_ERRORS' if status['errors'] else 'COMPLETED'; save()

if __name__=='__main__':
    status['sleep_prevention_active']=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    save()
    try: main()
    except Exception:
        status['state']='FAILED'; status['errors'].append(traceback.format_exc()); save(); raise
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        status['sleep_prevention_active']=False; save()
