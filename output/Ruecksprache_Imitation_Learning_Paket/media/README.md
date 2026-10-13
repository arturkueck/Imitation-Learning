# Medien für die erste Rücksprache

Erstellt am 12. Oktober 2026. Alle Dateien sind lokal erzeugt; es wurde kein Modell trainiert und keine neue Simulation ausgeführt.

## Dateien und Verwendung

- `01_sensor_vs_state.png`: Konzeptgrafik (1800 × 1120 Pixel). Links ändert sich nur die gemessene Greiferposition, rechts der reale Zustand. Die grünen Pfeile zeigen idealisierte gewünschte Aktionen. Sie sind keine gemessenen Modellausgaben. Die eingezeichnete Invarianz ist das Lernziel bei irrelevanten Messfehlern, keine Aussage über beliebige Sensorfehler.
- `02_sensor_vs_state.mp4`: 10 Sekunden, 10 Bilder/s, 1440 × 900 Pixel, H.264; dieselbe Unterscheidung als schematische Animation. Sichtbar beschriftet mit „Schematische Illustration – keine Versuchsdaten“. Die eingezeichnete Rückkehr zur Referenz demonstriert das Lernziel und keine Leistungsfähigkeit eines trainierten Modells.
- `02_sensor_vs_state.gif`: Endlosschleife derselben 10-Sekunden-Animation, 100 ms pro Bild (= 10 Bilder/s).
- `02_animation_storyboard.png`: Tatsächliche Frames aus der Animation zu t = 0, 3 und 5,5 Sekunden, zur visuellen Prüfung und als statische Alternative.
- `03_historical_lift_seeds.png`: Historische lokale nominale Lift-Ergebnisse für alle drei Trainingsseeds, mit identischem Achsenmaßstab von 0 bis 100 %. Es werden absolute Erfolge pro 20 Rollouts ausgewiesen. Drei Linien verbinden die beiden Methoden desselben Trainingsseeds. Gepoolte Zahlen dienen nur der Beschreibung.
- `make_media.py`: Reproduzierbarer Erstellungscode. Benötigt Pillow, NumPy, imageio und imageio-ffmpeg; ausführbar mit der vorhandenen `praxis/.venv/Scripts/python.exe`.
- `qa_video_frame_3s.png`: Aus dem fertigen MP4 zurückgelesenes Einzelbild bei t = 3 Sekunden. Beide statischen Abbildungen und die Animation wurden visuell geprüft; MP4-Metadaten bestätigen 10,0 Sekunden bei 10 Bildern/s, die GIF-Datei enthält 100 Frames à 100 ms.
- `04_stack_erfolg.mp4` und `05_stack_misserfolg.mp4`: Kleine, byteidentische Kopien ausgewählter vorhandener Stack-Replays (8,25 bzw. 27 Sekunden). Der Unterordner enthält außerdem Coverbilder, Storyboards und `replay_manifest.json` mit Originalpfaden, Hashes und Ergebnisfeldern. Die Auswahl illustriert Erfolg/Misserfolg verschiedener Startzustände, keinen Benchmarkvergleich. Das Erfolgsbeispiel erfüllt das gespeicherte Stack-Kriterium, wird aber zugleich als vorzeitiger Transport eingeordnet. Details und Vortragsregie stehen in `../Medien_und_Quellen.md`.

## Daten und Grenzen der Interpretation

Die historischen Ergebnisse stammen ausschließlich aus `praxis/reports/lift_ph_full_100ep_summary.json` (SHA-256: `36d54a96b4d401b07a7eb55211d5ded1e98f2b7419194f128728bf44d3211197`). Nominale Werte: Seed 1 BC 16/20, frühere Erweiterung 18/20; Seed 2 15/20 und 20/20; Seed 3 13/20 und 18/20. Summe: 44/60 und 56/60. Die Trainingskonfiguration `praxis/configs/lift_ph_bc_contraction_w1e100_seed1.json` enthält 100 Epochen mit 100 Updates pro Epoche. Die Verfahrensbeschreibung steht in `praxis/README.md`.

Diese Abbildung zeigt die **frühere lokale Erweiterung**, nicht die noch untrainierte neue Loss-Variante. Ein Ergebnisunterschied beweist weder einen kausalen Dynamikmechanismus noch Stabilität. Die drei Trainingsseeds werden einzeln gezeigt; die 60 Test-Rollouts sind keine 60 unabhängigen Trainingswiederholungen. Es wird keine Signifikanz behauptet. Die Vorarbeit motiviert eine kontrollierte Untersuchung; sie ist nicht deren Ergebnis.

Die Konzeptgrafik und Animation sind eigene schematische Zeichnungen ohne externe Bildvorlagen. Die Datenabbildung verwendet lokale Vorarbeiten. Die wissenschaftliche Literaturzuordnung gehört in das zugehörige Gesprächsdokument; die Medien treffen keine Neuheitsbehauptung.
