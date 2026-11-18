<!-- current-bc-status:start -->
> Stand 12.11.2026: **Abgeschlossen**. Weitertraining mit gleichen neuen Batches; Ergebnis je Seed uneinheitlich. [Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.
<!-- current-bc-status:end -->

# Nachtlauf: BC von 30.000 auf 60.000 Updates fortsetzen

Ziel: Prüfen, ob die beiden bisher verglichenen BC-Varianten von weiteren
Updates profitieren und ob das Curriculum später aufholt. Dieser Versuch ist
eine vorab geplante Fortsetzung nach Einsicht in die ersten Resultate. Er ist
kein unveränderter ursprünglicher Endtest und kein weiterer X/XY-Stufenversuch.

## Festgelegter Versuch

- Sechs Ausgangsmodelle: `mixed` / `curriculum`, jeweils Seeds 1, 2, 3.
- Modellgewichte **und AdamW-Momente** vom festen letzten Checkpoint bei 30.000
  übernehmen. Die alten Modelle und Ergebnisse werden nicht verändert.
- Je weitere 30.000 Updates, Ziel 60.000 insgesamt; Batch 64, LR 1e-4,
  Weight Decay 1e-6, Clip 10, unveränderte Architektur und Lernregel.
- Gleichmäßig über sieben Phasen und dann deren Trainingsframes ziehen. Die
  beiden Arme bekommen innerhalb jedes Seeds **denselben Batch zur selben Zeit**.
  Der Name `curriculum` bezeichnet hier die Trainingsvorgeschichte; in der
  Fortsetzung werden keine X/XY-Stufen wiederholt.
- Vorhandene Demonstrationen und ursprüngliche 180/20-Trajektoriensplits
  unverändert. Keine neuen Trainingslabels, kein Critic, keine RL-Updates.
- Bei 40k, 50k und 60k: dieselben 20 Entwicklungsstarts wie bisher für zwei und
  drei Würfel. Der feste 60k-Checkpoint wird verwendet; kein Best-of-Dev.
- Anschließend auf **100 neuen gepaarten Starts je Aufgabe** sowohl die sechs
  30k-Eltern als auch die sechs 60k-Modelle prüfen. Namespace
  2026115000–2026115099; frühere Endtests werden nicht erneut zur Bestätigung
  verwendet. Alle zwölf Checkpoints werden vor dem ersten neuen Ergebnis
  eingefroren. Hauptmaß: vollständiger stabiler Dreierturm, 50 gültige Frames.
- Ein gemeinsames Maximum von acht Stunden ab Supervisorstart umfasst Training,
  Entwicklungsauswertung und neue Bestätigung. Bis zu zwei Minuten sind für das
  kontrollierte Beenden vorgesehen. Ein unvollständiger Lauf liefert Teilresultate,
  keine bestätigte Verbesserung. Keine automatischen Neustarts oder Fortsetzungen.

## Ergänzende Diagnose

Bei 30k und an allen folgenden Prüfpunkten werden zusätzlich zum Aktions-MSE
der gewichtete BCE und gesamte Validierungsloss gespeichert. Je Phase 0–5:
TP, FP, FN, Precision, Recall und F1 bei derselben Schwelle 0,8.
Das prüft den Abschlussklassifikator auf vorgegebenen Demonstrationszuständen.
Ein False Positive bedeutet ein Abschluss-Signal auf einem als nicht abgeschlossen
markierten Frame; es beweist keinen tatsächlich zu frühen Wechsel im Online-Rollout.
Phase 6 bleibt wie bisher aus dem trainierten Abschlussloss ausgeschlossen.

Die Simulation verwendet unverändert den vorhandenen Aufgabenkoordinator und
geometrischen Rückzugsschutz. Eine umfassende Video-/Trajektoriendiagnose einzelner
Fehler ist nicht Teil dieses automatisierten Laufs. Es werden keine Lossgewichte
auf Grundlage der Diagnose während des Laufs angepasst.

## Start

`ready_001` ist nach Vorbereitung und technischem Smoke der vorgesehene Lauf.
Die Vorbereitung startet kein langes Training. Aus dem Projektstamm:

```powershell
& '.\experiments\curriculum\axis_bc_extension_20261110\Start-NightRun.ps1'
```

Der Starter prüft zuerst alle eingefrorenen Hashes und startet den Supervisor
versteckt. Windows bleibt während des Supervisorlaufs wach. Eine bereits
vorhandene Startsperre verhindert einen zweiten Lauf im selben Ordner.

Status ohne ML-Imports:

```powershell
& '.\praxis\.venv\Scripts\python.exe' '.\experiments\curriculum\axis_bc_extension_20261110\night.py' status --output '.\experiments\curriculum\axis_bc_extension_20261110\ready_001'
```

Die Prozessprüfung muss im selben Windows-Kontext wie der Hintergrundlauf
erfolgen. Bei fehlendem Prozesszugriff meldet sie einen unbekannten Prozessstatus
statt einen erfundenen Trainingsabbruch. Das Monitoring merkt sich Byteoffset,
Logidentität und letzte Metriken; bei Logrotation wird neu gelesen. Im Normalfall
liest es nur Status und neue Metrikzeilen. Bei mehr als 15 Minuten ohne
Statusänderung wird gewarnt; Evaluationen werden als eigene Phase ausgewiesen.

Eine leere Datei `STOP` in `ready_001` beendet die Arbeit bei der nächsten
Update-Runde beziehungsweise dem nächsten Simulationsframe. Letzte Modellstände
werden erhalten. Ein Betriebssystemstillstand oder Herunterfahren kann nicht
durch diesen kooperativen Supervisor behoben werden.

## Ergebnisse und Reproduzierbarkeit

- `status.json`, `supervisor_status.json`, `metrics.jsonl`: Betrieb und Fortschritt.
- Je Modell `offline_u*.json`: Aktionsfehler, Abschlussdiagnose, Validierungsloss.
- `panel_u*.json`, `dev*_u*.json`: vollständig abgeschlossene Entwicklungspanels.
- `confirmation/`: eingefrorene Eltern und Fortsetzungen, neue Einzelergebnisse.
- `result_summary.json`: Erfolgszahlen und gepaarte Gewinne/Verluste pro Seed.
- `parents.json`, `provenance.json`, `source_snapshot/`, Samplepläne und
  Checkpoints: Eingänge, Quellstand und Zustände. Keine Eltern werden überschrieben.

Erfolgsraten pro Trainingsseed berichten. Die 100 Szenen sind keine 100
unabhängigen Trainingsreplikate. Sinkender Loss allein bestätigt keine verbesserte
Policy. Dieser Lauf trennt mehr Trainingszeit von einer Änderung der Lernregel;
er prüft kein neu entworfenes Curriculum.

Technischer Smoke: echte Elterngewichte und Optimizer von Seed 1, je drei
zusätzliche GPU-Updates auf identischen Batches, Abschlussdiagnose und je 20
Simulationsframes auf zwei und drei Würfeln. Eigener Ordner und technische
Markierung. Automatische Tests prüfen unter anderem den identischen nächsten
CPU-Schritt nach AdamW-Restore, Sampling, Messgrößen, getrennte Namespaces,
Zeitbudget, Paarung und inkrementelles Monitoring.
