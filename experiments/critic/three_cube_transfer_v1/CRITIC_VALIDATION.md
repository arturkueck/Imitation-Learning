# N2-2 · Critic-Vortraining und Critic-Validierung

**Status: läuft** · Start 19.11.2026 12:29 Uhr · Ergebnis folgt nach Abschluss durch den Monitor

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

## Ergebnis

Folgt nach Abschluss. Bis dahin gibt es keine Aussage zur Critic-Akzeptanz.
