# Datenvertrag für Wunschaufnahmen · Entwurf V3

## Unveränderliche Schlüssel

`family_id → episode_id → scene_revision → observation_id`. Ein Aufnahmeauftrag ergänzt `request_id` und optional `candidate_id`. Diese IDs sind unabhängig von den fünf austauschbaren Netzausgabeslots. `target_track_ids` sind vorhergesagte zeitliche Zuordnungen, keine unbekannten Simulations-Objekt-IDs. Ein unsicherer Szenenbereich kann ohne Objekttrack über `target_scope=scene` angesprochen werden.

Alle Ansichten derselben Familie bleiben im selben Datensplit. Ein Kandidatenbild darf erst nach einer protokollierten Aufnahme Teil eines Beobachtungskontexts werden. Für vorab gerenderte Trainingskandidaten werden anfänglicher Kontext und zukünftiger Kandidateninhalt strikt getrennt gespeichert.

## Operationaler Bereich

```text
observations/<observation_id>/rgb.png
observations/<observation_id>/camera.json
observations/<observation_id>/robot_state.json
observations/<observation_id>/known_robot_mask.png       optional
observations/<observation_id>/empty_reference.png         optional
calibration/<calibration_id>.json
requests/capture_requests.jsonl
contexts/<context_id>.json
```

`camera.json` enthält tatsächliche optische Pose im Roboterbasissystem, Intrinsik, Bildabmessungen, Zeit, Modell-/Kalibrierungsrevision und Szenenrevision. `calibration/<id>.json` muss die zugehörigen unveränderlichen Basis-/Welt- und EE-/Kamera-Transformationen auflösen; eine bloße Zeichenkette ohne auflösbare Kalibrierung ist für einen echten Datensatz unzureichend. Die bekannte Roboterpose wird je Aufnahme gespeichert, nicht pauschal für eine gesamte bewegte Episode angenommen.

`capture_requests.jsonl` enthält sowohl negative Entscheidungen als auch konkrete Aufträge. Entscheidungen speichern Bedarf, tatsächliche Anforderung, Anlass und optional Bedarfswahrscheinlichkeit, erwarteten Nettogewinn und Kandidaten-ID. Aufträge speichern die Wunschpose sofort. Weitere Datensätze ergänzen Planpose, Gelenkwinkel, Istpose, neues Bild und Auswertung. Die Wunschpose wird nicht durch nachfolgende Zustände überschrieben.

Ein Plan protokolliert seinen Backend ausdrücklich: `sim_reference`, `visual_verified` oder `known_static_and_visual`. Ein Simulations-Referenzplan darf nicht als Nachweis eines tatsächlich visuell belegten Freiraums umgedeutet werden. Unbekannte Sollobjekt-Abstände werden nicht zu Merkmalen des Kandidatennetzes.

Die Einheiten sind Meter und Radiant. Quaternionen sind w,x,y,z; optische Kameraachsen sind +X rechts, +Y unten, +Z nach vorn. `T_base_camera` bildet optische Kamerakoordinaten nach `robot_base` ab. Die Montage `T_EE_camera` bildet optische Kamerakoordinaten nach EE ab. Daraus folgt `T_base_EE = T_base_camera · inverse(T_EE_camera)`.

Ein Bilddatensatz enthält die tatsächliche Kamerapose auch dann, wenn die Wunschpose verfehlt wurde. Diese Aufnahme kann ein gültiges RGB-Beispiel sein, aber kein korrekt ausgeführtes Beispiel für eine andere Wunschpose. Kameraposen ohne explizite Bezugssysteme oder mit geänderter, nicht neu validierter Kalibrierung werden nicht stillschweigend gleichgesetzt.

## Getrennte Trainings-/Auswertungslabels

```text
oracle/<episode_id>/object_geometry.json
oracle/<observation_id>/visible_instance_ids.png
oracle/<observation_id>/visibility.json
labels/<perception_revision>/<context_id>/candidate_gains.json
```

Diese Dateien sind Labels beziehungsweise Qualitätsauswertungen und keine Features des Anforderungsmodells. Kandidatengewinne werden je eingefrorener Wahrnehmungsrevision berechnet. Ein besserer Geometrie-Sollfehler darf nicht als Laufzeitmerkmal erscheinen. Fehlgeschlagene Aufnahmen haben einen Fehlerstatus und kein erfundenes Null- oder Erfolgslabel.

Die Render-/Trainingspipeline muss den Datenvertrag noch umsetzen. Der vorliegende Journalprototyp prüft IDs, Zustandsfolge, Poseformat und Versionsbezüge. Er kontrolliert weder, ob ein Bildpfad tatsächlich auf ein Kamerabild zeigt, noch ob ein Planreferenz wirklich kollisionsfrei ist. Das sind Pflichten des späteren Aufnahmetreibers beziehungsweise Planers. Er sendet keine Bewegungsbefehle.

## Beispielstatus

`example/capture_requests.jsonl` ist ausdrücklich synthetisch. Die erste Entscheidung verlangt kein Bild. Der folgende konkrete Wunschauftrag besitzt eine Pose, wird aber mangels validierter Bahn blockiert. Es gibt darin keinen gefälschten Bildpfad oder eine als tatsächlich erreicht ausgegebene Pose. Der spätere automatische Trainer darf dieses Verzeichnis nicht als echte Aufnahmeepisoden einlesen.
