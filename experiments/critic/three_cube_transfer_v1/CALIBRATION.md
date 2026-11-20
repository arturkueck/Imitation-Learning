# Kalibrierung der Dreierstarts

Stand 19.11.2026 · N1-5 · Eingefroren als `difficulty_v1`

## Maß und Grenzen

Die Einteilung verwendet die Summe der direkten horizontalen Transportstrecken vom Mittelpunkt von Würfel B zur Basis A und von C zur selben Basis. Eine größere Strecke verlangt mehr horizontalen Transport. Das Maß erfasst die geplanten Wege in der Tischebene. Greiferanflug, Hubhöhe, Umwege, Freiraum und Tischlage gehen in die Klassengrenzen nicht ein. Die übrigen Geometriemerkmale bleiben in `difficulty_v1` definiert. [Merkmalsdefinition](difficulty.py)

Die 100 Kalibrierungsfamilien wurden jeweils einmal nach ihrer Transportstrecke sortiert. Die Grenzen liegen in der Mitte zwischen den Werten auf Rang 34 und 35 beziehungsweise 67 und 68. Diese Drittelregel ergibt 34, 33 und 33 Familien und verwendet ausschließlich Kalibrierungsgeometrien. Die 300 Episodenausgänge dienten anschließend der deskriptiven Prüfung der Klassen. Die Grenzwerte wurden vor der Panelzuordnung gespeichert. [Eingefrorene Regel](difficulty_v1.json) · [SHA-256](difficulty_v1.sha256)

| Klasse | Transportstrecke `x` in m | Familien | A 1 | A 2 | A 3 | Aggregate Episodenquote |
|---|---|---:|---:|---:|---:|---:|
| leicht | `x < 0.2551708829974316` | 34 | 13/34 | 9/34 | 12/34 | 34/102 (33,3 %) |
| mittel | `0.2551708829974316 ≤ x < 0.3261966323421625` | 33 | 15/33 | 13/33 | 13/33 | 41/99 (41,4 %) |
| schwer | `0.3261966323421625 ≤ x` | 33 | 12/33 | 8/33 | 8/33 | 28/99 (28,3 %) |
| Gesamt | | 100 | 40/100 | 30/100 | 33/100 | 103/300 (34,3 %) |

Erfolg ist ein stabiler Dreierturm über 50 aufeinanderfolgende Frames. Auf den gemeinsamen Kalibrierungsszenen hat jeder A-Parent die niedrigste Erfolgsquote in „schwer“ und die höchste in „mittel“. Damit ist die beobachtete Beziehung für alle drei Parents nicht monoton. Die Regel bildet ein Panel mit langen Transportwegen aus der regulären Startverteilung. Wie die Klassen auf unabhängigen Familien oder mit anderen Policies mit Erfolg zusammenhängen, bleibt offen. Die gepoolten 300 Episoden enthalten 100 geteilte Starts. [N1-4-Zusammenfassung](../../../praxis/results/critic/three_cube_transfer_v1/calibration_n1_4/summary.json)

## Panelzuordnung

Für die regulären Panels wurden alle reservierten Familien klassifiziert. Für die schwierigen Panels wurden die ersten 50 beziehungsweise 75 Starts der Klasse „schwer“ in aufsteigender Seedreihenfolge gewählt. Das Manifest enthält die verbindlichen Szenenseeds, Klassen und Transportstrecken. Es bindet die verwendete Regel per SHA-256. Testzuordnung und Validierungszuordnung beruhen ausschließlich auf dem Zustand direkt nach dem Reset. Die Testpanels bleiben für Rollouts und Ergebnisauswertung geschlossen. Das separate Zweierpanel folgt dem bestehenden Splitmanifest. [Geprüfte Panelzuordnung](difficulty_panels_v1.json) · [Splitmanifest](splits.json)

| Panel | Geprüfte Kandidaten | Zugeordnet | Leicht | Mittel | Schwer |
|---|---:|---:|---:|---:|---:|
| Validierung regulär | 100 | 100/100 | 43 | 27 | 30 |
| Validierung schwierig | 139 | 50/50 | 0 | 0 | 50 |
| Test regulär | 150 | 150/150 | 50 | 42 | 58 |
| Test schwierig | 183 | 75/75 | 0 | 0 | 75 |

## Reproduktion und Integrität

Rohdaten, Konfiguration und 13 Quellhashes von N1-4 wurden geprüft. Die gespeicherten Anfangszustände und Merkmale von 100/100 Kalibrierungsfamilien wurden mit demselben Dreier-Szenengenerator reproduziert. Die Panelzuordnung wurde zweimal ausgeführt und ergab dasselbe Manifest. Die Zuordnung benötigte keine Policy-Aktionen oder Optimizerupdates. Die neun Geometrietests bestanden. [Kalibrierungs- und Zuordnungsskript](freeze_difficulty.py)

```powershell
$env:PYTHONPATH=(Resolve-Path praxis/src).Path
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/freeze_difficulty.py assign
Get-FileHash experiments/critic/three_cube_transfer_v1/difficulty_v1.json
```
