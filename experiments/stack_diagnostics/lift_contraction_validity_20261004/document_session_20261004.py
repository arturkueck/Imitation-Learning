"""One-time, reversible documentation maintenance; never launches experiments."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

project = Path(__file__).resolve().parents[3]
session = project / 'experiments/stack_diagnostics/lift_contraction_validity_20261004/supervised_6h_20261004_0904'
utc = datetime.now(timezone.utc)
assert utc.date().isoformat() == '2026-10-04', 'Date-specific Berlin offset must be reviewed.'
berlin = utc.astimezone(timezone(timedelta(hours=2)))
stamp = utc.strftime('%Y%m%dT%H%M%SZ')
archive = session / 'archive' / ('documentation_' + stamp)
assert not archive.exists()
archive.mkdir(parents=True)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

helpers = ['debug_clearance_arrays.py', 'debug_clearance_data.py',
           'debug_clearance_recorded.py', 'write_verified_closeout.py']
mutable = [project / 'README.md', project / 'FORSCHUNGSPLAN.md',
           session.parent / 'RESEARCH_STATUS.md', session / 'PILOT_INTERPRETATION.md']
originals = {p: p.read_bytes() for p in mutable}
baseline = {p: digest(p) for p in session.rglob('*')
            if p.is_file() and session / 'archive' not in p.parents}
(archive / 'snapshot_before.json').write_text(json.dumps(
    {str(p.relative_to(project)): value for p, value in baseline.items()}, indent=2), encoding='utf-8')

# Saved original bytes allow exact rollback of each navigation edit.
history = []
for p, data in originals.items():
    target = archive / 'edit_history' / p.relative_to(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    assert digest(target) == hashlib.sha256(data).hexdigest()
    history.append({'original_path': str(p.relative_to(project)),
                    'archived_original': str(target.relative_to(session)), 'sha256': digest(target)})

# The preceding project-wide rg search found no filename references, including JSONL.
# Protect against a source manifest accidentally pinning any helper by digest/name.
for manifest in project.glob('experiments/**/source_hashes.json'):
    data = manifest.read_text(encoding='utf-8')
    for name in helpers:
        assert name not in data and baseline[session / name] not in data, str(manifest)
moves = []
for name in helpers:
    source = (session / name).resolve()
    target = (archive / 'helpers' / name).resolve()
    assert source.is_relative_to(session.resolve()) and target.is_relative_to(session.resolve())
    assert source.is_file() and not target.exists()
    target.parent.mkdir(exist_ok=True)
    source.rename(target)
    assert digest(target) == baseline[source]
    moves.append({'original_path': str(source.relative_to(project)),
                  'archived_path': str(target.relative_to(project)),
                  'sha256': digest(target), 'bytes': target.stat().st_size,
                  'reason': 'Unreferenced one-time debugging/documentation helper; retain for history.'})

review = session / 'REVIEW_20261004.md'
review.write_text(f'''# Bewertung der sechs Stunden und Entscheidung für die nächste Etappe

Dokumentiert **{berlin.isoformat()}** / **{utc.isoformat()}**. Anlass: Nutzerfragen zur Bilanz, Änderung des Vorgehens und Archivierung. Dies ist eine nachträgliche Bewertung, kein vorab festgelegtes Experimentprotokoll und keine neue Trainingsfreigabe.

## Gesicherter Stand

Session 04.10.2026, 09:11:19–15:11:19 Berlin abgeschlossen; [Prozess-/Provenienzprüfung](final_verification_1791119630.json), [gespeicherte Pause der Automation](automation_closeout.json). Genau ein neuer Trainingsseed im Sensorpilot, beide Arme 2.000 Updates, insgesamt 104 Evaluationsepisoden. Nachfolgende Diagnosen benutzen eingefrorene Checkpoints. [Gesamtsynthese mit Primärliteratur und Rohdatenverweisen](SESSION_RESEARCH_REPORT.md).

- Sensorpilot: nominal 4/10 gegen 3/10, Bias +5 mm 3/10 gegen 4/10, Bias −5 mm 3/10 gegen 4/10, Aktionsimpuls 3/10 gegen 3/10. Keine robuste Überlegenheit, Lernschwelle von beiden nicht erreicht.
- Volle Aktionsantwort einschließlich Rotation: 91,9 % geringerer medianer Ratio-Vorhersagefehler im kleinen Gegenprüfungstest; kein entsprechend großer Taskgewinn. [Befund](mechanism_action7_001/RESULT.md).
- Zustandslokale Aktionsantwort: 56,12 % geringerer medianer Ratiofehler an acht gültigen Ankern; falsche Freigaben 6→1. [Befund](local_response_001/RESULT.md).
- Empirische Fehlerhülle verletzt in 10/48 neuen gültigen Antworten; die Entwicklungsregel scheitert trotz 0 falschen Freigaben mit Marge in diesem Satz. [Negativer Befund](error_margin_001/RESULT.md).
- Neuer voller, gewichteter Kontraktionsloss rechnerisch und per Gradientenprüfung verifiziert; keine neue Policy damit trainiert. [Referenz und Grenzen](method_reference_001/RESULT.md).

Historische ältere Lift-Taskgewinne gehören zu anderen Trainingsläufen. Kein Nachweis schnellerer Lernkonvergenz, stabiler Stacks, allgemeiner Stabilität oder einer Erklärung des Direct-vs-Diffusion-Gaps durch diese Session. Forschungsgewinn ist die Eingrenzung fehlerhafter Dynamikannahmen und ein prüfbarer Methodenentwurf; noch kein nachgewiesener neuer Algorithmusvorteil.

## Änderung des Vorgehens

Die Richtung bleibt Robustheit durch einen begründeten BC-Zusatzloss. Die nächste Etappe wird auf **eine** entscheidende Mechanismusfrage begrenzt: Bei gleichem lokal identifiziertem B, gleicher eingefrorener Policy und neuen Prüfdemos A_frozen gegen A_local vergleichen. A beschreibt die Wirkung der anfänglichen Zustandsabweichung bei gleicher Aktion; B die zusätzliche Aktionswirkung. Die Vermutung, dass A den Restfehler erklärt, ist noch unbestätigt.

Vor einem Anschlussversuch Auswahl, Identifikations-/Prüfzweige, Fehlerentscheidung, benötigte Abdeckung und Kostenbudget fixieren. Vorhandene Fehlerhülle nicht anhand neuer Prüfoutcomes retunen. Bei weiter unzureichender Entscheidungsgüte oder Abdeckung diese Variante zurückstellen; keine unbefristete Kette zusätzlicher Filter. Kontaktphasen ausdrücklich im geplanten Nenner behalten.

Bei tragfähigem Ergebnis folgt erst ein gepaarter Methodenvergleich über mehrere Trainingsseeds: BC, bestehender Zusatzloss und neuer Zusatzloss. Effektive Regularisierungsstärke zusätzlich kontrollieren; gleicher Faktor lambda hat in den Audits nicht dieselbe Gradientennorm erzeugt. Robustheit ist primäres Ziel; Lern- und Recheneffizienz separat messen, einschließlich Simulatoridentifikation/Cachekosten. Kein anhand Evaluation ausgewählter Best-Checkpoint.

Die 27 gespeicherten Diagnose-Supervisorjobs umfassen zusammen 2.452,249 s (rund 40,9 min), einschließlich Vorprüfungen und technischer Fehler. Das ist keine vollständige Bilanz aller sechs Stunden: Analyse, Vorbereitung und nicht vollständig instrumentierte Setuprechnung sind nicht erschöpfend enthalten. [Kosteninventar](research_cost_inventory.json). Die sechs Stunden waren keine sechs Stunden Policytraining.

## Dokumentation und Aufbewahrung

Ältere NEXT_*-Dateien sind erledigte bzw. überholte Sessionaufträge; sie dienen nur der Planungshistorie. Fachlich negative Ergebnisse sind relevante Evidenz und bleiben erhalten. Rohdaten, Protokolle, Quellenpins, Dataset, End-/Lernkurvencheckpoints, Logs und Prüfungen bleiben an ihren ursprünglichen Pfaden. Nur nicht referenzierte Hilfsskripte werden verschoben, mit Datum, Hash und Rückweg im Archivmanifest. Keine Daten gelöscht; kein weiterer Lauf gestartet.
''', encoding='utf-8')

jobs = []
for path in sorted(session.glob('*/supervisor_result.json')):
    result = json.loads(path.read_text(encoding='utf-8'))
    if not (path.parent / 'RESULT.md').exists():
        continue
    finish = datetime.fromtimestamp(result['finished_unix'], timezone.utc).astimezone(timezone(timedelta(hours=2)))
    launch = json.loads((path.parent / 'launch.json').read_text(encoding='utf-8'))
    start = datetime.fromtimestamp(launch['launch_unix'], timezone.utc).astimezone(timezone(timedelta(hours=2)))
    jobs.append(f"| [{path.parent.name}]({path.parent.name}/RESULT.md) | {start.strftime('%H:%M:%S')}–{finish.strftime('%H:%M:%S')} | [Zeitquelle]({path.parent.name}/supervisor_result.json) |")

readme = session / 'README.md'
readme.write_text(f'''# Einstieg: abgeschlossene BC-Forschung vom 4. Oktober 2026

**Aktualisiert {berlin.isoformat()} / {utc.isoformat()}.** Sechs-Stunden-Fenster 09:11:19–15:11:19 Berlin abgeschlossen. Training und Diagnoseprozesse beendet, Wachhalteanforderung freigegeben, Automation PAUSED. Kein Anschlussversuch gestartet. Dieser Index ordnet vorhandene Evidenz; er verändert keine früheren Messungen.

## Aktuell lesen

1. [Gesamtbericht](SESSION_RESEARCH_REPORT.md): Literatur, historische Projektergebnisse, einzelner Sensorpilot, Mechanismustests, Hypothesenledger, Kosten und Grenzen.
2. [Datierte Bewertung und nächstes Vorgehen](REVIEW_20261004.md): eine letzte begrenzte Zustandsantwortdiagnose, Abbruchentscheidung, danach gegebenenfalls replizierter Trainingsvergleich.
3. [Algorithmusreferenz](method_reference_001/RESULT.md): Implementierung geprüft, kein damit erzielter Policygewinn.
4. [Endprüfung](final_verification_1791119630.json) und [Automationsabschluss](automation_closeout.json).
5. [Projektziel und Forschungsplan](../../../FORSCHUNGSPLAN.md).

**Fazit:** Konkrete Mängel der bisherigen Dynamiknäherung identifiziert; voller und lokaler Aktionsansatz verbessert einige Vorhersagen. Die empirische Fehlerhülle überträgt sich nicht zuverlässig. Noch keine robuste neue BC-Verbesserung oder schnellere Lernkonvergenz. Lift-Erfolg ist kein stabiler Stack.

## Datierung der Primärjobs

Alle Zeiten **04.10.2026, Europe/Berlin (UTC+02:00)**. Start aus launch.json, Ende aus supervisor_result.json; dies datiert die Ausführung des Primärjobs, nicht den späteren Bericht oder seine Reparatur. Der technische Rückgabecode allein entscheidet nicht über wissenschaftliche Gültigkeit. Beispielsweise hat mechanism_AB_001 physikalisch ungültige Daten; mechanism_correction_001 ist nach vollständiger Datenerhebung technisch gescheitert und separat analyserepariert. Details jeweils im Bericht. Manche frühen RESULT.md enthalten selbst keine Zeitzeile; die unveränderten Maschinenzeitquellen werden deshalb hier explizit verlinkt.

| Diagnosebericht | Primärjob Berlin | Unveränderte Zeitquelle |
|---|---|---|
{chr(10).join(jobs)}

Der Sensorpilot ist separat in [RESULT.md](RESULT.md) und [run_result.json](attempts/attempt_002/run_result.json) dokumentiert. Seed 41004, 2.000 Updates je Arm, 104 vollständige Episoden einschließlich Lernkurve. Abschlusszeit aus der Run-Zeitquelle; [Agentprüfungen](agent_checks.jsonl) und [lokale Aufsicht](monitor_checks.jsonl) sind getrennt. Zusammenfassungen sind keine weiteren Trainingsreplikate.

## Historie und Aufbewahrung

[PILOT_INTERPRETATION.md](PILOT_INTERPRETATION.md), [früherer Forschungsstatus](../RESEARCH_STATUS.md), [ursprünglicher Anschlussplan](../NEXT_EXPERIMENT.md), alle NEXT_*.md/NEXT_*.json sowie SESSION_CLOSEOUT.md und FINAL_CHECK_COMMANDS.md sind historische Sessionanweisungen, keine aktuellen Startaufträge. Der aktuelle Vorschlag steht ausschließlich in REVIEW_20261004.md/FORSCHUNGSPLAN.md; seine Ausführung ist hier nicht angeordnet.

Alle Diagnoseordner einschließlich gescheiterter Vorprüfungen/Versuche und Analyse-Reparaturen bleiben vollständig erhalten. Historischer Diffusionsabbruch und andere Experimentserien werden nicht bereinigt. Die Session enthält vor dieser Ordnung rund 308 MB (294 MiB); die größten Dateien sind wissenschaftliche Rohdaten, kein entbehrlicher Cache. Archivierung der Hilfsskripte ordnet den Arbeitsbereich und spart keinen Speicher.

[Archiv dieser Dokumentationspflege]({archive.relative_to(session).as_posix()}/README.md): vier nicht referenzierte Hilfsskripte und bytegetreue Originale der ergänzten Navigation. Manifest mit Originalpfad, Archivpfad, SHA256, Zeit und Wiederherstellungshinweisen. Keine Löschung.
''', encoding='utf-8')

rel = session.relative_to(project).as_posix()
current = (f'**Aktueller Einstieg ({berlin.isoformat()}):** Die sechs Stunden sind abgeschlossen; '
           'Automation pausiert. Ältere ACTIVE-Status und NEXT-Aufträge unten gehören zur Chronik. ')
for path in [session / 'PILOT_INTERPRETATION.md', session.parent / 'RESEARCH_STATUS.md']:
    text = path.read_text(encoding='utf-8')
    heading, rest = text.split('\n', 1)
    link = 'README.md' if path.parent == session else session.name + '/README.md'
    path.write_text(heading + '\n\n' + current + f'[Dokumentationsindex]({link}), ' +
                    f'[datierte Bewertung]({"REVIEW_20261004.md" if path.parent == session else session.name + "/REVIEW_20261004.md"}).\n' + rest, encoding='utf-8')
path = project / 'README.md'
# The existing root README uses UTF-16 with BOM; preserve its encoding.
readme_encoding = 'utf-16' if path.read_bytes().startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8'
text = path.read_text(encoding=readme_encoding)
heading, rest = text.split('\n', 1)
path.write_text(heading + '\n\n' + f'BC-Forschung, abgeschlossen am 4. Oktober 2026: [aktueller Ergebnis- und Dokumentationsindex]({rel}/README.md), [datierte Iterationsbewertung]({rel}/REVIEW_20261004.md).\n' + rest, encoding=readme_encoding)
path = project / 'FORSCHUNGSPLAN.md'
with path.open('a', encoding='utf-8') as f:
    f.write(f'\n\n## Datierte Bewertung und Begrenzung der nächsten Etappe\n\nStand {berlin.isoformat()}. [Bewertung der sechs Stunden]({rel}/REVIEW_20261004.md) ergänzt den abgeschlossenen Stand: eine begrenzte A_frozen/A_local-Diagnose bei gleicher B_local-Antwort; vorab festgelegte Abdeckungs-/Fehler-/Kostenentscheidung, bei erneutem Scheitern Variante zurückstellen. Danach gegebenenfalls replizierter Methodenvergleich mit kontrollierter Regularisierungsstärke. Kein Lauf neu gestartet oder automatisch eingeplant. [Aktueller Dokumentationsindex]({rel}/README.md).\n')

moved_map = {session / name: archive / 'helpers' / name for name in helpers}
protected = 0
for path, before in baseline.items():
    if path in mutable or path in [readme, review]:
        continue
    actual = moved_map.get(path, path)
    assert actual.is_file() and digest(actual) == before, str(actual)
    if path not in moved_map:
        protected += 1
closure = json.loads((session / 'automation_closeout.json').read_text(encoding='utf-8'))
assert digest(session / 'SESSION_RESEARCH_REPORT.md') == closure['final_report_sha256']

manifest = {'state': 'REVERSIBLE_DOCUMENTATION_ARCHIVE_VERIFIED', 'utc': utc.isoformat(),
            'berlin': berlin.isoformat(), 'files_deleted': 0, 'training_or_simulator_started': False,
            'moved_helpers': moves, 'navigation_originals': history,
            'historical_session_files_unchanged_in_place': protected,
            'moved_helper_hashes_verified': len(moves),
            'original_final_report_hash_still_valid': True,
            'new_document_hashes': {p.name: digest(p) for p in [readme, review]},
            'restore': 'For each moved_helpers entry, move archived_path back to original_path only if original_path does not exist. All paths are project-relative; verify sha256 first. edit_history stores exact pre-edit bytes for optional navigation rollback.',
            'scope': 'No experimental reports, raw data, checkpoints, configs, source pins or logs removed/rewritten.'}
(archive / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(archive / 'README.md').write_text(f'''# Reversibles Dokumentationsarchiv

Erstellt {berlin.isoformat()} / {utc.isoformat()}. [Manifest](manifest.json).

Vier einmalige, im Projekt nicht über Dateinamen referenzierte Debug-/Abschlusshelfer wurden nach helpers/ verschoben. Ihre SHA256 sind unverändert. Archivierte Helfer sind historische Quellen und sollen nicht von ihrem neuen Ort ausgeführt werden; relative Pfade in ihnen beziehen sich auf den ursprünglichen Ort.

Unter edit_history/ liegen bytegetreue Versionen der vier ergänzten Navigationsdateien. Relative Links darin gehören zu den ursprünglichen Pfaden. Aktuelle Übersicht: [Sessionindex](../../README.md). Alle älteren NEXT-Aufträge bleiben an ihren referenzierten Pfaden, sind im aktuellen Index ausdrücklich historische Aufträge.

Wiederherstellung: Original- und Archivpfad sowie Hash aus dem Manifest verwenden. Zuerst Hash prüfen, danach bei fehlendem Originalpfad zurückverschieben; bestehende Dateien nicht überschreiben. Zum Rücksetzen von Navigation vorhandene aktuelle Version separat sichern und archivierte Originalbytes verwenden.

**Keine Datei gelöscht.** {protected} ursprüngliche Sessiondateien unverändert an ihrem Ort geprüft; vier Helfer bytegetreu verschoben. Gesamtbericht und dessen Abschluss-Hash unverändert. Fachlich negative Ergebnisse, technische Fehlstarts, Checks, Logs, Checkpoints, Protokolle und Quellenpins bleiben erhalten.
''', encoding='utf-8')
print(json.dumps({'state': manifest['state'], 'berlin': berlin.isoformat(), 'archived_helpers': len(moves),
                  'protected_files_verified': protected, 'deleted': 0, 'archive': str(archive)}, ensure_ascii=False))
