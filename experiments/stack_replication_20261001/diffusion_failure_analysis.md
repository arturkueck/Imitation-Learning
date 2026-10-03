# Forensische Analyse: Direct- und Diffusion-Checkpoints

**Kein Training, keine neuen Gewichte, keine Auswahl eines besseren Checkpoints.** Untersucht sind ausschließlich die sechs finalen Checkpoints aus `ERGEBNISSE.md`, Trainingsseeds 1–3, identische Startzustände 46000–46039.

Die Daten zeigen eine **häufig schwache und uneinheitlich gerichtete Transportverteilung**, obwohl einzelne Diffusionssamples verwendbare Kommandos enthalten. Auf Expert-Transportbeobachtungen sind 28–32% der ersten Aktionen stark und zielgerichtet; die übrigen erfüllen diese gemeinsame Bedingung nicht. Die erste ausgeführte Aktion ist im stabilen Transport **nicht systematisch schwächer** als die unmittelbar folgenden Aktionen. Fehlende Expert-Vollhöhe allein erklärt das Scheitern nicht: erfolgreiche Direct-Rollouts unterschreiten diese ebenfalls häufig.

**Kontrollierte Tests:** Diffusion bleibt bei 1/2/4 ausgeführten Aktionen und bei DDIM-5/10/50 in jedem Trainingsseed bei **0/40 stabilen Stacks**. In keiner dieser Bedingungen wird der Release-Indikator erreicht. Eine Aktion verschlechtert den Transportindikator in allen drei Seeds gegenüber zwei; vier Aktionen und DDIM-50 liefern gemischte Phasenverbesserungen, ohne das Stack-Problem zu lösen. DDIM-20 wurde vollständig offline ausgewertet.

Die Untersuchung beschreibt Fehler und kontrollierte Inferenzänderungen. Sie isoliert weder das Diffusionslernziel gegenüber der Architektur noch einen kausalen Effekt einzelner Gripperkommandos.

## Datengrundlage und Definitionen

- 20 bestehende Validierungsdemos × 21 eingefrorene Observations (Offsets −10…+10): **420 Histories**, jeweils zwei Frames und 15 rohe Merkmale je Frame. Alle Histories und alle **6.720 Expert-Chunkpositionen** sind bitgenau mit dem HDF5 abgeglichen.
- Pro Trainingsseed, Observation und DDIM-Konfiguration **64 vollständige 16×7-Samples**: insgesamt **322.560 Diffusionschunks**. Die ersten acht Initialrausch-Samples stammen aus dem vorhandenen Panel; 56 weitere aus dem fest gespeicherten RNG 20261001. Alle vier Schrittzahlen und alle Trainingsseeds verwenden dasselbe gespeicherte Initialrauschen.
- Chunkindex **0 = Aktion des vorherigen Frames**, **1 = erste tatsächlich ausgeführte Aktion**, 2 = zweite. Die drei Ausführungshorizonte verwenden exakt `[1:2]`, `[1:3]`, `[1:5]`. Tabellen speichern zusätzlich die 1-basierte Position, um Verwechslungen auszuschließen.
- XYZ/XY-Normen und Z sind **dimensionslose Controllerkommandos**, keine Meter. Z-Anteil = `abs(Z) / norm(XYZ)`; zusätzlich ist das vorzeichenbehaftete Z gespeichert. Gripper >0 schließt, <0 öffnet.
- Zielcosinus = XY-Aktion zur **EEF→Basiswürfel-A-Richtung in der eingefrorenen letzten Observation**. Derselbe Vektor gilt für alle Chunkpositionen. Vor der Transportphase sind Lift-Korrekturen in andere Richtungen nicht automatisch falsch.
- „Stark und zielgerichtet“: XY-Norm >0,25 und Zielcosinus >0,5. Zusätzlich ausgewertet: geschlossener Gripper und Stärke >50% der jeweiligen Expert-XY-Norm. Die Schwellen sind Diagnosen aus dem vorhandenen Protokoll, keine Erfolgsgarantie.
- Abweichung vom Expert: MSE über alle sieben Kanäle und XYZ-RMSE je passender zukünftiger Chunkposition. Samplevarianz wird **innerhalb derselben Observation** über 64 Ziehungen berechnet (ddof=1); danach Mittelung über Observations. Direct ist deterministisch und besitzt keine Samplingvarianz.
- Die Hauptauswertung „stabiler Transport“ verwendet die gleichen **100 Observations bei +6…+10** wie der Ausgangsbericht. Zusätzliche Tabellen enthalten das gesamte Panel, den Vorbereich und +0…+2. Die Hauptquantile sind Mittelwerte der **zustandsbedingten Quantile**, keine Quantile einer Mischung unterschiedlicher Zustände.
- Das eingefrorene Panel liegt um den Expert-Wechsel Lift→Transport. Es deckt keine vollständigen Greif- und Release-Episoden ab. Aussagen über spätes Öffnen oder Kontakte stammen aus den vollständigen Rollout-Traces.
- Historisch 240 gespeicherte Starts mit vollständiger Messphase; bei 20 Diffusion-Seed-1-NPZs fehlen die gespeicherten Tailframes. Neu vollständige 1/2/4-Tests und DDIM-5/10/50-Tests einschließlich aller Tails. 500 Schritte bei 20 Hz, anschließend 40 Stabilitätsframes. Jeder neue Startzustands-Hash wird gegen das eingefrorene Protokoll geprüft. Trainingsseeds bleiben die unabhängigen Replikate; keine Signifikanzbehauptungen aus gepoolten Samples oder Starts.

Der Abschlussaudit bestätigt **960 unterschiedliche neue Rollouts** (360 Direct, 600 Diffusion), 240 historische Starts, alle vollständigen neuen Traces und **2.640 zusätzliche native Chunkvergleiche mit Fehler 0 und identischem RNG-Zustand**. Die Ergebnismatrix enthält 27 Zeilen mit je 40 Starts; drei DDIM-10-Kontrollzeilen zeigen dieselbe Replanning-Baseline nochmals. Das sind 1.080 tabellierte neue Startzeilen, keine 1.080 unabhängigen Neurollouts.

## 1. Alle 16 Chunkpositionen

Vollständige Werte je Modell, Trainingsseed, Position, Phase und DDIM-Konfiguration stehen in `chunk_position_metrics.csv/.json`. Die folgende Grafik zeigt sämtliche Positionen des Transportpanels; die Schattierung markiert die zwei ausgeführten Baseline-Aktionen. Späte XYZ-Normen steigen vor allem mit der Absenkkomponente. Das ist kein Nachweis für stärkeren späteren XY-Transport.

![Alle 16 Positionen: XYZ, XY, Z, Richtung, Gripper und Expert-Abweichung](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_profiles.png>)

![Samplevarianz, Z-Anteil und Wahrscheinlichkeit starker zielgerichteter Aktionen](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_variance_probability.png>)

**Erste ausgeführte Aktion gegen die nächsten drei (Indizes 1 gegenüber 2–4):**

| Modell/Seed | XY Index 1 | XY 2–4 | Δ XY, gepaart | Obs mit erster Aktion schwächer | XYZ Index 1 | XYZ 2–4 |
| --- | --- | --- | --- | --- | --- | --- |
| direct/1 | 0.529 | 0.412 | 0.117 | 9.0% | 0.550 | 0.429 |
| diffusion/1 | 0.303 | 0.254 | 0.049 | 9.0% | 0.397 | 0.359 |
| direct/2 | 0.549 | 0.434 | 0.115 | 6.0% | 0.572 | 0.452 |
| diffusion/2 | 0.291 | 0.251 | 0.041 | 13.0% | 0.405 | 0.385 |
| direct/3 | 0.546 | 0.424 | 0.122 | 4.0% | 0.571 | 0.441 |
| diffusion/3 | 0.290 | 0.246 | 0.043 | 8.0% | 0.392 | 0.363 |

Diffusion: nur 8–13% dieser Observations haben eine schwächere erste XY-Aktion als den Mittelwert 2–4. Direct: 4–9%. Die Vermutung eines allgemein schwachen Chunkanfangs wird damit für den stabilen Transport nicht gestützt.

Falls „Action 1“ die **erste rohe Vorhersageposition** meint: Index 0 ist ebenfalls nicht systematisch XY-schwächer. Bei Diffusion beträgt seine XY-Norm **0,324 / 0,308 / 0,308** gegenüber **0,277 / 0,270 / 0,267** im Mittel der Indizes 1–3; nur 11% / 12% / 9% der Transportobservations zeigen die umgekehrte Relation. Diese Position wird jedoch als Vergangenheitsaktion nicht ausgeführt. `raw_first_vs_later.json` enthält denselben Vergleich für Direct und zusätzlich alle späteren Positionen.

**Phasenabhängigkeit:** Im Vorbereich und unmittelbar nach dem Expert-Wechsel sind die späteren XY-Aktionen im Mittel stärker — auch bei Direct. Der zukünftige Expert-Chunk ändert dort seine Bewegung. Ein über alle Phasen gepoolter Vergleich würde diese Änderung mit einem Positionsfehler verwechseln. `chunk_first_vs_later.json` enthält alle Phasen, den Vergleich 2–15 und die um den Expert-Verlauf bereinigte Differenz. Relativ zum Expert bleibt Diffusion am Transportanfang stärker unter der gewünschten Amplitude als später; das ist etwas anderes als eine absolut schwächere erste Aktion.

## 2. Identische Observation, 64 Samples

| Diffusionseed | Mittel ‖XY‖ | Q10 / Q50 / Q90 | ‖Mittelaktion XY‖ | Zielcosinus der Samples | P(stark+Ziel) | Schwacher Mittelwert mit brauchbaren Samples | Alle 64 schwach |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.303 | 0.041 / 0.179 / 0.767 | 0.227 | 0.496 | 32.1% | 59.0% | 0.0% |
| 2 | 0.291 | 0.040 / 0.164 / 0.757 | 0.203 | 0.481 | 29.3% | 73.0% | 0.0% |
| 3 | 0.290 | 0.041 / 0.163 / 0.754 | 0.207 | 0.477 | 28.5% | 69.0% | 0.0% |

**Antwort auf die Samplefrage:** Einzelne Samples sind brauchbar. In jeder der 100 Transport-Observations je Seed existiert mindestens ein starkes zielgerichtetes Sample; deren zustandsbedingte Wahrscheinlichkeit reicht von 6,25% bis 64,06%. In 59–73% dieser Observations ist die Norm der Mittelaktion ≤0,25, obwohl solche Samples existieren. Die bedingte Q90-XY-Norm liegt im Mittel bei 0,754–0,767, die bedingte Median-Norm nur bei 0,163–0,179. Das unterscheidet `E[‖aXY‖]` von `‖E[aXY]‖`. **Die native Policy führt ein einzelnes Sample aus, nicht diese gemittelte Aktion.** Die schwache Mittelaktion ist ein Diagnosebefund und kein tatsächlich angewandter Mittelungsfehler.

| Seed | Var(X) | Var(Y) | Var(Z) | Var(Gripper) | Lift- und Transportmodus jeweils ≥15% |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.065 | 0.065 | 0.064 | 0.017 | 73.0% |
| 2 | 0.065 | 0.067 | 0.086 | 0.023 | 69.0% |
| 3 | 0.061 | 0.067 | 0.069 | 0.015 | 66.0% |

Liftmodus: XY<0,12, Z>0,02, Gripper geschlossen. Transportmodus: XY>0,25, Zielcosinus>0,5, Z<−0,05, Gripper geschlossen. Beide Aktionsregime koexistieren in 66–73% identischer Transportobservations. Das zeigt breite, phasenuneinheitliche konditionierte Verteilungen. Eine deskriptive eindimensionale KDE der signierten Zielprojektion (drei Bandbreiten, Abstand ≥0,20, Prominenz ≥10%) erkennt bei keiner Transportobservation in allen drei Bandbreiten stabil mehrere Gipfel. Die gemeinsame zweidimensionale KDE von Zielprojektion und Z erkennt dagegen bei **12% / 11% / 11%** der Transportobservations mehrere lokale Gipfel über alle drei Bandbreiten. Kriterien: Scott-Bandbreite ×0,7/1/1,4, Gipfelhöhe ≥15% des Maximums, Abstand ≥0,20 und zugeordnete Samplemasse ≥10%. Diese explorative, koordinatenabhängige Dichteanalyse zeigt begrenzte Mehrgipfligkeit; sie ist kein formaler Multimodalitätstest und belegt keine allgemeine Zweimodalität.

![64 Samples je identischer Observation, exemplarisch vor, am und nach Wechsel](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_sample_modes.png>)

![Gemeinsame bedingte Dichte der Zielprojektion und Z-Kommandos](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_joint_density.png>)

![Bedingte Zieltransportwahrscheinlichkeiten und Aktionsregime für alle 20 Demos](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_probabilities.png>)

Die Beispielgrafik verwendet vorab festgelegt die lexikografisch erste Validierungsdemo `demo_109`, Offsets −1, 0 und +8, ohne Auswahl nach Erfolg. Alle Einzelbeobachtungen und alle 16 Positionen stehen in `sample_observation_metrics.csv`; rohe Samples in zwölf NPZ-Dateien.

![Bedingte XY-Richtung: parallel und quer zum Ziel; Schwellen für Stärke und Richtung](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_xy_direction.png>)

## 3. DDIM-Inferenz: zuerst offline

| Seed | DDIM | XY-Mittel | Zielcosinus | P(stark+Ziel) |
| --- | --- | --- | --- | --- |
| 1 | 5 | 0.300 | 0.536 | 33.5% |
| 1 | 10 | 0.303 | 0.496 | 32.1% |
| 1 | 20 | 0.316 | 0.497 | 33.0% |
| 1 | 50 | 0.328 | 0.498 | 33.8% |
| 2 | 5 | 0.285 | 0.524 | 30.3% |
| 2 | 10 | 0.291 | 0.481 | 29.3% |
| 2 | 20 | 0.301 | 0.470 | 29.3% |
| 2 | 50 | 0.311 | 0.458 | 29.7% |
| 3 | 5 | 0.276 | 0.481 | 28.1% |
| 3 | 10 | 0.290 | 0.477 | 28.5% |
| 3 | 20 | 0.303 | 0.483 | 29.5% |
| 3 | 50 | 0.316 | 0.484 | 30.5% |

DDIM-50 erhöht die Transport-XY-Norm gegenüber 10 in den drei Seeds um +0,025 / +0,020 / +0,027, die brauchbare Aktionswahrscheinlichkeit nur um +1,70 / +0,39 / +2,06 Prozentpunkte. DDIM-5 verbessert die Richtung in Seeds 1/2, hat aber geringere Stärke und keine konsistente Verbesserung über alle Seeds. DDIM-20 liegt in seinen Veränderungen überwiegend zwischen 10 und 50 und liefert keinen klaren zusätzlichen Vorteil.

**Offline-basierte Auswahl für Closed-loop:** DDIM-5 als günstiger Endpunkt mit besserer Richtung in zwei Seeds; DDIM-50 als Endpunkt mit konsistent höherer Stärke. DDIM-20 bleibt beim Offline-Test. Die Entscheidung wurde vor den entsprechenden Rollouts getroffen; kein Checkpoint- oder Erfolgsselektieren. EMA, 100 Trainingszeitschritte, Epsilon-Parametrisierung, ursprüngliche Betas, Clipping, eta=0 und Observationen bleiben unverändert.

![DDIM-Schrittzahlen auf exakt gepaarten Rausch-Samples](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/ddim_offline.png>)

## 4. Replanning und DDIM closed-loop

| Vergleich | Modell/Seed | Ausgeführte Actions | DDIM | Stabile Stacks / 40 | Greifen / Lift / Transport / Nähe / Position / Absenken / Release | Median Maxhöhe m | Median Min-XY gehalten+geliftet m (n) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ddim | diffusion/1 | 2 | 5 | 0 | 29 / 21 / 9 / 5 / 1 / 0 / 0 | 0.886 | 0.092 (21) |
| ddim | diffusion/1 | 2 | 10 | 0 | 31 / 24 / 15 / 4 / 0 / 0 / 0 | 0.915 | 0.090 (24) |
| ddim | diffusion/1 | 2 | 50 | 0 | 27 / 25 / 12 / 5 / 0 / 0 / 0 | 0.906 | 0.079 (25) |
| ddim | diffusion/2 | 2 | 5 | 0 | 27 / 14 / 5 / 0 / 0 / 0 / 0 | 0.874 | 0.126 (14) |
| ddim | diffusion/2 | 2 | 10 | 0 | 27 / 18 / 10 / 2 / 0 / 0 / 0 | 0.870 | 0.077 (18) |
| ddim | diffusion/2 | 2 | 50 | 0 | 30 / 22 / 13 / 4 / 1 / 0 / 0 | 0.892 | 0.060 (22) |
| ddim | diffusion/3 | 2 | 5 | 0 | 33 / 24 / 4 / 2 / 1 / 0 / 0 | 0.908 | 0.117 (24) |
| ddim | diffusion/3 | 2 | 10 | 0 | 25 / 21 / 7 / 2 / 1 / 0 / 0 | 0.890 | 0.084 (21) |
| ddim | diffusion/3 | 2 | 50 | 0 | 29 / 21 / 7 / 1 / 1 / 0 / 0 | 0.886 | 0.106 (21) |
| replanning | diffusion/1 | 1 | 10 | 0 | 31 / 24 / 5 / 0 / 0 / 0 / 0 | 0.890 | 0.115 (24) |
| replanning | diffusion/1 | 2 | 10 | 0 | 31 / 24 / 15 / 4 / 0 / 0 / 0 | 0.915 | 0.090 (24) |
| replanning | diffusion/1 | 4 | 10 | 0 | 34 / 23 / 12 / 1 / 1 / 1 / 0 | 0.923 | 0.087 (23) |
| replanning | diffusion/2 | 1 | 10 | 0 | 29 / 14 / 2 / 1 / 0 / 0 / 0 | 0.868 | 0.095 (14) |
| replanning | diffusion/2 | 2 | 10 | 0 | 27 / 18 / 10 / 2 / 0 / 0 / 0 | 0.870 | 0.077 (18) |
| replanning | diffusion/2 | 4 | 10 | 0 | 27 / 20 / 12 / 4 / 0 / 0 / 0 | 0.880 | 0.090 (20) |
| replanning | diffusion/3 | 1 | 10 | 0 | 24 / 19 / 3 / 0 / 0 / 0 / 0 | 0.866 | 0.100 (19) |
| replanning | diffusion/3 | 2 | 10 | 0 | 25 / 21 / 7 / 2 / 1 / 0 / 0 | 0.890 | 0.084 (21) |
| replanning | diffusion/3 | 4 | 10 | 0 | 26 / 22 / 11 / 5 / 1 / 0 / 0 | 0.899 | 0.089 (21) |
| replanning | direct/1 | 1 | — | 27 | 37 / 37 / 37 / 37 / 35 / 34 / 28 | 1.037 | 0.004 (37) |
| replanning | direct/1 | 2 | — | 28 | 37 / 37 / 37 / 37 / 37 / 36 / 30 | 1.039 | 0.003 (37) |
| replanning | direct/1 | 4 | — | 31 | 39 / 39 / 39 / 39 / 37 / 36 / 32 | 1.042 | 0.005 (39) |
| replanning | direct/2 | 1 | — | 29 | 36 / 36 / 35 / 35 / 35 / 35 / 31 | 1.038 | 0.003 (36) |
| replanning | direct/2 | 2 | — | 30 | 37 / 37 / 37 / 37 / 35 / 34 / 30 | 1.040 | 0.003 (37) |
| replanning | direct/2 | 4 | — | 28 | 37 / 37 / 36 / 36 / 33 / 33 / 29 | 1.043 | 0.003 (37) |
| replanning | direct/3 | 1 | — | 29 | 34 / 33 / 33 / 32 / 32 / 32 / 29 | 1.034 | 0.002 (33) |
| replanning | direct/3 | 2 | — | 31 | 35 / 34 / 34 / 34 / 34 / 34 / 31 | 1.036 | 0.002 (34) |
| replanning | direct/3 | 4 | — | 33 | 37 / 36 / 36 / 36 / 36 / 36 / 33 | 1.040 | 0.003 (36) |

Die Originalbaselines bleiben unverändert bei Direct 28/30/31 und Diffusion 0/0/0. Gepaarte Änderungen gegenüber der jeweils frischen Zwei-Aktions-Baseline stehen in `closed_loop_paired_changes.json`, einschließlich geretteter und verlorener Start-IDs. Die frische Bedingung h=2/DDIM-10 dient identisch als Referenz beider Vergleiche; die entsprechende Ergebniszeile wird zweimal gezeigt und ist kein zusätzlicher unabhängiger Lauf. Alle Diffusionsbedingungen werden im selben Prozess ausgeführt. Der Ausführungshorizont bleibt beim DDIM-Vergleich zwei.

**Replanning:** Transportindikator bei h=1: **5/2/3**, h=2: **15/10/7**, h=4: **12/12/11** Starts je Seed. Häufigeres Neusampling verschlechtert diesen Indikator konsistent; h=4 verbessert Seeds 2/3, verschlechtert Seed 1. Das ergibt keine einheitliche Rettung der späteren Phasen. Direct bleibt in allen drei Horizonten deutlich erfolgreicher; seine h=1/2/4-Stackzahlen sind je Seed 27/28/31, 29/30/28 und 29/31/33.

**DDIM:** Mehr Schritte reichen bei diesen Gewichten nicht aus. DDIM-50 verbessert den medianen gehaltenen/gelifteten Mindestabstand in Seeds 1/2, verschlechtert ihn in Seed 3; es erreicht 0/1/1 Positionierungen und keinen Release. DDIM-5 erreicht ebenfalls keinen Release. Die Distanzmediane sind auf Starts mit gehaltenem/geliftetem Objekt bedingt; die Spalte n weist die jeweilige Zahl aus. Sie sind deshalb keine unbedingten gepaarten Distanz-Effekte. Die gepaarten Änderungen und Start-IDs aller Phasen stehen separat im JSON.

![Gepaarte Horizonte 1/2/4: Stackrate, Höhe und Zielabstand](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/replanning_closed_loop.png>)

![Gepaarte DDIM-5/10/50-Rollouts](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/ddim_closed_loop.png>)

![Richtungs- und Gripperwechsel an Replanning-Grenzen und innerhalb eines Chunks](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/replanning_action_reversals.png>)

**Numerischer Audit:** `get_torch_device` im nativen robomimic-Code schaltet cuDNN-Benchmarking ein. Dessen Kernelwahl kann zwischen Prozessen und Batchgrößen variieren. Beim historischen Seed-1-Diffusion-Replay betrug die maximale Abweichung der ersten zwei Aktionen etwa 6,46e−5; später wich die Objekt-/EEF-Trajektorie deutlich ab. Alle 120 Direct-Baseline-Replays reproduzierten bitgenau. Daher werden historische und frisch gepaarte Baselines separat berichtet. Keine Backend-Präzision wurde als Intervention verändert: CUDA-Matmul-TF32 aus, cuDNN-TF32 an, Benchmarking an. Gemeinsame Prozesse behalten die gecachten nativen Kernel für die jeweiligen Bedingungen. Das beseitigt nicht jede mögliche Hardware-Nichtdeterministik.

**Ausführungsaudit der Beschleunigung:** Die Closed-loop-Diffusionsinferenz verwendet unveränderte Batch-1-DDIM-Operationen in einem CUDA-Graph und einen Ausführungsstream. Die ursprünglichen `torch.randn((1,16,7))`-Ziehungen werden pro Episode in derselben Reihenfolge vorab gespeichert; kein Sample wird gemittelt oder ausgewählt. Observationen durchlaufen dieselbe Float64→GPU→Float32-Konvertierung wie die native Policy. Zwei vollständige 540-Frame-Episoden wurden im selben Prozess gegen die unveränderte native Inferenz geprüft: maximaler Fehler in allen Zuständen, Aktionen, Grasp-, Kontakt- und Erfolgsindikatoren **0**. Zusätzliche Prüfungen an tatsächlich erreichten Zuständen vergleichen Konditionierung, Aktionen und RNG-Zustand pro Start bei den ersten zwei und jeder hundertsten Chunkziehung. Offscreen-Rendering wird abgeschaltet, da keine Bilder in die Policy eingehen; die vollständige Episodenparität umfasst diese Änderung. Technisch abgebrochene Versuche sind separat erhalten und gehen nicht in die Vergleichsmatrix ein.

Der instrumentierte Offline-Sampler reproduziert den nativen Batch-1-Sampler für 5/10/20/50 Schritte in jedem Trainingsseed exakt (maximaler Fehler 0). Gegen alte Batch-64-Artefakte können neue Batch-128-Ergebnisse abweichen; die maximale protokollierte Chunkabweichung ist rund 0,063 bei Seed 1/DDIM-50. Alle neuen Offline-Bedingungen verwenden die gleiche Batchgröße 128. Native-Sampler-Parität und historische Bytegleichheit sind unterschiedliche Prüfungen.

Auch alle wiederverwendeten Direct-Offlinechunks wurden neu gegen Batch-1-Inferenz der finalen EMA-Gewichte geprüft: 420 Observations ×16 Positionen je Seed. Maximale Abweichung über alle sieben Kanäle **2,96e−6**; Änderung der mittleren ersten Transport-XY-Norm <4e−8. Das bestätigt deren Zuordnung zu den untersuchten Checkpoints und eingefrorenen Zuständen.

Der gepaarte Vergleich der acht alten und neuen gemeinsamen Samples ist in `offline_batch_sensitivity.json` gespeichert. Auf den 100 Transportobservations beträgt die Änderung der mittleren ersten XY-Norm in allen verfügbaren Vergleichen höchstens 0,000004; die mittlere absolute Änderung pro Sample höchstens 0,000086. Die Klassifikation „stark+zielgerichtet“ wechselt nur bei einem von 800 Samples in Seed 1/DDIM-50 (0,125 Prozentpunkte), sonst bei keinem. Die maximale Chunkabweichung allein überschätzt damit die Sensitivität dieser Transportkennzahlen. Dies ist ein Vergleich alter und neuer Ausführung; Batchgröße und weitere Backenddetails sind dabei nicht unabhängig isoliert.

## 5. Closed-loop-Fehlerlokalisierung aller historischen Starts

| Modell/Seed | grasp | lift | transport_started | near | position | lower | release | sustained_success | Erfolg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| direct/1 | 3 | 0 | 0 | 0 | 0 | 1 | 6 | 2 | 28 |
| direct/2 | 3 | 0 | 0 | 0 | 2 | 1 | 4 | 0 | 30 |
| direct/3 | 5 | 1 | 0 | 0 | 0 | 0 | 3 | 0 | 31 |
| diffusion/1 | 9 | 7 | 9 | 11 | 4 | 0 | 0 | 0 | 0 |
| diffusion/2 | 14 | 8 | 10 | 6 | 2 | 0 | 0 | 0 | 0 |
| diffusion/3 | 13 | 8 | 10 | 7 | 0 | 2 | 0 | 0 | 0 |

Erster nicht erfüllter Indikator in der angegebenen Reihenfolge. Die Indikatoren sind nicht zwingend verschachtelt und nicht jeder ist eine notwendige native Success-Bedingung. Expert-Vollhöhe wird separat gespeichert und nicht als verpflichtende Fehlerstufe behandelt. Das verhindert, dass ein erfolgreiches niedriges Direct-Stack fälschlich als Liftfehler klassifiziert wird.

![Fehlerphase, maximale Höhe und erster nicht regelgerechter Grasp-Verlust aller 240 Starts](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/baseline_failure_map.png>)

Kriterien aus dem bestehenden Protokoll: **Grasp** = natives Prädikat; **Lift** = B-z>0,88 m; **Transport gestartet** = gehalten, B-z>0,98 m, XY-Geschwindigkeit>0,02 m/s, Bewegungsrichtung B→A mit Cosinus>0,5 für drei Frames. **Nähe** = XY<3 cm und relative B−A-Höhe>3,2 cm; **Position** = XY<9 mm bei derselben Höhenbedingung; **Absenken** = zusätzlich relative Höhe 4 cm ±8 mm; **Release** = zusätzlich Würfelkontakt und kein Grasp. **Stabil** = ursprüngliche native Success-Bedingung durchgehend in 40 zusätzlichen Frames, Würfelkontakt und freigegebenes Objekt. Expert-Vollhöhe verlangt separat B-z≥1,045 m und EEF-z≥1,049 m für drei Frames. Online-Zieltransport- und Wechselanalysen verwenden die aktuelle B→A-Richtung; Offline-Aktionscosinus verwenden den oben definierten eingefrorenen EEF→A-Vektor.

| Modell/Seed | Starts mit nicht regelgerechtem Grasp-Verlust | Median Maxhöhe m | Median minimale XY gehalten+geliftet m | Median Gripperwechsel |
| --- | --- | --- | --- | --- |
| direct/1 | 7 | 1.039 | 0.003 | 2 |
| direct/2 | 4 | 1.040 | 0.003 | 2 |
| direct/3 | 3 | 1.036 | 0.002 | 2 |
| diffusion/1 | 29 | 0.915 | 0.090 | 90 |
| diffusion/2 | 26 | 0.866 | 0.079 | 90 |
| diffusion/3 | 25 | 0.869 | 0.082 | 86 |

Objektverlust wird operationalisiert als Wechsel des nativen Grasp-Prädikats von wahr zu falsch. Jede Transition ist gespeichert; zusätzlich Dauer bis Wiedergriff, mindestens drei Frames ohne Grasp, EEF–B-Abstand und Höhenänderung nach fünf Frames. „Nicht regelgerechte Freigabe“ bedeutet, dass Abstand <9 mm, relative Höhe 4 cm ±8 mm und Würfelkontakt am Ereignis nicht gemeinsam erfüllt sind. Ein kurzfristiger Prädikatwechsel ist nicht automatisch ein physischer Fall.

![Kommandos um den ersten nicht regelgerechten Grasp-Verlust; bedingte Mediane und IQR](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/loss_aligned_actions.png>)

Die Ereignisgrafik wählt pro Start den ersten nicht regelgerechten Grasp-Verlust: 80 Diffusion- und 14 Direct-Starts. Ihre Schattierung ist der Interquartilsbereich über diese ausgewählten Fälle, kein Konfidenzintervall. Diffusions-XY-Normen unmittelbar davor haben seedweise Mediane von **0,020 / 0,024 / 0,022**, XYZ-Normen **0,043 / 0,066 / 0,043**. Die Zielabstände beim ersten Verlust liegen im Median bei **12,90 / 13,20 / 12,20 cm**, bei Direct **1,61 / 1,40 / 1,98 cm**. Diese Ereignisse liegen häufig vor dem stabilen Transport und sind nicht dieselben Zustände wie das eingefrorene Expert-Transportpanel.

Zeitbezug: Traceindex `i` enthält Zustand **nach** Aktion `i`; Zeit seit Reset `(i+1)×0,05 s`. Vorfehleramplitude ist Aktion `i−1`; die am Verlust beteiligte Aktion `i` steht separat daneben. Bei gescheiterter Stabilisierung wird der erste beobachtete native Success-Verlust im 40-Frame-Tail mit Zeit und Vorfehleramplitude gespeichert. Sonst ist der Fehleranker der erste nicht regelgerechte Grasp-Verlust, ohne Behauptung, er verursache den endgültigen Aufgabenfehler. Nie erreichte Phasen bleiben am Messhorizont zensiert; CSV enthält dann die Horizontamplitude und keinen erfundenen Ereigniszeitpunkt. Gripperwechsel und alle Grasp-Verluste innerhalb der Messphase stehen im JSON; CSV enthält pro Start erste Zeiten sowie Counts. Maxhöhe und Mindestabstand werden sowohl bis zum Messhorizont als auch über den gesamten verfügbaren Trace ausgegeben. Bei den ersten 20 historischen Diffusion-Seed-1-Traces fehlen die Tailframes im NPZ; diese Lücke wird ausgewiesen, alle neuen Rollouts besitzen vollständige Tails.

## 6. Höchstens drei Ursachenhypothesen

### H1: Zustandsbedingte Aktionsverteilung liefert zu selten hinreichenden Zieltransport

**Dafür:** Bei eindeutigen Expert-Transportobservations nur 28–32% starke zielgerichtete Samples, Zielcosinus etwa 0,477–0,496 gegenüber Direct nahe 1; 66–73% identischer Zustände enthalten relevante Lift- und Transportregime. Die Median-Samplestärke liegt weit unter dem Expert. Die historische Diffusion erreicht nur 0/0/2 Positionierungen und kein Absenken oder Release.

**Dagegen / Grenze:** Einzelne Samples sind durchaus stark und zielgerichtet; die mittlere Aktionsrichtung ist deutlich besser als die mittlere Sample-Richtung. Keine robust zweigipflige Zielprojektionsdichte nachgewiesen. Expert-Observations sind nicht die im Rollout erreichten Zustände. Die Analyse trennt Lernziel, Architektur, Konditionierungsrepräsentation und möglichen Rollout-Verteilungswechsel nicht kausal.

**Bewertung:** Das Defizit der bedingten Aktionsverteilung ist belegt. Sein isolierter kausaler Beitrag zum Rollout-Scheitern und seine Entstehungsursache bleiben offen.

### H2: Häufiges Neusampling könnte kohärente Bewegungen unterbrechen und den Transport verschlechtern

**Dafür:** Innerhalb eines gezogenen Chunks sind aktive XY-Aktionen Index 1 und 3 sehr kohärent (Cosinus 0,974–0,983), während bei jedem Replanning neues Rauschen gezogen wird. Unter einem bereits starken zielgerichteten ersten Kommando bleiben 69–73% der Samples über alle ersten vier Kommandos stark, zielgerichtet und geschlossen. Ein anderer Modus bei der nächsten Ziehung ist somit plausibel.

**Intervention:** Stabile Stacks pro Seed: h=1: 0/0/0; h=2: 0/0/0; h=4: 0/0/0. Das beschreibt den direkten Test der Replanning-Hypothese. Längeres Ausführen ändert zugleich Reaktionslatenz und Anzahl der Rauschziehungen; ein isolierter Effekt von „Moduswechseln“ ist damit nicht bewiesen.

**Dagegen / Grenze:** Die erste ausgeführte Aktion ist im stabilen Transport nicht absolut schwächer als die folgenden. Die vierteilige Erfolgsbedingung wird nur von 20–22% aller Samples erfüllt. Größere Chunks können ebenso unpassende Aktionen länger ausführen. Mehr Richtungswechsel an Replanning-Grenzen allein wären kein Kausalbeweis.

**Bewertung:** Als Erklärung einzelner Transportdefizite teilweise gestützt: h=1 erreicht seltener Transport. Als alleinige Erklärung der 0/40-Stacks im getesteten Bereich nicht gestützt: h=4 erreicht weiterhin keinen Release und keinen stabilen Stack. Richtungsumkehrungen liegen beim h=2-Test an Replanning-Grenzen bei 25–29% der geeigneten Paare, innerhalb eines Chunks nur bei 0,2–0,3%; das ist ein bedingter Zusammenhang, kein isolierter Moduswechsel-Effekt.

### H3: Instabiler Griff und unpassende Gripperwechsel könnten nachhaltigen Lift/Transport verhindern

**Dafür:** Historisch 80/120 Diffusionstarts mit mindestens einem nicht regelgerechten Grasp-Verlust; 36/120 erreichen keinen Grasp und weitere 23/120 keinen Lift als ersten fehlenden Indikator. Die Einzelereignisse erlauben den zeitlichen Abgleich mit Öffnungskommandos und Armamplitude.

Unter 206 nicht regelgerechten nativen Grasp-Transitionen liegen 167 unmittelbar bei einem Öffnungskommando, 171 bei Öffnung in den letzten drei Kommandos. 182 dauern mindestens drei Frames.

**205 von 206** dieser Diffusionsereignisse liegen weiter als 3 cm vom Ziel entfernt; alle **167** Ereignisse mit gleichzeitigem Öffnungskommando liegen außerhalb dieses Bereichs. Bei den ersten Verlusten pro Start wird in **27/29, 19/26 und 17/25** Fällen geöffnet. Das unterscheidet den Befund von einer bloßen Verletzung des sehr engen 9-mm-Freigabefensters.

**Dagegen / Grenze:** Auf den eingefrorenen Expert-Transportobservations sind Gripperbefehle überwiegend geschlossen; Öffnung ist dort keine allgemeine Erklärung schwacher XY-Samples. Verlust kann auch durch Armbewegung oder Kontaktgeometrie entstehen. Häufigkeit und zeitliche Nähe belegen keine Gripperkausalität; ein isolierter Gripper-Eingriff wurde in dieser Untersuchung nicht vorgenommen. Nicht erreichte Expert-Vollhöhe allein ist durch die erfolgreichen Direct-Gegenbeispiele widerlegt.

Konkret erreichen **19 / 23 / 26** der erfolgreichen historischen Direct-Starts die Expert-Vollhöhe nicht: insgesamt **68 von 89** stabilen Stacks. Ein pauschales Vollhöhenkriterium würde diese erfolgreichen Gegenbeispiele übersehen.

**Bewertung:** Frühes Öffnen fern vom Ziel und Grasp-Verlust sind zeitlich und räumlich belegt. Ob ein stabilisierter Gripper allein die Stacks retten würde, ist ohne entsprechenden isolierten Test nicht entschieden.

## Artefakte und Reproduktion

Alle Ergebnisse liegen in `failure_analysis/`. Hauptdateien:

- [DATA_DICTIONARY.md](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/DATA_DICTIONARY.md>)
- [protocol.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/protocol.json>)
- [final_input_verification.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/final_input_verification.json>)
- [final_evaluation_audit.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/final_evaluation_audit.json>)
- [stream_episode_parity_v5.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/stream_episode_parity_v5.json>)
- [direct_offline_parity.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/direct_offline_parity.json>)
- [chunk_position_metrics.csv](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_position_metrics.csv>)
- [chunk_position_metrics.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_position_metrics.json>)
- [chunk_first_vs_later.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_first_vs_later.json>)
- [raw_first_vs_later.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/raw_first_vs_later.json>)
- [sample_observation_metrics.csv](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/sample_observation_metrics.csv>)
- [sample_summary.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/sample_summary.json>)
- [conditional_density_modes.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_density_modes.json>)
- [conditional_joint_density_modes.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/conditional_joint_density_modes.json>)
- [chunk_coherence.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/chunk_coherence.json>)
- [ddim_paired_comparison.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/ddim_paired_comparison.json>)
- [offline_batch_sensitivity.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/offline_batch_sensitivity.json>)
- [baseline_failures.csv](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/baseline_failures.csv>)
- [baseline_failures.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/baseline_failures.json>)
- [baseline_events.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/baseline_events.json>)
- [loss_first_events.csv](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/loss_first_events.csv>)
- [loss_event_summary.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/loss_event_summary.json>)
- [closed_loop_summary.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_summary.json>)
- [closed_loop_failures.csv](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_failures.csv>)
- [closed_loop_failures.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_failures.json>)
- [closed_loop_events.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_events.json>)
- [closed_loop_paired_changes.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_paired_changes.json>)
- [historical_replay_comparison.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/historical_replay_comparison.json>)
- [closed_loop_action_coherence.json](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/failure_analysis/closed_loop_action_coherence.json>)

Die zwölf Dateien `diffusion_seed{1,2,3}_ddim{5,10,20,50}.npz` speichern sämtliche Rohchunks `[Observation, Ziehung, Chunkposition, Kanal]`; `noise64.npy` speichert identisches Initialrauschen. Neurollouts speichern Observationen und vollständige Zustands-/Aktions-Traces; die Originalrollouts und Checkpoints bleiben erhalten.

Reproduzierbar über die vorhandene Python-Umgebung `praxis/.venv/Scripts/python.exe`: zuerst `scripts/audit.py`, dann `scripts/offline.py --seed 1/2/3`, `scripts/direct_offline_audit.py`, `scripts/localise.py`, `scripts/stats.py`, `scripts/raw_first.py`, `scripts/modes.py`, `scripts/modes2d.py`, `scripts/batch_sensitivity.py`, `scripts/direction_plot.py`. Direct-Rollouts: `scripts/run_closed.py --direct-only`; Diffusion: `scripts/validate_streams.py`, danach `scripts/run_final_closed.py`. Anschließend `scripts/summarise_closed.py`, `scripts/plots.py`, `scripts/loss_plot.py`, `scripts/closed_plots.py`, `scripts/audit.py --final`, `scripts/final_qc.py` und `scripts/report.py`. Vorhandene abgeschlossene Rollout-Dateien werden fortgesetzt beziehungsweise wiederverwendet. Die gescheiterte Vier-Stream-Paritätsprüfung (`stream_validation_v6.log`) ist ausschließlich technischer Audit und kein Modellversuch. Offline und Closed-loop-GPU-Läufe werden seriell gehalten. Kein Skript enthält Training oder Optimizer-Updates.
