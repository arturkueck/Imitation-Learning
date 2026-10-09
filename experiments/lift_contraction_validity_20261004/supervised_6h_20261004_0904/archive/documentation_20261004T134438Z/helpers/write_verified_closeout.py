import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

session = Path(__file__).resolve().parent
project = session.parents[2]
closure_path = session / 'automation_closeout.json'
closure = json.loads(closure_path.read_text(encoding='utf-8'))
audit_path = session / closure['shutdown_verification']
audit = json.loads(audit_path.read_text(encoding='utf-8'))
assert closure['persisted_status'] == 'PAUSED'
assert audit['state'] == 'FINAL_SESSION_PROVENANCE_AND_SHUTDOWN_VERIFIED'
assert audit['awake_release_verified'] and not audit['coordinator_alive'] and not audit['launcher_alive']
assert audit['all_diagnostic_workers_and_supervisors_exited'] and not audit['pilot_workers']
# Fixed closeout date 2026-10-04: Europe/Berlin is UTC+02:00.
now = datetime.now(timezone(timedelta(hours=2))).isoformat()
closure['documentation_verified_berlin'] = now
closure['shutdown_verification_sha256'] = hashlib.sha256(audit_path.read_bytes()).hexdigest()

report = session / 'SESSION_RESEARCH_REPORT.md'
with report.open('a', encoding='utf-8') as f:
    f.write('\n\n### Überwachung nach Abschluss pausiert\n\n'
            f'App-Rückmeldung und gespeicherter PAUSED-Status nach dem finalen Prozess-/Provenienzaudit geprüft; andere Automationsfelder unverändert. Dokumentiert {now}. '
            '[Automationsabschluss](automation_closeout.json). Keine laufenden Sessionworker, Supervisoren, Coordinator oder Launcher; Wachhalteanforderung freigegeben. '
            'Der Abschluss bestätigt den technischen Ablauf, keine robuste neue BC-Verbesserung. Kein weiterer Lauf gestartet.\n')
closure['final_report_sha256'] = hashlib.sha256(report.read_bytes()).hexdigest()
closure_path.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

notice = ('## Verifizierter Abschluss der Sechs-Stunden-Session\n\n'
          f'Stand {now}: Die unveränderte Deadline 04.10.2026, 15:11:19.697 Berlin ist abgelaufen. '
          'Finales Audit bestanden: alle Sessionworker/-Supervisoren sowie Coordinator und Launcher beendet, Wachhalteanforderung freigegeben; Automation anschließend über die App auf PAUSED gesetzt und gespeichert bestätigt. '
          'Pilot: exakt 2.000 Updates pro Arm, 104 vollständige Evaluationsepisoden; Hashes und Paarungen erneut verifiziert. '
          'Die neue Kontraktionsloss-Referenz ist implementiert und numerisch/auf eingefrorenen Parametern geprüft; sie wurde nicht als neue Policy trainiert. '
          'Keine robuste neue BC-Verbesserung oder schnellere Lernkonvergenz nachgewiesen. '
          'Nächste Empfehlung: lokal identifizierte Zustandsantwort A gegen eingefrorenes A bei gleicher lokaler Aktionsantwort B auf neuen Demos prüfen; Protokoll und Grenzen vorher fixieren. Dieser Anschlussversuch läuft nicht.\n\n')

pilot = session / 'PILOT_INTERPRETATION.md'
text = pilot.read_text(encoding='utf-8')
headline, rest = text.split('\n', 1)
pilot.write_text(headline + '\n\n' + notice + '[Gesamtsynthese](SESSION_RESEARCH_REPORT.md), [Endaudit](final_verification_1791119630.json), [Automationsabschluss](automation_closeout.json). Die folgenden aktiven Anweisungen beschreiben den historischen Sessionverlauf.\n' + rest, encoding='utf-8')

plan = project / 'FORSCHUNGSPLAN.md'
text = plan.read_text(encoding='utf-8')
headline, rest = text.split('\n', 1)
linkbase = 'experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/'
plan.write_text(headline + '\n\n' + notice + '[Gesamtsynthese](' + linkbase + 'SESSION_RESEARCH_REPORT.md), [Lossreferenz](' + linkbase + 'method_reference_001/loss_reference.py), [Abschluss](' + linkbase + 'automation_closeout.json).\n' + rest, encoding='utf-8')

status = session.parent / 'RESEARCH_STATUS.md'
with status.open('a', encoding='utf-8') as f:
    f.write('\n\n' + notice + '[Gesamtsynthese](supervised_6h_20261004_0904/SESSION_RESEARCH_REPORT.md), [verifizierter Abschluss](supervised_6h_20261004_0904/automation_closeout.json).\n')
print(json.dumps({'state': closure['state'], 'berlin': now, 'report_sha256': closure['final_report_sha256'], 'plan': str(plan)}, ensure_ascii=False))
