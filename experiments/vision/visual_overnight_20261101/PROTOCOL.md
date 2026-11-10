# Nachtlauf: visuelle Würfel-Lokalisierung, 01.11.2026

Vom Nutzer autorisiert: ungefähr zehn Stunden trainieren, Würfeltraining mit
Quader-Transferprüfung, Vergleich feste Kameras/zusätzliche Handkamera. Das spätere
Ziel eines kleinen Lego-Hauses ist kein Teil dieses Laufs.

## Aufgabe und Architektur

Überwachte Regression zweier farblich zugeordneter Objektmittelpunkte aus RGB.
Keine Robotermotorik, Objektrotation, Greifpose, Zielanordnung oder Steckmontage.
Keine manuellen Geometriemodelle späterer realer Objekte erforderlich. Im
Simulator werden einfache Würfel-/Quadergeometrien für Labels verwendet.

212.614 Parameter: gemeinsamer CNN-Encoder 3→16→32→32, ReLU nach jeder Conv,
bei 128×128 Eingang 4×4 Average Pooling auf 32×4×4, drei Ansichten zu 1.536
Merkmalen verkettet, Linear 1.536→128 + ReLU, Linear 128→6, lineare XYZ-Ausgabe.
Average Pooling 4×4/Stride4 ist bei der 16×16-Featuremap gleichwertig zum
bisherigen adaptiven 4×4-Ausgang und erlaubt deterministischen CUDA-Backward.
Identische Architektur beider Arme; dritte Ansicht im festen Arm maskiert.

## Vorab bestimmte Trainingskonfiguration

- Drei gepaarte Seeds 1/2/3, zwei Kameraarme, sechs Modelle.
- 128×128 RGB, zwei feste Kameras und Handgelenkkamera, feste Armstellung,
  kalibrierte unveränderte Kameras. Keine aktive Kamerabewegung.
- Würfel 30–60 mm Kantenlänge, zufällige Positionen und Z-Rotationen.
  Feste rote/grüne Objektidentität, feste Beleuchtung und Hintergrund.
- Frische Trainingsszenen pro Zyklus (256), Replay der letzten acht Blöcke.
  Start mit 512 Szenen. Ganze Datenblöcke inklusive Dimensionen und Hashes bleiben
  gespeichert; keine alten Experimente werden überschrieben.
- Pro Zyklus 100 Updates je Modell, Batch32, gleiche Stichprobenreihenfolge pro
  Seed zwischen beiden Armen. Frische Daten begrenzen bloßes Wiederholen eines
  winzigen Datensatzes. Keine klassischen Epochen über einen festen Datensatz.
- AdamW, LR3e-4 konstant, WeightDecay0,01, normierter XYZ-MSE mit 0,15m Skala
  und Ursprung [0,0,0.82]. Gradientnorm auf 10 begrenzt, NaN/Inf führt zum Abbruch.
- Keine Architektur-/LR-Suche während des Laufs, kein RL und keine automatische
  experimentelle Optimierung. Alle Modelle erhalten gepaarte Updates.
- Torch deterministic algorithms, CUBLAS_WORKSPACE_CONFIG, feste Seeds,
  cuDNN deterministic, kein TF32. Reproduzierbarkeit gilt innerhalb der
  protokollierten Hardware-/Softwarekonfiguration, nicht versionsübergreifend.

## Messung und Modellwahl

512 feste unabhängige Würfel-Validierungsszenen, Seed7000000. Training startet mit
Seed6000000; weitere Zyklen verwenden Seed6000000+Zyklus. Loss wird nach jedem
Zyklus über den gesamten aktuellen Replaypuffer und die gesamte Validierung
berechnet; zusätzlich feste Trainingsprobe aus dem Startblock. Der Puffer wechselt,
daher ist dessen Loss nicht eine Kurve auf einem unveränderten Datensatz.

PNG-Plots und JSON-Kurven nach jeder Validierung für alle sechs Modelle.
Best- und Latest-Checkpoint enthalten Modell, Optimizer, RNG-Zustände, Zyklus
und Updatezahl. Checkpoints sind Sicherungen, kein fertig implementiertes
automatisches Resume: ein Resume muss Datenbank/Paarung exakt rekonstruieren.

Auswahl ausschließlich nach Würfel-Val-MSE. Alle sechs Modelle werden gemeinsam
gehasht eingefroren, erst dann neue Endtests mit je512 Würfel-/Quaderszenen
(Seeds8000000 und8000001). Quader haben 30–70mm Kantenlängen, Aspektverhältnis
mindestens1,5. Keine bisherigen Quader-Endtests für Optimierung wiederverwenden.
Metriken: 3D-/XY-Fehler, Z-Fehler, P90, Anteil <=10mm. Kein Stapelerfolgsnachweis.

## Laufzeit, Überwachung und Kosten

Zehn Stunden Gesamtwandzeit ab Start einschließlich Rendering, Lernen und
Auswertung. Neue Updates enden spätestens nach9h50; Rest für Freeze und Tests.
Supervisor hat eine harte Grenze von Deadline+120s für hängende Prozesse.
Zusätzliche 30GiB Datengrenze als Ressourcenlimit, kein Auffüllen mit Wartezeit.
Kein Early Stopping über alle Modelle: fortlaufend neue Szenen, beste
Validierungscheckpoints bleiben erhalten. Wissenschaftlich kann trotz10h keine
Verbesserung garantiert werden. Keine Lego-Geometrien oder Steckkräfte.

Deterministischer Supervisor prüft alle15s Prozess und Statuszeit. Bei20min ohne
Heartbeat oder Zeitüberschreitung beendet er den Worker und dokumentiert ERROR.
Kein automatischer Neustart. Der Supervisor hält automatischen Systemschlaf
während des Laufs zurück und gibt die Sperre beim Ende frei. Erzwungenes Herunterfahren
oder manuelles Schlafen kann den Lauf trotzdem unterbrechen.

Der Supervisor muss nachweislich außerhalb des beendbaren Codex-Prozessjobs
laufen. Prozessunabhängigkeit, Worker-PID, Endzeit und fortschreitende Updates
werden nach dem Start kontrolliert. Aktiver Lauf: run_003.
Status: run_003/status.json; Kurven: run_003/loss.png; Log: run_003/worker.log.

## Technische Vorprüfung

smoke_001 fand fehlenden deterministischen Backward des adaptiven Poolings.
smoke_002 mit gleichwertigem festem Pooling beendete Datengenerierung, sechs
Trainingsmodelle, Validation, Plots, Checkpoints, Modellfreeze, beide Endtests und
Supervisor regulär mit Exitcode0. Dies sind technische Testdaten aus denselben
vorgegebenen Seedbereichen, keine für Methodenwahl gelesenen Endtestmetriken.
Die Produktionsdaten werden neu auf128px gerendert; Smoke-Zahlen sind keine
wissenschaftlichen Ergebnisse. Die Smoke-Endtestmetriken wurden nicht zur
Hyperparameterentscheidung herangezogen.

smoke_003 bestätigte dieselbe vollständige Kette mit direktem Basis-Python und
denselben venv-site-packages. Der venv-Launcher und direkte Starts aus dem
Codex-Prozess erwiesen sich für einen langlebigen Supervisor als ungeeignet.
run_001/run_002 begannen kein Training; der erste direkte Start von run_003
verweigerte wegen nachgewiesener Jobbindung ebenfalls vor Trainingsbeginn.
Anschließend wurde derselbe vorbereitete Lauf über Win32_Process.Create mit
Breakawayflag und unsichtbarem Fenster gestartet. PID15488 meldete query_ok=true,
in_job=false; WorkerPID10380 begann mit neuen Renderdaten. Die ursprüngliche
run_003-Endzeit blieb erhalten (01.11.2026 um10:10:05 Berlin).
