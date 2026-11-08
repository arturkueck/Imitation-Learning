# Lernen aus bestätigten Abschnitten gescheiterter Versuche

Die anschließende Train-/Valid-Fehlerdiagnose steht in
[diagnosis_004/REPORT.md](diagnosis_004/REPORT.md). Sie liest keine Endtestrollouts
und verändert weder Controller noch Modelle. Reproduktion:
`praxis/.venv/Scripts/python.exe experiments/partial_self_imitation_20261104/diagnose.py --output experiments/partial_self_imitation_20261104/diagnosis_NEW`.

Autorisiert am 04.11.2026 durch „Kannst du diesen Versuch direkt starten?“.
Neuer, begrenzter Fixed-Data-Pilot; kein Online-RL, kein Vision-Training, keine
Hardwarebewegung. Bestehende Datensätze und Checkpoints bleiben unverändert.

## Daten und Vorprüfung

Der korrigierte `native_data_v1`-Datensatz liefert 60 Trainings- und 40
Validierungsversuche für Dreiertürme, darunter 33 erfolgreiche Trainingsversuche.
Er enthält nur drei gescheiterte Trainingsfamilien mit streng bestätigten
Übergangsabschnitten. Die Vorprüfung `smoke_001` stoppte deshalb vor dem Training
am Mindestmengengate. Es wurden keine Qualitätskriterien gelockert.

Der Hauptlauf ergänzt vor dem Training einen festgelegten Pool von 240 neuen
Dreierturmversuchen: 180 Training, 60 Validierung, Seeds 2026100000–2026100239,
zyklisch die drei eingefrorenen C-Teacher. Alle Ausgänge bleiben erhalten.
Gates: mindestens 20 erfolgreiche Trainingsfamilien und fünf gescheiterte
Trainingsfamilien mit bestätigten Abschnitten. Bei Nichterfüllung stoppt der Lauf.

Abschnitte aus Fehlversuchen: erste Paarplatzierung mit zehn gültigen
Freigabeframes und 50 nachfolgenden kontinuierlich gültigen, kontaktfreien
Bestätigungsframes; zusätzlich die bestehende strenge native Prüfung für den
nächsten Pickup. Bestätigungsframes liefern Labels, keine zukünftigen Inputs.
Train/Valid bleiben auf Ebene vollständiger Startfamilien getrennt.

`smoke_002` prüft alle vier Optimizerpfade mit fünf Updates, identische C/D-Samples,
die Wirkung der Gewichtung und vollständige native Rollouts einschließlich
identischer Starts in separat erzeugten Umgebungen. Die technische Prüfung ist
aus wissenschaftlichen Trainings-/Testergebnissen ausgeschlossen. Sechs
gezielte Tests prüfen unter anderem Kontakt-/Zensierungsrejektion und Datenlecks.

## Vergleich

Alle Varianten starten je Replikat beim selben C_seed1/2/3-Parent, mit frischem
AdamW, 5000 Updates, Batch64, LR3e-5, Weight Decay1e-6, Gradient Clip10.
Original-only Completion-BCE benutzt in allen Armen dieselben 48 Beispiele und
denselben Koeffizienten0.1. Architektur, Aktionsraum und Sequencer bleiben gleich.

| Arm | Actor-Daten / Loss-Anteile |
|---|---|
| A | 100% Originalexperten |
| B | 75% Original, 25% erfolgreiche eigene Episoden |
| C | 75% Original, 25% Vereinigung erfolgreicher Episoden und bestätigter Fehlversuchabschnitte |
| D | Exakt C-Samples, normierte Qualitätsgewichtung nur innerhalb des 25%-Eigenanteils |

Eigene Beispiele werden nach Phase, Episode, Abschnitt und Frame gesampelt.
Auswahl, Sampling und Gewichtung bleiben getrennt. Ein gemeinsamer Outcome-Score
bewertet für vollständige und partielle Konstrukte die Bewegung über 50
Bestätigungsframes und XY-Ausrichtung: 0.5 +0.25 clip(1-d/8mm) +0.25 clip(1-xy/9mm).
Das ist ein handdefinierter Score, kein gelernter Critic und keine bestätigte
optimale Gewichtung. B/C vergleichen eine Datenstrategie; die Herkunft eines
Abschnitts ist nicht von Phasenverteilung und Datenumfang isoliert.

## Auswertung und Betrieb

Alle zwölf finalen 5000er-Checkpoints werden vor dem ersten Test eingefroren.
Keine Checkpoint-Auswahl anhand von Tests. 50 neue gepaarte Dreierturmstarts
2026110500–2026110549 je Modell und je unverändertem Parent: insgesamt750 Tests.
Technische Seeds2026110490/2026110491 sind davon getrennt. Identität der Starts
wird über Initialzustand-Hashes geprüft. Tests werden nicht automatisch wiederholt.
Ein festes 3-Stunden-Limit umfasst Sammlung, Training und Auswertung; keine
automatischen Neustarts. Teilresultate werden als solche gespeichert.

```powershell
praxis/.venv/Scripts/python.exe experiments/partial_self_imitation_20261104/supervise.py
praxis/.venv/Scripts/python.exe experiments/partial_self_imitation_20261104/monitor.py
```

`run_001/status.json` zeigt die aktuelle Phase, `run_001/protocol.json` den
festgeschriebenen Ablauf. `runtime/run_001.supervisor.json` überwacht ausschließlich
den eigenen Worker. `run_001/monitor/state.json` hält Logoffset und letzte Prüfung.
Eine `run_001/STOP`-Datei beendet ausschließlich diesen Lauf. Rohdaten und Gewichte
bleiben lokal. Nach erfolgreichem Abschluss stehen `RESULTS.md` und `results.json`
im Laufordner. Diese Dateien sind vor Abschluss keine Leistungsbehauptung.

Der erste abgekoppelte Start innerhalb der Sandbox wurde vor Erzeugung eines
Workers beendet. Ohne vorhandenen Laufordner wurde der Supervisor anschließend
mit externer Ausführungsfreigabe gestartet. Die externe Kontrolle bestätigte
Supervisor89048, Worker-Launcher118392 und Interpreter24664. Da die Sandbox diese
Prozesse nicht direkt auflisten kann, verwendet der Routine-Monitor dort den
frischen, durch `worker.poll()` abgesicherten Supervisor-Heartbeat.

Grenzen: gepoolte Erfahrungen dreier Teacher, privilegierte Zustandsinputs und
feste Bauaufgabe. Keine Aussage zu genauer Selbstkopie, unbekannten Formen,
visuellem Closed Loop oder realem Roboter. Der Vergleich überprüft zunächst nur
den Nutzen der Datenstrategie bei gleichem Updatebudget.
