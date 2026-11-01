# A: Bildkonsistenzprüfung ohne Training

Stand: 01.11.2026. Kein Training, keine Optimizer-Updates, keine erneute Modellinferenz. Die Auswertung verwendet die gespeicherten Vorhersagen der sechs eingefrorenen Modelle aus `uncertainty_001`. Es werden keine Checkpoints verändert und keine reservierten Testdaten gelesen.

## Was implementiert ist

Die Prüfung erhält ausschließlich RGB-Bilder, die bereits gespeicherten kalibrierten Kamerastrahlen und vorhergesagte Boxen. Objektpositionen, Sollgrößen, Sollorientierungen und Sichtbarkeitslabels werden erst im getrennten Bewertungsteil gelesen.

1. Aus den kalibrierten Strahlen wird die Abbildung Weltkoordinate → Bildpixel rekonstruiert. Die Kameraposition stammt aus dem bereits gespeicherten Strahlenursprung. Der maximale Projektionsrestfehler über die Kalibrierungsgitter wird protokolliert. Das ist ein interner Konsistenztest der gespeicherten Kalibrierung, keine Vermessung realer Kamerafehler.
2. Ray-Box-Schnitte projizieren die vorhergesagten Volumen auf das 160×160-Bild. Ein Tiefenpuffer berücksichtigt, welche vorhergesagte Box eine andere verdeckt. Als erwartete Konturen zählen äußere Silhouetten und sichtbare Wechsel zwischen Boxflächen. Konturen hinter näher liegenden vorhergesagten Objekten werden nicht gefordert.
3. RGB-Kanten werden aus geglätteten Farbgradienten bestimmt. Die Distanz von erwarteten, bildlich prüfbaren Konturen zur nächsten Bildkante liefert einen normierten Konturwiderspruch.
4. Eine zusätzliche Erscheinungsheuristik trennt farbige Vordergrundhinweise, sehr hellen neutralen Hintergrund und unbekannte Pixel. Der Anteil vorhergesagter sichtbarer Boxfläche auf solchem Hintergrund liefert einen zweiten Widerspruch. Beide Anteile werden gleich gewichtet. Es handelt sich nicht um eine präzise Silhouettensegmentierung und nicht um einen IoU-Vergleich mit echten Objektmasken.
5. Sind weniger als zwei Ansichten ausreichend prüfbar, wird die Bildevidenz ausdrücklich als unbekannt ausgegeben. Dieser Zustand darf nicht als geometrische Übereinstimmung interpretiert werden.

## Robotermasken und verdeckte Bereiche

Exakte Robotermasken und Objektmasken sind in diesem Datensatz nicht gespeichert. Die Prüfung verwendet keine nachträglich aus Sollobjektgeometrie erzeugten Masken. Dunkle beziehungsweise neutrale Pixel bleiben überwiegend unbekannt, sodass Roboter, Greifer, Schatten und graue Objekte nicht pauschal als freie Fläche gelten.

Diese Erscheinungsheuristik ist **keine verlässliche Robotermaske**. Farbige Roboterteile, Kanten der Umgebung und sehr helle Objekte können die Bewertung täuschen. Verdeckungen durch nicht vorhergesagte Objekte oder den realen Roboter werden nicht geometrisch aufgelöst. Korrekte Robotermasken aus Gelenkständen/Kinematik und eine robustere Objekt-/Hintergrundsegmentierung sind eigenständige mögliche Verbesserungen; sie wurden hier nicht vorgetäuscht.

## Fairer Vergleich

Verwendet werden dieselben 2.000 bestehenden Validierungsszenen und exakt dieselbe Familienaufteilung wie bei der Ensemble-Diagnose: 1.000 für Kalibrierung, 1.000 für die zurückgehaltene Auswertung. Datenhashes werden gegen den vorherigen Lauf geprüft, aktuelle Vorhersagehashes dokumentiert.

Verglichen werden fünf Ansätze:

- Positionsstreuung zwischen Seeds als bisherige Referenz.
- Streuung physischer Boxecken.
- Streuung sortierter Kantenlängen.
- RGB-Bildkonsistenz einschließlich fehlender Bildevidenz.
- Kombination aus Positionsstreuung und Bildkonsistenz.

Alle Ansätze priorisieren Gruppen mit fehlender Seed-Unterstützung. Die einzelnen Signale werden über ihre empirischen Perzentile auf der Kalibrierungshälfte normiert. Für die Kombination werden vorher festgelegte Bildgewichte 25 %, 50 % und 75 % verglichen. Die Kalibrierung wählt die Variante mit der größten Summe gefundener Fehler bei 5 % und 10 % Zurückstellung; die zurückgehaltenen Fehlerlabels werden dafür nicht benutzt. Dies ist die Auswahl einer Diagnoseheuristik, kein Training eines Modells.

Der Vergleich auf der zurückgehaltenen Hälfte stellt jeweils exakt 5 %, 10 % oder 20 % der Vorhersagegruppen zurück. Die zugehörigen Rangschwellen ergeben sich ohne Fehlerlabels aus der dortigen Scoreverteilung. Das ermöglicht gleiche Prüf-/Aufnahmebudgets, liefert aber noch keine feste Schwelle für einen späteren Betrieb.

## Qualitätskriterien

Primär zählt der Anteil erkannter Fehler bei gleichem Budget. Fehler bedeutet wie bisher: Position mehr als 10 mm daneben oder falsche Zusatzdetektion. Größen- und Orientierungsfehler allein zählen in diesem primären Vergleich noch nicht als Fehler.

Ergebnisse werden zusätzlich getrennt nach Anordnung, nach tatsächlicher Sichtbarkeit und für gemeinsam falsche Vorhersagen mit drei Seeds und höchstens 3 mm Streuung ausgewiesen. Die echte Sichtbarkeit wird nur zur Auswertungs-Stratifizierung verwendet. Fehlende Sollobjekte können durch die Reprojektion vorhandener Boxen weiterhin nicht zuverlässig entdeckt werden.

Für die Verbesserung gegenüber der Referenz wird ein 95%-Perzentilintervall aus 1.000 gepaarten Bootstrap-Stichproben von Szenen berechnet. Objekte derselben Szene bleiben zusammen. Das Intervall ist bedingt auf die ausgewählte Heuristik und die vorhandenen Checkpoints; Unsicherheit aus Rezeptwahl und Checkpoint-Auswahl wird nicht mitgeschätzt.

Da die ursprüngliche Validierung schon zur Checkpoint-Auswahl diente, bleibt die Untersuchung explorativ. Eine unabhängige Prüfung auf neuen Szenen ist weiterhin erforderlich, bevor eine Regel aktiviert werden sollte. Eine gute Bildübereinstimmung belegt weder geometrische Richtigkeit noch kollisionsfreien Raum.

## Artefakte und Reproduktion

- `results.json`: Hauptmetriken, Teilgruppen, Bootstrap-Intervalle und Provenienz.
- `fixed_comparison.png/.svg`, `fixed_wrist_comparison.png/.svg`: Fehlererkennung und verbleibende Fehler bei gleichem Budget sowie tatsächlicher Fehler gegen Bildscore.
- `*_objects.csv`, `*_views.csv`: sämtliche objekt- und ansichtsweisen Diagnosesignale.
- `qualitative_examples.png/.csv`: bewusst ausgewählte zusätzliche Treffer, übersehene Fehler und unnötige Warnungen. Keine repräsentative Zufallsstichprobe. Drahtkanten im Bild zeigen auch verdeckte Flächen; die Bewertung verwendet nur prognostizierte sichtbare Flächen.

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_image_consistency.py praxis/tests/test_ensemble_uncertainty.py -q -p no:cacheprovider
$env:OPENBLAS_NUM_THREADS='4'
$env:OMP_NUM_THREADS='4'
& .\praxis\.venv\Scripts\python.exe experiments/visual_scene_v2_20261101/image_consistency.py --name image_consistency_002
```

Bestehende Ergebnisordner werden nicht überschrieben. 15 Tests bestanden, darunter Kameraprojektion, Tiefenpuffer, verschobene Box, unbekannte Pixel, parallele Strahlen, fehlerhafte Kalibrierung, leere Auswertungsteilgruppen und identische Prüfbudgets.

`source_used.py` ist die per Hash gegen `results.json` geprüfte Quellkopie des tatsächlich ausgeführten Laufs. Die aktuelle Skriptversion ergänzt anschließend nur die Behandlung leerer Auswertungsteilgruppen und entfernt eine unbenutzte Variable; die gemessenen Ergebnisse wurden dadurch nicht verändert.
