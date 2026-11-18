"""Fixed descriptive endpoints for the frozen completion/placement calibration."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def analyze(out):
    plan = read(out/'plan.json')
    if read(out/'status.json')['state']!='COMPLETE':
        raise ValueError('Require complete run')
    groups = read(out/'groups.json')
    col = {name:i for i,name in enumerate(read(out/'trace_schema.json'))}
    panels, details, scenes = {}, [], {}
    for group in groups:
        case, arms = group['case'],group['arms']
        panel = panels.setdefault(case['panel'],{})
        control = arms['control']
        if case['panel']!='known':
            scene = scenes.setdefault(str(case['seed']),dict(initial_sha256=control['initial_sha256'],
                features=control['initial_features'],control_success_by_parent={}))
            scene['control_success_by_parent'][case['model']] = control['success']
        for arm,row in arms.items():
            bucket = panel.setdefault(arm,dict(n=0,successes=0,gains=0,losses=0,exposed=0,
                guard_blocked_frames=0,by_parent={},phase_contexts={}))
            bucket['n'] += 1
            bucket['successes'] += int(row['success'])
            bucket['gains'] += int(row['success'] and not control['success'])
            bucket['losses'] += int(control['success'] and not row['success'])
            bucket['exposed'] += int(any(row[k]>0 for k in ('action_override_frames','completion_override_frames','guard_blocked_frames')))
            bucket['guard_blocked_frames'] += row['guard_blocked_frames']
            parent = bucket['by_parent'].setdefault(case['model'],dict(n=0,successes=0,gains=0,losses=0))
            for key in ('n','successes','gains','losses'):
                parent[key] += int(True if key=='n' else row['success'] if key=='successes' else
                    (row['success'] and not control['success']) if key=='gains' else (control['success'] and not row['success']))
            with np.load(out/'traces'/f"{case['id']}_{arm}.npz") as archive:
                trace = archive['trace']
            for stage in (1,2):
                for phase in (1,5):
                    key = f'{stage}/{phase}'
                    scope = (trace[:,col['placement']]==stage)&(trace[:,col['phase']]==phase)&(trace[:,col['retreat']]==0)
                    rows = trace[scope]
                    context = bucket['phase_contexts'].setdefault(key,dict(reached=0,exited=0,
                        teacher_ready_frames=0,stalled_despite_20_ready_frames=0,exits_without_pre_readiness=0,
                        release_entries_without_readiness=0,guard_blocked_frames=0,unready_exit_reasons={}))
                    if not len(rows):
                        continue
                    context['reached'] += 1
                    done = bool(rows[:,col['actual_done']].any())
                    context['exited'] += int(done)
                    ready_count = int((rows[:,col['teacher_ready']]==1).sum())
                    context['teacher_ready_frames'] += ready_count
                    context['stalled_despite_20_ready_frames'] += int(not done and ready_count>=20)
                    context['guard_blocked_frames'] += int(rows[:,col['guard_blocked']].sum())
                    for event in row['events']:
                        if event['placement']!=stage or event['phase']!=phase or phase!=5:
                            continue
                        context['exits_without_pre_readiness'] += int(not event['pre_placement_ready'])
                        context['release_entries_without_readiness'] += int(not event['release_entry_ready'])
                        xy,height,contact,speed,angular,lower = event['pre_placement_features']
                        cfg = plan['placement_readiness']
                        reasons = dict(xy=xy>cfg['xy_max_m'],height=abs(height-cfg['height_m'])>cfg['height_tolerance_m'],
                            contact=not contact,linear_speed=speed>cfg['source_linear_max_m_s'],
                            angular_speed=angular>cfg['source_angular_max_rad_s'],lower_prefix=not lower)
                        for reason,bad in reasons.items():
                            context['unready_exit_reasons'][reason] = context['unready_exit_reasons'].get(reason,0)+int(bad)
            details.append(dict(case=case['id'],panel=case['panel'],seed=case['seed'],model=case['model'],arm=arm,
                success=row['success'],gain=bool(row['success'] and not control['success']),
                loss=bool(control['success'] and not row['success']),final_stage=row['final_stage'],final_phase=row['final_phase'],
                events=row['events'],guard_blocked_frames=row['guard_blocked_frames']))
    result = dict(technical_only=plan['technical_only'],optimizer_updates=0,panels=panels,
        scenes=scenes,details=details,
        inputs_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
            ('plan.json','groups.json','integrity.json','trace_schema.json')},
        scope='Opened calibration plus separately reported selected known failures; no blind confirmation or new training replication')
    (out/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    lines = ['# Abschluss und Ablage: eingefrorene Kalibrierung','',
        f"Technical only: {plan['technical_only']}; optimizer updates: 0; episodes: {plan['episodes']}.",
        '', 'Gepaarte vollstaendige Aufgabe, unveraenderte 50 strenge Frames.',
        '', '| Panel | Arm | Modell/Szenen-Paare | Erfolge | Gewinne | Verluste |',
        '|---|---|---:|---:|---:|---:|']
    for panel,arms in panels.items():
        for arm,bucket in arms.items():
            lines.append(f"| {panel} | {arm} | {bucket['n']} | {bucket['successes']} | {bucket['gains']} | {bucket['losses']} |")
    lines += ['', '## Phasenkontexte','',
        '| Panel | Arm | Platzierung/Phase | Erreicht | Verlassen | Stillstand trotz >=20 Expertenbereit-Frames | Austritt ohne Ablagebereitschaft | Freigabeeintritt ohne Bereitschaft |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for panel,arms in panels.items():
        for arm,bucket in arms.items():
            for key,c in bucket['phase_contexts'].items():
                lines.append(f"| {panel} | {arm} | {key} | {c['reached']} | {c['exited']} | {c['stalled_despite_20_ready_frames']} | "+
                    (f"{c['exits_without_pre_readiness']} | {c['release_entries_without_readiness']} |" if key.endswith('/5') else 'n/a | n/a |'))
    lines += ['', '## Einzelne bekannte Fehler','', '| Parent | Seed | Arm | Erfolg | Endplatzierung/Phase | Guard-Blockierungen |',
        '|---|---:|---|---:|---|---:|']
    for row in details:
        if row['panel']=='known':
            lines.append(f"| {row['model']} | {row['seed']} | {row['arm']} | {int(row['success'])} | {row['final_stage']}/{row['final_phase']} | {row['guard_blocked_frames']} |")
    lines += ['', '## Interpretation und Grenzen','',
        'Die Ablagebereitschaft ist eine vorab definierte physikalische Vergleichsregel. Ein Austritt ohne diese Bedingung ist kein alleiniger Ursachenbeweis. '
        'Die Expertenregel ist ebenfalls nicht unfehlbar. Guard, Aktion und Abschluss wirken durch unterschiedliche Folgezustaende.',
        '', 'Alle neuen Szenen sind geoeffnete Kalibrierung. Erfolgreiche Kontrollen und Verluste bleiben erhalten. '
        'Gleiche Szenen ueber drei geerbte Parents sind abhaengig; die Zahlen ersetzen keine neuen unabhaengigen Trainingsseeds. '
        'Keine Konfidenzintervalle oder allgemeine Ueberlegenheit aus diesem kleinen Diagnosepanel ableiten.',
        '', 'Anfangsmerkmale und Initialzustandshashes stehen in analysis.json/scenes. '
        'Sie sind noch keine validierte Schwierigkeitsskala. Kein Guard und keine Expertenregel wird automatisch in die Hauptpolicy uebernommen.',
        '', 'Reproduktion der Auswertung: analyze.py --output <dieser Laufordner>.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    analyze(parser.parse_args().output.resolve())
