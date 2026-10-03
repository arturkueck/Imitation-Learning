# Trainingsseed-Replikation: direkter Chunk-Regressor vs. Diffusion

Drei unabhängige Trainingsinitialisierungen je Modellklasse, jeweils 30.000 Gradient Updates. Seed 1 ist der bereits abgeschlossene, exakt passende Ausgangsversuch; Seeds 2 und 3 wurden frisch initialisiert und vollständig neu trainiert. Keine Auswahl des besten Zwischencheckpoints.

## Ergebnis je Trainingsseed

| Modell | Seed | Stabile Stacks / 40 | Erfolgsrate |
|---|---:|---:|---:|
| diffusion | 1 | 0/40 | 0.0% |
| diffusion | 2 | 0/40 | 0.0% |
| diffusion | 3 | 0/40 | 0.0% |
| direct | 1 | 28/40 | 70.0% |
| direct | 2 | 30/40 | 75.0% |
| direct | 3 | 31/40 | 77.5% |

| Modell | Mittelwert | Stichproben-SD | Minimum–Maximum |
|---|---:|---:|---:|
| diffusion | 0.0% | 0.0 Prozentpunkte | 0.0–0.0% |
| direct | 74.2% | 3.8 Prozentpunkte | 70.0–77.5% |

Die drei Trainingsseeds sind die Replikate. Die 40 identischen Startzustände innerhalb eines Modells sind gepaarte Aufgabenfälle; sie erhöhen nicht die Anzahl unabhängiger Trainingsreplikate. Bei n=3 werden keine Signifikanzbehauptungen oder scheingenauen Konfidenzintervalle angegeben.

![Erfolg je Trainingsseed](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/seed_success.png>)

## Rollout-Phasen

Alle Werte sind Anzahlen unter denselben 40 Starts. Phasenindikatoren sind separat gezählte Diagnosen, kein zwingend verschachtelter Funnel.

| Modell/Seed | Greifen | Anheben | Expert-Höhe | Transport | Vollhöhe vor Transport | Vorzeitig | 3 cm | Position | Absenken | Release | Stabil |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| diffusion/1 | 31 | 24 | 4 | 15 | 1 | 17 | 4 | 0 | 0 | 0 | 0 |
| diffusion/2 | 26 | 18 | 3 | 8 | 1 | 13 | 2 | 0 | 0 | 0 | 0 |
| diffusion/3 | 27 | 19 | 1 | 9 | 0 | 14 | 2 | 2 | 0 | 0 | 0 |
| direct/1 | 37 | 37 | 10 | 37 | 8 | 27 | 37 | 37 | 36 | 30 | 28 |
| direct/2 | 37 | 37 | 10 | 37 | 9 | 28 | 37 | 35 | 34 | 30 | 30 |
| direct/3 | 35 | 34 | 5 | 34 | 4 | 30 | 34 | 34 | 34 | 31 | 31 |

Kriterien unverändert gegenüber dem Einzelversuch: Expert-ähnliche Vollhöhe verlangt gehaltenen Würfel z≥1,045 m und EEF z≥1,049 m für drei Frames. Vorzeitiger Transport ist eine zielgerichtete horizontale Bewegung vor diesem Kriterium. Das ist eine Abweichung vom Expert, kein automatischer Aufgabenfehler. Der stabile Stack verlangt die ursprüngliche Success-Bedingung durchgehend in 40 zusätzlichen Frames (2 s), Würfelkontakt und keinen gehaltenen Würfel.

Greifen verwendet das native Grasp-Prädikat; Anheben verlangt B-z>0,88 m. Der bestehende Transportindikator verlangt gehaltenen Würfel B-z>0,98 m, XY-Geschwindigkeit >0,02 m/s und Zielrichtungs-Cosinus >0,5 für drei Frames. „Vollhöhe vor Transport“ bezieht sich auf diesen Indikator. Die zusätzliche Früherkennung prüft schon bei B-z>0,88 m dieselbe horizontale Bewegung, solange mindestens eine Vollhöhengrenze noch unterschritten ist, und zählt nur Ereignisse vor der ersten vollständigen Lift-Erkennung. Die Indikatoren verwenden daher bewusst verschiedene Höhengates; Transport bedeutet hier nicht jegliche erste horizontale Bewegung.

Der 3-cm-Bereich verlangt XY-Abstand <3 cm und B−A-Höhe >3,2 cm. Positionierung verlangt XY-Abstand <9 mm bei derselben Höhe; Absenken zusätzlich B−A-Höhe 4 cm ±8 mm. Release verlangt dabei Würfelkontakt und keinen Grasp.

## Variation der Startzustände

![Gleiche 40 Startzustände, drei Trainingsseeds](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/start_state_success.png>)

- **diffusion: Von allen drei Seeds gelöst: 0/40**. Starts: keine.
- **diffusion: Seedabhängig: 0/40**. Starts: keine.
- **diffusion: Von keinem Seed gelöst: 40/40**. Starts: 46000, 46001, 46002, 46003, 46004, 46005, 46006, 46007, 46008, 46009, 46010, 46011, 46012, 46013, 46014, 46015, 46016, 46017, 46018, 46019, 46020, 46021, 46022, 46023, 46024, 46025, 46026, 46027, 46028, 46029, 46030, 46031, 46032, 46033, 46034, 46035, 46036, 46037, 46038, 46039.
- **direct: Von allen drei Seeds gelöst: 23/40**. Starts: 46003, 46004, 46006, 46007, 46008, 46009, 46010, 46011, 46013, 46014, 46015, 46016, 46017, 46018, 46019, 46022, 46023, 46026, 46031, 46032, 46033, 46034, 46038.
- **direct: Seedabhängig: 12/40**. Starts: 46000, 46001, 46002, 46020, 46021, 46028, 46029, 46030, 46035, 46036, 46037, 46039.
- **direct: Von keinem Seed gelöst: 5/40**. Starts: 46005, 46012, 46024, 46025, 46027.

Bei systematischen Direkt-Fehlschlägen zeigt die folgende Tabelle den ersten nicht erfüllten Phasenindikator. Dies ist eine Beschreibung der Messwerte, keine kausale Fehlerklassifikation.

| Start | Direkt Seed 1 | Direkt Seed 2 | Direkt Seed 3 |
|---|---|---|---|
| 46005 | Greifen | Greifen | Greifen |
| 46012 | Release | Release | Release |
| 46024 | Greifen | Positionierung | Greifen |
| 46025 | Greifen | Greifen | Greifen |
| 46027 | Absenken | Absenken | Greifen |

Vollständige Erfolgsanteile je Start sind in `analysis.json` unter `start_states` gespeichert. Diese Startzustandsvariation ist von der Streuung der drei modellweiten Erfolgsraten zu unterscheiden.

Die gespeicherten Direkt-Rollouts enthalten drei nachvollziehbare Beispiele: Start 46000 ist seedabhängig, 46003 wird von allen drei Seeds gelöst, 46005 von keinem. Die Zustands-/Aktionsplots und vier Videos liegen unter `representative`; die Videos spielen gespeicherte Simulatorzustände ab und sind keine zusätzlichen Evaluationen. Das Seed-3-Modellpaar auf Start 46003 zeigt zusätzlich beide Modellklassen bei identischen Anfangsbedingungen.

![Seedabhängiger Start 46000](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/representative/direct_start_46000.png>)

![Modellvergleich: Trainingsseed 3, Start 46003](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/representative/model_pair_seed_3_start_46003.png>)

Im gezeigten Diffusion-Rollout wird der Würfel wiederholt nur teilweise angehoben und später verloren; schwache XY-Aktionen und wechselnde Gripperbefehle erreichen das Ziel nicht. Das Direktmodell erreicht hier keine Expert-Vollhöhe, steuert aber gezielt zum Ziel und gibt den Würfel stabil frei. Dieses Beispiel veranschaulicht die Trajektorien und ersetzt keine Auswertung über die Trainingsseeds.

## Offline auf identischen Validierungsbeobachtungen

20 eingefrorene Validierungsdemos, jeweils −10 bis +10 Frames um den Expert-Umschaltpunkt. Verwendet wird Chunk-Aktion 1, also die zuerst ausgeführte Aktion. Diffusion: dieselben acht gespeicherten Initialrausch-Samples je Beobachtung; Grenzreaktion: 32 gepaarte Rausch-Samples je Demo für Frame −1 und 0. Direkt: eine deterministische Vorhersage. Diese Inferenzsamples sind keine Trainingsreplikate.

| Modell/Seed | Grenzreaktion / Expert (Median) | Früh | Pünktlich | Spät | Kein Start | XY/Expert (Median) | Falsche XY-Richtung | Transport-Cosinus (Mittel) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| diffusion/1 | 0.62% | 45.00% | 25.00% | 3.75% | 26.25% | 28.68% | 19.62% | 0.5064 |
| diffusion/2 | 0.43% | 40.00% | 18.12% | 5.00% | 36.88% | 25.80% | 19.88% | 0.4920 |
| diffusion/3 | 0.58% | 48.12% | 18.75% | 4.38% | 28.75% | 25.36% | 20.25% | 0.4812 |
| direct/1 | 1.65% | 100.00% | 0.00% | 0.00% | 0.00% | 76.01% | 0.00% | 0.9977 |
| direct/2 | 1.97% | 100.00% | 0.00% | 0.00% | 0.00% | 81.46% | 0.00% | 0.9944 |
| direct/3 | 1.71% | 100.00% | 0.00% | 0.00% | 0.00% | 77.59% | 0.00% | 0.9977 |

Grenzreaktion = ‖ΔXYZ-Vorhersage‖ / ‖ΔXYZ-Expert‖ zwischen den gepaarten Grenzframes; zusätzlich ist die Projektion auf den Expert-Sprung gespeichert. Beginn verlangt XY-Aktionsnorm >0,25 und Zielrichtungs-Cosinus >0,5 für drei Frames. Früh: früher als −2 Frames; pünktlich: ±2 Frames; spät: >2 Frames. Das begrenzte Fenster kann früheren Beginn nur linkszensiert erfassen. Stabiler Transport: +6 bis +10 Frames.

![Lift–Transport-Profile je Trainingsseed](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/boundary_profiles.png>)

## Offline ↔ Closed Loop

![Explorative Zusammenhänge auf Trainingsseed-Ebene](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/offline_rollout.png>)

| Metrik | Gepoolt (n=6) | Direkt (n=3) | Diffusion (n=3) |
|---|---:|---:|---:|
| Grenzreaktion | +0.985 | +0.346 | nicht definiert |
| Früher Offline-Beginn | +0.995 | nicht definiert | nicht definiert |
| Pünktlicher Offline-Beginn | -0.976 | nicht definiert | nicht definiert |
| XY-Stärke | +0.997 | +0.458 | nicht definiert |
| Transport-Cosinus | +0.998 | -0.187 | nicht definiert |
| Falsche Richtung | -0.998 | nicht definiert | nicht definiert |
| Rollout-Greifrate | +0.920 | -0.756 | nicht definiert |
| Rollout-Maximalhöhe (Median) | +0.978 | -0.594 | nicht definiert |

Pearson-Korrelationen dienen ausschließlich der Beschreibung. Gepoolte Werte können vollständig durch den Modellklassenunterschied entstehen. Innerhalb einer Klasse reichen drei Punkte nicht zur belastbaren Wahl einer Prognosemetrik; konstante Erfolgsraten oder Merkmale liefern keine definierte Korrelation. Greifrate und erreichte Höhe sind Rollout-Diagnosen, keine rein offline verfügbaren Prädiktoren.

Innerhalb der Direktklasse ist die Rangfolge nicht eindeutig: r(XY-Stärke, Stackrate)=+0.458, r(Grenzreaktion, Stackrate)=+0.346, r(Richtungs-Cosinus, Stackrate)=-0.187. Alle drei Direktmodelle beginnen offline in sämtlichen Validierungsdemos früh; die dennoch unterschiedlichen Stackraten können durch diesen konstanten Timing-Indikator nicht erklärt werden. Diese drei-Punkte-Werte werden nicht als validierte Vorhersagegüte interpretiert.

## Drei Forschungsfragen

1. **Reproduzierbarkeit:** Direkt 74.2% ± 3.8 Prozentpunkte gegenüber Diffusion 0.0% ± 0.0. Der Abstand bleibt in jedem der drei Trainingsseeds bestehen.
2. **Exaktes Expert-Timing:** 70/89 erfolgreiche Direkt-Rollouts transportieren vorzeitig; 68/89 erreichen keine Expert-Vollhöhe. Diese Fälle zeigen, dass die scharfe Expert-Umschaltung und ihre maximale Lift-Höhe nicht notwendig für einen stabilen Stack in diesen Starts sind. Das ist keine Aussage, dass jedes frühe Transportieren sicher oder erfolgreich ist.
   Bei diesen erfolgreichen frühen Starts beträgt der vertikale Abstand der orientierungsabhängigen Würfel-Bounding-Boxes beim ersten gemessenen horizontalen Transport mindestens 9.8 cm und im Median 16.8 cm. Das hilft zu erklären, warum die zusätzliche Expert-Lift-Höhe in der vorliegenden Zwei-Würfel-Aufgabe nicht erforderlich ist; es ist keine allgemeine Sicherheitsgarantie für andere Aufgaben.
   Im programmierten StackExpert liegt das Lift-EEF-Ziel 24 cm über der anfänglichen Würfelhöhe, das anschließende Transportziel 19 cm über dem Basiswürfel. Der Expert wechselt damit abrupt sein Zwischenziel und senkt dessen Höhe wieder ab. Die native Aufgabenbedingung fordert stattdessen Ausrichtung, Kontakt, Freigabe und Stabilität des fertigen Stacks; diese zusätzliche Zwischenhöhe ist kein Erfolgskriterium.
3. **Nützlichere Offline-Diagnosen:** XY-Stärke und Richtungs-Cosinus im stabilen Transport beschreiben die Fähigkeit zur Zielsteuerung direkter als die Grenzreaktion. Die Einzelwerte und Profile müssen zusammen mit Greifen, Lift und Release betrachtet werden. Dieser Versuch kann ihren Nutzen als Diagnose stützen, aber bei drei Seeds je Klasse keine allgemein gültige Prognoserangfolge etablieren. Eine schwache Grenzreaktion allein ist kein hinreichender Grund, ein Closed-Loop-fähiges Modell zu verwerfen.

Der kontrollierte Vergleich repliziert die bestehenden Modellklassen einschließlich ihrer jeweiligen Architektur und ihres Lernziels. Er isoliert keine einzelne mathematische Eigenschaft von Diffusion unabhängig von der Architektur. Das Direktmodell hat 67.467.376, Diffusion 65.648.903 Parameter. Keine neue Methode wurde eingeführt.

## Trainingskontrolle und Aufwand

Identische 180/20 Demos und State-Observationen (15 Merkmale × 2 Frames), 16×7 Aktionen, Replanning nach zwei ausgeführten Aktionen; uniforme Verteilung, Batch 8, 30.000 Updates = 240.000 Trainingsfenster. Keine Normalisierung der Rohbeobachtungen oder Actions. AdamW 1e−4, Gewichtszerfall 1e−6, 500 Warmup-Updates mit Cosine-Scheduler, EMA Power 0,75. Innerhalb jeder Modellklasse variiert ausschließlich der Trainingsseed sowie der Ablagepfad. Direkter MSE über alle 16×7 Ausgaben, Diffusion ursprüngliches Epsilon-Ziel und DDIM mit zehn Inferenzschritten. Der korrigierte Scheduler zählt ausschließlich Trainingsupdates.

| Neues Training | Updates | Trainingslaufzeit | Offline + 40 Rollouts |
|---|---:|---:|---:|
| diffusion/2 | 30000 | 50.9 min | 22.1 min |
| diffusion/3 | 30000 | 37.3 min | 13.8 min |
| direct/2 | 30000 | 10.7 min | 4.7 min |
| direct/3 | 30000 | 11.0 min | 3.9 min |

Drei statt fünf Seeds: eine gemeinsame CUDA-GPU mit 12 GB VRAM und anfangs ungefähr 26 GB freiem Datenträgerspeicher. Laufzeiten umfassen zeitweise konkurrierende GPU-Prozesse und sind keine isolierten Leistungsbenchmarks. Die vorhandenen Seed-1-Läufe und Artefakte wurden wiederverwendet.

Alle 240 Startzustands-Hashes, 30.000 Optimizer-/Scheduler-Schritte pro Modell, Konfigurationsgleichheit, unveränderte Daten und stabile Erfolgs-Tails sind in `verification.json` geprüft. Frische Gewichtsinitialisierungen für Seeds 2/3 wurden gehasht. Die 62 Demonstrationen mit schwarzen Bildern bleiben unverändert; dieser Versuch verwendet ausschließlich State-Daten.

## Artefakte

- `protocol.json`: eingefrorene Seeds, Datenhash, Starts und Kontrollen.
- `analysis.json`: alle Einzelwerte, Startzustandsanteile und deskriptive Korrelationen.
- `verification.json`: vollständiger Audit und Checkpoint-Hashes.
- `direct/seed_2`, `direct/seed_3`, `diffusion/seed_2`, `diffusion/seed_3`: Konfiguration, Initialisierungsaudit, Checkpoints, Offline-Chunks, Logs und Rollout-Zustands-/Aktionsverläufe.
- Seed 1: unveränderte Referenzartefakte in `../stack_direct_20261001` sowie `../stack_switch_20261001/source`; Checkpointpfade in `protocol.json`.
