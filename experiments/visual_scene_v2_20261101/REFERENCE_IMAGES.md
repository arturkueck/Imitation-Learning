# Referenzbilder und Robotermasken

Die Erfassung ist in `reference_capture.py` eingerichtet; die auswertbare RGB-Differenzprüfung liegt getrennt in `reference_evidence.py`. Es wird kein Vision-Modell trainiert oder verändert.

## Eingaben der Bildprüfung

- Ursprüngliches RGB-Bild aus dem gespeicherten Validierungsdatensatz.
- Objektfreies RGB-Referenzbild bei derselben Kamera-, Roboter- und Beleuchtungseinstellung.
- Vollständige Robotersilhouette aus der bekannten Robotergeometrie. Sie wird in der objektfreien Szene gerendert, sodass unbekannte Objekte ihre Form nicht beeinflussen.
- Bereits vorhandene Kamerakalibrierung für die Rückprojektion der vorhergesagten Boxen.

Die Bildprüfung erhält weder exakte Objektpositionen noch exakte Objektmasken. Das öffentliche Maskenmodul importiert keinen Simulator. Die nachgelagerte Qualitätsauswertung erhält separat die sichtbaren Objekt-IDs aus der Simulation.

## Erzeugung in der Simulation

Die bestehenden Szenen werden anhand der gespeicherten Familien-Seeds wiederhergestellt. Geometrie und Kamerastrahlen müssen bis auf maximal 1e-7 absolute numerische Abweichung übereinstimmen; diskrete Eigenschaften exakt. Vor der Verwendung der Referenz wird das erneut gerenderte RGB mit dem alten RGB verglichen. Erlaubt sind höchstens 32 einzelne Farbkanalabweichungen von jeweils maximal 1/255 über die drei Bilder einer Szene. Größere Abweichungen brechen ab. Die alten RGB-Eingaben und die gespeicherten Modellvorhersagen werden dabei nicht ersetzt.

Für die Referenzaufnahme werden nur die Rendergruppen der unbekannten Objekte ausgeblendet. Es gibt keinen Physikschritt und keine Änderung an Kamerapose, Roboterpose oder Beleuchtung. Anschließend werden die Rendergruppen auch bei Fehlern wiederhergestellt. Die Referenz enthält weiterhin den Roboter und die feste Umgebung. Die bekannte Robotermaske wird um zwei Pixel erweitert, um unsichere Randpixel auszuschließen.

Ein neues Bild aus einer veränderten Handkamerapose benötigt eine zu dieser Pose passende Referenz. Die jetzige Simulation kann diese direkt erzeugen. Dasselbe Vorgehen ist nicht automatisch als reale Lösung für beliebig wechselnde Handkameraposen verfügbar.

## RGB-Differenzmasken und Qualitätsmessung

Die Farbdifferenz zum Referenzbild wird geschwellt, kleine isolierte Komponenten werden entfernt und geschlossene Konturen gefüllt. Das kann auch graue Objekte und helle Objektflächen berücksichtigen, ohne alle hellen Pixel als Tisch anzunehmen. Tatsächlich identische, vollständig kontrastlose Bereiche bleiben grundsätzlich mehrdeutig. Schatten können zusätzliche Vordergrundpixel erzeugen.

Vier vorab festgelegte Farbdifferenzschwellen (8, 16, 24, 32 in RGB-Normeinheiten) werden auf der Kalibrierungshälfte bewertet. Der beste mittlere IoU auf nichtleeren Ansichten bestimmt die Schwelle für die zurückgehaltene Hälfte. Die exakten Simulationsmasken werden somit zur Offline-Kalibrierung und Qualitätsmessung verwendet, niemals als Eingabe der späteren Maskenerzeugung. Das ist keine garantierte Fehlerquote und kein neuronales Training.

Gemessen werden mittlerer IoU pro nichtleerer Ansicht, gepoolter IoU, Präzision, Recall und Fehlalarme auf objektleeren Ansichten. Die bekannten Roboterbereiche werden in Vorhersage und Sollmaske identisch ausgeschlossen; ausgeschlossene Sollobjektpixel werden separat ausgewiesen. Die Bildmasken sind binärer Vordergrund, keine Objekt-Instanzsegmentierung.

Zusätzlich wird wie zuvor gemessen, ob die neuen Bildbelege die Positionsfehler der unveränderten Vision-Vorhersagen besser markieren. Ensemble und Bildverfahren werden bei identischen Zurückstellungsbudgets verglichen. Die Familienaufteilung bleibt gleich. Die zurückgehaltenen bisherigen Validierungsdaten sind bereits mehrfach untersucht worden: Auch dieses Ergebnis ist ein Entwicklungsvergleich, keine unabhängige Schlussprüfung.

Diese Masken dürfen nicht als Nachweis freien Raums oder als Freigabe einer Roboterbewegung verwendet werden. Sie enthalten keine metrische Tiefe und können Schatten beziehungsweise verdeckte Objekte falsch behandeln.

## Ausführen

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_reference_evidence.py praxis/tests/test_image_consistency.py praxis/tests/test_ensemble_uncertainty.py -q -p no:cacheprovider
& .\praxis\.venv\Scripts\python.exe experiments/visual_scene_v2_20261101/reference_capture.py --name reference_consistency_003
```

Bestehende Ausgaben bleiben erhalten. Der erfolgreiche kleine Probelauf liegt unter `reference_preflight_002`. Die ersten abgebrochenen Versuche bleiben mit Logs nachvollziehbar: zunächst eine numerische Rotationsabweichung von etwa 1e-14, danach ein einzelner Farbkanal mit einer Abweichung von 1/255. Daraufhin wurden die oben dokumentierten engen Reproduktionstoleranzen eingeführt. Die ursprünglichen Trainingsdaten und Checkpoints wurden nicht verändert.

Der vollständige erfolgreiche Lauf liegt unter `reference_consistency_002`; sein `README.md` enthält die Qualitätszahlen. Das Verzeichnis `observations` enthält nur Referenzen, bekannte Roboter-/Kamerainformationen und aus RGB abgeleitete Masken. Der zuerst zur Diagnose mitgespeicherte vollständige Szenenzustand wurde ohne Neuberechnung der Scores nach `evaluation_only` verschoben; im Eingabebereich verbleiben ausschließlich die neun Panda-/Greifergelenkpositionen. `separate_robot_state.py` und der ursprüngliche Ergebnisbericht dokumentieren diese reine Speichertrennung. Die aktuelle Erfassungsfunktion speichert direkt nur den Roboterzustand. Das Maskenmodul liest keinerlei Gelenk- oder Objektzustände.
