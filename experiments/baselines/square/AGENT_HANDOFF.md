# Uebergabe: laufendes Square-Experiment

Start: 30.09.2026, 20:20 Uhr Europe/Berlin.

- Unabhaengiger Windows-Prozess: PID **23388** (venv-Python-Launcher).
- Tatsaechlicher Pipeline-Python-Prozess: PID **23616**, siehe `status.json`.
- Start-Launcher PID 11792 ist bereits beendet; Pipeline und Training laufen weiter.
- Detached-Mechanismus: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
  CREATE_BREAKAWAY_FROM_JOB`, ausserhalb des Jobs der Start-Shell.
- Aufgabe: Square / `NutAssemblySquare`, Panda, Kamera und Propriozeption.
- Reihenfolge: **BC -> BC-RNN -> BC-Transformer**, eine GPU, sequentiell.
- Geplant je Modell: 50 Epochen x 100 Batches, danach 20 Rollouts und 20 MP4-Videos.
- Gepruefter echter Trainingsfortschritt: BC Epoche 26, 2600 Trainingsbatches,
  mittlerer Training-MSE **0.0440613973**; Validation-MSE **0.0745595848**.
  Dies sind Zwischenwerte, keine finalen Evaluationsergebnisse.
- Alle drei Kurztests bestanden: Trainingsbatches, Validation, Checkpoint laden,
  Policy-Rollout, Offscreen-Rendering und lesbare MP4-Dateien.
- Keine CUDA-OOM- oder MuJoCo-Fehler beim geprueften Start.

## Pfade

Basis: `C:\Users\artur\Desktop\Programmieren\IT\Imitation Learning\experiments\baselines\square`

- Configs: `<algorithm>\config.json`.
- Modelle: `<algorithm>\runs\<algorithm>\<timestamp>\models\`,
  spaeter `<algorithm>\final.pth` und `<algorithm>\best_validation.pth`.
- Trainingslogs: `logs\bc_training.log`, `logs\bc_rnn_training.log`,
  `logs\bc_transformer_training.log`.
- Evaluationslogs: `logs\<algorithm>_evaluation.log`.
- Pipeline-Logs: `logs\pipeline.log`, `logs\pipeline.stderr.log`.
- Videos: `videos\<algorithm>\rollout_00.mp4` bis `rollout_19.mp4`.
- Einzelmetriken: `evaluation\<algorithm>\evaluation_results.json`.
- Status: `status.json`; Startinformationen: `launch.json`.
- Abschluss: `evaluation_results.json`, `evaluation_results.csv`, `RESULTS.md`.
- Protokoll, Hyperparameter und Einschraenkungen: `README.md`.

## Fortschritt pruefen (PowerShell)

```powershell
Get-Process -Id 23388,23616 -ErrorAction SilentlyContinue
Get-Content -LiteralPath 'C:\Users\artur\Desktop\Programmieren\IT\Imitation Learning\experiments\baselines\square\status.json'
Get-Content -LiteralPath 'C:\Users\artur\Desktop\Programmieren\IT\Imitation Learning\experiments\baselines\square\logs\bc_training.log' -Tail 35 -Wait
```

Das Log-Follow mit Ctrl+C zu beenden stoppt nur die Anzeige.
Windows verwendet hier keine tmux-Sitzung; ein Reattach-Befehl ist deshalb nicht
anwendbar. Status und Dateilogs ersetzen die tmux-Konsole. Fuer die weiteren
Modelle entsprechend `bc_rnn_training.log` oder `bc_transformer_training.log` lesen.

Die Pipeline laeuft nach dem Ende dieser Agent-Session weiter. Nicht erneut starten,
solange die genannten Prozesse laufen. Bei Fehlern enthalten `status.json` und die
modellbezogenen Logs den Fehler; es werden keine Ergebnisse erfunden.
