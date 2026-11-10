# Kontrollierter Versuch: explizite Dynamik aus zwei Frames

**Einordnung: C – die kontinuierliche Dynamikdarstellung hilft messbar, löst aber die schwache Umschaltsensitivität nicht.** Die mediane Reaktion auf denselben gepaarten Expert-Grenzübergang wächst auf Validierungsdaten um den Faktor 2.71, bleibt jedoch bei 1.4 % des Expert-Aktionssprungs. Keine der 640 gepaarten Vorhersagen vollzieht bei identischem Anfangsrauschen den klaren Lift→Transport-Wechsel. Der Effekt erscheint ähnlich auf Trainingsdaten. Die Rollout-Zahlen unten bestimmen zusätzlich, ob ein praktischer Trade-off vorliegt; die Klassifikation bedeutet keine generelle Widerlegung anderer Repräsentationen.

## Kontrolle des Vergleichs

- Ausgangspunkt: korrigierter Scheduler, zwei ausgeführte Aktionen, Epoch-300-Checkpoint; SHA256 `a2c2cca1cd087409261402f3b95f7b6592961e6aac92c276c72657dd436343f4`.
- Beide Varianten starten aus demselben funktionsbewahrend erweiterten Checkpoint. Alte Netz-/EMA-Gewichte und AdamW-Momente werden übernommen, zusätzliche Projektionsspalten und deren Momente starten bei null. Initiale Vorhersagen zwischen Varianten bitgleich; maximaler Unterschied zur ursprünglichen Policy 0.00000234 durch Rundung.
- Baseline: bisherige 15 Zustandsfeatures unverändert, vier zusätzliche Kapazitätskontroll-Kanäle konstant null. Dynamik: dieselben Rohfeatures plus vier kontinuierliche Merkmale. Deshalb in **beiden Armen exakt 65,763,591 Parameter**, gegenüber ursprünglich 65,648,903. Nur die FiLM-Eingangsbreite wächst in beiden von 286 auf 294; keine anderen Netzblöcke ändern sich. Die zusätzlichen Baseline-Gewichte bleiben tatsächlich exakt null; die Dynamikgewichte lernen, EMA-L2-Norm 1.699.
- Identischer unveränderter Datensatz: 200 Demos, 180 Training / 20 Validierung, identische vorbestehende Splits. Die 62 Demos mit schwarzen Bildern bleiben unverändert und separat dokumentiert; für diese State-Policy werden Bilder nicht verwendet.
- **5.000 Gradient Updates pro Arm**, Batch 8, Seed 1, uniformes Sampling; 40.000 Ziehungen und Lernratenfolgen bitgleich geprüft. Kein Oversampling. AdamW-/EMA-Step 30.000→35.000. Gemeinsamer Cosinus-Neustart bei 1e−4 mit 500 Warmup-Updates, weil die ursprüngliche LR bereits null war. Kein Zwischencheckpoint ausgewählt.
- History 2, Chunk 16, ausgeführte Aktionen 2, DDIM 10 / Diffusion-Training 100 Schritte und sonstige Hyperparameter identisch. Beide Arme FP32 mit deaktiviertem TF32 und cuDNN-Benchmark; diese numerische Kontrolle gilt für Training und Evaluation. Historische Ergebnisse außerhalb dieses Vergleichs sind dadurch keine bitgleichen Trainingskontrollen.
- Keine zusätzliche Sensorinformation, keine History-Verlängerung, kein binäres Phasenlabel, kein Controller und keine XY-Korrektur. Alle gespeicherten ursprünglichen und ausgeführten Aktionen sind bitgleich.

## Features und Skalierung

Bei 20 Hz: `Δz = z_t − z_(t−1)`, `v_z = Δz / 0,05 s`. EEF und Würfel B stammen ausschließlich aus den beiden bereits vorhandenen Frames. Die vier Features werden einmal aus dem Fenster berechnet und in beide History-Slots kopiert: **kein dritter Frame**. Δz und v_z sind kollinear, nach Standardisierung sogar redundant; vier Kanäle liefern nur zwei unabhängige dynamische Größen. Relative Transporthöhen wurden zur Isolierung nicht ergänzt.

Normalisierung: `(Feature − Trainingsmittel) / Trainingsstandardabweichung`, ohne Clipping, ausschließlich auf den 27.322 Trainings-Ankerframes fitten. Die bisherigen Rohbeobachtungen bleiben unnormalisiert; ihre Komponentenverteilungen stehen in [original_feature_scales.json](original_feature_scales.json). Positionen haben Größenordnung 1 m, die kritische Einzeländerung dagegen etwa 1 mm.

| Feature (m bzw. m/s) | Trainingsmittel | Trainings-Std | Lift-Median | Transport-Median |
|---|---:|---:|---:|---:|
| delta_eef_z | -0.000991 | 0.006083 | 0.010199 | -0.001923 |
| velocity_eef_z | -0.019823 | 0.121655 | 0.203972 | -0.038462 |
| delta_B_z | 0.000193 | 0.005294 | 0.010216 | -0.001925 |
| velocity_B_z | 0.003852 | 0.105880 | 0.204325 | -0.038493 |

Die Höhenänderungs-Std betragen 6,083 mm (EEF) und 5,294 mm (B). Im Lift liegen die normalisierten Δz-Mediane bei 1,840 / 1,893, im Transport bei −0,153 / −0,400. Die Verteilungen umfassen 5.120 Lift- und 3.693 Transport-Ankerframes. Die vier Features werden in allen Phasen berechnet, ohne Griff- oder Phasengate. [Vollständige Verteilungen](feature_distribution.json), [Histogramme](feature_distributions.png).

## Offline: Reaktion auf die Expert-Grenze

Unverändertes vorheriges Validierungspanel: 20 Demos × 21 Offsets (−0,5 bis +0,5 s), acht Draws je Frame und 32 Draws je unmittelbarem Grenzframe. Vollständige Action-Chunks gespeichert. Die zentrale Sensitivitätsmessung verwendet **identisches initiales Diffusionsrauschen vor/nach der Grenze** und zwischen Modellen: 640 Paare auf Validierung, zusätzlich 1.440 Paare auf 180 Trainingsdemos mit acht Draws. Die ausgewertete erste ausgeführte Aktion ist Chunkindex 1. Native DDIM-Implementierung und Diagnose-Schleife stimmen exakt überein.

Sensitivität = `||a_post − a_pre|| / ||Expert_post − Expert_pre||`. Expertgerichtete Reaktion projiziert die Änderung auf den Expert-Sprung, damit größere Änderungen in falscher Richtung nicht als Erfolg zählen. Unterschiedliche Draws sind keine zusätzlichen unabhängigen Demos.

| Metrik | Baseline | Dynamik |
|---|---:|---:|
| Paar-Sensitivität / Expert-Sprung, Validierung, Median | 0.50 % | 1.35 % |
| Paar-Sensitivität / Expert-Sprung, Training, Median | 0.48 % | 1.36 % |
| Expertgerichtete Paar-Reaktion, Validierung, Median | 0.31 % | 0.98 % |
| Klarer Lift → klarer Transport bei gepaartem Rauschen | 0.0 % | 0.0 % |
| Vorzeitiger Start, früher als −0,1 s | 40.0 % | 26.9 % |
| Start innerhalb ±0,1 s | 21.2 % | 37.5 % |
| Start im Fenster gefunden | 65.6 % | 72.5 % |
| Startzeit, Median unter gefundenen Starts | -0.20 s | -0.05 s |
| Grenzbeobachtungen mit beiden Modi | 97.5 % | 90.0 % |
| Klarer Lift-Modus direkt vor Grenze | 24.4 % | 24.1 % |
| Klarer Transport-Modus direkt nach Grenze | 44.0 % | 56.2 % |
| XY-Aktionsbetrag vor / nach Grenze, Mittel | 0.44 / 0.44 | 0.42 / 0.50 |
| Z-Aktion vor / nach Grenze, Mittel | -0.10 / -0.12 | -0.07 / -0.21 |
| XY / Expert nach Grenze, Median | 30.0 % | 42.0 % |
| XY / Expert im stabilen Transport, Median | 28.2 % | 40.8 % |
| Gripper öffnet direkt vor / nach Grenze | 0.3 % / 0.2 % | 0.3 % / 0.6 % |
| Grenz-Streuung XY / Z, mittlere Standardabweichung | 0.37 / 0.23 | 0.36 / 0.18 |

„Vor“ = Offsets −2/−1, „nach“ = 0/1/2, stabiler Transport = +6…+10. Klarer Lift: XY < 0,12, Z > 0,02, geschlossen; klarer Transport: XY > 0,25, Zielcosinus > 0,5, Z < −0,05, geschlossen. Beide Modi pro Beobachtung: mindestens 15 % der Draws jeweils in beiden Modi. Offline-Start: drei aufeinanderfolgende signifikante XY-Befehle zum Ziel über das gespeicherte Fenster; n=160 Demo/Draw-Verläufe. Der Median der Startzeit enthält nur gefundene Starts, nicht fehlende Starts. Diese Offline-Startdiagnose ersetzt keinen geschlossenen Rollout.

Die Dynamikfeatures verbessern insbesondere den Verlauf der Z-Aktion über das breitere Fenster und reduzieren frühe XY-Befehle. **Unmittelbar am gepaarten Grenzframe bleibt die lokale Reaktion winzig**. Die größere Seed-Varianz gegenüber der kleinen Zustandsreaktion und die anhaltende Moduskoexistenz sind die zentrale Gegen-Evidenz zu „Skalierung reicht aus“. [Aktionsprofile](boundary_profiles.png), [Rohmetriken](analysis.json), [Trainingskontrollen und Trainings-Paare](diagnostics.json), [Trainingsloss](training_loss.png).

## Vollständige Rollouts

20 unveränderte feste Startzustände, Seeds 46000–46019, beide Arme mit identischen Startzustands-Hashes wie bisher. Maximal 500 Schritte plus 40 Policy-Schritte zur Stabilitätsprüfung; keine Aktionseingriffe.

| Stufe | Baseline | Dynamik |
|---|---:|---:|
| Greifen | 15/20 (75 %) | 12/20 (60 %) |
| Anheben, B > 0,88 m | 11/20 (55 %) | 10/20 (50 %) |
| Expert-ähnliche Höhe erreicht | 2/20 (10 %) | 2/20 (10 %) |
| Transport begonnen, B > 0,98 m | 5/20 (25 %) | 10/20 (50 %) |
| Vorzeitiger Transport, Bewegung | 8/20 (40 %) | 9/20 (45 %) |
| 3-cm-Zielbereich | 2/20 (10 %) | 1/20 (5 %) |
| Positioniert, < 9 mm | 0/20 (0 %) | 0/20 (0 %) |
| Abgesenkt | 0/20 (0 %) | 0/20 (0 %) |
| Release mit Würfelkontakt | 0/20 (0 %) | 0/20 (0 %) |
| Stack, auch vorübergehend | 0/20 (0 %) | 0/20 (0 %) |
| Stabiler Stack, weitere 2 s | 0/20 (0 %) | 0/20 (0 %) |

Voller Lift: gehaltenes B ≥ 1,045 m und EEF ≥ 1,049 m für drei Schritte; **„Höhe erreicht“ heißt noch nicht, dass bis dahin keine frühe XY-Bewegung stattfand**. Transport: gehaltenes B > 0,98 m, horizontale Geschwindigkeit > 0,02 m/s und Zielcosinus > 0,5 für drei Schritte. Vorzeitige Bewegung: dasselbe Bewegungskriterium bei B > 0,88 m, bevor beide vollen Höhenschwellen erreicht sind. Kleine kontinuierliche Bewegungen können dieses Kriterium erfüllen; daher separat die Befehle XY > 0,25 angeben. Positionierung < 9 mm, Absenken auf 40 ± 8 mm über A, Release mit Würfelkontakt; nativer Stack und weitere 2 s durchgehend stabil separat.

- **baseline:** maximale gehaltene Würfelhöhe, Median 0.996 m; absolut höchste erreichte Würfelhöhe 1.065 m; Würfelhöhe beim Transportbeginn, Median 1.011 m (n=5); Transportbeginn relativ zu vollem Lift-Ende, Median -1.98 s (n=2); vorzeitiger XY-Befehl 5/20; volle Höhe vor erstem Transport 0/20; XY-Richtungswechsel im Transport, Median 2.50.
- **dynamics:** maximale gehaltene Würfelhöhe, Median 1.033 m; absolut höchste erreichte Würfelhöhe 1.080 m; Würfelhöhe beim Transportbeginn, Median 1.026 m (n=10); Transportbeginn relativ zu vollem Lift-Ende, Median -2.80 s (n=2); vorzeitiger XY-Befehl 5/20; volle Höhe vor erstem Transport 1/20; XY-Richtungswechsel im Transport, Median 2.50.

XY-Distanz nach **erstem korrektem vollen Lift-Ende**, Mittel und gültiger Nenner:

| Zeit danach | Baseline | Dynamik |
|---|---:|---:|
| 0.5 s | 7.60 cm (n=2) | 10.95 cm (n=2) |
| 1.0 s | 7.49 cm (n=2) | 8.57 cm (n=2) |
| 2.0 s | 6.03 cm (n=2) | 5.00 cm (n=2) |

Diese bedingten Distanzen sind nur für Episoden mit vollem Lift definiert. Fehlende Lifts werden nicht als 0 cm oder als Transporterfolg behandelt. Verschiedene Nenner sind kein fairer alleiniger Transportvergleich. In beiden Varianten erreichen 0 gemeinsame Startzustände die volle Lift-Höhe: []. [Gepaarte Stufendifferenzen](rollout_matched.json), [alle individuellen Baseline-Werte](baseline/rollouts/results.json) und [Dynamik-Werte](dynamics/rollouts/results.json) enthalten max. Höhe, Transporthöhe, Zeitpunkt, Verzögerung und Richtungswechsel pro Seed. [Stufenvergleich](rollout_stages.png).

## Schlussfolgerung und nächster Versuch

Die explizite kontinuierliche Darstellung vorhandener Dynamik verbessert die Konditionierung und einige Offline-Zeitmetriken. **Sie reicht in diesem kontrollierten 5.000-Update-Versuch nicht aus, um den abrupten Expert-Moduswechsel zuverlässig abzubilden.** Dass die Sensitivität bereits auf Trainings-Grenzframes klein bleibt, spricht gegen ein ausschließlich durch neue Rollout-Zustände verursachtes Problem. Rollout-Stabilität kann zusätzlich beitragen, wird aber hier nicht als alleinige Erklärung behauptet.

Die Evidenz stützt damit **C mit einem Rollout-Trade-off** stärker als A. B wäre zu stark formuliert: Ein sauberer lokaler Umschaltmechanismus wurde offline gerade nicht gelernt. Transportstarts steigen von 5/20 auf 10/20, aber Greifen sinkt von 15/20 auf 12/20, Anheben von 11/20 auf 10/20 und der 3-cm-Zielbereich von 2/20 auf 1/20. Volle Lift-Höhe bleibt bei 2/20, vorzeitige Bewegung steigt von 8/20 auf 9/20, alle späteren Stufen bleiben null. Das ist ein Trade-off im Sinne von D und keine Behebung der Umschaltung. Die kleine feste Stichprobe und ein Trainingsseed erlauben keine Behauptung einer statistisch gesicherten allgemeinen Rollout-Verschlechterung. Die Daten beweisen nicht, welches Teilproblem von Diffusion-Lernziel, Konditionierung oder Chunk-Modellierung dafür verantwortlich ist.

Als nächsten Forschungsversuch ist ein **kontrollierter Vergleich mit einer anderen Policy-Struktur bzw. einem direkten Action-Chunk-Lernziel** sinnvoll: gleiche Beobachtungen, gleiche Daten, gleicher Updatebudget und dieselben gepaarten Grenztests. Zuerst prüfen, ob dieses Modell den Expert-Sprung empfindlicher abbildet; nicht gleichzeitig History, Phasenlabels oder Controller ändern. Dieser Vergleich wurde hier noch nicht implementiert. Ein einzelner Trainingsseed, 20 feste Rollout-Starts, redundante Δz/v-Kanäle und die Fortsetzung ab einem bereits trainierten Modell begrenzen die Verallgemeinerung. Weitere Repräsentationen oder Training von Grund auf sind damit nicht ausgeschlossen.

## Nachvollziehbarkeit

Für alle 40 Rollouts sind Simulatorzustände, tatsächliche Zwei-Frame-Observations einschließlich Dynamikkanälen und ursprüngliche/ausgeführte Aktionen gespeichert. Für beide Modelle sind alle offline gesampelten 16×7-Chunks gespeichert. Repräsentative Videos sind Replays dieser Zustände; keine weiteren Policy-Runs:

- Seed 46003: [gepaarte Zustands-/Aktionsverläufe](rollout_pair_46003.png), [Baseline-Video](baseline/rollouts/46003.mp4), [Dynamik-Video](dynamics/rollouts/46003.mp4).
- Seed 46004: [gepaarte Zustands-/Aktionsverläufe](rollout_pair_46004.png), [Baseline-Video](baseline/rollouts/46004.mp4), [Dynamik-Video](dynamics/rollouts/46004.mp4).

Es gibt keine erfolgreichen Stack-Rollouts; die Replays zeigen Zwischenfortschritte und charakteristische Fehler. [Isolationsprüfung](verification.json), [eingefrorenes Protokoll](protocol.json).

Reproduktion aus dem Workspace mit `praxis/.venv/Scripts/python.exe` und Skripten in `experiments/stack_diagnostics/stack_followup_20261001/scripts`: `dynamics_common.py` (Protokoll einmalig), `train_dynamics.py baseline|dynamics`, `offline_dynamics.py baseline|dynamics` (optional `--train-boundary`), `evaluate_dynamics.py baseline|dynamics`, `analyze_dynamics.py`, `diagnostics_dynamics.py`, `verify_dynamics.py`, `plot_dynamics_rollouts.py`, `render_dynamics.py`, `report_dynamics.py`. Vorbereitung/Training verweigern ein Überschreiben vorhandener Endcheckpoints; vor einer Replikation einen neuen Ausgabeordner verwenden.
