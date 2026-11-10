"""Independent DP training and repaired Square robustness evaluation."""
import ctypes
from datetime import datetime, timezone
import json, os, re, subprocess, sys, time, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
SHARED=ROOT/'experiments/baselines/square/scripts'
sys.path.insert(0,str(SHARED))
from atomic_json import write_json
EXP=ROOT/'experiments/baselines/diffusion_20261001'
LOGS=EXP/'logs'; LOGS.mkdir(exist_ok=True)
manifest=json.loads((EXP/'manifest.json').read_text())
started=time.monotonic(); deadline=started+manifest['deadline_hours']*3600
status=dict(state='STARTING',pid=os.getpid(),jobs={},results=[],errors=[],
    started_at=datetime.now(timezone.utc).isoformat(),deadline_hours=manifest['deadline_hours'],
    repair=dict(state='PENDING',output_root=str(EXP/'repair')))
repair=None; repair_log=None

def report():
    rows=['# Diffusion Policies und reparierte Störungsprüfung','',
        f"Status: {status['state']}; Laufzeit: {status.get('elapsed_minutes',0)} Minuten.",
        f"Square-GMM-Störungsprüfung: {status['repair']['state']}.",'',
        '| Modell | Split | Erfolg | Stabil nach Nachlauf |', '|---|---|---:|---:|']
    for r in status['results']:
        rows.append(f"| {r['name']} | {r['split']} ({r['episodes']}) | {r['success_rate']:.0%} | {r['sustained_success_rate']:.0%} |")
    rows+=['','## Vergleich und Grenzen','',
        'Neue Modelle: UNet-Diffusion Policy mit EMA, zwei Beobachtungen, 16 vorhergesagten Aktionen und acht ausgeführten Aktionen pro Neuplanung. DDIM mit zehn Entrauschungsschritten. 300 Epochen à 100 Batches, Batchgröße 8.',
        'Datensätze und Aufteilung bleiben identisch: jeweils 180 Trainings- und 20 Validierungstrajektorien. Alle 100 Epochen wird ein Checkpoint gespeichert.',
        'Checkpointauswahl auf 15 Entwicklungsepisoden (Seeds 6000–6014); unabhängiger Vergleich auf 50 Tests (Seeds 26000–26049), identisch zu den bisherigen BC-Tests.',
        'Bisherige Ergebnisse auf diesen Test-Seeds: StackTwo Vision kurz 4 %, Vision lang 0 %, Objektpositionen-RNN 0 %; Square GMM 20 %, RNN 12 %, Transformer 12 %. Unterschiede in Modellgröße, Trainingsbudget und Initialisierung verhindern eine reine isolierte Algorithmen-Aussage.',
        'Objektpositionen sind privilegierte Simulatorinformationen; die State-Policy dient der Diagnose und ist keine visuelle Roboter-Policy. Eine Trainingsinitialisierung je Modell; Erfolg ist nicht vorab garantiert.','']
    for task in ('stack_two','square'):
        tests=[r for r in status['results'] if r['split']=='test' and r['name'].startswith(task)]
        for r in tests:
            rows.append(f"Gemessen: {r['name']} erreicht {r['success_rate']:.0%} in 50 Tests.")
    repaired=EXP/'repair/robustness/square_rnn_gmm_repaired/SUMMARY.json'
    summaries=([repaired] if repaired.exists() else [])+list((EXP/'robustness').glob('*/SUMMARY.json'))
    if summaries:
        rows+=['','## Robustheit','', '| Modell | Bedingung | Erfolg | Abfall (Prozentpunkte) |','|---|---|---:|---:|']
        for path in summaries:
            summary=json.loads(path.read_text())
            for r in summary['conditions']:
                rows.append(f"| {summary['method']} | {r['condition']} | {r['success_rate']:.0%} | {r['success_drop_percentage_points']:.1f} |")
    rows+=['','## Fehler','']
    rows += [f'- {e}' for e in status['errors']] or ['Keine bisher.']
    rows+=['','Videos: `videos/` und `repair/robustness/`; vier Perspektiven plus zwei Sekunden Nachlauf.',
        'Die vorherige Square-Prüfung brach beim atomaren Ersetzen einer Statusdatei mit WinError 5 ab. Die Reparatur verwendet eindeutige Temporärdateien und bis zu zehn Wiederholungsversuche bei kurzfristigen Dateisperren. Eine echte Windows-Sperre wurde im Vorabtest nachgestellt und erfolgreich überbrückt.',
        'Die bisherigen vier Trainings waren technisch abgeschlossen; sie werden nicht unverändert wiederholt. Die schwachen Stapelergebnisse werden mit einem anderen Aktionsmodell untersucht.']
    (EXP/'RESULTS.md').write_text('\n'.join(rows),encoding='utf-8')

def update_repair():
    if repair is None: return
    code=repair.poll()
    if code is None: status['repair']['state']='RUNNING'; return
    summary=EXP/'repair/robustness/square_rnn_gmm_repaired/SUMMARY.json'
    status['repair']['state']='COMPLETED' if code==0 and summary.exists() else 'FAILED'
    if status['repair']['state']=='COMPLETED':
        write_json(ROOT/'experiments/baselines/workday_20261001/recovery.json',dict(
            square_robustness='COMPLETED',summary=str(summary),
            note='Original failed run preserved; complete repetition with fixed status writes.'))
    elif not status['repair'].get('reported'):
        status['errors'].append('Repaired Square robustness failed; see logs/repair_square_gmm.log')
        status['repair']['reported']=True

def save():
    update_repair()
    status['updated_at']=datetime.now(timezone.utc).isoformat()
    status['elapsed_minutes']=round((time.monotonic()-started)/60,1)
    write_json(EXP/'status.json',status); report()

def terminate(child):
    if child and child.poll() is None:
        subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
        child.wait(timeout=30)

def run(script,args,tag,minutes):
    remaining=deadline-time.monotonic()
    if remaining<90: raise TimeoutError('Global 6.5-hour budget exhausted')
    status['current_step']=tag; save()
    with (LOGS/(tag+'.log')).open('w') as log:
        child=subprocess.Popen([sys.executable,'-u',str(SHARED/script),*map(str,args)],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        status['child_pid']=child.pid; save()
        try: code=child.wait(timeout=min(minutes*60,remaining-45))
        except subprocess.TimeoutExpired:
            terminate(child); raise TimeoutError(tag+' exceeded its budget; checkpoints preserved')
        finally: status.pop('child_pid',None)
    if code: raise RuntimeError(f'{tag}: exit {code}; see logs/{tag}.log')

def attempt(action,label):
    try: return action()
    except Exception as error:
        status['errors'].append(f'{label}: {error}'); print(traceback.format_exc(),flush=True); save()

def evaluate(checkpoint,name,split,horizon,episodes,seed,videos):
    status['state']='EVALUATING'; save()
    label=split+'/'+name
    run('evaluate.py',[checkpoint,label,'--output-root',EXP,'--episodes',episodes,
        '--seed',seed,'--horizon',horizon,'--video-episodes',videos],
        'eval_'+split+'_'+name,35)
    path=EXP/'evaluation'/label/'evaluation_results.json'
    data=json.loads(path.read_text())
    row={k:data[k] for k in ('episodes','success_rate','sustained_success_rate')}
    row.update(name=name,split=split,checkpoint=str(checkpoint),path=str(path))
    status['results'].append(row); save(); return row

def main():
    global repair, repair_log
    validation=json.loads((EXP/'smoke/validation.json').read_text())
    assert len(validation['models'])==3 and validation['windows_sharing_retry']
    # GMM rollouts are batch-one and share the GPU with training; separate
    # process and output directory keep the repaired evaluation independent.
    repair_log=(LOGS/'repair_square_gmm.log').open('w')
    repair=subprocess.Popen([sys.executable,'-u',str(SHARED/'robustness_suite.py'),
        manifest['repair_checkpoint'],'square_rnn_gmm_repaired','--output-root',str(EXP/'repair'),
        '--episodes','10','--horizon','400','--seed','36000','--video-episodes','2'],
        cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=repair_log,stderr=subprocess.STDOUT)
    status['repair']['pid']=repair.pid; save()
    selections=[]
    for job in manifest['jobs']:
        name=job['name']; folder=EXP/name
        if list(folder.glob('runs/**/*.pth')): raise RuntimeError('Existing run; refusing overwrite: '+name)
        status['state']='TRAINING'; status['jobs'][name]='TRAINING'; save()
        attempt(lambda:run('train_model.py',[job['config']],'train_'+name,75),name+' training')
        files=list(folder.glob('runs/**/models/model_epoch_*.pth'))
        if not files: status['jobs'][name]='FAILED'; save(); continue
        log=(LOGS/('train_'+name+'.log')).read_text(errors='replace')
        losses={int(e):json.loads(v)['Loss'] for e,v in re.findall(r'Validation Epoch (\d+)\s*(\{.*?\})',log,re.S)}
        available=[p for p in files if int(p.stem.split('_')[2]) in losses]
        best=min(available,key=lambda p:losses[int(p.stem.split('_')[2])]) if available else files[0]
        last=max(files,key=lambda p:int(p.stem.split('_')[2]))
        measured=[]
        for label,path in [('best_saved_validation',best),('last',last)]:
            if measured and path==best and path==last: break
            row=attempt(lambda:evaluate(path,name+'_'+label,'development',job['horizon'],15,6000,0),name+' '+label)
            if row: measured.append(row)
        if measured:
            chosen=max(measured,key=lambda r:(r['success_rate'],r['sustained_success_rate']))
            selections.append(dict(job=job,checkpoint=chosen['checkpoint'],success=chosen['success_rate']))
            attempt(lambda:evaluate(chosen['checkpoint'],name,'test',job['horizon'],50,26000,8),name+' test')
            status['jobs'][name]='COMPLETED'; save()
    # Check pairing against the prior BC tests, not only among new models.
    pairs={}
    for selection in selections:
        job=selection['job']; path=EXP/'evaluation/test'/job['name']/'evaluation_results.json'
        if not path.exists(): continue
        prior='square_rnn_gmm' if job['task']=='Square' else 'stack_two_vision_short'
        old=json.loads((ROOT/'experiments/baselines/workday_20261001/evaluation/test'/prior/'evaluation_results.json').read_text())
        new=json.loads(path.read_text())
        hashes=lambda data:[(r['seed'],r['intervention']['initial_state_sha256']) for r in data['rollouts']]
        pairs[job['name']]=hashes(old)==hashes(new)
        if not pairs[job['name']]: status['errors'].append(job['name']+': initial states differ from BC baseline')
    status['paired_starts_vs_bc']=pairs; save()
    for selection in selections:
        job=selection['job']
        if job['oracle']: continue
        status['state']='ROBUSTNESS'; save()
        attempt(lambda:run('robustness_suite.py',[selection['checkpoint'],job['name'],
            '--output-root',EXP,'--episodes','10','--horizon',job['horizon'],
            '--seed','36000','--video-episodes','2'],'robustness_'+job['name'],50),job['name']+' robustness')
    if repair.poll() is None:
        try: repair.wait(timeout=max(1,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            terminate(repair); status['errors'].append('Square repair exceeded global budget')
    update_repair()
    status['state']='COMPLETED_WITH_ERRORS' if status['errors'] else 'COMPLETED'; save()

if __name__=='__main__':
    status['sleep_prevention_active']=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    save()
    try: main()
    except Exception:
        status['errors'].append(traceback.format_exc()); status['state']='FAILED'; save(); raise
    finally:
        terminate(repair)
        if repair_log: repair_log.close()
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        status['sleep_prevention_active']=False; save()
