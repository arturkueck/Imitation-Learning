# Visuelle Lokalisierung: Modell, Training und Grenzen

## Tatsächlich ausgeführt

Der Pilot ist überwachte Regression von RGB auf zwei Objektmittelpunkte. Er
lernt weder Roboteraktionen noch eine Zielanordnung, Objektorientierungen,
Greifstellen oder Stabilität. Kein RL, kein Self-Imitation-Training in diesem
Vorversuch. Zwei feste Ansichten werden mit denselben Ansichten plus
Handgelenkkamera verglichen. Die dritte Ansicht wird im Kontrollarm auf null
gesetzt. Ein gemeinsamer CNN-Encoder wird für alle Ansichten wiederverwendet;
beide Arme besitzen dieselbe Parameterzahl.

512 Trainingsszenen, 128 Entwicklungsszenen, je 128 reservierte Würfel-/Quader-
Testszenen. Pro Szene zwei farblich zugeordnete Objekte. Keine überlappenden
Mittelpunkt-Konfigurationen zwischen Splits; siehe DATA_AUDIT.json. Feste
Kamerakalibrierung, feste Armstellung, feste Objektfarben, 64×64 Pixel pro Bild.
Es gibt keine Variation realer Hintergründe oder Beleuchtung. Diese Vereinfachungen
begrenzen jede Aussage über unbekannte reale Objekte.

## Architektur

Eingabetensor: B × 3 Ansichten × 3 RGB-Kanäle × 64 × 64.

| Stufe | Ausgabe je Bild | Aktivierung | Parameter |
|---|---|---|---:|
| Conv2D, 3→16, Kernel 5, Stride 2, Padding 2 | 16×32×32 | ReLU | 1.216 |
| Conv2D, 16→32, Kernel 3, Stride 2, Padding 1 | 32×16×16 | ReLU | 4.640 |
| Conv2D, 32→32, Kernel 3, Stride 2, Padding 1 | 32×8×8 | ReLU | 9.248 |
| Adaptive Average Pooling | 32×4×4 = 512 Merkmale | keine | 0 |
| Zusammenfügen der drei Ansichten | 1.536 Merkmale | keine | 0 |
| Linear, 1.536→128 | 128 Neuronen | ReLU | 196.736 |
| Linear, 128→6 | 6 Werte | linear, unbegrenzt | 774 |

Insgesamt **212.614 trainierbare Parameter**, drei Conv-Schichten und zwei
Linear-Schichten. Vier ReLU-Anwendungen entlang eines Bild-/Ausgabepfades;
keine Sigmoid-/Softmax-Ausgabe, kein Dropout, keine BatchNorm, kein vortrainierter
Backbone. Float32-Gewichte benötigen ungefähr 0,81 MiB; Aktivierungen, Gradienten
und Optimizerzustände kommen hinzu. Die Ausgaben sind XYZ für Rot und Grün.
Der Kopf mit 128 Neuronen enthält den Großteil der Parameter. Bei Conv-Schichten
werden Kanäle und räumliche Dimensionen angegeben; sie sind keine bloßen
vollverbundenen Neuronenzahlen.

## Loss und Optimierung

RGB-Werte werden auf [0,1] skaliert. Zielkoordinaten werden als
`(XYZ - [0,0,0.82]) / 0.15` normiert. Loss ist der Mittelwert der quadrierten
Abweichung über Batch, beide Objekte und alle drei Achsen. Alle Achsen haben
dieselbe metrische Skalierung. Für diesen eindeutigen, synthetisch beschrifteten
Regressionsfall ist MSE eine nachvollziehbare Baseline. Er liefert keine
Unsicherheit; bei mehrdeutigen verdeckten Szenen kann er unbrauchbare Mittelwerte
begünstigen. Huber-Loss wäre ein separater Vergleich für Ausreißer, behebt aber
keine fehlende Sichtbarkeit oder mehrdeutige Zielverteilung.

AdamW: Lernrate 0,0003, betas=(0,9; 0,999), epsilon=1e-8, Weight Decay=0,01.
Die Werte sind aus dem lokal installierten PyTorch 2.11.0+cu128 geprüft.
Kein Lernratenscheduler, keine Augmentation, keine frühe Beendigung.
Batchgröße 32, 600 Optimizerupdates pro Modell, zwei Seeds pro Kameraarm.
Es wird mit Zurücklegen gesampelt: 600×32/512 = **37,5 Datenpass-Äquivalente**,
keine 37,5 vollständigen, durchmischten Epochen.

## Kurven und Overfitting

run_002 protokollierte alle 100 Updates nur einen Minibatch-Trainingsloss und
den vollständigen Validation Loss. Für die angeforderten aussagekräftigeren
Kurven wurde diagnostic_001 mit denselben Daten, Seeds, Architektur und
Hyperparametern zusätzlich ausgeführt. Es lädt ausschließlich train/valid,
keine Endtests. Alle 25 Updates und vor dem ersten Update werden beide ganzen
Datensätze ausgewertet (25 Punkte pro Modell). Diese Kurven sind in
diagnostic_001/training_validation_loss.png und als SVG gespeichert. Die
Generalisierungslücke liegt zusätzlich als PNG vor.

| Diagnoselauf bei Update 600 | Training MSE | Validation MSE |
|---|---:|---:|
| Fest, Seed 1 | 0,04793 | 0,05656 |
| Fest + Hand, Seed 1 | 0,01524 | 0,01913 |
| Fest, Seed 2 | 0,11798 | 0,13820 |
| Fest + Hand, Seed 2 | 0,01570 | 0,02010 |

Noch kein ausgeprägtes anhaltendes Overfitting-Muster: die Entwicklung verbessert
sich überwiegend weiterhin. Ein Validation Loss über dem Trainingsloss allein
beweist kein Overfitting. Vor allem der feste Kameraarm zeigt deutliche
Seedabhängigkeit. Die kleinen Datenmengen erlauben keine robuste Aussage über
Modellkapazität. Besseres Trainingsergebnis beweist weder Quaderübertragung noch
Millimetergenauigkeit. Die Z-Schätzung bei Quadern ist ein eigener Verteilungssprung.

Die Checkpointauswahl bleibt wie zuvor nur bei 100er-Updates erlaubt. Der im
Diagnoselauf für Fest+Hand/Seed1 sichtbare kleinere Val-Wert bei Update 575 führt
nicht nachträglich zur Auswahl oder zum erneuten Endtest.

**Reproduzierbarkeit:** Die Diagnose ist keine numerisch exakte Wiederaufnahme:
GPU-Determinismus war im ursprünglichen Pilot nicht erzwungen. Trotz gleicher
Seeds weichen die Kurven/Endgewichte zwischen Läufen ab. Daher werden Diagnose-
Losses nicht als Losses der ursprünglich endgetesteten Checkpoints ausgegeben.
Diagnose ist keine zusätzliche unabhängige Trainingsreplikation für die
Kamera-Hypothese. Der vollständige Originalquelltext von run_002 ist gesichert
und gegen den Manifesthash geprüft. Vor künftigem Produktionstraining sind
deterministische Einstellungen, Runtimeversionen und Optimizer-/RNG-Checkpoints
explizit zu speichern.

## Ursprünglicher reservierter Endtest, run_002

Mittlerer euklidischer Mittelpunktfehler in mm, je 128 Szenen mit zwei Objekten:

| Kameraarm | Würfel Seed 1 / 2 | Quader Seed 1 / 2 |
|---|---|---|
| Zwei feste Kameras | 42,44 / 74,41 | 36,60 / 71,31 |
| Zwei feste + Handkamera | 27,75 / 29,90 | 23,23 / 25,34 |

Konstante Schätzung der mittleren Trainingsposition: ungefähr 110–111 mm Fehler.
Die Handkamera verbessert in diesem Setup beide gepaarten Seeds. Die absoluten
Fehler sind zu groß für präzises Stapeln. Größere Quader sind teilweise leichter
sichtbar als Würfel; kleinere Quaderfehler beweisen deshalb keine allgemeine
Formübertragbarkeit. Nur zwei Seeds und eine Armstellung, kein Signifikanznachweis.
Ein Objektfehler ist keine unabhängige Szene; die Objekte einer Szene teilen
Bildbedingungen. Der Quader-Endtest ist nun für Methodenwahl verbraucht.

## Vorschlag für die nächste Entwicklungsstufe – noch nicht gestartet

1. Zunächst die kleine Architektur als Referenz behalten und ihr Lernverhalten
   bis maximal 100 tatsächliche Epochen auf Würfeln untersuchen: Batch 32,
   ohne Zurücklegen, 16 Updates je Epoche. Ganze Train-/Validationslosses jede
   Epoche. Early Stopping nach 15 Epochen ohne vorab definierte Verbesserung
   (z.B. absolut 1e-4 im normierten Val-MSE), besten Checkpoint behalten.
   Keine vorab behauptete optimale Epochenzahl. Epochengrenzen, Startgewichte,
   Datenreihenfolge und LR bleiben zwischen Kameraarmen gepaart.
2. Auf ausschließlich Entwicklung getrennte Daten- und Auflösungsablation:
   mehr unabhängige Szenen, danach 128×128 statt 64×64. Änderungen nicht zugleich
   einer größeren Modellgröße zuschreiben. Zielgenauigkeit vorab in mm festlegen.
3. Modellkapazität erst danach kontrolliert variieren, z.B. breiterer CNN-Encoder
   oder räumliche Keypoint-/Heatmap-Ausgabe statt direkter XYZ-Regression.
   Train/Val niedrig und beide präzise: kleines Modell kann genügen. Beide hoch:
   Optimierung, Sichtbarkeit, Auflösung und Repräsentation prüfen. Train niedrig,
   Val schlechter: mehr unabhängige Daten oder Regularisierung prüfen.
4. Modell von der Farbbindung lösen, Armstellungen und Kamerakalibrierung variieren,
   Objektorientierung/Greif- und Ablagepose ergänzen; anschließend IL und reale
   Bewegungsplanung. Dies ist eine neue Aufgaben-/Architekturvariante.
5. Vor neuer Methodenwahl neue Quader- und Anordnungs-Endtests reservieren.
   Die bisherige Quaderquote nicht durch wiederholte Anpassung optimieren.

Der vorgeschlagene Entwicklungsplan ist kein automatisch gestarteter langer
Trainingslauf. Bestehende Experimente und Checkpoints blieben erhalten.
