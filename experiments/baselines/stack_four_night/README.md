# Unbeaufsichtigter StackFour-Nachtlauf

Ein Start fuehrt automatisch alle Schritte aus:

1. 200 erfolgreiche synthetische Expertendemonstrationen sammeln, maximal 1200 Versuche.
2. Daten und offiziellen lokalen 90/10-Trajektoriensplit pruefen.
3. BC-RNN und BC-Transformer jeweils 1000 Epochen trainieren (Seed 1,
   100 Batches/Epoche, Batch 16), sequentiell.
4. Je Modell 50 nominale Evaluationsepisoden und 12 Robustheitsbedingungen
   mit je 20 Episoden ausfuehren; Collage und zwei Sekunden Nachlauf.

```powershell
& .\experiments\baselines\stack_four_night\start.ps1
```

Der Prozess laeuft unabhaengig vom Terminal und Agenten. Windows-Sleep wird
waehrend der Arbeit verhindert, das Display darf ausgehen. Nicht neu starten
oder ausschalten. `launch.json` verhindert Doppelstarts.

Der skriptgesteuerte Experte ist ein Kandidat, kein menschlicher Experte.
Es werden ausschliesslich nach dem Erfolgskriterium erfolgreiche Trajektorien
gespeichert. Reicht die Datensammlung nicht aus, stoppt die Pipeline mit FAILED,
statt mit unvollstaendigen Daten zu trainieren. Der erste Kurztest hatte 1/2 Erfolge.

Status: `status.json`; laufende Sammlung: `logs/collection.log`.
Der Collection-Report unter `experiments/baselines/additional_tasks/stack_four/`
zeigt akzeptierte Trajektorien und Fehlversuche. Danach zeigt `training_status.json`
im selben Taskordner den jeweiligen Algorithmus und Arbeitszustand.
Checkpoints, Evaluation, Videos, Robustheitsresultate und Modelllogs liegen
ebenfalls unter `experiments/baselines/additional_tasks/stack_four/`.

Dieser Lauf ist ein begrenzter Ein-Seed-Erstversuch, kein vollstaendiger
15-Stunden-Vergleich mit mehreren Seeds. CubeHandover ist nicht eingeplant:
hier fehlt noch ein geeigneter Demonstrator. Bestehende Square-Ergebnisse bleiben erhalten.
