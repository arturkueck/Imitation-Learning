# Sechs Stunden beaufsichtigte BC-Forschung

Neue Nutzeranweisung am 04.10.2026: Überwachung alle 30 Minuten, Fehler beheben und nach Fehlstart erneut starten; Nutzer kommt in sechs Stunden zurück. Diese Anweisung ersetzt die bisherigen No-Retry-Regeln für technische Fehler dieses Methodenversuchs. Der alte Diffusionslauf und sämtliche historischen Versuche bleiben erhalten.

## Vergleich und wissenschaftliche Grenzen

BC versus konsistente EEF-Sensor-Augmentation, Seed 41004, jeweils genau 2.000 Updates, bestehender Lift-PH-Datensatz mit 180/20 Demos, gleiche 256×256-Policy, Adam, Batch 100 und Normalisierung wie vorher. Sensorradius 5 mm, Mix 0,5, eigene Noise-RNG. Kein neues Policy-Modell als Forschungsbeitrag; kontrollierte Prüfung der Sensorrobustheit. Der Pilot und die vorab festgelegten Evaluationsfälle werden aus dem bisherigen Protokoll übernommen. Kein Verlängern wegen schlechter Ergebnisse und keine Checkpointauswahl anhand von Evaluation. Ein Seed ist keine robuste Verbesserung.

Nominale Lernkurve bei 500/1.000/2.000 Updates; final zusätzlich ±5 mm Sensorbias und separat x-Aktionsimpuls +0,5. Gepaarte Startzustände, Anfangsgewichte und die gesamte Trainingsbatchreihenfolge prüfen. Literatur, frühere Resultate, neue Dynamikdiagnosen und dieser Pilot bleiben getrennte Evidenz.

## Technische Aufsicht

- `session.json` fixiert die Gesamtdeadline sechs Stunden nach Einrichtung. Jeder technische Versuch erhält `attempts/attempt_NNN`; keine Wiederaufnahme oder Überschreibung historischer Checkpoints. Pro Versuch maximal zwei Stunden einschließlich Evaluation, stets begrenzt durch die ursprüngliche Gesamtdeadline.
- Vor dem Trainingsstart vollständiger GPU-/Dataset-/Simulator-/Checkpoint-Integrationstest. Zwei Testmodelle erhalten jeweils einen Prüfupdate und werden anschließend verworfen; diese Vorprüfung zählt nicht als Pilottraining und wird separat protokolliert. Die eigentlichen B0/B1-Modelle starten danach frisch.
- Der lokale Coordinator kontrolliert den Worker alle fünf Sekunden, protokolliert Zustandsänderungen sowie spätestens alle 30 Minuten einen lokalen Check. Er erkennt Fehler unabhängig vom Agent-Trigger, hält die beaufsichtigte Session während des autorisierten Fensters aktiv und beendet ihre Worker an der Deadline. Windows-Job mit Kill-on-close; Safe-Stop vor Timeout; Wachhalteanforderung wird beim Sessionende freigegeben.
- Der App-Heartbeat bleibt sechs Stunden ACTIVE, auch bei Fehlstart und auch nach Trainingsabschluss. Er protokolliert seine tatsächlichen Agent-Checks separat in `agent_checks.jsonl`. Lokale Kontrollen dürfen nicht als Agent-Checks dargestellt werden.
- Nach technischem Fehler konkrete Diagnose/Reparatur, neue Vorprüfung und neuer frischer Versuch. Kein blindes Wiederholen desselben Fehlers, keine parallelen Trainings und keine Verlängerung des Update- oder Zeitbudgets. Schlechte Taskleistung ist kein Startfehler und kein Retrygrund.
- Bis zur Gesamtdeadline nach erfolgreichem Pilot: Artefakte prüfen, Ergebnisse berichten und die nächste fachlich begründete Diagnose zur Zustands-/Aktionsantwort mit bestehenden Checkpoints verfolgen. Kein ungeplanter Trainingssweep und kein Kontraktionstraining ohne bestandene Machbarkeitsgates.

## Befehle für den Agent-Trigger

Arbeitsverzeichnis ist die Projektwurzel. Status lesen:

```powershell
& praxis/.venv/Scripts/python.exe experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/coordinator.py status
```

Nach einer konkret dokumentierten technischen Korrektur am `runner_template.py` oder der Laufzeit einen neuen Versuch anfordern:

```powershell
& praxis/.venv/Scripts/python.exe experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/coordinator.py repair --reason 'Konkreter Fehler und vorgenommene Korrektur'
```

Der Coordinator prüft Deadline, laufende Prozesse, Reparaturidentität und eine neue Vorprüfung. Falls der Coordinator selbst ausgefallen ist, `coordinator.py start` erneut ausführen: Das fixierte Sessionfenster wird nicht neu begonnen, vorhandene Versuche bleiben erhalten und laufende Prozesse werden zuerst geprüft. Den abgelaufenen Coordinator nicht starten.

Am Ende Gesamtstatus, Versuchshistorie, Updates/Losses, Hashes, Evaluation und Forschungsentscheidung in `RESULT.md` sichern. Worker/Coordinator und Wachhaltemodus beenden; erst dann den App-Heartbeat pausieren.
