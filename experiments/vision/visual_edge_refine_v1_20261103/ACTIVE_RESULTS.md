# Zentrierte ein-/zweiseitige Aufnahme: Funktionsprüfung

Aktueller vollständiger Lauf: `active_smoke_002`. Zwei frische Entwicklungsfamilien95345001/0–1, keine Umteilung historischer Daten und kein Training. Das B-Ensemble bleibt eingefroren. Technischer Vorgängerlauf `active_smoke_001` ist erhalten; der aktuelle Lauf speichert zusätzlich alle Seiten-Zwischenstände und die exakten neuronalen Vergleichseingaben und erzeugt beschriftete GIFs automatisch.

## Steuerung und Fokus

Beide neuen Szenen fordern aufgrund vorhergesagter Überdeckung zwei Seiten an, die erste zusätzlich aufgrund von vier Konsensobjekten. Familie0 beginnt rechts und wechselt nach Rückkehr zur Startpose nach links. Familie1 beginnt links und wechselt nach Rückkehr nach rechts. Die erste Seite wird nur aus vorhergesagter Kantensichtbarkeit gewählt, nicht anhand zukünftiger RGB-Aufnahmen. Beide Schwenks kehren exakt zur gespeicherten Startpose nach der anfänglichen Ausrichtung zurück; anschließend wird die ursprüngliche Pose vor der Ausrichtung wiederhergestellt.

| Familie | Erste Seite | Zweite Seite | Max. gemessene Zielabweichung | Gruppe im Bild, aktive Aufnahmen | Rückkehrfehler, max. Gelenkabweichung |
|---|---|---|---:|---:|---:|
|0|rechts|links|0,0769°|110/110|0|
|1|links|rechts|0,1001°|110/110|0|

Pro Szene122 gespeicherte Kamerabilder einschließlich Ausrichtung/Wiederherstellung. Die110 aktiven Bilder enthalten Hin- und Rückwege; nur die beiden Hinwege dienen der geometrischen Auswertung. Der feste Zielpunkt stammt aus der anfänglichen geschätzten Gruppe und der bekannten Tischhöhe0,8 m. Die Sichtfeldprüfung betrifft vorhergesagte Objekte; sie ist kein Nachweis, dass alle echten, eventuell unerkannten Objekte erfasst sind. Die angegebenen Zielabweichungen wurden an den gespeicherten Kameraposen gemessen.

## Erkennungsqualität bleibt gesondert zu bewerten

Szenenfehler in mm-äquivalent, inklusive Geometrie-/Objektzählfehler, kein reiner Positions- oder Platzierfehler:

| Familie | Anfang | Nach erster geometrischer Anpassung | Nach beiden Seiten, übernommene Geometrie | Neuronale Fusion beider Endbilder | Ergebniszustand |
|---|---:|---:|---:|---:|---|
|0|7,899|10,509|9,670|8,404|weiterhin unsicher|
|1|5,679|1,905|4,075|6,445|durch aufgenommene Ansichten gestützt|

Die GT-Werte pro Seite wurden erst nach Abschluss aller Aufnahmeentscheidungen aus den gespeicherten Zwischenständen berechnet. Sie waren keine Eingaben der Steuerung oder Übernahmeprüfung.

Der Test bestätigt die zentrierte Kameraführung und die Zustandsfolge. Er bestätigt **keine zuverlässige Verbesserung der Rekonstruktion**: In Familie0 verschlechtert die geometrische Korrektur die Anfangsschätzung; die Szene bleibt allerdings ausdrücklich unsicher. In Familie1 helfen beide Seiten gegenüber dem Anfang, aber die zweite Seite verschlechtert die bessere Zwischenlösung nach der ersten Seite. Das RGB-Konsistenzmaß erkennt diese GT-Verschlechterung nicht zuverlässig. Der Gate ist daher keine Qualitätsgarantie und `supported_by_acquired_views` keine kalibrierte Erfolgswahrscheinlichkeit. Eine unsichere Szene darf nicht als freigegebene Grundlage für eine Roboterplatzierung gelten.

In diesen kleinen Fällen wurden keine Regeln nachträglich angepasst. Die beiden Richtungen und der Rückweg funktionieren; eine lernende Aufnahmeentscheidung und eine bessere Bewertung des tatsächlichen Zusatznutzens bleiben getrennte nächste Schritte. Auch eine anfangs angeforderte zweite Seite wird derzeit aufgenommen, wenn die erste Seite schon den Unterstützungstest besteht; diese konservative Regel ist explizit protokolliert, noch nicht gelernt oder auf Kosten/Nutzen optimiert.

## Prüfung

- Elf Tests bestanden: bisherige Geometrie-/Adapterprüfungen plus Null-/Ein-/Zweiseitenentscheidung, Eskalation nach unzureichender erster Seite, Gegenrichtungen und feste optische Achse sowie explizite Unsicherheit.
- Beide vollständigen Simulationsläufe erfolgreich abgeschlossen, kein Optimizer-Update. Die alten Versuche und Checkpoints bleiben erhalten.
- Alle31 registrierten Dateien im aktuellen Lauf, sämtliche enthaltenen Quellcodehashes und die drei B-Startgewichte geprüft.
- Beide Entwicklungsfamilien im gemeinsamen Datenregister verifiziert. Keine Nutzung alter Validierungs-/Endtestfamilien oder zukünftiger Kandidaten-RGBs für Entscheidungen.
- Reservierte Prüf-RGBs und Rückweg-Bilder sind aus Tracking/Anpassung ausgeschlossen. Jede gespeicherte Analyse verwendet ausschließlich Frames vor ihrer zugehörigen Entscheidung.
- Beide Rückkehrtests und die Wiederherstellung der ursprünglichen Gelenkpose stimmen innerhalb1e-8 rad.
- Die neuronalen Vergleichsergebnisse aus `neural_contexts.npz` mit den eingefrorenen Gewichten exakt reproduziert: maximale numerische Abweichung0.
- Kamerapfad und beschriftete Kontaktansichten visuell geprüft. Keine unabhängige virtuelle Kameradrehung, alle Posen entstehen aus der Armkinematik.

## Dateien

Anleitung und Regeln: `ACTIVE_SETUP.md`. Pro Szene unter `active_smoke_002/development/scene_XXXX/`: `decisions.json`, `motion.json`, `analysis_after_sweep_1.json`, `analysis_after_sweep_2.json`, `neural_contexts.npz`, `sequence.npz`, `result.json`, `active_motion.gif`, `camera_path.png`, `tracking.gif`, `comparison.png`.

Dies sind ausschließlich Entwicklungsdaten. Für ein späteres Aufnahmebedarf-Modell müssen neue, getrennte Trainings-/Validierungs-/Kalibrierungsfamilien angelegt werden. Keine Website-Veröffentlichung und keine Erweiterung der Kollisionslogik in diesem Schritt.
