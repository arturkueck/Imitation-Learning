# Technischer Hintergrundstart · 02.11.2026

Der ursprüngliche direkte Start über Python-Popen und Breakaway meldete für Supervisor und Deadline-Guard `query_ok=true, in_job=true`. Beide verweigerten die Arbeit und sind nachweislich beendet. Es gab noch keine Haupttrainingsdaten oder Optimizer-Updates. Die Dateien dieses Fehlstarts einschließlich Konfiguration sind in launch_attempt_001 erhalten.

Ein reiner WMI-Probeprozess mit Basis-Python und CREATE_BREAKAWAY_FROM_JOB bestätigte danach `in_job=false` (independent_probe_result.json). Win32_ProcessStartup mit CREATE_NO_WINDOW wurde vom WMI-Provider als ungültiger Parameter abgewiesen; ShowWindow=0 plus Breakaway ist akzeptiert. Dies ändert keine Sicherheitsprüfung.

Der einmalige korrigierte Start erfolgt über launch_wmi.ps1/independent_bootstrap.py. Supervisor PID89740 und Worker PID88820 bestätigen beide `in_job=false`. Der Deadline-Guard PID68704 läuft ebenfalls unabhängig. Die Prozessidentitäten werden mit Startzeit registriert, damit wiederverwendete PIDs nicht beendet werden.

Neue eingefrorene Quellkopien: source_retry_001, Hashes in config.json. Ursprüngliche Quellkopien in source bleiben erhalten. Daten, Seeds, Architektur, Loss, Lernrate und gemeinsame Deadline wurden nicht verändert. Go 00:31:20 Berlin; korrigierter Hintergrundstart 00:53:37 Berlin; Ende unverändert 16:31:20 Berlin.

Die gehostete Website zeigt weiterhin einen veröffentlichten Snapshot. Live-Dateistatus ist nur lokal unter http://127.0.0.1:4173/trainings.html?run=vision-active-v3-run1 verfügbar. Es wurde kein Remote-Live-Sync behauptet oder eingerichtet.
