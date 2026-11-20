# S-1 · Datenpool für Selbstimitation

Nach [Protokoll v3 §3](PROTOCOL_V3.md#3-datenpool-s-1-keine-optimizerupdates) laufen drei eingefrorene A-Parents auf denselben 400 Familien aus `online_interaction` (2100003250–2100003649). Alle 1.200 Ausgänge gehen in den Pool ein. Rauschen und Projektion folgen N2-1b mit σ = 0,05 auf XYZ und δ_max = 0,20. Jeder Parent hat einen fortlaufenden PCG64-Strom mit Seed `7800 + p`. Es gibt 0 Optimizerupdates.

## Datenvertrag

Die NPZ-Dateien behalten die Arrays von [N2-1b](CRITIC_DATA_NOISY.md). `il_v2_value[t]` ist das Minimum der beiden Critic-Ausgaben des zugehörigen IL-v2-Modells für den Zustand vor dem Schritt und die tatsächlich ausgeführte Aktion (XYZ und Greifer). Die Episodenzeile enthält je zusammenhängendem Abschnitt `stage`, `phase`, `start_frame` und `last_frame` (beide 0-basiert und inklusiv). `completed` hält fest, ob der Folgezustand zu einer anderen Stufe oder Phase überging. Beim Horizontende ohne Übergang bleibt der letzte Abschnitt unvollständig.

Die JSON-Episodenzeile wird nach dem NPZ atomar veröffentlicht. Sie bindet dessen SHA-256 und den Zustand des Zufallsstroms nach dem letzten Frame. Der Supervisor-Status, die Worker-Identität und der Monitorzustand liegen im [Laufordner](../../../praxis/results/critic/three_cube_transfer_v1/self_imitation_pool_s1/). Der [Dashboard-Eintrag](../../../monitor/training-runs.json) verweist auf Konfiguration und Abschlussmanifest. Das Manifest wird erst nach 1.200 Episoden geschrieben und vom Monitor gegen Rohdaten und vollständige Nenner geprüft.

## Startprüfung am 20.11.2026

- Start um 11:29 Uhr Europe/Berlin, Cutoff 13:30 Uhr, harte Deadline 14:00 Uhr. Der Worker beendet die aktuelle Arbeit spätestens beim nächsten Prüfschritt ab 13:58 Uhr, damit der Supervisor den Halt vor der Deadline protokollieren kann.
- Supervisor PID `23508`, erstellt `1795170560.908681` Unix-Sekunden. Worker PID `24348`, erstellt `1795170561.1133916` Unix-Sekunden. Monitor `OK` mit beiden Prozessidentitäten, 1/1.200 gesicherten Episoden, 0 neuen Fehlerzeilen und 0 Optimizerupdates.
- 25 Vertragstests bestanden. Alle drei Critic-Gewichte stimmen mit dem N2-2b-Abschluss überein. In Episode 0000 wurden NPZ-Hash, 335 bitgleiche Critic-Werte, Phasengrenzen und Zufallsstrom geprüft. Die Konfiguration hat SHA-256 `059da7ee184560cada89eff8b2b68f7ec545b84a54a1cc46e008453e90cbd40c`.
- Der erste Supervisor-Aufruf endete beim Parsen der Zeitargumente. Nach Korrektur der Argumentübergabe startete die einzige Datenerhebung. Beim ersten Aufruf gab es keinen Worker und keinen Laufordner.

## Monitor und Fortsetzung

Aus dem Repository-Stamm:

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/self_imitation_pool.py monitor
```

Für einen geordneten Halt erzwingt die Datei `STOP` im Laufordner eine Unterbrechung am nächsten Prüfschritt. Die letzte veröffentlichte Episodenzeile je Parent legt den Zufallszustand fest. Eine unterbrochene Episode wird ab ihrem Anfang mit demselben Szenenseed und Zufallszustand ausgeführt. Nach `PAUSED` und bestätigtem Prozessende kann der Supervisor im nächsten autorisierten Zeitfenster mit `start resume --cutoff <Zeit> --deadline <Zeit>` fortsetzen, sobald die STOP-Datei entfernt ist. Der Worker prüft Quell- und Eingabeprovenienz sowie die bisherige Episodenfolge und deren Zufallsströme vor der Fortsetzung.

## Ergebnis und Abschlussprüfung am 20.11.2026

Der Lauf endete vor dem Cutoff ohne Unterbrechung. Um 12:42 Uhr meldete der Monitor `COMPLETE`. Supervisor 23508 und Worker 24348 waren beendet, der Worker mit Exitcode 0. Es gab 0 Fehlerzeilen, 0 Unterbrechungen und 0 Optimizerupdates.

| Parent | Episoden | Erfolge | Fehlschläge (Horizont) | Simulatorinstabilität | Frames |
|---|---|---|---|---|---|
| 1 | 400 | 175 | 225 | 0 | 284.478 |
| 2 | 400 | 133 | 267 | 0 | 312.060 |
| 3 | 400 | 148 | 252 | 0 | 302.508 |
| gesamt | 1.200 | 456 | 744 | 0 | 899.046 |

Alle 1.200 Episoden liegen auf denselben 400 Familien aus `online_interaction`. Alle 899.046 Frames tragen einen IL-v2-Wert, es gab 0 Grenzverletzungen. Die Workerlaufzeit betrug 4.233 s, das sind 1.021 Episoden/h. Die Zahlen beschreiben den Datenpool. Sie sind keine Wirksamkeitsaussage, weil die Parents unverändert sind und das Explorationsrauschen wirkt.

**Manifest und Hashes.** `summary.json` hat SHA-256 `1a5a19dbc0beed4ff5dd31259be8e6c27b46acecd78cfb3c237bc9abf8780c77`. Datensatz `dataset_sha256` = `c83c8eb3634b1996d335ed72435665059a7b5f7b064978843e7caeec032c6aab` (verkettete `arrays_sha256` in Episodenreihenfolge), Zeilen `6fa84120…c1d4`, Konfiguration `059da7ee…d40c` wie beim Start.

**Prüfung.** Der Monitor rechnete beim ersten `COMPLETE` mit `verify()` gegen die Rohdaten nach. Danach lief `self_imitation_pool.py verify` erneut fehlerfrei. Es prüft alle 1.200 NPZ-Hashes, Datenvertrag, Phasenabschnitte und Zufallsströme je Parent, außerdem Quellhashes, 400 Familien und die vollständige Neuberechnung von `summary.json`. Die 25 Vertragstests (`test_self_imitation_pool.py`, `test_critic_data_noisy.py`, `test_critic_data.py`) bestanden erneut. Testfamilien blieben geschlossen. Der Pool ist die Eingabe für S-2.
