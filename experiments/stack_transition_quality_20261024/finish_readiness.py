"""Publish the final review bundle, without creating launch authorization."""
from pathlib import Path
from collections import Counter
import json, datetime
from transition_pilot import sha, dump, ARRAYS

P=Path(__file__).resolve().parent
plan=json.loads((P/'READY_PLAN.json').read_text())
native=json.loads((P/'native_data_v1/manifest.json').read_text())
ready=json.loads((P/'DATA_READINESS.json').read_text())
smoke=json.loads((P/'NATIVE_TECHNICAL_SMOKE.json').read_text())
assert ready['data_ready'] and smoke['technical_only'] and set(smoke['updates'].values())=={3}
bundle=plan['ready_bundle']
bundle['code_hashes']={path:sha(path) for path in bundle['code_hashes']}
inputs=[Path(ARRAYS),Path(plan['original']['path']),Path(plan['replay_manifest']['path'])]
replay=json.loads(Path(plan['replay_manifest']['path']).read_text())
inputs.extend(Path(r['path']) for r in replay['rows'] if r['count']==3 and r['split']=='train' and r['success'])
inputs.extend(Path(parent['path']) for parent in plan['parents'])
bundle['input_hashes']={str(path.resolve()):sha(path) for path in inputs}
bundle['supersedes']='READY_PLAN.json; pins cached original arrays and every replay episode as well'
dump(P/'READY_PLAN_v2.json',plan)
start=json.loads((P/'START_READINESS.json').read_text())
start.update(ready_plan=str(P/'READY_PLAN_v2.json'),ready_plan_sha256=sha(P/'READY_PLAN_v2.json'),
             native_technical_smoke=str(P/'NATIVE_TECHNICAL_SMOKE.json'),
             technical_only_updates_per_model=3,production_training_started=False)
dump(P/'START_READINESS.json',start)

rows=['# Datensatzbericht: Übergänge zum nächsten Griff', '',
      'Stand 24.10.2026. Neue Simulationen und technische Kurztests sind abgeschlossen; der produktive Trainingslauf wurde nicht gestartet.', '',
      '200 vorab zugewiesene Episoden: je 100 Drei-/Viererrollouts, pro Höhe 60 Training und 40 Validierung. Die Reduktion von ursprünglich 400 auf 200 ist in cohort_revision_v2.json dokumentiert; die Akzeptanzgates wurden nicht gelockert. Drei eingefrorene Teacher werden zyklisch zugewiesen. Fehlgeschlagene Vollrollouts bleiben im Inventar.', '',
      '| Quelle | Vollerfolge / Versuche |', '|---|---:|']
for n in (3,4):
    for teacher in (1,2,3):
        cohort=[r for r in native['rows'] if r['count']==n and r['teacher'].endswith(f'C_seed{teacher}.pth')]
        rows.append(f'| {n} Würfel, Teacher {teacher} | {sum(r["complete_success"] for r in cohort)}/{len(cohort)} |')
rows.extend(['', 'Dies sind Sammelergebnisse, keine unabhängigen Endtests und kein Ergebnis des neuen Trainings.', '',
    '| Split | Abschnitte | Familien | Präfix 2 / 3 |', '|---|---:|---:|---:|'])
for split in ('train','valid'):
    s=ready['summary'][split]
    rows.append(f'| {split} | {s["sections"]} | {s["families"]} | {s["prefix_counts"]["2"]} / {s["prefix_counts"]["3"]} |')
rows.extend(['', 'Pre-action-Eingänge und Teacheraktionen sind zeitlich zugeordnet. Akzeptiert wird nur bestätigtes natives Greifen und Anheben bei durchgehend erhaltenem unteren Turm einschließlich 50 Nachlaufframes. Nachlauf ist Bewertungsinformation und kein zusätzlicher Actiontarget. Training und Validierung teilen keine Startfamilien. Alle Quell- und Teacherhashes wurden geprüft.', '',
    f'Qualität im Training: Mittel {ready["score_mean"]:.4f}, Standardabweichung {ready["score_std"]:.4f}; effektive Abschnittszahl nach Gewichtung {ready["section_weight_ess"]:.2f} von 49. Der Erhaltterm ist nach strenger Annahme konstant; nur Ruhe und Zentrierung variieren. Daher ist der Gewichtungskontrast klein.', '',
    '## Vorbereitete Evaluationszustände', '', '| Panel | Präfix | vorbereitet / 20 |', '|---|---:|---:|'])
for panel in ('development','confirmation'):
    for prefix in (2,3):
        subset=[r for r in native['prepared_starts'] if r['panel']==panel and r['prefix']==prefix]
        rows.append(f'| {panel} | {prefix} | {sum(r["prepared"] for r in subset)}/20 |')
rows.extend(['', 'Fehlgeschlagene Vorbereitung bleibt im gemeinsamen Nenner; zusätzlich muss die bedingte Leistung auf vorbereiteten Zuständen berichtet werden. Die Bestätigungsabdeckung bei Präfix 3 beträgt nur 10/20 und begrenzt die Gesamtquote auf 50 %. Das ist kein 90-%-Benchmark. Die reservierte Schlussvorbereitung wird erst nach dem gemeinsamen Modellfreeze ausgeführt.', '',
    'Frische Umgebungen reproduzierten in geprüften Drei- und Viererbeispielen erste Aktion, Folgezustand und Folgebeobachtung exakt (maximale gemessene Abweichung 0). Das umfasst Simulations-, Controller- und Sequencerzustand.', '',
    '## Kosten und Grenzen', '',
    f'Der letzte Sammelaufruf meldet {native["elapsed_seconds"]:.1f} Sekunden. Er enthält nicht die gesamte frühere Probe und Entwicklungsarbeit. Ein vollständiger End-to-End-Timer wurde im laufenden Prozess noch nicht gespeichert; deshalb wird dieser Wert nicht als Gesamtkosten ausgegeben. Alle 200 Episoden wurden beendet. Diese Vorbereitung wird separat von der erst nach Go beginnenden Achtstundengrenze berichtet.', '',
    'Nur acht Trainingsabschnitte betreffen Präfix 3. Teacherbias, strenge Erfolgsselektion und fehlende explizite Turmgeometrie im Actor bleiben wissenschaftliche Grenzen. Kein Datensatzgate beweist eine spätere Erfolgssteigerung.', '',
    'Öffentliche MimicGen-Daten wurden tatsächlich heruntergeladen und geprüft, wegen anderer Geometrie, Rotationsaktionen und fehlender kompatibler Phasenlabels aber nicht beigemischt. Siehe PUBLIC_DATASET_REVIEW.md.'])
(P/'DATASET_REPORT.md').write_text('\n'.join(rows),encoding='utf-8')

report='''# Startprüfung abgeschlossen – Freigabe ausstehend

Alle vorab definierten Daten- und Signalprüfungen sind bestanden. Verbindlicher Plan ist READY_PLAN_v2.json; START_READINESS.json bindet dessen Hash. Es existiert keine Startfreigabe und kein produktiver Trainingsprozess.

- 200 neue Episoden; 49 Trainings- und 32 Validierungsabschnitte, getrennte Familien und drei Teacher.
- 49 technische Tests bestanden. Zusätzlich wurden auf dem echten eingefrorenen Datensatz alle sechs Modelle mit je drei GPU-Updates geprüft. Diese technischen Modelle werden verworfen; der Langlauf startet aus den ursprünglichen Parents.
- Fehlerhafte Greifer-Dictionary-Kontaktabfrage korrigiert; native Grasp-/Kontaktlabels, vollständiger Zustandsreplay, Onlineauswertung, gemeinsame Checkpointauswahl und persistierte Teilresultate implementiert.
- Datensatz, Originalarrays, Replayepisoden, Parents, Benchmarks und tatsächlich importierter Simulatorcode sind per Hash gebunden. Änderung verhindert den Start.
- Ein Supervisor, Prozesssperre, feste Deadline, Teilresultate bei Timeout und Wachhaltefreigabe sind vorbereitet. Keine automatische Wiederholung reservierter Tests.

## Konkreter freizugebender Lauf

Sechs Modelle: B0 und B aus denselben drei Parents, je maximal 10.000 Updates. Batch 64, Lernrate 3e-5; 50 % Original, 25 % bisheriger Replay, 25 % neue sichere Übergänge. B0 nutzt Einheitsgewichte, B ausschließlich Qualitätsgewichte auf dem neuen Viertel. Dieselben Samples und Controller in beiden Armen; keine neuen Skriptexpertenaktionen, kein RL, keine zusätzliche Sicherheitssteuerung. Die vorhandenen sieben Phasen und der vorhandene Sequencer bleiben identisch.

Maximal acht Stunden ab ausdrücklichem Go: spätestens nach fünf Stunden Optimierung/Entwicklung beenden, drei Stunden für Bestätigung, reservierte Tests und Bericht vorsehen. Wenn Tests das Budget überschreiten, ehrlich Teilresultate ausweisen; Deadline nicht verlängern. Agentkontrolle einmal pro Stunde, nur wesentliche Änderungen melden. Der technische Supervisor kontrolliert unabhängig die Prozessdeadline.

Auswahl auf Entwicklung bei 0/3000/10000 Updates, einschließlich unverändertem Parent als Nullupdate-Kandidat. Alle sechs Modelle vor Bestätigung und reservierten Endtests gemeinsam einfrieren. Primär Turmerhalt während nächster Aufnahme; vollständige Zwei-/Drei-/Vierertürme separat. Vorbereitete Türme sind keine vollständigen Stapelerfolge. Kein Fünfertraining und kein versprochenes 90-%-Ergebnis.

## Unvermeidbare Unsicherheit

Die Qualitätsgewichtung ist nur moderat verschieden; nur acht Trainingsabschnitte enthalten bereits drei gestapelte Würfel. Ein Nullergebnis ist plausibel. Die kleinen und teilweise nicht vorbereitbaren Entwicklungspanels liefern begrenzte Aussagekraft; ihre Coverage und bedingte Leistung müssen separat berichtet werden. Dieser Pilot prüft zunächst Gewichtung, nicht die zusätzliche Architektur mit expliziten Turmfeatures.

Webdaten sind gefunden, aber nicht direkt kompatibel. Eine Retargeting-Pipeline wäre ein eigener Versuch. Details: PUBLIC_DATASET_REVIEW.md. Messzahlen und Datensatzgrenzen: DATASET_REPORT.md.
'''
(P/'EXECUTION_READINESS.md').write_text(report,encoding='utf-8')

path=P/'TRAINING_RUN_PLAN.md';text=path.read_text(encoding='utf-8')
text=text.replace('400 feste Vollrollouts:200 mit drei und200 mit vier Würfeln. Pro Höhe erste160 Training, letzte40 Validierung;', '200 feste Vollrollouts:100 mit drei und100 mit vier Würfeln. Pro Höhe Indizes0–59 Training und160–199 Validierung (Laufzeitrevision v2);')
text=text.replace('Der aktuelle Collector speichert noch nicht Sequencer.pair und sämtliche internen Roboter-/OSC-Controllerzustände; seine bestandene physische Zustandsrekonstruktion allein erfüllt diese Replayabnahme daher noch nicht.', 'Vollständige Controller- und Sequencerzustände sind nun gespeichert; der Replay in frischer Umgebung wurde für Drei- und Viererzustände mit exakt identischer erster Aktion und Folgezustand bestätigt.')
text=text.replace('Vorgeschlagene Obergrenze acht Stunden inklusive Sammlung und Auswertung: bis2h für Datenerfassung/Prüfung, bis4h für gepaarte Optimierung und Entwicklung, mindestens2h für Endtests/Bericht.', 'Obergrenze acht Stunden AB GO: bis5h für gepaarte Optimierung und Entwicklung, mindestens3h für Endtests/Bericht. Die abgeschlossene Datenerfassung/Prüfung wird separat bilanziert.')
text=text.replace('Der Langlauf bleibt technisch blockiert, bis ein vollständiger nativer, eingefrorener Datensatz die Gates besteht und unabhängige Onlineevaluation samt Checkpointauswahl und vorbereitetem Replay implementiert/validiert ist.', 'Datensatzgates, Onlineevaluation, Checkpointauswahl und vollständiger vorbereiteter Replay sind inzwischen bestanden beziehungsweise implementiert und geprüft. Der Langlauf wartet ausschließlich auf das ausdrückliche Go für READY_PLAN_v2.json.')
path.write_text('> **Aktueller Stand:** [Abgeschlossene Startprüfung](EXECUTION_READINESS.md), [Datensatzbericht](DATASET_REPORT.md), verbindlicher READY_PLAN_v2.json. Ältere Zwischenstände sind überholt.\n\n'+text,encoding='utf-8')
for name in ('README.md','IMPLEMENTATION_VALIDATION.md','AUDIT_SIGNOFF.md'):
    path=P/name
    if path.exists():
        text=path.read_text(encoding='utf-8')
        text=text.replace('**Dokumentierter Versuchsplan, noch nicht implementiertes oder gestartetes Training.**','**Implementierter und technisch geprüfter Versuchsplan; produktives Training noch nicht gestartet.**')
        path.write_text('> **Abschluss der Vorbereitung:** Alle Startgates bestanden; aktuelle Abnahme in [EXECUTION_READINESS.md](EXECUTION_READINESS.md), Daten in [DATASET_REPORT.md](DATASET_REPORT.md). Frühere offene Punkte unten sind historische Zwischenstände. Freigabe zum Langlauf steht aus.\n\n'+text,encoding='utf-8')
manifest=json.loads((P/'documentation_manifest.json').read_text())
manifest['status']='READY_AWAITING_EXPLICIT_USER_GO'
for name in ('README.md','TRAINING_RUN_PLAN.md','EXECUTION_READINESS.md','DATASET_REPORT.md','PUBLIC_DATASET_REVIEW.md','READY_PLAN_v2.json','START_READINESS.json'):
    path=P/name;manifest['artifacts'][name]=dict(bytes=path.stat().st_size,sha256=sha(path))
dump(P/'documentation_manifest.json',manifest)
print(json.dumps(dict(status=plan['status'],plan=str(P/'READY_PLAN_v2.json'),approval_created=False)))
