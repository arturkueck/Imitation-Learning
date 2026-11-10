# Freigegebener Pilot gestartet, 03.11.2026

Nutzer wählte ausdrücklich den getrennten Pilotlauf für Ergebnisse bis Mittag: 1.000 neue Trainingsfamilien, 256 neue Validierungsfamilien, 333 fest ausgewählte ausschließlich historische V3-Trainingsfamilien als Replay (24,98 %). A/B mit drei gepaarten Seeds, maximal zehn Epochen, übrige Modell-/Loss-/Optimierungs-/Kameraprüfparameter unverändert. Keine Endtests zur Auswahl. Die größeren Vorbereitungen bleiben erhalten und laufen nicht parallel.

Feste Deadline **03.11.2026, 12:00:00 Europe/Berlin** in budget.json/session.json, unabhängig von späteren Watcheraufrufen. Start etwa01:48 Berlin. Aktuell zunächst Datenerzeugung; noch keine Behauptung von Optimizer-Updates. Tatsächlicher Stand in status.json, später curves.json/results.json.

Supervisor PID95256, Worker PID45356, genaue Worker-Startzeit in launch.json. Beide Unabhängigkeitsprüfungen query_ok=true/in_job=false. Vier Windows-spawn-Simulatorworker plus Ressourcenverwaltung tatsächlich gestartet; Hostprüfung bestätigte laufenden Worker und passende create_time. Keine reale Robotik, ausschließlich Simulatorreferenz für Kollisionsprüfung.

runtime_entry.py hält den Rechner während des Prozesses wach, setzt ab11:57 STOP_REQUESTED und beendet um12 Uhr die registrierte Prozessfamilie anhand PID+create_time. Kontrollierte Stopps bewahren Teilresultate und Trainingszustand. Keine automatische Wiederholung, kein Folgeexperiment. Laufzeitcode als Kopie in runtime_source, Trainingsimplementierung im versiegelten source-Archiv.

Heartbeat `vision-v4-pilot-bis-12-uhr-pr-fen` ist ACTIVE, Intervall zwei Stunden. Normaler Fortschritt bleibt ohne Chatmeldung. Hostsicht für Prozessprüfungen mit exec_command sandbox_permissions=require_escalated verwenden; Sandbox-PID-Abwesenheit ist kein Absturznachweis. Zuerst `praxis/.venv/Scripts/python.exe experiments/visual_side_v4_20261102/pipeline.py monitor --run pilot_001`, dann bei Fehler gezielt neue Logbytes untersuchen. Keine wissenschaftlichen Änderungen und keine automatischen Neustarts. Nach Abschluss tatsächliche Artefakte in FOLLOWUP_REVIEW.md bewerten und Automation pausieren.

Loss-Plots und cyan/orange/grüne 3D-Vergleiche werden während des Trainings automatisch geschrieben. Website-Text anschließend aus echten Resultaten vorbereiten; keine automatische Veröffentlichung angeordnet. Ein fertiges Modell oder Qualitätsverbesserung wird vor der Auswertung nicht zugesichert.
