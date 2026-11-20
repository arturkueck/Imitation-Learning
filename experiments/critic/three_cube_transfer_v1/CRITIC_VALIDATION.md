# N2-2 · Critic-Vortraining und Critic-Validierung

**Status: erledigt** · Start 19.11.2026 12:29 Uhr, Abschluss gegen 12:59 Uhr · **Kriterien nach §6 erfüllt: alle drei Critics bestehen auf `validation_normal`** ([Ergebnis](#ergebnis-abschluss-19112026))

Umsetzung von [PROTOCOL.md §5 und §6](PROTOCOL.md#6-critic-akzeptanzkriterien-vor-den-daten-festgelegt) mit der Freigabe N2-2/N2-3 aus dem [Nachtplan](NACHTPLAN.md#freigaben). Code: [critic_validation.py](critic_validation.py), Tests: [test_critic_validation.py](test_critic_validation.py). Laufdaten liegen unter `praxis/results/critic/three_cube_transfer_v1/critic_validation_n2_2/` und nicht im Git.

## Ablauf im Worker

1. **Vortraining.** Je A-Parent *p* wird ein Twin-Q-Critic trainiert, nur auf den 300 N2-1-Episoden dieses Parents. Vor dem Laden werden alle Episodenhashes und der Datensatzhash `9f0aeaaf…daff9a2ba` geprüft. Die Konfiguration: 20.000 Updates, Batch 256, AdamW mit Lernrate 3·10⁻⁴, kein Early Stopping und keine Abstimmung auf der Validierung. Die Initialisierung verwendet den Seed `c_p = 7100 + p`, die Minibatches `r_p = 7200 + p`. Die Normierung wird aus den Critic-Datenframes dieses Parents bestimmt und als Buffer mit dem Critic gespeichert. Nach dem Training ist der Critic per SHA-256 eingefroren (`critics/parent_p.pt` und `.json`, mit Optimizerzustand, Losskurve und Laufzeit).
2. **Validierungsrollouts.** Die drei eingefrorenen A-Parents laufen auf `validation_normal` (100 Familien) und `validation_hard` (50 Familien aus [difficulty_panels_v1.json](difficulty_panels_v1.json), Regel-SHA geprüft). Das ergibt 450 Episoden mit derselben Episodenfunktion und demselben Datenvertrag wie N2-1, 0 Optimizerupdates und ohne Exploration. Die Trajektorienhashes sind gespeichert, sie dienen später als BC-Referenz für Runde 0 und als Determinismusprüfung (§8, §9).
3. **Auswertung nach §6** aus den gespeicherten Rollouts und den eingefrorenen Critics. Danach schreibt der Worker `summary.json`.

## Festlegungen der Umsetzung (innerhalb von §6)

- **Vortrainingsziel:** Regression beider Q-Köpfe auf den beobachteten diskontierten Return (γ = 0,995) an der Parentaktion. Das entspricht unverändert `Learner.warm` aus [base/core.py](../base/core.py) mit Breite 256, Gewichtsabfall 10⁻⁶ und Gradientenclip 10. Das Protokoll legt Updates, Batch und Lernrate fest. Das Ziel übernimmt es aus dem Basiscode.
- **Aktionseingang** des Critics: `x, y, z, Greifer` (Spalten 0, 1, 2, 6), wie die trainierten Teile nach §2.
- **Phasenpunkte:** Je Episode zählt der erste Frame jeder erreichten Kombination aus Stufe und Policy-Phase. Frame 0 ist immer der erste Frame seiner Kombination und deckt damit den Episodenstart ab, ohne doppelt gezählt zu werden. Der Rückzugsmodus des Sequencers bildet keinen eigenen Punkt.
- **Baseline:** je Punkt der mittlere diskontierte Return (für die MSE) beziehungsweise die Erfolgsquote, jeweils aus den Critic-Daten desselben Parents. Fehlt ein Punkt dort, gilt die Gesamterfolgsquote des Parents. Die Zahl solcher Ersatzwerte wird ausgewiesen.
- **AUC:** Mann-Whitney mit Gleichständen zu ½. Die Gewichtung erfolgt nach der Episodenzahl je Punkt. Geeignet sind Punkte mit mindestens 10 Erfolgen und 10 Fehlschlägen auf dem jeweiligen Panel. Die geeigneten Punkte bleiben im Bootstrap fest. Fehlt in einer Ziehung an einem Punkt eine Klasse, entfällt dieser Punkt nur in dieser Ziehung. Die Zahl solcher Fälle wird ausgewiesen.
- **Bootstrap:** 2.000 Ziehungen über Familien, Seed 7300, je Parent und Panel neu gestartet. Dieselben Ziehungen gelten für AUC und MSE-Differenz. Es wird das 95-%-Perzentilintervall berichtet.
- **ECE:** 10 gleich breite Klassen auf [0, 1]. Vorhersagen außerhalb fallen in die Randklassen, ihr Wert bleibt unverändert.
- **Endlichkeit:** geprüft auf allen Frames der Validierungsrollouts, nicht nur an den Phasenpunkten.
- Bestanden ist nach §6 nur, wenn alle drei Critics auf `validation_normal` bestehen. `validation_hard` wird getrennt berichtet und entscheidet nicht.

## Prüfungen vor dem Start

- [29/29 Tests](test_critic_validation.py) bestanden (11 neue, 9 aus N2-1, 9 Geometrietests). Die neuen Tests prüfen die Phasenpunkte, die AUC mit Gleichständen und Bootstrapgewichten, ECE-Sollwerte, die Bestehensregel einschließlich „nicht bewertbar“ und nicht endlicher Werte, die Reproduzierbarkeit des Bootstraps und die Baseline. Dazu kommen ein bitgleich deterministisches Vortraining auf synthetischen Daten, der STOP-Halt, die Panels und der Dashboardeintrag. Ein technischer Test des Auswertungspfads lief auf echten N2-1-Daten von Parent 1 mit einem zufällig initialisierten Critic, mit 0 Optimizerupdates und ohne Validierungs- oder Testdaten.
- Der Befehl `check` und der Supervisor prüfen vor dem Start das Häkchen N2-2/N2-3, `Gesamtpause: nein`, den Protokollstatus `FREIGEGEBEN`, den Abschluss von N2-1 mit Datensatzhash sowie die Panelgrößen und -bereiche.

## Lauf und Bedienung (aus dem Repository-Stamm)

Der Lauf startete am 19.11.2026 um 12:29 Uhr mit Startfenster bis 14:30 Uhr und harter Deadline 14:45 Uhr (Worker 14:44 Uhr). Prozessidentität: Supervisor PID **36840** (Erstellungszeit Unix 1795087737.3515823), Worker PID **30672** (Erstellungszeit Unix 1795087737.5778196). Der Startwrapper der venv hatte PID 31324. Dashboardeintrag: `three-cube-transfer-v1-critic-validation`.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_validation.py monitor
# Fortsetzung nur nach PAUSED, beendeten Prozessen und ohne STOP-Datei:
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_validation.py start resume --cutoff <ISO+01:00> --deadline <ISO+01:00>
```

**Halt und Fortsetzungspunkt.** Ein Halt erfolgt über die Datei `STOP` im Laufordner. Der Worker setzt dann `PAUSED`, beim Vortraining nach höchstens 100 Updates, bei den Rollouts an einer Episodengrenze. Fertige Critics werden per SHA-256 geprüft wiederverwendet. Ein unvollständiges Vortraining wird verworfen und für diesen Parent aus denselben Seeds vollständig neu gerechnet. Es ist bitgleich deterministisch (Test). Bei den Rollouts setzt die Fortsetzung beim Index der ersten fehlenden `episodes/NNNN.json` an. `config.json` bindet die Quellen per SHA-256, eine Fortsetzung mit geänderten Quellen bricht ab. Bei `COMPLETE` gleicht der Monitor einmalig Rohepisoden, Critic-Hashes und Auswertung gegen `summary.json` ab.

## Ergebnis (Abschluss 19.11.2026)

Supervisor (PID 36840) und Worker (PID 30672) stehen auf `COMPLETE`, sind beendet und haben dieselbe Prozessidentität wie beim Start. Der Worker endete mit Exitcode 0 gegen 12:59 Uhr, also vor dem Startfenster-Ende (14:30 Uhr) und der Deadline (14:45 Uhr). Es gab keine Pause, keine Fortsetzung und keine Wiederholung. Um 13:00 Uhr meldete `critic_validation.py monitor` den Status `COMPLETE` ohne Fehlerzeilen. Dabei lief einmalig `verify`: Alle 450 Rohepisoden wurden geladen und gegen Plan und Datenvertrag geprüft, die drei Critics per SHA-256 geladen und die gesamte Auswertung nach §6 neu berechnet. Das Ergebnis stimmt mit `summary.json` überein (`result_verified: true`).

**Entscheidung nach §6: bestanden.** Alle drei Critics erfüllen auf `validation_normal` alle vier Bedingungen. Entscheidend ist nur dieses Panel.

### Reguläre Validierung (`validation_normal`, entscheidet)

| Parent | A-Erfolge | geeignete Punkte | gewichtete AUC [95-%-KI] | MSE Critic | MSE Phasen-Baseline | Differenz [95-%-KI] | ECE | bestanden |
|---|---|---|---|---|---|---|---|---|
| 1 | 41/100 | 14/14 | 0,853 [0,787; 0,909] | 0,0266 | 0,0462 | −0,0196 [−0,0286; −0,0081] | 0,040 | ja |
| 2 | 29/100 | 14/14 | 0,886 [0,794; 0,951] | 0,0210 | 0,0420 | −0,0210 [−0,0293; −0,0109] | 0,033 | ja |
| 3 | 29/100 | 14/14 | 0,817 [0,750; 0,879] | 0,0321 | 0,0448 | −0,0127 [−0,0213; −0,0036] | 0,039 | ja |

Schwellen nach §6: AUC ≥ 0,60 mit unterer Grenze > 0,50, mindestens zwei geeignete Punkte, Differenzintervall vollständig < 0, ECE ≤ 0,10, alle Vorhersagen endlich.

### Schwierige Validierung (`validation_hard`, getrennt berichtet, entscheidet nicht)

| Parent | A-Erfolge | geeignete Punkte | gewichtete AUC [95-%-KI] | MSE Critic | MSE Phasen-Baseline | Differenz [95-%-KI] | ECE | Bedingungen erfüllt |
|---|---|---|---|---|---|---|---|---|
| 1 | 23/50 | 14/14 | 0,925 [0,860; 0,971] | 0,0217 | 0,0422 | −0,0205 [−0,0301; −0,0083] | 0,058 | alle |
| 2 | 19/50 | 14/14 | 0,906 [0,849; 0,953] | 0,0203 | 0,0440 | −0,0237 [−0,0322; −0,0134] | 0,048 | alle |
| 3 | 16/50 | 12/14 | 0,778 [0,675; 0,865] | 0,0315 | 0,0362 | −0,0048 [−0,0191; +0,0114] | 0,052 | nicht Bedingung 3 |

Bei Parent 3 schließt das Intervall der MSE-Differenz auf dem schwierigen Panel die 0 ein. Zwei Punkte (`stage2_phase5`, `stage2_phase6`) waren dort mit 24 Episoden und 8 Fehlschlägen nicht geeignet. Nach §6 hat das keinen Einfluss auf die Entscheidung.

### Weitere Angaben

- **Endlichkeit:** Alle Criticwerte auf allen Frames der Validierungsrollouts waren endlich (regulär 72.977 / 80.749 / 81.117 Frames, schwierig 35.012 / 37.605 / 39.663 Frames je Parent 1/2/3).
- **Phasenpunkte:** regulär 1.286 / 1.213 / 1.186 Punkteinträge, schwierig 612 / 612 / 554. Die Phasen-Baseline benötigte 0 Ersatzwerte, und in keiner Bootstrapziehung entfiel ein Punkt.
- **Endgründe der A-Rollouts:** Alle Fehlschläge endeten am Horizont, mit 0 Rückzugs-Timeouts und 0 Simulatorinstabilitäten. Das schwierige Panel (lange Transportwege) hatte bei keinem Parent eine niedrigere Erfolgsquote als das reguläre. Das deckt sich mit der nicht monotonen Kalibrierung aus N1-5.
- **Beobachtung ohne Bewertung:** Bei Parent 1 liegt auf der regulären Validierung der mittlere Criticwert an allen 14 Punkten unter dem mittleren beobachteten Return. Die ECE bleibt trotzdem unter der Schwelle.
- **Vortraining (gemessene Kosten):** je Parent 20.000 Updates in 43,2 / 43,4 / 43,0 s (rund 460 Updates/s, CPU mit 4 Threads). Der letzte mittlere Loss lag bei 0,0050 / 0,0026 / 0,0044, die MSE auf den eigenen Trainingsdaten bei 0,0027 / 0,0012 / 0,0022. Insgesamt 60.000 Critic-Updates, die Rollouts liefen mit 0 Optimizerupdates.
- **Durchsatz:** 983,7 Episoden/h über die aufsummierten Episodenlaufzeiten (1.646,9 s). Die Worker-Laufzeit einschließlich Vortraining und Auswertung betrug 1.797,2 s.

**Hashes** (Laufordner `praxis/results/critic/three_cube_transfer_v1/critic_validation_n2_2/`):

- Critic Parent 1: `a590842a33c5470673552370cb61cb39c54e0e5a1e35dbd69940343962d6b362`
- Critic Parent 2: `4a6daa4c0e150bcb5fd6b4ce7d2164fdb648cab6ae66ee2deca1272395fdefd4`
- Critic Parent 3: `5f698313d619202c73bdcc46d0ddd09a00f3ff733a14ecb1dd304ca42d76b41b`
- `trajectories_sha256` (BC-Referenz für Runde 0, §8/§9): `729aa1acd3d1c1c2e7f0fd4281aa3ae5616e7af237b8a5ab92fa4d4cfb32b92c`
- `dataset_sha256`: `fac1e51d12f47d399b685abd1d1bffa963c5e326ac0b2cfecd5a1c412d9ce570`
- `rows_sha256`: `3e161954b9b9f7644d5e62b09388dbdd5c32897144b3f1d075965253be3672eb`
- `config.json`: `305bc0e7d40a8d54350fc6e1f480578447fd0b2b138607314b0458f02664e7a7`

Nach dem Lauf bestanden erneut 29/29 Tests (Exitcode 0), der Code ist seit dem Start unverändert. Die Testfamilien blieben geschlossen. Diese Validierungsergebnisse sind nicht mit Testergebnissen zusammengefasst. Nach §6 und dem Nachtplan ist damit der Weg zu N2-3 frei. N2-3 ist mit dem Häkchen N2-2/N2-3 freigegeben.
