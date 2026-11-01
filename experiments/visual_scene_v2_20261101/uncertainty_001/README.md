# Unsicherheit aus drei eingefrorenen Seeds

Erstellt am 01.11.2026. **Kein Training, keine Optimizer-Updates, keine neuen Checkpoints.** Die sechs vorab ausgewählten Checkpoints wurden vor und nach ihrer jeweiligen Inferenz gegen die gespeicherten SHA-256-Hashes geprüft. Laufzeit der Auswertung: rund 15 Sekunden auf CUDA.

## Ergebnis

Die Streuung der Seeds enthält Information über Positionsfehler, erkennt aber gemeinsame Fehlvorstellungen nur unzureichend. Sie eignet sich als zusätzliches Signal zur Auswahl weiterer Aufnahmen; als alleinige Freigabe für Greifen, Stapeln oder Kollisionsfreiheit reicht sie nicht.

Auswertung auf 1.000 zurückgehaltenen Validierungsszenen nach einer Kalibrierung auf den anderen 1.000 Szenen:

| Kennzahl | Zwei feste Kameras | Fest + Handkamera |
| --- | ---: | ---: |
| Spearman-Korrelation Streuung / Positionsfehler, zugeordnete Objekte | 0,40 | 0,45 |
| Fehlerhafte Vorhersagegruppen ohne Zurückstellen | 8,55 % | 7,65 % |
| Auf Kalibrierung gewählte Streuungsschwelle | 7,5 mm | 15,5 mm |
| Beibehaltene Vorhersagegruppen | 90,53 % | 94,83 % |
| Fehlerhafte unter den beibehaltenen Gruppen | 4,47 % | 4,94 % |
| Anteil aller fehlerhaften Gruppen, der zurückgestellt wird | 52,67 % | 38,81 % |
| Fehlerhafte unter beibehaltenen Gruppen bei Türmen | 10,23 % | 11,81 % |
| Beobachtbare Sollobjekte ohne zugeordnetes Ensemble-Objekt | 10 / 2.794 | 6 / 2.794 |

Die Schwellen werden pro Kameravariante unabhängig gewählt. Deshalb ist die unterschiedliche Fehler-Erkennungsrate kein isolierter Vergleich des Nutzens der Handkamera. Die vergleichbaren Streuungs-/Fehlerkurven stehen in den CSV-Dateien.

**Wichtiger Befund:** Bei Fest + Handkamera bleiben 134 von 219 fehlerhaften Vorhersagegruppen unmarkiert. Allein bei Türmen bleiben 75 von 87 fehlerhaften Gruppen unmarkiert. Ein gemeinsamer Fehler der drei Seeds kann eine kleine Streuung haben.

## Verfahren und Definitionen

1. Inferenz aller drei Seeds auf identischen RGB-Bildern und Kamerastrahlen; beide Kameravarianten werden getrennt verarbeitet. Es gibt keine Aufnahme neuer Bilder und keine Simulation zusätzlicher Perspektiven.
2. Detektionsschwelle 0,5. Zuordnung zwischen Seeds ohne Sollgeometrie durch Hungarian-Matching auf Position und sortierten Kantenlängen; maximal 50 mm Positionsabstand. Nicht zugeordnete Detektionen erzeugen zusätzliche Gruppen. Höchstens ein Mitglied pro Seed je Gruppe. Feste Seed-Reihenfolge 1, 2, 3; bei dichten Objekten kann diese Zuordnung selbst mehrdeutig sein.
3. Ensemble-Position als Mittelwert der Mitglieder. Positionsstreuung als Wurzel des mittleren quadrierten räumlichen Abstandes vom Mittelwert. Zusätzlich Ausgabe der Streuung je Achse, Größenstreuung, minimalem Detektionsscore, Sichtbarkeit und maximaler Abweichung physischer Boxecken. Ecken werden permutationsunabhängig zugeordnet, um äquivalente Boxachsen nicht als Fehler zu behandeln. Als repräsentative Größe/Orientierung wird ein Mitglied mit geringster gesamter Eckenabweichung gewählt; Orientierungen werden nicht naiv gemittelt.
4. Eine Gruppe mit nur einem Seed hat rechnerisch Streuung null, gilt durch die fehlende Übereinstimmung aber immer als unsicher. Akzeptiert werden ausschließlich Gruppen mit drei Mitgliedern und Streuung unterhalb der gewählten Schwelle. Keine automatische Aktivierung dieser Regel im Produktivsystem.
5. Erst bei der Auswertung erfolgt die Zuordnung zu beobachtbaren Sollobjekten (ebenfalls maximal 50 mm). Eine Gruppe gilt als fehlerhaft, wenn sie kein Sollobjekt zugeordnet bekommt oder ihr Positionsfehler größer als 10 mm ist. Nicht zugeordnete Sollobjekte werden separat gezählt; ein von allen Modellen übersehenes Objekt besitzt keine auswertbare Vorhersageunsicherheit.

Die hier kalibrierte Regel bewertet **Position und falsche Zusatzdetektionen**. Sie garantiert keine richtige Größe, Orientierung oder Montagefähigkeit. Größen- und Eckenstreuung sind vorbereitete zusätzliche Diagnosesignale und noch nicht Bestandteil der Regel.

## Kalibrierung und Aussagegrenzen

Familien werden mit Zufallsseed 61101 disjunkt in zwei Hälften geteilt; die Zuordnung steht in `split.csv`. Kalibrierungsregel: möglichst viele Gruppen beibehalten, mindestens 30 Gruppen, nominale obere Wilson-95%-Grenze des Fehleranteils höchstens 5 %. Falls keine Schwelle passt, wird alles zurückgestellt. Schwellenraster: 0 bis 20 mm in 0,25-mm-Schritten, danach 25/35/50/100 mm; -1 bedeutet alles zurückstellen.

Die Wilson-Zahl ist ein deskriptives Auswahlkriterium, **keine statistisch abgesicherte Fehlergarantie**. Objekte derselben Szene sind abhängig, mehrere Schwellen werden durchsucht und die Checkpoints wurden bereits anhand derselben ursprünglichen Validierungsdaten ausgewählt. Auch die zurückgehaltene Hälfte ist daher keine unabhängige Schlussprüfung. Auf ihr liegt die nominale obere Fehlergrenze sogar über 5 %: 5,34 % beziehungsweise 5,82 %.

Die reservierten IID-/OOD-Testdaten wurden weder gelesen noch für die Schwellen verwendet. Die Aussage bezieht sich auf vorhandene Validierungsbedingungen, nicht auf unbekannte reale Objekte. Drei Seeds können dieselben systematischen Fehler teilen. Ein Streuungswert von beispielsweise 2 mm bedeutet ausdrücklich nicht, dass die wahre Position mit einer bestimmten Wahrscheinlichkeit innerhalb von 2 mm liegt.

## Plots und Rohdaten

- `fixed_uncertainty.png` / `.svg` und `fixed_wrist_uncertainty.png` / `.svg`: tatsächlicher Fehler gegen Streuung, Fehleranteil nach Zurückstellen, übersehene Fehler und empirische Fehlerverteilung je Streuungsbereich. Die Punktwolke und die Fehlerverteilung enthalten zugeordnete Objekte; die Filterkurven enthalten zusätzlich falsche Zusatzobjekte. Fehlende Sollobjekte sind separat dokumentiert.
- `*_objects.csv`: objektweise Metriken inklusive Szenen-ID, Anordnung, Split und Sollzuordnung.
- `*_scenes.csv`: fehlende Sollobjekte und falsche Zusatzgruppen pro Szene.
- `*_calibration_sweep.csv` / `*_held_sweep.csv`: vollständige Schwellenverläufe.
- `*_predictions.npz`: eingefrorene Modellausgaben, keine Gewichte.
- `results.json`: Ergebnisse nach Anordnung sowie Checkpoint-, Daten- und Quellcodehashes.

Es gibt keine neuen Trainings-/Validierungs-Loss-Kurven: Dieser Durchlauf ist eine reine Inferenzdiagnose ohne Epochen.

## Reproduktion

Aus dem Repository, Ausgabe in einen neuen Ordner:

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_ensemble_uncertainty.py -q -p no:cacheprovider
& .\praxis\.venv\Scripts\python.exe experiments/visual_scene_v2_20261101/ensemble_uncertainty.py --name uncertainty_002
```

Sieben Regressionstests bestanden: permutierte Slots, fehlende Seed-Unterstützung, große Abweichungen, gemeinsam falsche Position, gemeinsam fehlendes Objekt, Boxachsensymmetrie und entfernte falsche Detektion. Bestehende Ausgabeverzeichnisse werden nicht überschrieben.

Weitere auswählbare Arbeitspakete stehen in `NEXT_STEPS.md`.
