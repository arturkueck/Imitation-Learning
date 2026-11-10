# Begrenzter Pilot: gemeinsame geometrische Boxkorrektur

01.11.2026. **Abgeschlossen, kein neuronales Training.** Drei eingefrorene Fest-plus-Handkamera-Modelle erzeugen Vorhersagen auf neuen RGB-Szenen. Anschließend werden ausschließlich geometrische Boxparameter verändert. Alle Checkpoint-Hashes wurden vor/nach geprüft; keine neuronalen Optimizer-Updates.

## Vorab festgelegter Umfang

`locked_plan.json` wurde vor der Szenenerzeugung geschrieben. 8 Entwicklungsszenen aus Seed 9301101 und 16 Prüfszenen aus Seed 9301102, nach Szenenfamilien getrennt. Pro Anordnung sind es zwei Entwicklungs- und vier Prüfszenen: verstreut, gemischt, Turm und Wand/Brücke. Es werden nur Szenen mit mindestens zwei Objekten aufgenommen, deterministisch nach Reihenfolge und Anordnungsquote, nicht nach Modellfehler. Die bisherigen reservierten IID-/OOD-Schlussprüfungen bleiben unberührt. Dieser kleine ausgeglichene Pilot ist kein repräsentativer großer IID-Endtest.

Die Parameterwahl bleibt für beide Hälften unverändert. Die Entwicklungszahlen wurden nicht zur anschließenden Anpassung der Prüfeinstellungen benutzt. Differenzschwelle 8 stammt aus der bereits abgeschlossenen Referenzmasken-Untersuchung.

## Verfahren ohne Sollgeometrie als Eingang

Alle vorhandenen Boxen werden gemeinsam in drei Ansichten verglichen. Eine weiche Silhouettenvereinigung misst sowohl zusätzlichen vorhergesagten Vordergrund als auch nicht erklärte Vordergrundfläche. Die Vereinigung berücksichtigt Überdeckung für die binäre Gesamtansicht. Sichtbare 3D-Kanten werden gesondert projiziert; näher liegende vorhergesagte Boxen sperren dahinterliegende Kantenpunkte. Robotermasken schließen bekannte Roboterflächen aus. RGB-Kanten und Konturen der aus Referenzbildern gewonnenen Maske liefern den Bildvergleich.

Optimiert werden Position, Größe und Orientierung mit L-BFGS-B: zunächst Position, danach zwei begrenzte gemeinsame Versuche ab ursprünglicher und verschobener Startlösung. Pro Koordinatenachse höchstens ±20 mm Positionsänderung, Größenfaktor exp(±0,18) und Rotationsvektorkomponenten ±0,175 rad. Das sind Komponentenbegrenzungen, keine Begrenzung des gesamten räumlichen Verschiebungs-/Drehwinkels auf dieselben Zahlen. Die Zielfunktion kombiniert Silhouette, Kantenabstand, Nähe zur Ausgangsschätzung und einfache Strafen für Tischdurchdringung/Boxüberschneidung. Letztere sind keine Stabilitäts- oder Kollisionsfreigabe.

Nur bei mindestens 0,005 Verbesserung der Zielfunktion wird die Kandidatenkorrektur übernommen. Zwei bildlich ähnlich gute Kandidaten mit über 5 mm Positionsunterschied markieren mögliche Mehrdeutigkeit. Diese Markierung ist eine Heuristik, keine Fehlerwahrscheinlichkeit. Die Funktion erhält keine Sollposition, Sollgröße, Sollorientierung oder Objekt-ID. Exakte Geometrie wird erst in `paired_metrics` zur Bewertung gelesen.

Es werden keine Objekte hinzugefügt oder entfernt. Die geometrische Suche ist kein BC-, IL-, RL- oder neuronales Finetuning. Im gesamten Versuch wurden 20.636 geometrische Zielfunktionsauswertungen protokolliert.

## Ergebnis auf 16 neuen Prüfszenen

60 paarweise zugeordnete Objekte. Ihre Sollzuordnung wird vor der Korrektur festgelegt und danach für den Fehlervergleich beibehalten, um eine günstigere Neu-Zuordnung nicht als Verbesserung auszugeben.

| Messgröße | Vorher | Nachher |
| --- | ---: | ---: |
| Mittlerer Positionsfehler | 4,58 mm | 4,72 mm |
| Mittlerer physischer Ecken-RMSE | 7,95 mm | 7,27 mm |
| Größenfehler MAE, sortierte Kantenlängen | 3,01 mm | 2,93 mm |
| Mittlerer Szenen-Recall: erkannt und Position ≤10 mm | 97,5 % | 92,5 % |

15 Objekte werden in der Position um mehr als 1 mm genauer, 24 um mehr als 1 mm schlechter, 21 verändern sich höchstens um 1 mm. In 14 von 16 Prüfszenen wird ein bildlich günstigerer Kandidat übernommen. Zwei Prüfszenen sind als möglicherweise mehrdeutig markiert.

Die gepaarte mittlere Positionsänderung beträgt +0,14 mm, also minimal schlechter. Ein gepaarter Szenen-Bootstrap mit 2.000 Wiederholungen ergibt ein 95%-Perzentilintervall von -1,99 bis +2,03 mm. Ein Positionsvorteil ist nicht belegt. Für die hier berichtete kleine mittlere Verbesserung des Eckenfehlers wurde kein eigenständiger Signifikanznachweis geführt.

| Anordnung · je 4 Prüfszenen | Position vorher | Position nachher |
| --- | ---: | ---: |
| Verstreut | 2,92 mm | 4,19 mm |
| Gemischt | 8,52 mm | 6,83 mm |
| Turm | 3,87 mm | 4,03 mm |
| Wand/Brücke | 3,34 mm | 4,03 mm |

Der 10-mm-Recall wird separat nach der Korrektur neu zugeordnet und pro Szene gemittelt; er ist nicht dasselbe wie ein über alle Objekte gepoolter Anteil. Die primären Fehlerwerte nutzen ausschließlich die vorher festgelegten Paarungen. Größen-MAE nutzt sortierte Kantenlängen und ist nicht unabhängig von der Eckenbewertung zu interpretieren.

## Urteil

Die gemeinsame Reprojektion und begrenzte Korrektursuche funktionieren technisch. Die Zielsetzung „Positionen zuverlässig genauer machen“ wird in diesem Pilot **nicht erreicht**. Ein besserer Bildscore reicht nicht: Größe und Orientierung können denselben Vordergrund auf unterschiedliche Weise erklären, einzelne Turmteile sind teilweise verdeckt und RGB-Referenzmasken enthalten Kontur-/Schattenabweichungen.

Diese Mechanismen sind mögliche Erklärungen, keine kausal getrennten Ursachenbefunde. Die Korrektur wird nicht als Standardausgabe oder Robotersteuerung aktiviert. Die kleine Verbesserung des Eckenfehlers rechtfertigt nicht, die Positionsverschlechterungen zu übergehen.

Sinnvolle nächste Untersuchung wäre ein kontrollierter Vergleich von reiner Positionskorrektur, fixierten Abmessungen und zusätzlicher Ansicht bei mehrdeutigen Fällen. Dafür neue Entwicklungs-/Prüffamilien und vorab festgelegte Übernahmekriterien verwenden; die jetzigen Prüfszenen nicht zur wiederholten Rezeptwahl nutzen. Es wurde kein weiterer Versuch oder Training gestartet.

## Dateien und Reproduktion

- `locked_plan.json`: unveränderte Planung einschließlich Parametergrenzen und Gewichte.
- `observations.npz`: RGB, Referenzen, bekannte Robotermasken und Kamerastrahlen.
- `evaluation_only.npz`: getrennte Sollgeometrie und Sichtbarkeitslabels.
- `seed*_predictions.npz`: eingefrorene Modellausgaben.
- `scene_*.json`: vollständige Vorher-/Nachher-Boxen, Bildkosten und Mehrdeutigkeitsmarkierung.
- `objects.csv`, `scenes.csv`, `results.json`: Messwerte und Checkpoint-Hashes.
- `paired_quality.png`: Vorher-/Nachher-Qualität und Bildkosten.
- `best_worst_examples.png`: größte Positionsverbesserung und größte Verschlechterung, bewusst ausgewählt, keine Zufallsstichprobe.

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_box_refinement.py -q -p no:cacheprovider
& .\praxis\.venv\Scripts\python.exe experiments/vision/visual_scene_v2_20261101/refinement_experiment.py --name refinement_002
```

Bestehende Ergebnisse werden nicht überschrieben. Fünf neue Tests bestanden: Parametergrenzen, Verdeckung, konsistente Projektion, erfolgreiche synthetische Positionskorrektur und leere Vorhersage. Kein Hardwaretest und keine Behauptung realer Montagefähigkeit.
