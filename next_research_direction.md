# Nächste Forschungsrichtung: Behavioural Cloning für Stack mit State-Input

**Aktualisierung vom 4. Oktober 2026:** Aktuelles Ziel, priorisierte
Algorithmusvorschläge und Bedingungen für neue Experimente stehen in
[FORSCHUNGSPLAN.md](FORSCHUNGSPLAN.md). Der nachfolgende Stand vom 1. Oktober
bleibt als Literatur- und Planungshistorie erhalten; er ist kein Auftrag,
die vorgeschlagenen Trainingsläufe automatisch auszuführen.

**Recherche- und Projektstand: 1. Oktober 2026.** Diese Ausarbeitung verbindet die lokale Replikation mit einer aktuellen, gezielten Literaturrecherche. Sie enthält Experimentpläne, keine neu erzielten Trainingsergebnisse. Laufzeit- und Implementierungsangaben für neue Ansätze sind Planungsschätzungen.

## 1. Wissenschaftlicher Ausgangspunkt

Die sinnvollste nächste Fragestellung lautet: **Welche begrenzte Erweiterung verbessert Aufgabenlösung oder Robustheit des bereits erfolgreichen Direct-Modells, und welcher Mechanismus erklärt den Effekt?** Exaktes Expert-Timing sollte dabei eine Diagnose bleiben. Es ist in diesem System kein ausreichendes Hauptziel.

Aus der [Seed-Replikation](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/ERGEBNISSE.md>) ergeben sich:

- Direct: 70,0 / 75,0 / 77,5 % stabile Stacks, Mittelwert **74,2 %**, Stichproben-SD **3,8 Prozentpunkte** über drei Trainingsseeds; jeweils 40 identische Starts.
- Diffusion: **0/40 pro Trainingsseed**, insgesamt 0/120. Das widerlegt diese konkrete Konfiguration unter diesem Budget, nicht Diffusion Policy als Modellfamilie.
- Direct reproduziert den abrupten Expert-Sprung ebenfalls kaum. Trotzdem transportieren 70/89 erfolgreiche Direct-Rollouts vor dem Expert-Vollhöhenkriterium; 68/89 erreichen diese Vollhöhe nicht.
- XY-Aktionsstärke und Zielrichtung unterscheiden die Modellklassen deutlich. Die gepoolten Korrelationen über sechs Modelle sind jedoch durch den Klassenunterschied konfundiert. Drei Seeds innerhalb Direct reichen nicht zur Validierung eines allgemeinen Offline-Prädiktors.
- Fünf Starts scheitern bei allen Direct-Seeds; darunter wiederholte Greif-, Absenk- und Release-Probleme. Transport ist bei Direct bereits wesentlich zuverlässiger als bei Diffusion.

**Folgerung aus diesen Projektdaten:** Eine Erweiterung muss stabile Stacks, vollständige Phasen und Störungsrobustheit messen. Eine größere Grenzreaktion, kleinere Validierungs-MSE oder späterer Transportbeginn allein wäre kein hinreichender Erfolg.

### Was tatsächlich implementiert und trainiert wurde

Gelesen wurden die [Projektbeschreibung](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/Projektarbeit Themenvorschlag -- Artur.md>), der Replikationsbericht samt Protokoll und Seed-Konfigurationen, Direct-Trainer/-Policy, Datenfenster, Evaluationsmetriken, StackExpert und StackTwo-Umgebung. Hinzu kamen die bisherigen [Dynamikversuche](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_dynamics_20261001/ERGEBNISSE.md>), [Balancierung](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/ERGEBNISSE.md>), [Placement-Diagnose](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_placement_20261001/DIAGNOSE.md>) und die lokale Lift-Erweiterung.

| Bestandteil | Verifizierter lokaler Stand | Konsequenz für die Erweiterung |
|---|---|---|
| Task | Lokales `StackTwo`, von robosuite Stack abgeleitet; zwei gleich große 4-cm-Würfel, eigener Stabilitäts-/Kontaktcheck | Ergebnisse sind kein unveränderter offizieller robomimic-Stack-Benchmarkscore. |
| Expert | Programmierter, zustandsbehafteter `StackExpert`; interne Phase, gespeichertes Ziel, Verweilzeiten | Ein Expert-Objekt bei einem fremden Zustand neu zu initialisieren liefert nicht automatisch ein korrektes DAgger-Label. |
| Daten | 200 erfolgreiche programmierte Demos; unveränderter Split 180 Training / 20 Validierung, 27.322 Trainingsanker | Keine 200 menschlichen PH-Demos. Validierungsdemos werden nicht nachträglich Trainingsdaten. |
| Eingaben | 15 Merkmale pro Frame: A-/B-Positionen im 6-dimensionalen `object`, EEF-Position, EEF-Quaternion, Gripperpositionen; zwei Frames | `object` enthält hier absolute Würfelpositionen. Die relativen Lift-Features dürfen nicht angenommen werden. |
| Direct | Residual-MLP, acht Blöcke, Breite 2048, 67.467.376 Parameter; MSE auf 16×7 Aktionen, Tanh-Ausgabe | Strukturell einfacher Regressor, aber kein kleines Netz. Action Chunking ist bereits vorhanden. |
| Diffusion | UNet, 65.648.903 Parameter, Epsilon-Lernziel, DDIM mit zehn Schritten | Klassenvergleich verändert Architektur und Lernziel zugleich. |
| Zeitindex | Trainingschunk am Anker t enthält Aktionen t−1 bis t+14; ausgeführt werden Indizes 1 und 2, also t und t+1 | Index 0 ist Vergangenheit. Ensembling und neue Wrapper müssen diese Ausrichtung erhalten. |
| Training | 30.000 Updates, Batch 8, uniforme Fenster, AdamW 1e−4, Cosine mit 500 Warmup-Schritten, EMA 0,75 | Bestehende Baseline bietet einen festen, überschaubaren Vergleich. |
| Skalierung | Rohbeobachtungen unnormalisiert, Actions bereits in [−1,1] | Normalisierung ist eine mögliche eigene Kontrolle, nicht stillschweigend mit einer neuen Methode zu kombinieren. |
| Evaluation | 500 Schritte bei 20 Hz; stabile Success-Bedingung über zusätzliche 40 Frames / 2 s | Das strenge Kriterium bleibt unverändert. |
| Hardware | Eine CUDA-GPU mit 12 GB VRAM; gemessene Direct-Trainingszeit circa 11 min, Diffusion circa 37–51 min | Breite Architektursuche ist weniger attraktiv als gezielte Ablation. |

Quellcode: [Direct-Modell und Wrapper](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_followup_20261001/scripts/direct_common.py>), [Training](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_followup_20261001/scripts/train_direct.py>), [Fenster und Metriken](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_followup_20261001/scripts/balance_common.py>), [Umgebungen](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/src/task_extensions/environments.py>), [Expert](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/src/task_extensions/stack_expert.py>).

Die 62 Demos mit schwarzen Bildabschnitten bleiben für State-Experimente im Datensatz. Sie sind kein begründeter Ausschlussgrund, solange keine RGB-Eingaben verwendet werden. Das fehlende vollständige Expert-Rückzugssegment begrenzt die Aussage zur Rückzugsfähigkeit; ein vollständiger Rückzug ist im bisherigen Erfolgskriterium nicht verlangt.

Die frühere Phasenbalancierung verbesserte einige Transportdiagnosen der Diffusion, verschlechterte aber Lift und löste keinen stabilen Stack. Explizite Δz-/Geschwindigkeitsfeatures verstärkten die Grenzreaktion, ohne damit den Task zu lösen. Diese Varianten sind keine belegten Verbesserungen der Direct-Baseline.

## 2. Robomimic-Abgleich: Release, Quellcode und lokale Erweiterungen

Lokal steht robomimic **0.5.0**, Commit `d309eaecc18acf4152a830a895a6984b8ac71b05`; dies ist im Checkout und im eingefrorenen Requirements-Stand geprüft. Die am Recherchedatum abrufbare [offizielle Release-Seite](https://github.com/ARISE-Initiative/robomimic/releases) führt v0.5 als neuestes Release. Die öffentlichen Registry-/Konfigurationsdateien wurden zusätzlich gelesen. Aussagen zur Verfügbarkeit beziehen sich auf diesen geprüften Stand, nicht auf beliebige externe Forks.

Vorhanden sind deterministisches BC, Gaussian/GMM/VAE, BC-RNN, BC-Transformer sowie UNet-Diffusion Policy. BC-Transformer hat `pred_future_acs`; damit ist zukünftige Aktionssupervision bereits vorgesehen. Die Standard-`get_action`-Methode liefert bei dieser Option die erste vorhergesagte Aktion und stellt keine vollständige ACT-Ausführungslogik mit temporalem Ensembling bereit. [Registry](https://raw.githubusercontent.com/ARISE-Initiative/robomimic/master/robomimic/algo/__init__.py), [BC-Konfiguration](https://raw.githubusercontent.com/ARISE-Initiative/robomimic/master/robomimic/config/bc_config.py), [BC-Implementierung](https://github.com/ARISE-Initiative/robomimic/blob/d309eaecc18acf4152a830a895a6984b8ac71b05/robomimic/algo/bc.py).

**Wichtiger Codebefund für Noise Injection:** Der lokale `GaussianNoiseRandomizer` verwendet in `_forward_in` `torch.rand * noise_std + noise_mean`. Das ergibt für positive `noise_std` gleichverteiltes, standardmäßig positiv verschobenes Rauschen, keine zentrierte Normalverteilung. Derselbe Ausdruck steht im geprüften öffentlichen Quellcode. Seine Standardstärke 0,3 wäre zudem für rohe Positionswerte in Metern sehr groß. Für ein kontrolliertes Gaussian-Experiment ist deshalb ein eigener, expliziter `torch.randn`-Perturbationspfad mit physikalischen Einheiten nötig. Die bestehende Direct-Policy umgeht Robomimics Observation Encoder ohnehin. [Randomizer-Code](https://raw.githubusercontent.com/ARISE-Initiative/robomimic/master/robomimic/models/obs_core.py), lokal [obs_core.py](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/upstream/robomimic/robomimic/models/obs_core.py>).

Lokal existiert bereits [Contraction-BC für Lift](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/src/robomimic_ext/contraction_bc.py>). Es erwartet Feedforward-BC und einen 10-dimensionalen Lift-Objektvektor. Es implementiert eine finite-difference Ein-Schritt-Näherung, **nicht den Original-Stable-BC-Loss**. Weder Stack-Daten noch Direct-Chunks sind direkt kompatibel. Auch die Lift-Dynamikmatrix darf nicht ungeprüft übertragen werden.

## 3. Literaturvergleich entlang der zehn gewünschten Kriterien

Die drei folgenden Tabellen bilden gemeinsam die Kriterien **1–10** für jeden Ansatz ab. Aufwand bedeutet zusätzliche Arbeit gegenüber dem bestehenden Projekt. Die Tagesangaben sind grobe persönliche Arbeitsbudgets inklusive Integration und Fehlerprüfung; sie sind keine veröffentlichten Benchmarks. Rechenfaktoren sind ungemessene Größenordnungen, sofern ausdrücklich keine lokalen Messwerte genannt werden.

### 3.1 Enthalten? Publikationsstatus? Mechanismus? — Kriterien 1 und 2

| Ansatz | 1. In geprüftem robomimic enthalten? | 2. Publikationsstatus und belegter Mechanismus |
|---|---|---|
| Stable-BC | Nein. Lokale Lift-Kontraktion ist nur inspiriert. | **Peer-reviewed: IEEE RA-L 2025**, DOI 10.1109/LRA.2025.3526439; ursprünglicher Preprint 2024. Regularisiert lokale Fehlerdynamik; modellfreie Variante benötigt weiterhin Annahmen über Roboterdynamik und beschränkte Umgebungsabweichung. [Journal](https://ieeexplore.ieee.org/document/10829660/), [Autorenprojekt](https://collab.me.vt.edu/Stable-BC/), [frei zugängliche Paperfassung](https://arxiv.org/html/2408.06246v1). |
| DART | Kein vollständiger Datenerhebungsalgorithmus. Observation Noise ersetzt DART nicht. | **Peer-reviewed: CoRL 2017.** Stört ausgeführte Expert-Aktionen während der Datenerhebung und zeichnet Expert-Korrekturen auf; Störungsniveau wird an Policy-Fehler angepasst. [Proceedings](https://proceedings.mlr.press/v78/laskey17a.html). |
| DAgger | Kein vollständiger interaktiver Aggregationsworkflow in der geprüften Registry. | **Peer-reviewed: AISTATS 2011.** Sammelt Expert-Labels auf Zuständen, die die aktuelle Policy besucht, und trainiert auf aggregierten Daten. [Proceedings](https://proceedings.mlr.press/v15/ross11a.html). |
| ACT / Action Chunking | **Chunking teilweise bereits vorhanden**: Direct, Diffusion und zukünftige BC-Transformer-Aktionen. Original-ACT mit CVAE und temporalem Ensembling nicht vollständig vorhanden. | **Peer-reviewed: RSS 2023.** ACT kombiniert Transformer, latente Aktionsfolgenmodellierung und temporales Ensembling. Ein Chunk-Regressor allein ist keine ACT-Reproduktion. [Proceedings](https://www.roboticsproceedings.org/rss19/p016.html). |
| Noise Injection / State Perturbation | Randomizer-Infrastruktur vorhanden; siehe Verteilungsfehler oben. Strukturierte, kanal- und zeitkonsistente Direct-Perturbation fehlt. | Allgemeine Technik, **kein einzelnes Paper mit eindeutigem Status**. DART liefert peer-reviewte Evidenz für gestörte Datenerhebung; daraus folgt keine Garantie für Offline-Input-Jitter mit unveränderten Labels. [DART](https://proceedings.mlr.press/v78/laskey17a.html), [Robomimic-Code](https://raw.githubusercontent.com/ARISE-Initiative/robomimic/master/robomimic/models/obs_core.py). |
| Data Augmentation | Bild-Crop/Color/Noise vorhanden. Task-konsistente State-Transformation und simulierte Trajektoriengenerierung fehlen als fertiger Stack-Workflow. | Allgemeine Technik. **MimicGen: peer-reviewed CoRL 2023** als konkreter Vertreter simulatorbasierter Demonstrationsgenerierung. Die hier vorgeschlagene kleine State-Translation ist eine eigene Ablation, keine MimicGen-Reproduktion. [MimicGen](https://proceedings.mlr.press/v229/mandlekar23a.html). |
| DiffClone | Nein als eigenständiges Verfahren; der Kern einer konditionierten Diffusionspolicy überlappt stark mit vorhandener Diffusion Policy. | **Preprint: arXiv:2401.09243, v3 2024**; dokumentierter NeurIPS-2023-TOTO-Workshop-/Competition-Beitrag. Keine begutachtete Hauptkonferenz-/Journalversion in den geprüften Quellen verifiziert. Visuelle Repräsentation und Diffusionspolicy für TOTO. [Paper und Status](https://arxiv.org/abs/2401.09243), [Volltext](https://arxiv.org/html/2401.09243v3). |
| Diffusion Model-Augmented BC (DBC) | Nein; vorhandene Diffusion Policy ist kein DBC. | **Peer-reviewed: ICML 2024.** Separates Modell der gemeinsamen Expert-Verteilung ergänzt den konditionalen BC-Loss; Policy bleibt eine gesonderte Komponente. [Proceedings](https://proceedings.mlr.press/v235/chen24as.html). |
| Consistency Policy | Nein. | **Peer-reviewed: RSS 2024.** Destilliert eine Diffusionspolicy in einen Generator mit wenigen Schritten. Der primäre Beitrag betrifft Inferenzaufwand. [Proceedings](https://www.roboticsproceedings.org/rss20/p071.html), [Autoren-Code](https://github.com/Aaditya-Prasad/Consistency-Policy/). |
| Conditional Flow Matching / PointFlowMatch | Nein. | **Peer-reviewed: CoRL 2024**, Proceedings veröffentlicht 2025. Untersucht Flow Matching und Eingabe-/Pose-Repräsentationen; Originalmethode verwendet Point Clouds. Ein State-Flow-Modell wäre eine Adaption. [Proceedings](https://proceedings.mlr.press/v270/chisari25a.html). |
| Streaming Flow Policy (SFP) | Nein. | **Peer-reviewed: CoRL 2025.** Erzeugt eine Aktionsfolge als Flow-Trajektorie, ausgehend von einer schmalen Verteilung um die letzte Aktion; Aktionen können während der Integration ausgeführt werden. [Proceedings](https://proceedings.mlr.press/v305/jiang25a.html). |
| FA-OPD | Nein. | **Peer-reviewed: ICML 2026.** Flow-Matching-Teacher und MLP-Student werden mit Aktions- und adversarialem Reward-Kanal auf Policy-Rollouts trainiert. Geht über rein offline BC hinaus. [Proceedings](https://proceedings.mlr.press/v306/wan26n.html). |
| Posterior Behavioral Cloning | Nein. | **Peer-reviewed: ICML 2026.** Modelliert den Posterior des Demonstratorverhaltens, um eine bessere Initialisierung für anschließendes RL-Finetuning zu schaffen. [Proceedings](https://proceedings.mlr.press/v306/wagenmaker26a.html). |

Der Zeitraum 2024–2026 wird damit durch begutachtete Arbeiten aus jedem Jahr abgedeckt. Aktualität allein macht ein Verfahren noch nicht für State-Stack mit 200 Demos geeignet. Insbesondere Point-Cloud-/Vision-Ergebnisse und RL-Finetuning-Erfolge sind keine nachgewiesenen Verbesserungen dieses Projekts.

### 3.2 Konkrete Schwäche, Aufwand und Datenbedarf — Kriterien 3 bis 7

| Ansatz | 3. Adressierte lokale Schwäche — Zuordnung ist eine Forschungsannahme | 4. Implementierung | 5. Zusätzliche Rechnung | 6. Neue Expert-Interaktionen? | 7. Mit bestehenden 200 Demos testbar? |
|---|---|---|---|---|---|
| Stable-BC | Drift nach kleinen Positionsfehlern; keine direkte Lösung für versteckte Expert-Phase oder fehlende Recovery-Labels | Original: hoch, circa 1–2 Wochen für Dynamik-/Jacobian-Modell und Chunk-Übertragung. Inspirierte finite differences: mittel, circa 3–5 Tage | Original: zusätzliche Ableitungen/Eigenwerte, möglicherweise mehrfaches BC-Budget. Zwei-Forward-Näherung grob 1,5–3× Training; Inferenz unverändert | Nein, wenn nötige Dynamikannahmen aus vorhandenen Daten tragfähig sind | Ja für begrenzte inspirierte Adaption; Original-Garantien auf Stack damit nicht verifiziert |
| DART | Fehlende echte Korrekturen nach Ausführungsfehlern | Mittel bis hoch, circa 4–8 Tage plus Oracle-Prüfung und Erhebung | BC-Training ähnlich; zusätzliche Simulationsversuche, Kovarianzschätzung, verworfene Demos | **Ja**: neue gestörte Expert-Ausführungen, auch bei programmiertem Expert | Nur als Ausgangsbestand. Vollständiges DART braucht zusätzliche Trajektorien |
| DAgger | Policy besucht Fehlgriffe, Abweichungen und Release-Zustände außerhalb erfolgreicher Demos | Hoch, circa 1–2 Wochen: zustands-/historienfähiger Oracle, Rollout-Logging, Aggregation, Chunk-Labels | Mehrere BC-Runden und Erhebung; Budget muss pro Runde begrenzt werden | **Ja**: Expert-Labels auf neu besuchten Zuständen; muss kein Mensch sein | Vortraining ja; vollständiges DAgger ausschließlich offline auf den 200 Demos nein |
| ACT / Chunking | Inkonsistente überlappende Pläne; längere Abläufe und versteckte Phase nur teilweise | Original-ACT: hoch, circa 1–2 Wochen. Ensembling-Wrapper: niedrig, circa 1–3 Tage | Original: neues Training, CVAE-/Transformer-Budget ungemessen. Wrapper: kein Training, bei Replanning nach jedem Frame circa doppelte Forward-Zahl gegenüber H=2 | Nein | Ja; State-only-ACT wäre eine Adaption der ursprünglichen Architektur/Modalität |
| Noise / Perturbation | Empfindlichkeit gegenüber kleinen Messfehlern; lokale Glättung | Niedrig, circa 1–2 Tage; physikalische Kanäle, RNG und History beachten | Ungefähr BC-Budget bei einem Perturbationssample pro Fenster; Inferenz unverändert | Nein für Offline-Input-Jitter. Echte gestörte Recovery-Erhebung wäre ein anderer Versuch | Ja, ohne neue korrekte Off-Distribution-Aktionslabels zu erhalten |
| Data Augmentation | Absolute Ortsabhängigkeit, knappe Szenenabdeckung | Kleine gemeinsame XY-Translation: circa 2–4 Tage. MimicGen-Integration: hoch, circa 1–2 Wochen oder mehr | State-Augmentation gering; MimicGen zusätzlich viele Simulatorversuche und Daten | Kleine State-Augmentation nein. MimicGen braucht keine neuen menschlichen Labels, aber neue simulierte Ausführungen | Kleine Adaption ja. MimicGen nutzt Ausgangsdemos, erzeugt aber einen größeren Datensatz |
| DiffClone | Könnte bei Multimodalität/Representation helfen; sein visueller Schwerpunkt passt wenig zum State-Engpass | Mittel bis hoch, circa 1–2 Wochen für faire State-Adaption | Neues Diffusionstraining/-sampling; aufwendige visuelle Vorverarbeitung wäre hier zusätzlicher, wenig zielgerichteter Aufwand | Nein für Offline-Training | Technisch eine State-Adaption ja; keine direkte TOTO-Reproduktion |
| DBC | Schwache Generalisierung eines rein konditionalen BC-Modells; Nutzung gemeinsamer Datenstruktur | Hoch, circa 5–10 Tage: zusätzliches Verteilungsmodell, Loss-Kopplung und Gewicht | Zusätzliches Modelltraining plus gekoppelte Policy-Optimierung; schnelles Policy-Forward weiterhin möglich | Nein | Ja; wie gut die gemeinsame Verteilung mit 180 Trainingsdemos gelernt wird, ist offen |
| Consistency Policy | Langsame Diffusionsinferenz | Hoch, circa 5–10 Tage: Teacher-/Student- und Distillation-Pipeline | Teacher plus Student-Training; Inferenz anschließend günstiger | Nein | Ja, aber vorhandener Teacher mit 0 % ist eine ungeeignete Erfolgsbasis |
| CFM / PointFlowMatch | Alternative Generatordynamik; möglicherweise bessere konditionierte Aktionsfolgen | State-CFM: mittel bis hoch, circa 4–8 Tage. Original-PointFlowMatch erfordert andere Modalität | Ähnliche Größenordnung generativen Trainings; Inferenz hängt von Integrationsschritten ab | Nein | State-CFM ja; Point-Cloud-Original nicht mit ausschließlich bestehenden State-Eingaben |
| SFP | Kohärenz aufeinanderfolgender Aktionen und iterative Inferenz | Hoch, circa 5–10 Tage: Flow-Ziel, letzte Aktion, Streaming-Ausführung | Neues Flow-Training; Inferenzvorteil zu messen, kein lokaler Speedup bekannt | Nein | Grundsätzlich State-Adaption möglich; Vorteil auf diesem Dataset nicht belegt |
| FA-OPD | Covariate Shift durch fehlende Rückmeldung auf Policy-Zuständen | Sehr hoch, mehrere Wochen: Teacher, Student, Reward-Modell und Online-Optimierung | Mehrere Netze plus viele Trainingsrollouts; deutlich über BC-only | Kein neuer menschlicher Expert zwingend; **neue Umgebungsinteraktionen erforderlich** | Initialisierung ja; voller Ansatz nicht allein mit offline Demos |
| Posterior BC | Unzureichende Aktionsabdeckung als RL-Initialisierung | Hoch, mehrere Wochen inklusive relevantem RL-Vergleich | Generatives Vortraining plus RL-Finetuning | Kein neuer Expert zwingend; für Kernbewertung neue RL-Interaktionen | Offline-Vorstufe ja; zentrale Finetuning-Frage benötigt weiteres Training in der Umgebung |

### 3.3 Baseline, messbare Hypothese und Umfangsrisiko — Kriterien 8 bis 10

Die Hypothesen sind **Vorschläge**, keine Behauptungen über bereits nachgewiesene Effekte. „Verbessert“ bedeutet zunächst positive gepaarte Unterschiede über Trainingsseeds; eine Signifikanzbehauptung ist bei drei Seeds nicht vorgesehen.

| Ansatz | 8. Sinnvolle Baseline | 9. Messbare Hypothese für dieses Projekt | 10. Umfangsrisiko |
|---|---|---|---|
| Stable-BC | Direct ohne Zusatzloss; identischer Perturbationszweig mit λ=0; Input-Jitter als aktive Kontrolle | Unter kleinem Aktionsimpuls ist der Erfolgsverlust gegenüber nominal kleiner als bei Direct und reine Noise-Injection erklärt den Effekt nicht vollständig | Mittel für inspirierte lokale Näherung; hoch für Originalreproduktion. Kontakt, Hidden State und H=2 begrenzen Stabilitätsannahmen |
| DART | Direct auf ursprünglichen Daten und Direct auf gleich vielen zusätzlichen ungestörten Expert-Demos | Gestörte Datenerhebung verbessert Störungserfolg stärker als dieselbe Zahl sauberer neuer Demos | Hoch: Expert kann unter Störung versagen; erfolgreiche Demos allein zeigen eventuell keine Recovery |
| DAgger | Direct; budgetgleiche Extra-Updates auf Originaldaten; gleiche Zahl zusätzlicher unabhängiger Expert-Demos | Bei gleichem Label-/Updatebudget verbessert Policy-State-Labeling Greif-/Release-Erfolg stärker als reine Datensatzvergrößerung | Hoch: falsch rekonstruierte Expert-Phase kann Labels systematisch verfälschen; Chunk-Labels brauchen zusätzliche Expert-Fortsetzungen |
| ACT / Chunking | Bestehendes Direct-H=2; Direct-H=1 ohne Ensembling | Zeitlich ausgerichtetes Ensembling reduziert Planrichtungswechsel bei erhaltenem stabilen Stack-Erfolg gegenüber H=1 | Niedrig für Wrapper; hoch für ACT. Glättung kann XY-Stärke oder notwendige Umschaltung schwächen |
| Noise / Perturbation | Direct, gleiche Architektur, gleiche Fenster und Updatezahl | EEF-Messbias verschlechtert den Erfolg eines mit kleinem EEF-Jitter trainierten Modells weniger | Niedrig. Unveränderte Labels können Korrekturgradienten unterdrücken; keine DAgger-/DART-Recovery-Supervision |
| Data Augmentation | Direct mit/ohne relative Darstellung, jeweils mit/ohne Augmentation; bei MimicGen gleich großes Zusatzdatenbudget | Relative Darstellung und/oder kleine Translation verbessern Erfolg auf neuen/verschobenen Szenen, ohne nominale Leistung zu verlieren | Niedrig bis mittel für XY-Transformation; hoch für MimicGen. Label-Invarianz ist roboterdynamisch nur näherungsweise gegeben |
| DiffClone | Vorhandene Diffusion Policy sowie Direct; Normalisierung separat kontrollieren | Eine konkret benannte DiffClone-Komponente verbessert XY-Richtung und Stackrate gegenüber derselben Diffusionsarchitektur ohne diese Komponente | Hoch: Methode überlappt mit bestehendem Ansatz; mehrere Änderungen wären schwer zuzuordnen |
| DBC | Direct mit λ=0 und gleicher Policy-Kapazität | Joint-Distribution-Regularisierung verringert den Erfolgsverlust unter Verteilungsverschiebung | Hoch: Verteilungsmodell könnte schmale Expert-Manifold verstärken; zweites Trainingsproblem |
| Consistency Policy | Derselbe erfolgreiche Teacher und sein Student; zusätzlich Direct für Latenz | Weniger Forward-Schritte senken Inferenzzeit, ohne Erfolgsverlust gegenüber Teacher | Hoch bei der aktuellen 0-%-Diffusion: zuerst Teacher-Erfolg herstellen; adressiert aktuelle Direct-Fehler kaum |
| CFM / PointFlowMatch | Kapazitäts-/budgetgleiche Diffusion und Direct, gleiche State-Inputs und Ausführung | Austausch des generativen Lernziels verbessert konditionierte XY-Richtung und stabilen Erfolg | Mittel bis hoch: zunächst Generator-/Solver-Bugs und Hyperparameter; punktwolkenbasierte Befunde nicht übertragbar |
| SFP | Direct und budgetgleiche Flow-Chunk-Policy ohne Streaming | Streaming verringert Richtungswechsel und Inferenzwartezeit bei gleichem Erfolg | Hoch: benötigt weitere generative Baseline, damit Streaming-Effekt isoliert ist |
| FA-OPD | BC-only-Teacher/Student und vergleichbar budgetierte Online-Optimierung | Beide Distillation-Kanäle verbessern Closed-Loop-Erfolg über BC-only hinaus | Sehr hoch: neue RL-/Reward-/Teacher-Fragen, große Simulationsbudgets |
| Posterior BC | Standard-BC plus **identisches RL-Finetuning** | Bei gleichem RL-Interaktionsbudget verbessert die Posterior-Initialisierung den Finetuning-Verlauf | Sehr hoch; beantwortet eine andere Kernfrage als kleine Offline-BC-Erweiterung |

### Einordnung der jüngeren Literatur

DBC ist wissenschaftlich interessant, weil es den bestehenden schnellen Regressor um ein anderes Regularisierungsprinzip ergänzen könnte. Der Preis ist ein zweites generatives Modell. Consistency Policy betrifft primär Geschwindigkeit. Die Autoren berichten Robustheit gegenüber Teacher-Qualität in ihren Experimenten; daraus folgt weder, dass ein Student immer die Teacher-Fehler übernimmt, noch dass die hiesige 0-%-Policy durch Destillation erfolgreich wird. Für dieses Projekt fehlt dafür ein belastbarer Anhaltspunkt. Diese beiden Ansätze sind verschieden von DiffClone. [DBC](https://proceedings.mlr.press/v235/chen24as.html), [Consistency Policy](https://www.roboticsproceedings.org/rss20/p071.html), [DiffClone](https://arxiv.org/abs/2401.09243).

CFM und SFP eröffnen einen Generatorvergleich, dessen Integrationsrisiko höher liegt als das eines kleinen Direct-Zusatzlosses. FA-OPD und Posterior BC zeigen aktuelle Richtungen 2026, passen aber vor allem zu einer Arbeit mit Online-Optimierung. Sie sind hier eher Abgrenzung und Ausblick als minimale nächste Erweiterung. [CFM](https://proceedings.mlr.press/v270/chisari25a.html), [SFP](https://proceedings.mlr.press/v305/jiang25a.html), [FA-OPD](https://proceedings.mlr.press/v306/wan26n.html), [Posterior BC](https://proceedings.mlr.press/v306/wagenmaker26a.html).

Eine BC-RNN-/BC-Transformer-Baseline mit längerer History wäre ebenfalls nützlich: Zwei Frames repräsentieren die internen Expert-Verweilzeiten nur begrenzt. Die Architekturen sind schon enthalten und daher primär Kontrollen. Längere History, neue Architektur, Normalisierung und Zusatzloss gleichzeitig zu verändern würde die Ursache eines Effekts verdecken.

## 4. Gemeinsames Evaluationsprotokoll für die drei Vorschläge

Die Vorschläge sind **Alternativen für eine begrenzte Projektarbeit**, keine Aufforderung, sämtliche Versuche auszuführen.

1. **Daten und Budget einfrieren:** gleicher Dataset-Hash, 180/20-Split, Actions, zwei History-Frames und bisherige Padding-Regeln; 30.000 Updates, Batch 8, AdamW, Scheduler und EMA wie Direct. Nur der explizit definierte Faktor verändert sich. Ausschließlich letzten Checkpoint verwenden.
2. **RNG trennen:** Initialisierung, Fensterindizes und Augmentationsrauschen bekommen eigene Generatoren. Derselbe Trainingsseed verwendet in allen Armen dieselben Fenster. Andernfalls verändert das Ziehen von Noise indirekt die Trainingsdatenfolge.
3. **Trainingsseeds:** mindestens die drei unabhängigen Initialisierungen 1, 2 und 3. Frische Trainingsarme werden von Grund auf trainiert. Historische Baseline nur wiederverwenden, wenn Trainingspfad und Ausführung unverändert bleiben; sonst passenden Kontrollarm neu trainieren.
4. **Starts:** alte 40 Starts 46000–46039 dienen der Replikation. Neue Starts 47000–47039 werden erst nach Festlegung von Hypothesen, Varianten und Hyperparametern evaluiert. Diese sind neue Initialzustände aus der bisherigen Aufgabenverteilung, keine automatisch bewiesene OOD-Verteilung. Gleiche Simulatorzustände/Hashes pro Bedingung und Arm verwenden.
5. **Hauptmetrik:** Erfolgsrate des stabilen Stacks mit unverändertem 2-s-Tail. Zusätzlich Erfolgsdifferenz gestört minus nominal pro Trainingsseed. Die 40 Starts sind gepaarte Fälle innerhalb eines Seeds, keine zusätzlichen unabhängigen Trainingsreplikate.
6. **Sekundärmetriken:** Greifen, Lift, Positionierung, Absenken, Release; minimaler XY-Abstand nach Lift; tatsächliche zielgerichtete XY-Bewegung; Grasp-Verlust und Gripperwechsel; Episodenlänge; Offline-XY/Expert und Ziel-Cosinus. Auf allen Episoden berichten und bedingte Nenner ausdrücklich nennen. Kein ausschließliches Mittel über erfolgreiche Rollouts.
7. **Timing:** Grenzreaktion und vorzeitiger Transport bleiben deskriptiv. Früher Transport wird nicht automatisch als Fehler gewertet. Nachträgliche Höhengates dürfen den Hauptbefund nicht verändern.
8. **Auswertung:** Einzelraten je Seed, Mittelwert/SD und gepaarte Arm-Differenzen. Bei n=3 keine allgemeine Überlegenheits- oder Signifikanzbehauptung. Ein Rollout-Bootstrap darf die geringe Zahl Trainingsseeds nicht verschleiern. Ein Seed-konsistenter Unterschied ≥5 Prozentpunkte ist ein vorab gewähltes praktisches Signal, keine Signifikanzschwelle. Kleine/inkonsistente Unterschiede gelten als unentschieden.
9. **Pilotgrenze:** maximal ein separat markierter Engineering-Pilot pro neuer Trainingsmethode, nur Trainingsdaten und festgelegte Validierungsdiagnosen. Beispielsweise 10 Simulator-Smokes auf separaten Seeds 45000–45009 zur Prüfung der Ausführung. Keine Hauptrollouts zum Tuning verwenden. Jede budgetbedingte Planänderung vor der Hauptauswertung dokumentieren.

Die alten 40 Starts sind bereits umfassend analysiert. Ein positiver Effekt ausschließlich auf ihnen liefert schwächere Generalisierungsevidenz als ein bestätigter Effekt auf den neuen 40 Starts.

## 5. Experimentvorschlag A: Sensorrobustheit versus lokale Fehlerkorrektur

### Forschungsfrage und Hypothese

**Forschungsfrage:** Hilft bei Direct schon kleine Input-Perturbation, oder bringt ein expliziter lokaler Kontraktionsloss zusätzlich bessere Robustheit gegen Ausführungsfehler?

**Hypothese A1:** EEF-Input-Jitter verringert den Erfolgsverlust unter EEF-Messbias gegenüber unregularisiertem Direct. **Hypothese A2:** Ein Kontraktionsloss verringert den Erfolgsverlust nach einem frühen Aktionsimpuls stärker als Input-Jitter, bei erhaltener nominaler Leistung. Ein negativer nominaler Unterschied von mehr als 5 Prozentpunkten zählt als relevanter Trade-off.

Das ist eine **Stable-BC-inspirierte Stack-Adaption**, keine Originalreproduktion und kein Stabilitätsbeweis. Die publizierte lokale Fehlerdynamik motiviert die Frage; der konkrete diskrete Loss stammt aus der vorhandenen Projektimplementierung. [Stable-BC](https://collab.me.vt.edu/Stable-BC/), [lokaler Loss](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/src/robomimic_ext/contraction_bc.py>).

### Variablen und Kontrollen

**Unabhängige Variable:** Trainingsziel, drei Arme:

- **A0:** unverändertes Direct-MSE.
- **A1:** Direct-MSE auf gestörtem EEF-Input; Labels unverändert. Pro Trainingsfenster δ aus einer zentrierten Normalverteilung mit σ=2 mm pro Raumachse, auf ±6 mm je Achse begrenzt. Dasselbe δ gilt für beide History-Frames. Cube-Positionen, Quaternion und Gripper bleiben unverändert. Das ist ein synthetischer Sensorfehler, keine neue Expert-Korrektur.
- **A2:** ursprüngliches sauberes Direct-MSE plus lokaler finite-difference Kontraktionsloss mit Perturbationsradius 2 mm und Zielverhältnis ρ=0,99. Die Richtung wird pro Fenster aus einem dreidimensionalen zentrierten Normalvektor gezogen und auf Länge 1 normiert; derselbe δ-Vektor verschiebt beide EEF-History-Frames. Kein zusätzlicher Input-Jitter im MSE-Zweig. λ=0,01 als vorab festgelegter Startwert aus dem vorhandenen lokalen Ansatz, ohne behauptete Optimalität.

Für A2 ist die Fehlerdynamik zunächst auf **freie EEF-Bewegung ohne Würfelkontakt** begrenzt. Eine konservative Trainingsmaske verwendet offenen Expert-Gripper und mindestens 3 cm EEF-Abstand zu beiden Würfelzentren; gespeicherte Simulatorzustände prüfen den Kontaktstatus dieser Frames. An Kontakt-/Greifübergängen wird keine lokale Glattheitsannahme erzwungen. Die Maske steuert nur den Zusatzloss, nicht die Policy-Inferenz.

Aus diesen Trainingsframes wird eine neue Stack-spezifische Näherung `ΔEEF ≈ a_xyz @ K + b` geschätzt. Pro Demo wird innerhalb der 180 Trainingsdemos eine innere Fit-/Prüftrennung verwendet. A2 wird nur durchgeführt, wenn das Modell die richtige Reaktionsrichtung reproduziert und auf den inneren Prüf-Demos pro Achse R²≥0,5 erreicht. Diese pragmatische Vorbedingung ist kein Beweis korrekter Gegenfaktualdynamik.

Der geplante Zusatzloss lautet für die erste ausgeführte Chunk-Aktion:

```text
Δa = π_xyz(o + δ)[Index 1] − π_xyz(o)[Index 1]
e_next_hat = δ + Δa @ K
L_contr = mean(relu(||e_next_hat||² / ||δ||² − ρ²))
L_A2 = MSE(gesamter sauberer Chunk, Expert-Chunk) + λ * L_contr
```

Weil H=2 ausgeführt wird und Kontakte dynamisch gekoppelt sind, misst dieser Ein-Schritt-Loss nur eine lokale Näherung. Er kann insbesondere keine Stabilität des gesamten Stack-Vorgangs garantieren. Die Wirkung auf spätere Phasen wird empirisch geprüft.

**Abhängige Variablen:** stabile Stackrate nominal/gestört, Erfolgsverlust, Greifrate nach frühem Impuls, XY-Fortschritt und Release; ergänzend lokales geschätztes Kontraktionsverhältnis und saubere Validierungs-MSE. Eine bessere Loss-Metrik ohne Rollout-Gewinn bestätigt A2 nicht.

**Kontrollbedingungen:** identische Architektur, History, Chunks, ausgeführte Indizes, Fenster, Seeds und Updates. λ=0 muss den A0-Loss ergeben. A1/A2-Perturbations-RNG beeinflusst weder Initialisierung noch Fensterfolge. Keine Normalisierung, Phasenbalancierung oder XY-Heuristik.

### Seeds, Rollouts und Aufwand

**Drei Trainingsseeds pro Arm**, insgesamt neun frische Trainingsläufe für einen vollständig gekoppelten Vergleich. Vier Evaluationsbedingungen mit jeweils 40 Starts pro Checkpoint:

| Bedingung | Starts und Eingriff |
|---|---|
| Historisch nominal | 46000–46039, unverändert |
| Neu nominal | 47000–47039, unverändert |
| EEF-Messbias | Dieselben neuen Starts; konstanter x-Bias +4 mm in 20 Fällen, −4 mm in 20 Fällen; beide History-Frames konsistent, Simulator unverändert |
| Früher Aktionsimpuls | Dieselben neuen Starts; bei Schritt 20 einmalig ±0,2 zur ausgeführten x-Aktion addieren, auf [−1,1] clippen; Vorzeichen vorab ausgeglichen |

Das sind **160 Rollouts pro Checkpoint, 1.440 insgesamt**, bis 500 Schritte plus Erfolgstail. Die Impulsgröße bezeichnet eine Controller-Aktion, keinen garantierten EEF-Versatz. Tatsächliche Abweichung und Recovery werden mitgeloggt. Bei nicht erreichten Phasen bleibt die Episode im Erfolgsnenner.

**Erwarteter Rechenbedarf:** A0/A1 nahe den gemessenen circa 11 min pro Direct-Training; A2 grob 17–33 min wegen zusätzlichem Forward/Backward. Training insgesamt circa 2–3 Stunden, Evaluation und Verarbeitung circa 2–4 Stunden; **Planungsbudget 4–7 Stunden**, plus ein kleiner Pilot und Dynamikfit. Keine isolierte Laufzeitmessung liegt vor. Implementierung circa 3–5 Arbeitstage. Bei VRAM-Engpass zuerst Zusatzloss auf einem festen Teil der Batch berechnen und diese Änderung vor allen Hauptläufen einfrieren, statt Batch oder Modell zwischen Armen unterschiedlich zu ändern.

### Implementierungsschritte

1. Einen eigenen `bc_direct_chunk`-Algorithmus mit reproduzierbarem Robomimic-Trainings-/Rollout-Adapter registrieren; der aktuelle Direct-Pfad liegt noch außerhalb der Standard-Algo-Registry. Gleiche EMA-Ausführung erhalten.
2. Strukturierte EEF-Perturbation implementieren; Verteilung, Einheiten, History-Konsistenz und λ=0-Gleichheit prüfen.
3. Train-only-Dynamikfit und konservative Free-Space-Maske erstellen. Bei gescheitertem Fit bleibt A2 als methodisch nicht tragfähige Erweiterung dokumentiert; A0/A1 sind trotzdem vollständig auswertbar.
4. Zusatzloss ausschließlich auf Index 1 XYZ implementieren; Original-MSE weiterhin auf alle 16×7 Komponenten. Roh-/EMA-Checkpoints und tatsächliche Updatezahlen auditieren.
5. Evaluator um Messbias und einmaligen Aktionsimpuls ergänzen; States, Actions und beide unveränderten nominalen Kontrollen speichern.
6. Ergebnisse pro Seed und Störungsart gegenüberstellen; vorab definierte Negativinterpretationen verwenden.

### Negative Ergebnisse und Interpretation

- **A1 hilft nur bei Messbias:** Evidenz für Sensorrobustheit, keine Evidenz für Recovery nach echten Ausführungsfehlern.
- **A1 verliert nominal:** Input-Jitter kann relevante Millimeterunterschiede oder Phasenwahl verwischen. Das erklärt einen Trade-off dieser Stärke, nicht die generelle Nutzlosigkeit von Augmentation.
- **A2 verbessert den geschätzten Loss, aber keine Rollouts:** Lokale EEF-Näherung oder freie Bewegungsphasen sind kein ausreichender Hebel für kontaktbehaftetes Stacken.
- **A2 verschlechtert XY-Aktionsstärke/Greifen:** Kontraktionsdruck kann notwendige Änderungen dämpfen oder mit Imitation konkurrieren. Das wäre gerade wegen der bestehenden Transportbefunde wissenschaftlich relevant.
- **Kein Unterschied bei drei Seeds:** Im gewählten Budget unentschieden; mögliche Ceiling-/Störungsstärke-Effekte prüfen, aber keine nachträgliche Suche bis zu einem positiven Ergebnis.

## 6. Experimentvorschlag B: Relative Geometrie und kleine State-Augmentation getrennt prüfen

### Forschungsfrage und Hypothese

**Forschungsfrage:** Lernt Direct Zielsteuerung und Szenenvariation zuverlässiger, wenn relative Geometrie explizit vorliegt, und trägt kleine gemeinsame XY-Translation darüber hinaus etwas bei?

**Hypothese B1:** Eine invertierbare relative Darstellung verbessert XY-Zielrichtung bzw. Erfolgsrate auf neuen Starts gegenüber Rohkoordinaten. **Hypothese B2:** Kleine gemeinsame Translation verringert den Erfolgsverlust unter verschobenen Würfelstarts zusätzlich. Ein positiver Effekt nur der Darstellung ist ein anderes Ergebnis als ein positiver Augmentationseffekt.

MimicGen belegt eine aufwendigere Alternative mit neu ausgeführten synthetischen Trajektorien. Das hier vorgeschlagene Experiment prüft bewusst eine eng begrenzte Transformation bereits vorhandener State-Fenster. Eine Wirksamkeit dieser konkreten Transformation auf Stack ist durch die Literatur nicht vorweggenommen. [MimicGen](https://proceedings.mlr.press/v229/mandlekar23a.html).

### Variablen und Kontrollen

**Unabhängige Variablen:** 2×2-Faktorielles Design mit zwei binären Faktoren:

| Arm | Koordinatendarstellung | Training-Augmentation |
|---|---|---|
| B00 | ursprüngliche absolute A-/B-Positionen | aus |
| B10 | `A−EEF`, `B−EEF`, absolute EEF-Position | aus |
| B01 | ursprüngliche absolute A-/B-Positionen | an |
| B11 | `A−EEF`, `B−EEF`, absolute EEF-Position | an |

Quaternion und Gripper bleiben identisch; pro Frame bleibt die Dimension **15**, pro Eingang **30**. Die Darstellung ist invertierbar, weil die absolute EEF-Position erhalten bleibt. Keine neuen Phasenlabels oder Simulatorinformationen werden Eingaben. Verglichen wird eine geometrische Umparametrisierung, nicht mehr Information oder Netzkapazität.

Augmentation: Mit Wahrscheinlichkeit 0,5 wird ein gemeinsames δxy gleichverteilt aus [−10 mm,+10 mm]² auf A, B und EEF in beiden History-Frames addiert. Actions bleiben unverändert, da es Weltkoordinaten-Delta-Aktionen sind. Z, Orientierung und Gripper werden nicht verändert. Die relative Geometrie bleibt exakt erhalten.

**Begrenzung:** Die gemeinsame Translation bewahrt relative Ziele und die Expert-Aktionsregel bei entsprechend verschobenem verstecktem Ziel. Der fest montierte Roboter und seine Gelenkdynamik sind jedoch nicht global translationsinvariant. Deshalb ist das keine bewiesene vollständige Simulator-Symmetrie. Innerhalb einer konservativen Arbeitsraumgrenze transformieren; den Anteil verworfener Transformationen berichten. Keine Rotation/Spiegelung oder unabhängige Würfelverschiebung mit unveränderten Actions hinzufügen.

**Abhängige Variablen:** stabile Stackrate, Greifrate, minimaler XY-Abstand nach Lift, Ziel-Cosinus/XY-Stärke, Positionierung/Release, Erfolgsverlust bei verschobenen Starts. Auswertung der beiden Haupteffekte und ihrer Interaktion pro Seed, bei n=3 deskriptiv.

**Kontrollbedingungen:** gleicher Direct-Aufbau einschließlich Parameterzahl, gleicher Split, Budget, Fensterfolge und Ausführung H=2. Rohwerte bleiben unnormalisiert. Für B10/B11 zuerst relative Positionen aus den absoluten Werten bilden; eine gemeinsame Translation darf diese relativen Features nicht verändern. Keine zusätzlichen Trainingsfenster als vermeintliche zusätzliche unabhängige Demos zählen.

### Seeds, Rollouts und Aufwand

**Drei Trainingsseeds pro Arm**, zwölf Trainingsläufe. Vier Bedingungen à 40 Starts:

- Alte 40 nominale Starts 46000–46039.
- Neue 40 nominale Starts 47000–47039.
- Dieselben neuen Starts, beide Würfel vor Episodenbeginn gemeinsam +10 mm in x verschoben; Roboter unverändert.
- Dieselben neuen Starts, beide Würfel gemeinsam −10 mm in x verschoben; Roboter unverändert.

Die verschobenen Starts werden vorab auf Tischgrenzen, Würfelüberschneidung und gültigen Simulatorzustand geprüft und dann eingefroren. Positions-/Orientierungs-/Geschwindigkeitswerte und vollständige State-Hashes sind zwischen Policies gleich. Eine kleinere Verschiebung kann noch innerhalb der Trainingsverteilung liegen: als **Szenenverschiebungs-Test** berichten, nicht ungeprüft als OOD-Nachweis. Training verschiebt EEF und Würfel gemeinsam, Evaluation nur die Würfel; der Test misst Aufgabenanpassung und ist kein algebraisch identischer Augmentationstest.

**160 Rollouts pro Checkpoint, 1.920 insgesamt.** Erwarteter Rechenbedarf: circa 12×11 min Training plus circa 3–5 Stunden Evaluation/Analyse, zusammen **5–8 Stunden** einschließlich Reserve. State-Transformation selbst ist billig; Simulatorrollouts dominieren einen großen Teil des Budgets. Implementierung circa 2–4 Arbeitstage. Bei engerem Budget ist B00/B10 als separater, vorher festgelegter Zweiarme-Versuch möglich; dann ist keine Aussage über Augmentation oder Interaktion zulässig.

### Implementierungsschritte

1. Reversible Featuretransformation am Direct-Eingang implementieren; numerisch prüfen, dass A/B aus relativen Features und EEF rekonstruierbar sind.
2. Gemeinsame XY-Transformation vor dem Flattening, mit getrenntem RNG und unveränderten Actions einbauen; Grenzen und tatsächliche Perturbationen protokollieren.
3. Vier Konfigurationen aus einer gemeinsamen Vorlage erzeugen; Eingabebreite/Parameterzahlen und Fensterindizes prüfen.
4. Simulator-Reset um kontrollierte gemeinsame Würfeltranslation erweitern; vollständige Zustände einfrieren und Gleichheit für alle Arme auditieren.
5. Zwölf Trainingsläufe durchführen und finale EMA-Policies auswerten; Haupteffekte und Interaktion pro Seed darstellen.

### Negative Ergebnisse und Interpretation

- **Nur B10 hilft:** Relative Features erleichtern die Optimierung; daraus folgt keine zusätzliche Abdeckungswirkung der Augmentation.
- **Augmentation hilft nur auf verschobenen Starts:** Spezifischer Generalisierungseffekt mit gegebenenfalls nominalem Trade-off; keine allgemeine Recovery-Fähigkeit belegt.
- **Augmentation schadet:** Gemeinsame Translation mit identischen Actions kann roboterdynamisch falsche Beispiele erzeugen oder absolute Arbeitsrauminformation entwerten.
- **Offline-Cosinus verbessert sich ohne mehr Stacks:** Laterale Diagnose ist allein nicht ausreichend; Greifen, Absenken und Release bleiben eigenständige Engpässe.
- **Kein Effekt:** Direct kann die relative Geometrie bereits ausreichend aus absoluten Inputs lernen. Das ist eine nützliche Grenze einer einfachen Repräsentationserweiterung.

## 7. Experimentvorschlag C: Replanning und temporales Ensembling isolieren

### Forschungsfrage und Hypothese

**Forschungsfrage:** Verbessern häufigeres Replanning oder kohärent gemittelte XYZ-Vorhersagen die Direct-Ausführung, ohne die benötigte XY-Stärke abzuschwächen?

**Hypothese C1:** Replanning nach jedem Schritt verringert den Erfolgsverlust nach einem Transportimpuls gegenüber H=2. **Hypothese C2:** Temporales XYZ-Ensembling verringert Richtungswechsel gegenüber H=1, ohne nominale Stackrate oder Zielannäherung wesentlich zu verschlechtern.

Dies ist ein **ACT-inspirierter Ausführungsversuch auf dem vorhandenen Regressor**. Transformer und CVAE werden nicht neu eingeführt; der Versuch isoliert zwei Ausführungskomponenten und ist keine ACT-Reproduktion. [ACT](https://www.roboticsproceedings.org/rss19/p016.html).

### Variablen und Kontrollen

**Unabhängige Variable:** Rollout-Wrapper, drei Arme auf identischen Checkpoints:

- **C0:** bisheriges H=2, Chunk-Indizes 1 und 2 werden nacheinander ausgeführt.
- **C1:** H=1, jeden Frame neuer Chunk; ausschließlich dessen Index 1 ausführen.
- **C2:** H=1, jeden Frame neuer Chunk; XYZ-Aktionen für denselben aktuellen Zeitpunkt aus maximal den letzten vier Chunks mitteln. Gewicht eines Alters j: proportional `exp(−0,5*j)`, j=0 für den neuesten Chunk. Rotation und Gripper stammen immer vom neuesten Chunk.

Die XYZ-Beschränkung hält Gripperentscheidung und Rotation zwischen C1/C2 gleichartig und vermeidet einen zusätzlich gemittelten Öffnungs-/Schließbefehl. Sie ist eine eigene, begrenzte Designentscheidung gegenüber vollständigem ACT-Ensembling. Die Gewichte bevorzugen neue Pläne und werden vor Evaluation eingefroren.

Die zeitliche Zuordnung ist entscheidend: Ein bei Schritt r erzeugter Chunk beginnt mit Aktion r−1. Für aktuellen Schritt t wird daher Index **t−r+1** verwendet. Index 0 darf nie als aktuelle Aktion behandelt werden. Nur tatsächlich gültige Vorhersagen verwenden; beim Episodenreset sämtliche Chunk-/History-Puffer leeren.

**Abhängige Variablen:** stabile Stackrate, Störungserfolgsverlust, XY-Richtungswechsel pro aktivem Transportframe, Streuung überlappender Pläne für denselben Zeitindex, XY-Stärke/Ziel-Cosinus, tatsächlicher Fortschritt pro Sekunde, Positionierung/Release und Inferenzzeit. Richtungswechsel zusätzlich im gemeinsamen 20-Hz-Zeitraster messen, damit verschiedene Replanning-Takte die Nenner nicht künstlich ändern.

**Kontrollbedingungen:** exakt gleiche EMA-Checkpoint-Hashes, Observation-History, Action-Grenzen, Starts und Erfolgstail. Keine neue Datennutzung, Normalisierung, Loss-Änderung oder geometrische Korrektur. C1 kontrolliert den Replanning-Effekt; nur C2−C1 isoliert den Ensembling-Effekt.

### Seeds, Rollouts und Aufwand

**Drei unabhängige Trainingsseeds**, nämlich die vorhandenen Direct-Checkpoints 1/2/3. **Null zusätzliche Trainingsläufe.** Es handelt sich um eine Ausführungsablation über drei trainierte Replikate, nicht um neun neue Trainingsseeds.

Vier Bedingungen à 40 Starts pro Wrapper/Checkpoint:

1. Alte nominale Starts 46000–46039.
2. Neue nominale Starts 47000–47039.
3. Neue Starts; beim ersten gehaltenen Lift B-z>0,88 m ein einzelner x-Aktionsimpuls ±0,2, Vorzeichen vorab ausgeglichen, Clipping wie A. Zeitpunkt und tatsächliche EEF-/B-Abweichung loggen. Episoden ohne gehaltenen Lift erhalten keinen Eingriff und bleiben im Gesamtnenner; ergänzend konditionierte Recovery-Rate mit Trigger-Nenner berichten.
4. Neue Starts mit identischem EEF-Messbias ±4 mm wie Vorschlag A.

**160 Rollouts pro Wrapper/Checkpoint, 1.440 insgesamt.** H=1 verdoppelt gegenüber H=2 näherungsweise die Forward-Aufrufe; C2 benötigt pro Frame weiterhin nur einen neuen Forward, zusätzlich einen sehr kleinen Mittelungsaufwand. Aus lokalen 40-Rollout-Laufzeiten abgeleitet: **circa 3–5 Stunden** für Evaluation, Logs und Analyse; kein Training. Implementierung circa 1–3 Arbeitstage. Tatsächliche Latenz nach GPU-Warmup mit CUDA-Synchronisation messen; Simulatorzeit separat ausweisen.

### Implementierungsschritte

1. Vorhandene Direct-Checkpoints unverändert über denselben Robomimic-Adapter laden; C0 zuerst auf den historischen Starts reproduzieren.
2. `replan_every` und gültige zeitgestempelte Chunks im Wrapper speichern; synthetischen Chunk mit bekannten Zeitwerten verwenden, um Indexverschiebungen zu prüfen.
3. C1 ohne Mittelung implementieren, danach C2 als einzige weitere Änderung. Episode-Reset und History-Padding prüfen.
4. Impuls am definierten Lift-Ereignis ergänzen; Trigger/Nicht-Trigger und tatsächliche Störung dokumentieren. Keine Policy-abhängig neu gesampelten Startzustände.
5. Alle Arme auf gepaarten Starts evaluieren, Inferenzzeit messen und Änderungen der XY-Stärke zusammen mit Richtungswechseln interpretieren.

### Negative Ergebnisse und Interpretation

- **C1 hilft, C2 nicht:** Häufigeres Feedback ist nützlich; Glättung bringt keinen zusätzlichen Gewinn.
- **C2 reduziert Richtungswechsel, aber auch Erfolg:** Geringere Aktionsvariation ist kein hinreichendes Gütekriterium. Mittelung kann entgegengesetzte Pläne auslöschen oder nötige Kurskorrekturen verzögern.
- **C2 verschlechtert Release trotz ungeändertem Gripperpfad:** Gemittelte Armbewegung kann das Timing zur Kontaktgeometrie verändern; Arm-/Gripperkoordination bleibt gekoppelt.
- **Kein Effekt:** Die bereits kurzen zwei ausgeführten Aktionen sind unter diesen Bedingungen ausreichend. Das begrenzt den Nutzen dieser ACT-Komponente, widerlegt aber weder Transformer noch CVAE.
- **Gewinn nur auf alten Starts:** Plausible Anpassung an bekannte Fälle; keine bestätigte Übertragung auf neue Starts.

## 8. Sachliche Entscheidungshilfe ohne pauschalen Gewinner

| Projektpriorität | Passende Alternative | Stärke | Preis / Aussagegrenze |
|---|---|---|---|
| Eigener Trainingsloss mit kontrolltheoretischer Motivation | A | Nutzt vorhandenen Code und trennt Sensorrobustheit von lokaler Korrektur | Dynamikfit und Kontaktannahmen sind der Engpass; nur inspirierte Methode |
| Geometrie und Datenknappheit bei gleicher Modellkapazität untersuchen | B | Klare faktorielle Trennung von Darstellung und Augmentation; vollständig offline | Zwölf Trainingsläufe und mehr Rollouts; künstliche Labels nur näherungsweise gültig |
| Sehr begrenzter Umfang mit sauberer Closed-Loop-Ablation | C | Keine neuen Trainings; direkter Test von Chunk-Kohärenz und Feedback | Beitrag ist Ausführung/Integration, kein neuartiger BC-Lernalgorithmus |

Bei strengem Zeitbudget kann C zuerst die Ausführungsfrage klären. Wenn die Projektarbeit ausdrücklich eine **neue Trainingsmethode in Robomimic** verlangt, liefern A oder B den größeren Implementierungsbeitrag. A ist theoretisch näher an Stable-BC, B vermeidet das zusätzliche Dynamikmodell. Das sind unterschiedliche Vorzüge; die vorhandenen Ergebnisse begründen keine Rangfolge ihrer erwarteten Erfolgsraten.

DART oder DAgger werden attraktiver, wenn der Schwerpunkt ausdrücklich auf **neuer Recovery-Supervision** liegen darf. Dann ist vor allem ein funktionierender Expert-Oracle erforderlich. Für DAgger muss dessen Phase aus Geschichte/Zustand valide fortgesetzt oder rekonstruiert werden. Für Chunk-Targets genügt ein einzelnes queried action label nicht: Es braucht eine Expert-Fortsetzung vom gespeicherten Zustand, oder der Versuch muss explizit auf Single-Step-BC wechseln. Beides verändert Aufwand und Baseline.

Falls interaktive Daten geplant werden, wären zwei begrenzte Erhebungsrunden mit festem Labelbudget und eine gleich große Sammlung ungestörter Expert-Demos die nötige Kontrolle. Die Vergleichsfrage ist dann, ob **gezielte Zustandsabdeckung** mehr bringt als bloß zusätzliche Daten. Das ist ein möglicher anderer Projektzuschnitt, kein kostenloser Zusatz zu den drei Offline-Vorschlägen.

**Speicherplanung:** Ein Direct-Gewichtssatz hat in float32 ungefähr 270 MB; Rohgewichte, EMA und AdamW-Momente zusammen ungefähr 1,08 GB pro Checkpoint, ohne Zusatzartefakte. Für neun bzw. zwölf Läufe deshalb vorzugsweise finale EMA-Inferenzgewichte behalten, Resume-Dateien begrenzt aufbewahren und keine großen Videos für alle Rollouts rendern. Die zuvor berichteten circa 26 GB freien Speicher sind ein historischer Wert, keine aktuelle Messung. Vor Experimentstart freien Speicher prüfen. Die drei Vorschläge nicht automatisch zu einer großen Gesamtsuche kombinieren.

## 9. Quellen und überprüfbare Links

Publikationsstatus wird bevorzugt aus Proceedings, Journal-Eintrag und Autorenquellen bestimmt. Eine arXiv-Seite allein ist kein Peer-Review-Nachweis. Insbesondere bei Stable-BC ist der veraltete arXiv-BibTeX auf der Projektseite vom inzwischen ausgewiesenen RA-L-Status zu unterscheiden. Die Auswahl ist eine gezielte Recherche für State-BC und begrenztes Projektbudget, kein systematischer Vollständigkeitsnachweis sämtlicher Arbeiten bis 2026.

| Quelle | Bibliographische Angabe / Zugang |
|---|---|
| Robomimic | ARISE Initiative. [Release-Notes](https://github.com/ARISE-Initiative/robomimic/releases), [Algorithmen-Dokumentation](https://robomimic.github.io/docs/modules/algorithms.html), [gepinnter Projekt-Commit](https://github.com/ARISE-Initiative/robomimic/tree/d309eaecc18acf4152a830a895a6984b8ac71b05). |
| Stable-BC | Mehta, Ciftci, Ramachandran, Bansal, Losey. *Stable-BC: Controlling Covariate Shift With Stable Behavior Cloning*. IEEE Robotics and Automation Letters, 2025. [DOI](https://doi.org/10.1109/LRA.2025.3526439), [Autorenprojekt](https://collab.me.vt.edu/Stable-BC/), [Preprint 2024](https://arxiv.org/abs/2408.06246), [Code](https://github.com/VT-Collab/Stable-BC). |
| DART | Laskey, Lee, Fox, Dragan, Goldberg. *DART: Noise Injection for Robust Imitation Learning*. CoRL 2017, PMLR 78:143–156. [Proceedings](https://proceedings.mlr.press/v78/laskey17a.html). |
| DAgger | Ross, Gordon, Bagnell. *A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning*. AISTATS 2011, PMLR 15:627–635. [Proceedings](https://proceedings.mlr.press/v15/ross11a.html). |
| ACT | Zhao, Kumar, Levine, Finn. *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware*. RSS 2023. [Proceedings](https://www.roboticsproceedings.org/rss19/p016.html), [Paper](https://www.roboticsproceedings.org/rss19/p016.pdf). |
| MimicGen | Mandlekar et al. *MimicGen: A Data Generation System for Scalable Robot Learning using Human Demonstrations*. CoRL 2023, PMLR 229:1820–1864. [Proceedings](https://proceedings.mlr.press/v229/mandlekar23a.html), [offizielle Dokumentation](https://mimicgen.github.io/docs/introduction/overview.html). |
| DiffClone — Preprint | Mani et al. *DiffClone: Enhanced Behaviour Cloning in Robotics with Diffusion-Driven Policy Learning*. arXiv:2401.09243, 2024, v3; TOTO-Workshop/Competition 2023. [Status/Abstract](https://arxiv.org/abs/2401.09243), [Volltext](https://arxiv.org/html/2401.09243v3). |
| DBC | Chen, Wang, Hsu, Lai, Sun. *Diffusion Model-Augmented Behavioral Cloning*. ICML 2024, PMLR 235:7486–7510. [Proceedings](https://proceedings.mlr.press/v235/chen24as.html). |
| Consistency Policy | Prasad, Lin, Wu, Zhou, Bohg. *Consistency Policy: Accelerated Visuomotor Policies via Consistency Distillation*. RSS 2024. [Proceedings](https://www.roboticsproceedings.org/rss20/p071.html), [Paper](https://www.roboticsproceedings.org/rss20/p071.pdf), [Code](https://github.com/Aaditya-Prasad/Consistency-Policy/). |
| CFM / PointFlowMatch | Chisari, Heppert, Argus, Welschehold, Brox, Valada. *Learning Robotic Manipulation Policies from Point Clouds with Conditional Flow Matching*. CoRL 2024, PMLR 270:982–993, veröffentlicht 2025. [Proceedings](https://proceedings.mlr.press/v270/chisari25a.html). |
| SFP | Jiang, Fang, Roy, Lozano-Pérez, Kaelbling, Ancha. *Streaming Flow Policy: Simplifying diffusion/flow-matching policies by treating action trajectories as flow trajectories*. CoRL 2025, PMLR 305:238–257. [Proceedings](https://proceedings.mlr.press/v305/jiang25a.html). |
| FA-OPD | Wan et al. *Adversarial Dual On-Policy Distillation from Expressive Teacher*. ICML 2026, PMLR 306:124737–124763. [Proceedings](https://proceedings.mlr.press/v306/wan26n.html). |
| Posterior BC | Wagenmaker, Dong, Tsao, Finn, Levine. *Posterior Behavioral Cloning: Pretraining BC Policies for Efficient RL Finetuning*. ICML 2026, PMLR 306:124171–124204. [Proceedings](https://proceedings.mlr.press/v306/wagenmaker26a.html). |

Lokale Hauptevidenz: [Replikationsbericht](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/ERGEBNISSE.md>), [Protokoll](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/protocol.json>), [Direct-Konfiguration](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/direct/seed_2/config.json>), [Diffusionskonfiguration](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_replication_20261001/diffusion/seed_2/config.json>), [Projektimplementierung Lift](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/praxis/README.md>). Keine Literaturerfolgsrate wird als erwartete Stackrate dieses Projekts eingesetzt.
