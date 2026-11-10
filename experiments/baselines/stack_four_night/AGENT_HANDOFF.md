# Laufender Nachtlauf

- Start: 30.09.2026, 22:36 Europe/Berlin.
- Detached venv-Launcher PID: 22844; eigentliche Pipeline PID: 5360.
- Startprozess PID 28248 ist beendet; die Pipeline laeuft eigenstaendig weiter.
- Aktueller erster Schritt: erfolgreiche Demonstrationen fuer StackFour sammeln.
- Danach automatisch: BC-RNN und BC-Transformer, je 1000 Epochen, nominale
  Evaluation, Robustheits-Suite und Videos mit vier Ansichten / zwei Sekunden Nachlauf.
- Status und Arbeits-PIDs: `status.json`.
- Collection-Log: `logs/collection.log`.
- Trainingsgesamtlog: `logs/training_pipeline.log`.
- Taskdaten, Checkpoints und Ergebnisse: `experiments/baselines/additional_tasks/stack_four/`.
- Windows-Sleep-Verhinderung ist waehrend der Arbeit aktiv; Display darf ausgehen.
- CubeHandover ist nicht geplant, weil ein geeigneter Demonstrator fehlt.

Fortschritt im Projektordner:

```powershell
Get-Content .\experiments\baselines\stack_four_night\status.json
Get-Content .\experiments\baselines\stack_four_night\logs\collection.log -Tail 20
```

Nicht nochmals starten. Sammlung, Training und Auswertung sind ein einziger
unbeaufsichtigter Ablauf; bei Fehlern werden Status und Traceback gespeichert.
