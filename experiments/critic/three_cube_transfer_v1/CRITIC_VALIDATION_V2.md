# N2-2b · Critic IL-v2

**Status: läuft seit 20.11.2026, 01:08 Uhr (Europe/Berlin).** Die Validierungsentscheidung steht aus.

Je A-Parent werden 300 Episoden aus N2-1 und 300 aus N2-1b gepoolt. Der Critic lernt mit der ausgeführten Aktion (XYZ und Greifer) und dem beobachteten diskontierten Return. Die Zustandsnormierung und die Phasen-Baseline stammen aus beiden Trainingsdatensätzen desselben Parents. Die Returns der verrauschten Episoden stammen aus einer verrauschten Fortsetzung. Sie messen daher keinen kontrafaktischen Return einer Fortsetzung mit dem unveränderten Parent. [Protokoll v2 §E](PROTOCOL_V2.md#e-neu-critic-il-v2-mit-aktionsvariation-n2-1b-n2-2b)

Je Parent sind 20.000 Monte-Carlo-Regressionsupdates mit Batchgröße 256, Lernrate 3·10⁻⁴, Initialisierungsseed 7100 + p und Minibatchseed 7200 + p festgelegt. Die Entscheidung nutzt [§6 des ursprünglichen Protokolls](PROTOCOL.md#6-critic-akzeptanzkriterien-vor-den-daten-festgelegt) auf den 450 gespeicherten A-Rollouts von N2-2. Pro Parent sind das 100 reguläre und 50 schwierige Episoden. Alle drei Critics müssen die Kriterien auf dem regulären Panel erfüllen. Es gibt keine neuen Rollouts. Die Testfamilien bleiben geschlossen.

## Prüfung vor dem Start

41 Tests bestanden. Der neue Fortsetzungstest hat mit synthetischen Daten bei Update 100 innerhalb eines Lossfensters angehalten und bis Update 120 fortgesetzt. Gewichte, Optimizerzustände und Lossverlauf waren bitgleich zum ununterbrochenen Lauf. Ein separater technischer Durchgang ohne Optimizerupdates prüfte die Originaldateien der 1.800 Trainingsepisoden und 450 gespeicherten Validierungsepisoden gegen Hash und Datenvertrag. Mit untrainierten Critics prüfte er auch den vollständigen Auswertungspfad für alle drei Parents. [Laufcode](critic_validation_v2.py) · [Tests](test_critic_validation_v2.py)

## Monitor und Fortsetzung

Aus dem Repository-Stamm:

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_validation_v2.py monitor
```

Laufordner ist `praxis/results/critic/three_cube_transfer_v1/critic_validation_n2_2b/`. `config.json` bindet den Code, das Protokoll und die Eingabemanifeste per SHA-256. Dashboard-ID `three-cube-transfer-v1-critic-validation-v2`.

Die Uhr und das Freigabehäkchen N2-1b/N2-2b wurden unmittelbar vor dem Start geprüft. Startgrenze 07:30 Uhr, weicher Halt um 08:59 Uhr, harte Supervisor-Deadline um 09:00 Uhr. Der Startwrapper hatte PID 35380 (Unix-Erstellungszeit 1795133311.0131009). Der Monitor bestätigte Supervisor PID 2696 (1795133311.0220723) und Worker PID 36748 (1795133311.2224195). Beide waren aktiv. Parent 1 hatte 1.500 von 20.000 Updates erreicht, bei einem mittleren Batch-Loss von 0,02524 im letzten 500er-Fenster und 0 neuen Fehlerzeilen. Derselbe Schritt war im lokalen Dashboard-Snapshot sichtbar.

Bei einem angeforderten Halt über die Datei `STOP` sichert der Worker den Stand an der nächsten Updategrenze (Prüfung alle 100 Updates). Zusätzlich sichert er alle 500 Updates. `critics/parent_p.resume.pt` enthält Critic, Optimizer, Torch-RNG, Minibatch-Sampler, Updatezahl und das offene Lossfenster. Eine unterbrochene Auswertung darf ihre reinen Vorwärtsdurchläufe erneut berechnen. Fertige Parents bleiben per Hash gebunden. Eine Fortsetzung erfordert `PAUSED`, beendete Prozessidentitäten und eine entfernte STOP-Datei. Sie erfolgt mit `start resume <Cutoff-ISO> <Deadline-ISO>` im nächsten freigegebenen Zeitfenster.

Bei `COMPLETE` prüft der Monitor Eingabemanifeste und Gewichte und berechnet beide Panels erneut. Die Abschlussprüfung berichtet AUC mit Intervall, MSE-Differenz mit Intervall, ECE und Endlichkeit je Parent getrennt nach Panel. Bei bestandenem §6 folgt D1b. Bei nicht bestandenem §6 greift die Gesamtpause nach v2 §E.
