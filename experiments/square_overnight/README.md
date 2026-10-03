# Nachtlauf: Square BC-RNN und BC-Transformer

Neue Trainingslaeufe fuehren am finalen Checkpoint zusaetzlich automatisch
die Robustheits-Suite aus (12 Bedingungen, je 20 Episoden, gepaarte
Anfangszustaende). Siehe `experiments/ROBUSTNESS.md`.
Die Ergebnisse bereits abgeschlossener Laeufe bleiben erhalten.

Video-Erweiterung: Der bereits abgeschlossene Lauf bleibt unveraendert.
Die Pipeline zeichnet bei kuenftigen Laeufen jetzt **50 Rollouts je Zwischenstand**
mit Seeds 6000-6049 als synchronisierte 2x2-Collage auf (768 x 768).
Die vier Ansichten sind agentview, vorne, rechts und diagonal oben mit dem
vollstaendigen Roboter. Die Angaben von 20 Rollouts weiter unten beschreiben
den urspruenglichen Lauf. Zusaetzliche Videos der fertigen Modelle und ein
Aufnahmeskript liegen unter `experiments/square_multiview/`.

Setup ist vorbereitet, aber noch nicht gestartet. Status: `status.json`.

Die vorhandenen Modelle werden von Epoche 50 auf **insgesamt 300 Epochen**
fortgesetzt. Die vollstaendigen `last.pth`-Checkpoints enthalten Modell- und
Adam-Zustand; die Pipeline nutzt robomimics native Resume-Funktion. Die alten
Experimente unter `experiments/square` bleiben erhalten.

Alle anderen Parameter bleiben wie zuvor: Seed 1, offizieller 180/20-Split,
agentview RGB 64 x 64, Propriozeption, MSE-Loss, Batch 16 und 100 Updates pro
Epoche. BC-RNN und Transformer laufen sequentiell auf der RTX 5070.
Source-Checkpoints und deren SHA-256 stehen in `manifest.json`.

## Ablauf

Pro Modell: Training bis Epoche 100, 20 Evaluation-Rollouts, dann Training bis
150 und Evaluation, entsprechend bis 300. Jeder Zwischenstand erhaelt eigene
Metriken und 20 Videos. Evaluation verwendet immer dieselben Seeds 6000–6019
und maximal 400 Schritte. Die gemessenen Ergebnisse von Epoche 50 werden als
Referenz uebernommen; deren Videos bleiben im urspruenglichen Experimentordner.

Configs: `<algorithm>/config.json` (Ziel 300) und
`<algorithm>/config_epoch_<epoch>.json` (gespeicherte Blockkonfigurationen).
Es wird nach 300 Epochen beendet, auch wenn noch Nachtzeit verbleibt.

Die Segmentierung erhaelt Optimizer und Epochenzaehler. robomimic setzt beim
Resume die Zufallszahlengeneratoren erneut auf Seed 1; daher entspricht der
Lauf nicht bitgenau einem ununterbrochenen 300-Epochen-Lauf. Dieselbe
Blockstruktur wird fuer beide Methoden verwendet. Wiederholte Evaluation
dient der Entwicklungsdiagnose; fuer belastbare Schlussfolgerungen sind
spaeter mehrere Trainingsseeds und separate Testepisoden erforderlich.

## Start (PowerShell im Projektordner)

```powershell
& .\experiments\square_overnight\scripts\start.ps1
```

Dies startet einen detached Windows-Prozess, der ohne aktive Agent-Session
weiterlaeuft. `launch.json` verhindert Doppelstarts. Fuer Windows wird das
bereits getestete GLFW-Offscreen-Rendering verwendet. Der Rechner muss
eingeschaltet und wach bleiben; Sleep oder Neustart unterbrechen das Training.

## Fortschritt und Ergebnisse

```powershell
Get-Content .\experiments\square_overnight\status.json
Get-Content .\experiments\square_overnight\logs\bc_rnn_to_epoch_100_training.log -Tail 30 -Wait
```

- Checkpoints: `<algorithm>/runs/<algorithm>/continued_from_epoch50/models/`.
- Resume-Checkpoint: derselbe Runordner, `last.pth` und `last_bak.pth`.
- Nach Abschluss: `<algorithm>/final.pth` und `<algorithm>/best_validation.pth`.
- Loss/TensorBoard: derselbe Runordner, `logs/`.
- Pipeline und Blocklogs: `logs/`.
- Evaluation: `evaluation/<algorithm>/epoch_<epoch>/evaluation_results.json`.
- Videos: `videos/<algorithm>/epoch_<epoch>/rollout_00.mp4` bis `rollout_19.mp4`.
- Fortschreitende Tabelle: `RESULTS.md`, `learning_curve.json`, `learning_curve.csv`.
- Fehler: `status.json` mit FAILED und Traceback sowie die zugehoerige Logdatei.

Die technischen Kurztests unter `smoke/` sind keine Forschungsresultate.
Bei einem Abbruch nicht erneut konfigurieren: die fortgeschrittenen
Resume-Checkpoints muessen erhalten bleiben. Ein neuer Pipeline-Start nach
einem Fehler benoetigt eine gezielte Wiederaufnahme ab dem letzten Block.
