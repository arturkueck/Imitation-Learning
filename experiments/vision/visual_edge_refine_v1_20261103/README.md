# RGB-Bildfolge, Kantentracking und geometrische Verfeinerung

Getrennter Entwicklungsversuch vom03.11.2026. Kein neuronales Training, kein Zugriff auf Endtestdaten, keine realen Roboterbewegungen. Das eingefrorene V4-B-Ensemble aus `visual_side_v4_20261102/pilot_001/perception_freeze.json` bleibt unverändert. Keine Erweiterung der Kollisionsprüfung: die vorhandene Simulatorreferenz und bereits geprüften Routen werden für die Bildaufnahme weiterbenutzt.

## Ablauf

1. Neue Entwicklungsfamilien bekommen einen bislang unbenutzten Seed-Namensraum. Historischer Familien-/RGB-/Geometrieindex und das gemeinsame transaktionale Register verhindern Datenüberschneidungen. Die neuen Familien sind keine Trainings- oder Endtestdaten.
2. Das B-Ensemble liefert die erste Quaderhypothese. Erkannt werden Konsensobjekte aus mindestens zwei der drei Seeds, maximal fünf. Es gibt kein CAD-Modell oder GT-Objektzählung als Eingabe. Fehlende Erkennungen können durch diese geometrische Stufe derzeit nicht hinzugefügt werden.
3. Eine vorhandene zulässige Seitenroute wird gewählt, ohne ihre spätere Erkennungsqualität zu kennen. Die Gelenkroute wird mit40 Stützstellen abgetastet. Pro Bild werden RGB320×320, tatsächliche Kamerapose, Intrinsik und Gelenkstellung gespeichert. Es sind statische Szenen mit scharfen Simulatorbildern und exakter Kinematik; reale Bewegungsunschärfe, Zeitstempelversatz und Kalibrierfehler sind noch nicht modelliert. Die GIF-Abspielgeschwindigkeit ist keine reale Fahrgeschwindigkeit.
4. Kantennahe Eckpunkte werden mit Lucas-Kanade verfolgt. Vorwärts-/Rückwärtsprüfung und Helligkeitsvergleich lokaler5×5-Patches verwerfen unzuverlässige Tracks. Neue Punkte werden nur in Bildregionen um projizierte, vorhergesagte Objektkanten initialisiert. Kein Simulator-Segmentierungsbild dient als Trackingmaske.
5. Mindestens drei Beobachtungen und1,5° Parallaxe sind für einen triangulierten Punkt nötig. Schlechte Kondition, negative Tiefe und Reprojektionsfehler über2 Pixel werden verworfen. Bekannte Kameraposen geben den metrischen Maßstab vor.
6. Je Quader werden neun Parameter angepasst: Position3, Rotation3 und logarithmische Seitenlängen3. Robuste kleinste Quadrate gleichen projizierte Kanten mit RGB-Kanten und triangulierte Punkte mit der Quaderoberfläche ab. Vorhersagebasierte Verdeckungen und eine Bindung an die Anfangsschätzung begrenzen Fehlanpassungen. Das ist keine vollständige Photogrammetrie/MVS-Rekonstruktion beliebiger Objektformen. Photometrie dient hier der Trackprüfung, nicht einer dichten photometrischen Optimierung.
7. Kandidat und Übernahme werden getrennt gespeichert. Alle Bilder mit Index modulo3 gleich0 (außer Anfangsbild) bleiben aus Tracking, Triangulation und Anpassung ausgeschlossen. Nur der Übernahme-Gate liest sie. Er verlangt mindestens5 % und0,05 Pixel Verbesserung bei unveränderter anfänglicher Kantenstützmenge und höchstens0,25 Pixel Verschlechterung in den ursprünglichen drei Ansichten. Mindestens sechs triangulierte Punkte, drei Anpassungs-/drei Prüfansichten und erfolgreiche Optimierung sind erforderlich. Veränderungen sind begrenzt: pro Positionsachse15 mm, pro Rotationsvektorkomponente10°, Seitenlängen ungefähr±15 %; zur Übernahme zusätzlich maximal15 mm Gesamtverschiebung. Eine verworfene Aktualisierung lässt die Anfangsschätzung unverändert.

Die Prüfansichten stammen aus derselben neuen Szene: sie sind ein RGB-Konsistenz-Gate, **kein unabhängiger Endtest und keine Verbesserungsgarantie**. Das Kantenmaß besitzt Mehrdeutigkeiten; auch ein akzeptierter Kandidat kann geometrisch falsch sein. Die ursprünglichen drei Ansichten waren bereits Eingabe des Vision-Modells, werden aber nicht zur geometrischen Anpassung verwendet.

## Auswertung und Dateien

Erst nach der Übernahmeentscheidung nutzt die Auswertung echte Simulatorobjekte. Vier Verfahren werden auf derselben vollständigen aktiven GT-Objektmenge verglichen:

- erste B-Ensemble-Schätzung;
- bisherige neuronale Fusion mit einem zusätzlichen Endbild;
- ungefilterter geometrischer Kandidat;
- tatsächlich übernommene Geometrie einschließlich abgelehnter Updates.

`results.json` enthält Szenenfehler inklusive FP/FN, Positionsabstände zugeordneter Objekte, Ablehnungsgründe und Trackingzahlen. `comparison.png` vergleicht die Verfahren. Pro Szene unter `development/scene_XXXX/`:

- `sample.npz`: unveränderte Ausgangs-/Endansichten und ausschließlich für Auswertung gespeicherte GT-Labels;
- `sequence.npz`, `cameras.json`: tatsächliche Bildfolge, Gelenkstellungen und Kameraposen;
- `tracks.json`: 2D-Tracks und akzeptierte triangulierte Punkte;
- `result.json`: Kandidaten, Übernahme-Gate und erst danach berechnete GT-Metriken;
- `tracking.gif`, `sequence.png`: Kamerafolge mit vorhergesagten Kanten und ausschließlich Anpassungs-Tracks;
- `comparison.png`, `scene.json`: Cyan=Simulator, Orange=erste Schätzung, Grün=übernommene Geometrie.

Die Daten- und Checkpointhashes werden dokumentiert. Das Modell erhält weiterhin nur seine vorgesehenen RGB-/Strahl-/Maskeneingaben; die neue Geometriestufe erhält RGB, Kamerakalibrierung und Vorhersagen. Echte Objektpositionen und Simulatorsegmentierungen fließen nicht in deren Optimierer oder Gate.

## Start

Aus dem Repository-Root:

```powershell
praxis/.venv/Scripts/python.exe -m pytest experiments/vision/visual_edge_refine_v1_20261103/test_geometry.py -q -p no:cacheprovider --basetemp experiments/vision/visual_edge_refine_v1_20261103/test_tmp
praxis/.venv/Scripts/python.exe experiments/vision/visual_edge_refine_v1_20261103/run.py --run smoke_003 --scenes 4 --frames 40
```

Ein vorhandener Ausgabeordner wird nicht überschrieben. Für weitere Diagnosen neuen Namen wählen. Der CLI ist auf1–16 Entwicklungsszenen und16–80 Bilder begrenzt. Sechs Tests prüfen metrische Projektion/Triangulation, fehlende Parallaxe, synthetische Verfeinerung, Ausschluss der Prüf-RGBs aus Fit/Tracks, Ablehnung ohne Evidenz und unveränderte Routenendpunkte. Die Untersuchung verbessert noch keine aktive Aufnahmepolitik und ersetzt keine Kollisions- oder reale Sicherheitsprüfung.
