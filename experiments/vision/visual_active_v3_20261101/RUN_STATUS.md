# V3 gestartet · 02.11.2026

Registrierter Hauptlauf: run_001. Aktueller Zustand ausschließlich in run_001/status.json; Optimizer-Updates stehen dort als step und später in curves.json. Beim Start dieses Dokuments lief die Datenerzeugung, noch keine Haupt-Optimizer-Updates. Keine Behauptung eines bereits fertigen verbesserten Modells.

Go 00:31:20 Berlin, unabhängiger korrigierter Hintergrundstart 00:53:37, gemeinsame Deadline **16:31:20 Berlin am 02.11.2026**. Wahrnehmungs-Trainingsende spätestens08:31:20, anschließend Modellvalidierung und Folgeagent innerhalb der globalen Deadline.

Supervisor PID89740, Worker PID88820 und Deadline-Guard PID68704. PID allein ist keine dauerhafte Identität; registrierte Startzeiten in registered_processes.json beachten. Aktuelle Unabhängigkeitsbelege in run_001/independence.json, run_001/worker_independence.json und deadline_guard_independence.json. Supervisor und Worker bestätigten query_ok=true/in_job=false. Fehlstart und einmalige technische Korrektur siehe run_001/LAUNCH_REPAIR.md.

**Monitoring muss Host-Sicht verwenden:** Normale Sandbox-Aufrufe von psutil sehen die unabhängigen PIDs nicht und lieferten einen falschen Fehler. Loopbackzugriff war in derselben Sandbox ebenfalls gesperrt. `monitor_check.py` sowie `completion_gate.py claim` und `deadline_guard.py register` daher gezielt über exec_command mit sandbox_permissions=require_escalated ausführen. Nach Host-Prüfung bestätigte monitor_check.py beide PIDs aktiv, Fortschritt und null neue Fehler. Diese Toolberechtigung ist kein Grund, Schutzprüfungen zu deaktivieren. Kein Neustart allein wegen fehlender eingeschränkter Prozesssicht.

Die zweistündliche Chat-Automation vision-v3-folgeagent-nach-trainingsabschluss ist aktiv. Sie startet bei validiertem Abschluss genau einen Folgeagenten. FOLLOWUP.md enthält den Auftrag; keine Endtests vor Entscheidung über Fortsetzung. Nach kompletter Anschlussphase Checkpoints/Ergebnis erhalten, tatsächlichen Zustand berichten und Automation pausieren.

Live-Frontend: http://127.0.0.1:4173/trainings.html?run=vision-active-v3-run1 (nur lokal). API bestätigte V3 mit status=running und stage=render. Die gehostete Website bleibt ein veröffentlichter Snapshot, keine Live-Verbindung. Ein zusätzlicher Serverstart war wegen eingeschränkter Sandbox-Sockets überflüssig; der vorhandene Server liefert den aktualisierten Registereintrag. Keine fremden Server wurden beendet.

Freigaben: zwei erfolgreiche 1.000-Familien-Datenpiloten (zweiter mit endgültigen Holdouts/Grau-Hell-Erweiterung), numerischer Preflight mit Original-Forward-Gleichheit, Masken-/Präfixprüfung, exaktem Low-Level-Resume und 204 nativen Bewegungsproben. Kompletter Smoke-Lauf mit sechs Modellen, einer Epoche, zwölf Kurvenpunkten, Checkpoints und 360 Geometrie-Artefakteinträgen erfolgreich. 36 unterschiedliche Regressionstests bestanden. Dies sind technische Prüfungen, keine nachgewiesene Endqualität des Hauptlaufs.
