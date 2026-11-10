# Aktive Handkamera: Planungsprototyp ohne Training

Stand: 2026-11-01. Es wurde kein Training gestartet und kein Optimizer ausgeführt.
Die vorhandenen Vision-Modelle und deren Checkpoints werden nicht verändert.

## 1. Freier Raum für den gesamten Arm

Implementierung: `praxis/src/active_view/collision.py`, `geometry.py`, `visual_map.py`.

Der freie Raum wird als Menge zulässiger **gemeinsamer Sieben-Gelenk-Konfigurationen** geprüft. Unabhängige erlaubte Winkelintervalle je Gelenk würden nicht ausreichen: Zwei einzeln erlaubte Gelenkwinkel können zusammen eine Kollision verursachen.

- Panda-Kollisionsgeometrien als konvexe Hüllen; Finger bleiben in ihrer aktuellen Stellung fixiert, werden geometrisch aber mitgeprüft.
- Kameragehäuse und Halterung als zusätzliche Volumenproxies. Insgesamt 15 Kollisionskörper und 81 zu prüfende Selbstkollisionspaare in dieser Szene. Direkte mechanische Verbindungen haben explizite Ausnahmen.
- Gelenkgrenzen, Selbstkollisionen, Tisch, Umgebung, Kartenränder und unbekannter Raum werden geprüft. Abstände: 10 mm zur Umgebung, 2 mm bei Selbstkollisionen. Diese Werte sind Prototyp-Parameter, keine am realen Roboter validierten Sicherheitsabstände.
- Eine Bahn wird entlang des gesamten linearen Gelenksegments anhand konservativer Abstandsschranken und Bewegungsgrenzen adaptiv geprüft. Freie Endpunkte oder eine feste dünne Stichprobe reichen nicht zur Freigabe. Nicht nachweisbar freie Segmente werden verworfen.
- Eine visuelle Karte enthält freie, möglicherweise belegte und unbekannte Voxel. Beide letzten Zustände sind für die Bewegung gesperrt. Veraltete oder geänderte Karten erfordern einen Stopp beziehungsweise Neuplanung.

Die visuelle Schnittstelle bekommt RGB-Masken, Kamerakalibrierung und metrische Sichtstrahlgrenzen zum bekannten Hintergrund; sie erhält keine Objektpositionen oder Objektgeometrien. Nur vollständig durch Hintergrundbeobachtungen belegte Voxel werden freigegeben.

**Grenze des Bildverfahrens:** Hintergrunddifferenzen sind kein zuverlässiger Sicherheitsdetektor. Gleich aussehende, transparente oder verdeckte Hindernisse können unentdeckt bleiben. Die Kollisionsaussage gilt nur relativ zur eingegebenen Geometrie und korrekt belegten Karte.

## 2. Nützliche Kameraposition auswählen

Implementierung: `praxis/src/active_view/planner.py`.

Um einen angegebenen unsicheren Zielbereich werden Kameraposen vorgeschlagen. Inverse Kinematik, Ganzarmprüfung, Sichtfeld und freie Sichtlinie filtern die Vorschläge. Bewertet werden neue Blickrichtung, Entfernung, Abstand zu Hindernissen und Gelenkbewegung. Erst eine erreichbare Pose mit geprüfter Bahn wird ausgewählt.

Das ist eine geometrische Heuristik für erwarteten Informationsgewinn. Eine tatsächliche Verbesserung der Objekterkennung durch das neue Bild wurde noch nicht gemessen. Der Zielbereich wird in dieser Demo vorgegeben; eine automatische Anbindung an die Unsicherheit des Vision-Modells ist noch offen.

## 3. Bahn und Bildaufnahme

Direkte Verbindung, begrenzte Umwegsuche und anschließend begrenztes bidirektionales RRT-Connect suchen im Gelenkraum. Jede Verbindung und jede Abkürzung durchlaufen dieselbe Bahnprüfung. Ein quintisches Zeitprofil begrenzt die vorgesehenen Gelenkgeschwindigkeiten und -beschleunigungen. Vor jedem Simulationsschritt wird erneut geprüft; Bilder werden über einen Aufnahme-Callback erzeugt.

Die Ausführung ist **kinematische Simulation**. Es gibt keinen Hardwaretreiber, keinen Drehmomentregler und keine Behandlung realer Nachführfehler oder Bremswege. Für bewegte Hindernisse fehlen laufende Sensorintegration und eine entsprechende Echtzeit-Stoppstrategie.

## Nachgewiesener Stand

Ergebnisdatei: `reference_demo_002/report.json`.

| Prüfung | Ergebnis |
| --- | --- |
| Trainingsstart / Optimizer-Updates | nein / 0 |
| Geometrisch zulässige Blickkandidaten | 15 |
| Ausgewählte Bahn | 2 Wegpunkte, 100 Wiedergabeschritte |
| Kollisionsprüfungen | 1.150 |
| Anfangs-Abstandsschranke nach Margen | 19,69 mm |
| Native MuJoCo-Roboter-Umwelt-Durchdringungen bei Wiedergabe | 0 |
| Visuelle Karte | 4.385 freie, 159 möglicherweise belegte, 32.696 unbekannte Zellen |
| Start im visuellen Modus | verweigert: unbekannter Raum bei `robot0_link0_collision` |

Die erfolgreiche Fahrt verwendet ausdrücklich **Simulations-Referenzgeometrie**. Der visuelle Versuch ist separat und schaltet bei Ablehnung nicht auf diese Referenz um. Ein vollständig kamerabasierter autonomer Ablauf ist damit noch nicht nachgewiesen.

Für den visuellen Versuch wurden drei echte Renderer-RGB-Bilder und zuvor aufgenommene leere Referenzbilder verglichen. Hintergrundtiefe und Robotermaske stammen in diesem Diagnoseaufbau aus der Simulation. Sie sind bekannte Kalibrierungsdaten, keine aus RGB geschätzten Größen. Eine reale Installation muss diese Größen durch vermessene feste Umgebung, kalibrierte Mehrbildgeometrie oder ein anderes geprüftes Verfahren bereitstellen. Unbekannte Objektgeometrien müssen dafür nicht in den Simulator übertragen werden.

14 Regressionstests bestanden. Darunter: Hindernis am Ellbogen trotz freier Kamera, Hindernis am Kameragehäuse, Kollision zwischen freien Bahnendpunkten, geprüfter Umweg, gesperrter unbekannter Raum, veraltete/geänderte Karte und Geschwindigkeits-/Beschleunigungsgrenzen.

Artefakte: `before.png`, `after.png`, `motion.gif`, `trajectory.json`, `path.npz`, `visual_observation.png`, `empty_reference.png`, `visual_map.npz` im Ergebnisordner.

## Ausführen

Aus dem Repository mit der vorhandenen Python-/MuJoCo-/robosuite-Umgebung:

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_active_view.py -q
& .\praxis\.venv\Scripts\python.exe experiments/camera_planning/active_view_20261101/demo.py --name reference_demo_003
```

Die Demo legt einen neuen Ergebnisordner an; bestehende Ergebnisordner werden nicht überschrieben. Beide Befehle führen kein Modelltraining aus.

## Nächster Schritt ohne Training

Zuerst kalibrierte feste Umgebungsgeometrie und zusätzliche feste Kameras so einbinden, dass die initiale Ganzarm-Konfiguration und ein Bewegungskorridor tatsächlich visuell belegt sind. Ein bekanntes Montagevolumen braucht eine explizite, vermessene Behandlung. Unbekannte Bereiche dürfen nicht pauschal freigegeben werden. Danach den vollständigen Ablauf mit ausschließlich dieser Karte testen; erst anschließend Unsicherheit und erneute Vorhersage des Vision-Modells anbinden und den gemessenen Nutzen der Zusatzbilder auswerten.
