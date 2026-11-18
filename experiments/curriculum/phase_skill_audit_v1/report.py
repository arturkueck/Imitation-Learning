"""Summarize a completed, fixed-protocol phase diagnosis."""
from pathlib import Path
import argparse
import json
import statistics
from collections import Counter


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);args=parser.parse_args()
    run=args.run
    read=lambda name:json.loads((run/name).read_text(encoding='utf-8'))
    summary=read('summary.json');plan=read('plan.json');units=read('isolated_phases.json')
    full=read('full_rollouts.json');teachers=read('expert_reference.json')
    if not summary['complete'] or plan['technical_only']:raise ValueError('Require complete scientific diagnostic')
    rows=[]
    for stage in plan['placements']:
        for phase in plan['phases']:
            groups=[summary['models'][m][str(stage)][str(phase)] for m in plan['model_ids']]
            values={k:sum(g[k] for g in groups) for k in groups[0]}
            selected=[r for r in units if r['placement']==stage and r['phase']==phase]
            values.update(placement=stage,phase=phase,name=plan['phase_names'][str(phase)],
                all_isolated_successes=sum(r['success'] for r in selected),
                median_final_eef_goal_error_mm=statistics.median(r['final']['eef_goal_error']*1000 for r in selected),
                median_final_xy_error_mm=statistics.median(r['final']['xy_error']*1000 for r in selected),
                median_final_height_mm=statistics.median(r['final']['height_above_target']*1000 for r in selected),
                final_held=sum(r['final']['held'] for r in selected),
                final_pair_contact=sum(r['final']['pair_contact'] for r in selected))
            rows.append(values)
    failures=Counter(f"placement {r['final_stage']}, phase {r['final_phase']}, retreat_timeout={r['retreat_timeout']}" for r in full if not r['success'])
    grasp_groups={True:[],False:[]}
    for r in full:
        segment=next((s for s in r['segments'] if s['stage']==2 and s['phase']==3 and not s['retreat']),None)
        if segment is not None:grasp_groups[segment['start']['held']].append(r)
    grasp_table={str(k):dict(n=len(v),task_successes=sum(r['success'] for r in v)) for k,v in grasp_groups.items()}
    result=dict(rows=rows,full_successes=summary['full_episode_successes'],failed_episode_endpoints=dict(failures),
                teacher_reference=summary['teacher_reference'],second_lift_initial_grasp=grasp_table)
    (run/'diagnostic_tables.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# BC-Phasendiagnose: Ergebnisse','',
           'Drei unveränderte B-Modelle bei 30.000 Updates. Ausschließlich bereits verwendete Entwicklungsszenen; keine neue Bestätigungsprüfung und kein Training.','',
           f"Expertenkontrollen: {summary['teacher_reference']['successes']}/{len(teachers)} erfüllen das vorab definierte Diagnosekriterium. Alle BC-Starts wurden gegen den jeweiligen Expertenstart samt Simulationshistorie per SHA-256 geprüft.",'',
           '| Platzierung | Phase | Isoliert: alle Versuche | Isoliert: gültige Kontrollen/Eingänge | Vollständig: Besuche | Geeigneter Eingang | Physisches Ziel am letzten Frame |','|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['placement']} | {r['name']} | {r['all_isolated_successes']}/{r['isolated_attempts']} | {r['isolated_successes']}/{r['valid_reference_attempts']} | {r['full_visits']} | {r['full_eligible']} | {r['full_physically_ready_at_last_frame']} |")
    lines+=['','Isolierte Nenner schließen ungeeignete Eingänge oder erfolglose Expertenkontrollen aus. Vollständige Phasenbesuche hängen vom Erreichen früherer Phasen ab. Die letzte Spalte ist eine Momentaufnahme; bei Open ersetzt sie keine 50 stabilen Frames.','',
            '## Vollständige Drei-Würfel-Aufgabe','']
    for model,value in summary['full_episode_successes'].items():lines.append(f"- {model}: {value['successes']}/{value['n']}")
    lines+=['','## Wichtigster diagnostischer Befund','']
    for held,value in grasp_table.items():lines.append(f"- Erkannter Griff zu Beginn des zweiten Lift = {held}: {value['task_successes']}/{value['n']} vollständige Erfolge.")
    lines+=['','Travel und Open erreichen aus Expertenstarts jeweils 30/30 Diagnoseziele (zwei Platzierungen, drei Modelle, fünf gemeinsame Startkontexte). Im vollständigen Ablauf fehlt bei 15/48 erreichten zweiten Lift-Starts ein erkannter Griff; alle 15 Versuche scheitern. Diese Assoziation legt einen kontrollierten Eingriff in den zweiten Greifprozess nahe, beweist die Ursache aber noch nicht.','',
            'Die strenge Lift-Schwelle wird isoliert nur 6/30-mal eingehalten. Die medianen Abstände sind jedoch 6,41 bzw. 7,43 mm bei einer 6-mm-Schwelle; alle 30 isolierten Lift-Versuche enden mit erkanntem Griff. Daraus folgt kein generelles Versagen der Lift-Bewegung.','',
            'Ein reines zeitliches Nacheinandertrainieren der Phasen ist daher noch nicht begründet. Die sieben Köpfe besitzen eigene MLPs; das Trainieren von Lift baut keine gemeinsame Repräsentation für Travel auf. Ein nächstes BC-Curriculum sollte Zustandsabdeckung und Übergänge gezielt prüfen.']
    lines+=['','## Physische Abstände im isolierten Test','',
            '| Platzierung | Phase | Median EEF-Zielabstand (mm) | Median seitlicher Würfelfehler (mm) | Median Höhe über Zielwürfel (mm) | Kontakt am Ende |','|---|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['placement']} | {r['name']} | {r['median_final_eef_goal_error_mm']:.2f} | {r['median_final_xy_error_mm']:.2f} | {r['median_final_height_mm']:.2f} | {r['final_pair_contact']}/{r['isolated_attempts']} |")
    lines+=['','Der EEF-Zielabstand bezieht sich ausschließlich auf das Lift-Ziel und ist nur in der Lift-Zeile fachlich relevant. Kontakt ist nur bei Descend/Open Zielkriterium. Ein knapp vor 6 mm abgeschlossener Lift ist nicht automatisch Ursache eines fehlgeschlagenen Gesamtversuchs.','',
            '## Endzustände fehlgeschlagener Gesamtversuche','']
    for key,count in failures.items():lines.append(f'- {key}: {count}')
    lines+=['','Endzustände lokalisieren den Abbruch; sie beweisen keine Ursache. Vollständige Messungen stehen in `full_rollouts.json` und `isolated_phases.json`.','',
            '## Nicht erfüllte Expertenkontrollen','']
    for r in teachers:
        if not r['success']:
            lines.append(f"- Seed {r['seed']}, Platzierung {r['placement']}, Phase {r['phase']}: Kontakt={r['final']['pair_contact']}, seitlicher Fehler={1000*r['final']['xy_error']:.2f} mm, Höhe={1000*r['final']['height_above_target']:.2f} mm.")
    lines+=['','Ein fehlender Kontakt unmittelbar vor Open kann durch Absetzen beim Öffnen korrekt entstehen. Das vorab festgelegte Descend-Kriterium ist dann strenger als die Experten-Phasengrenze. Diese Fälle werden ausgewiesen und ausgeschlossen; die Kriterien werden nach Sichtung nicht geändert. Auch ein fehlender geeigneter Open-Eingang kann auf diese Definition zurückgehen, statt auf einen Fehler der Bewegung.','',
            '## Daten und Grenzen','',
            'Die Phasen-/Aktionslabels wurden aus dem Expertencontroller rekonstruiert und exakt mit den archivierten Phasen-/Eingabe-/Abschlusslabels verglichen. Ganze Demonstrationen bleiben in ihrem bisherigen Train-/Validierungssplit. Open deckt im Trainingsdatensatz lediglich 15–18 Frames ab; ein vollständiger Rückzug und 50 stabile Halteframes fehlen. Die bestehende Clock-Korrektur bleibt identisch aktiv.','',
            'Fünf isolierte Startkontexte je Platzierung werden für alle drei Modelle wiederverwendet. Die 15 Modell-Kontext-Versuche je Tabellenzeile sind deshalb keine 15 unabhängigen Szenen. Aus diesen Daten folgt keine nachgewiesene Curriculum-Verbesserung. Optimizer-Updates: 0.']
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
