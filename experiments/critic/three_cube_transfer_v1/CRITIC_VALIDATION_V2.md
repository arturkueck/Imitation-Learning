# N2-2b · Critic IL-v2

**Status: erledigt, §6 bestanden (alle drei Parents).** Gestartet am 20.11.2026 um 01:08 Uhr, abgeschlossen um 01:10 Uhr (Europe/Berlin), Abschlussprüfung um 04:00 Uhr. [Ergebnis](#ergebnis-und-abschlussprüfung-am-20112026)

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

## Ergebnis und Abschlussprüfung am 20.11.2026

**Entscheidung: §6 bestanden.** Alle drei Critics IL-v2 erfüllen die Kriterien auf dem regulären Panel (`validation_normal`). Damit folgt D1b, eine Gesamtpause nach v2 §E greift nicht. Das schwierige Panel wird nur berichtet, dort sind ebenfalls alle Prüfungen erfüllt.

Gewichtete AUC und MSE-Differenz (Critic − Phasen-Baseline) mit 95-%-Familienbootstrap (2.000 Ziehungen, Seed 7300). Kriterien nach §6: AUC ≥ 0,60 bei unterer Grenze > 0,50, MSE-Differenz mit Intervall unter 0, ECE ≤ 0,10, alle Werte endlich.

| Parent | Panel | Erfolge | Punkte | AUC [95 %] | MSE-Differenz [95 %] | ECE | §6 |
|---|---|---|---|---|---|---|---|
| 1 | regulär | 41/100 | 14 | 0,885 [0,826; 0,936] | −0,0285 [−0,0349; −0,0208] | 0,022 | ja |
| 2 | regulär | 29/100 | 14 | 0,916 [0,835; 0,973] | −0,0284 [−0,0349; −0,0198] | 0,024 | ja |
| 3 | regulär | 29/100 | 14 | 0,882 [0,823; 0,931] | −0,0175 [−0,0286; −0,0005] | 0,028 | ja |
| 1 | schwierig | 23/50 | 14 | 0,951 [0,894; 0,987] | −0,0284 [−0,0363; −0,0194] | 0,029 | (ja) |
| 2 | schwierig | 19/50 | 14 | 0,933 [0,867; 0,983] | −0,0283 [−0,0366; −0,0179] | 0,047 | (ja) |
| 3 | schwierig | 16/50 | 12 | 0,954 [0,902; 0,991] | −0,0236 [−0,0307; −0,0160] | 0,024 | (ja) |

„Punkte“ zählt die für die AUC geeigneten Phasenpunkte mit mindestens 10 Erfolgen und 10 Fehlschlägen. Alle 347.123 vorhergesagten Frames sind endlich. Kein Phasenpunkt fiel auf die Gesamtquote zurück, und keine Bootstrap-Ziehung war undefiniert.

**Einordnung.** Bei Parent 3 liegt die obere Grenze der MSE-Differenz auf dem regulären Panel mit −0,0005 nur knapp unter 0. Das Kriterium ist erfüllt, der Vorsprung vor der Phasen-Baseline ist dort aber klein. §6 bewertet die Vorhersage des Zustandswerts auf Rollouts des unveränderten Parents. Ob der Critic auf Aktionen reagiert, wie es der Actor-Critic braucht, prüft erst D1b nach v2 §A. Die Returns der N2-1b-Trainingsepisoden stammen aus verrauschten Fortsetzungen (siehe oben).

**Vortraining.** Je Parent 20.000 Updates auf 600 Episoden, insgesamt 60.000 Critic-Updates. Trainingsframes 423.107 / 461.647 / 448.109. Mittlerer Batch-Loss im ersten 500er-Fenster 0,0435 / 0,0341 / 0,0408, im letzten 0,0087 / 0,0064 / 0,0103. Rechenzeit etwa 37 s je Parent auf der CPU. 0 neue Rollouts, 0 Rollout-Optimizerupdates, Testfamilien geschlossen.

**Abschlussprüfung.** Der Monitor meldete `COMPLETE` mit Worker-Exitcode 0. Supervisor (PID 2696) und Worker (PID 36748) waren beendet, und es gab 0 Fehlerzeilen im Log. Der Monitor führte die eingefrorene Prüfung `verify()` aus. Diese wurde danach noch einmal getrennt mit `critic_validation_v2_report.py --verify` ausgeführt (`VERIFY OK`, 9,6 s). Dabei stimmten eingefrorene Eingaben und Quellhashes aus `config.json`, Gewichtshashes und die Neuberechnung beider Panels für alle drei Parents mit `summary.json` überein. 13/13 Tests in `test_critic_validation.py` und `test_critic_validation_v2.py` waren erneut grün.

| Artefakt | SHA-256 |
|---|---|
| `summary.json` | `767bccfcfb9a972bbb064039c2eb1abaa55477e41d5aac69e038c23c4b142e94` |
| `config.json` | `e22b693dd9b0a01f203f7159dbff257c1dbfc1232a0b14a6608f34a582fa176e` |
| Critic Parent 1 | `4e7e3f75ca1e97b0e6af4af86537a7ba68d8184344541f4b77a2759af39bb70c` |
| Critic Parent 2 | `4efc72591f26bec7cc442c46a1a6b1784f6174572b991698fcd3243ce560b5fe` |
| Critic Parent 3 | `d746d59d42f48b046d64a02c05cfb468d6a9ebe19da7bd9e23e48507f65ffca9` |
| Eingaben N2-1 / N2-1b / N2-2 | `9f0aeaaf…a2ba` / `448a117b…0068` / `fac1e51d…e570` |
| [critic_validation_v2.py](critic_validation_v2.py) | `74de6bf05674d886c0f2633baf45b8ee4ceba12efc9eac75265736ef21ae30c6` |
| [critic_validation_v2_report.py](critic_validation_v2_report.py) (nur Lesen) | `aedcd19443e2810c12be969de20b0e97102e0afd34839bd3d515c9ec43652974` |

Kompakter Bericht ohne Punktlisten, aus dem Repository-Stamm:

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_validation_v2_report.py
```

Die Critic-Gewichte liegen unter `praxis/results/critic/three_cube_transfer_v1/critic_validation_n2_2b/critics/` und sind nicht im Git. Der Fortsetzungspunkt wird nicht mehr gebraucht.
