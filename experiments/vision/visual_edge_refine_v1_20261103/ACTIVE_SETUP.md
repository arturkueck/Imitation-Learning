# Zentrierte ein-/zweiseitige Aufnahme

Neuer Einstieg: `run_active.py`. Das bisherige `run.py` und seine aufgenommenen Versuche bleiben als einfacher Vergleich erhalten. Kein neuronales Training, keine reale Roboterbewegung und kein neuer Kollisionsbackend. Vorhandene IK-/Gelenk-/Pfadprüfungen werden weiterbenutzt; nach Änderung der Kameraausrichtung werden die alten Routen ausdrücklich nicht ungeprüft übernommen.

## Zielpunkt und Kamerafahrt

Die erste Drei-Kamera-Aufnahme des eingefrorenen B-Ensembles liefert Quaderhypothesen und Seed-Abweichungen. Der Zielpunkt ist die Mitte ihrer räumlichen Ausdehnung; die bekannte Tischhöhe0,8 m begrenzt die untere Ausdehnung. Es werden keine echten Objektpositionen zum Anvisieren verwendet. Die gesamte vorhergesagte Gruppe muss mit Bildrandabstand ins Kamerabild passen.

Zunächst richtet der Arm die Kamera auf diesen Punkt aus. Die dabei erreichte Gelenkpose wird als gemeinsame **Schwenk-Startpose** gespeichert. Danach folgen gerichtete Kamerabögen mit festem Zielpunkt und tatsächlicher IK für die montierte Kamera. Jede Seite versucht28°, bei nicht erreichbarer vollständiger Bahn20° und14°; mindestens8 cm Baseline und maximal1,5° Zielabweichung an aufgenommenen Stützstellen. Alle vorhergesagten Objekte müssen im Bild bleiben. Die Rollorientierung wird stetig von der vorherigen Kamerapose übertragen.

Nach jedem Schwenk fährt die exakt umgekehrte Gelenkroute zurück zur gespeicherten Schwenk-Startpose. Wird die zweite Seite angefordert, folgt erst danach der entgegengesetzte Bogen und wieder der Rückweg. Am Ende wird auch die ursprüngliche Pose vor der anfänglichen Ausrichtung wiederhergestellt. Ausrichtung und Wiederherstellung sind in den Bildern als eigene Phasen markiert; die Zentrierbedingung gilt für die ausgerichteten Schwenks und deren Rückwege. Die Bildfolge ist eine Simulation ohne Bewegungsunschärfe und keine ausgeführte Echtzeit-Robotertrajektorie.

## Noch regelbasierte Aufnahmeentscheidung

Die Steuerung ist **nicht gelernt oder probabilistisch kalibriert**. Zu Beginn fordern mindestens3 Konsensobjekte, projizierte Überdeckung über25 %, Ensemble-Streuung über4 mm oder unvollständiger Seed-Konsens zwei Seiten an. Ansonsten wird eine Seite angefordert. Nur ein einzelnes besonders konsistentes Objekt kann ohne Schwenk bleiben. Ohne Konsensobjekte wird kein vermeintlich zuverlässiger Zielpunkt erfunden; der Zustand bleibt unsicher.

Die erste Seite wird nach der erwarteten Sichtbarkeit der geschätzten Objektkanten gewählt. Es werden dafür keine zukünftigen Seitenbilder gerendert oder ausgewertet. Erst nach dem ersten tatsächlichen Schwenk wird erneut entschieden: Wenn bereits zwei Seiten angefordert waren oder die erste Seite nicht genügend geometrische Unterstützung liefert, folgt die Gegenseite. Es gibt höchstens zwei Seiten und keine wiederholte Auswahl derselben Seite. Unerreichbare Richtungen werden samt Grund gespeichert.

Geometrische Unterstützung verlangt pro Objekt mindestens6 räumlich unterschiedliche triangulierte Punkte und höchstens1,5 Pixel Prüf-Kantenfehler. Wiedererfasste Punkte innerhalb2 mm zählen nicht mehrfach. Alle Regeln, Bildmengen und Gründe werden gespeichert. Wenn auch zwei Seiten nicht reichen oder die Gegenseite nicht erreichbar ist, lautet das Ergebnis `still_uncertain`. `supported_by_acquired_views` bedeutet lediglich geometrische RGB-Konsistenz, keine Garantie einer korrekten oder vollständigen Erkennung.

## Bilder und Daten für spätere Entscheidungen

`decisions.json` protokolliert Anfangsmerkmale, Wunschrichtung, Planungsfehler, erste tatsächliche Qualität und Zweitseitenentscheidung. `motion.json` enthält tatsächliche Gelenk-/Kameraposen, Phasen und Aufnahmeindizes. `result.json` enthält Fokussierung, Rückkehrfehler, aufgenommene Seiten und verbleibende Unsicherheit. Damit sind Eingaben und Entscheidungen für ein späteres Aufnahmebedarf-Modell vorhanden; Trainingslabels und ein solcher Trainer werden hier noch nicht erzeugt.

Nur die tatsächlich aufgenommenen Hinweg-Bilder gehen in Tracking/Geometrie ein. Rückweg-Bilder dienen dem Bewegungsnachweis und werden nicht als neue unabhängige Beobachtungen gezählt. Jede dritte Hinweg-Aufnahme bleibt aus Tracking und Anpassung ausgeschlossen und dient nur dem Übernahme-Gate. Nach einer zweiten Seite wird gegen die zuletzt übernommene Geometrie geprüft; Gesamtverschiebung und Konsistenz mit den ursprünglichen Bildern bleiben begrenzt. Die Simulatorobjekte werden erst nach allen Entscheidungen zur Bewertung geöffnet.

Neue Familien bleiben ausschließlich Entwicklung; alte Trainings-/Validierungs-/Endtestdaten werden weder umgeteilt noch überschrieben. Das B-Ensemble ist eingefroren. Ausgewertet werden erste Schätzung, neuronale Fusion der tatsächlich aufgenommenen Endbilder, ungefilterte und übernommene Geometrie. Der bisherige Szenenfehler umfasst Geometrie und Zählfehler und ist keine Roboter-Platziergenauigkeit.

## Befehle

```powershell
praxis/.venv/Scripts/python.exe -m pytest experiments/vision/visual_edge_refine_v1_20261103/test_geometry.py experiments/vision/visual_edge_refine_v1_20261103/test_active.py -q -p no:cacheprovider --basetemp experiments/vision/visual_edge_refine_v1_20261103/test_tmp_active
praxis/.venv/Scripts/python.exe experiments/vision/visual_edge_refine_v1_20261103/run_active.py --run active_smoke_002 --scenes 2 --frames 28
```

Ausgabeordner werden nicht überschrieben. `--frames` zählt die Stützstellen pro Hinweg, nicht den ganzen Versuch. `active_motion.gif` zeigt die tatsächliche Fahrt mit einem roten Kreuz auf dem projizierten festen Zielpunkt und Phasenbeschriftung. `camera_path.png` zeigt die tatsächlichen Kamerapositionen. Die bisherigen Tracking-GIFs und dreifarbigen Geometrieplots werden ebenfalls geschrieben. Die beschrifteten GIFs entstehen automatisch; `active_reporting.py` kann sie auch getrennt aus den gespeicherten Originalbildern erstellen, ohne Vorhersagen oder Entscheidungen zu verändern.

Nach jeder Seite werden Kandidaten, übernommene Geometrie und Tracks separat in `analysis_after_sweep_1.json` beziehungsweise `analysis_after_sweep_2.json` gespeichert. `neural_contexts.npz` bewahrt die exakten tatsächlich verwendeten RGB-/Strahleingaben des neuronalen Vergleichs. Aktuelle Szenen bleiben Entwicklungsmaterial; für späteres Kopftraining sind frische, getrennte Request-Trainingsfamilien nötig.
