# Vergleichende Literatur- und Implementierungsübersicht für Plan A

*Stand: 29. September 2026. Fokus: eine kleine Offline-BC-Erweiterung auf dem
robomimic-Lift-PH-Datensatz (Low-Dim, Panda/Franka).* 

## Ausgangspunkt in robomimic

robomimic 0.5 enthält deterministisches BC, stochastische Gaussian-/GMM-/VAE-
Policies, BC-RNN, BC-Transformer und Diffusion Policy sowie Offline-RL-Verfahren
[1]. Die Basis-BC-Policy minimiert auf Demonstrationsbeobachtungen einen
gewichteten Aktionsfehler; der Standard ist MSE. Damit wird nicht ausdrücklich
trainiert, nach einer vom Demonstrationsverlauf abweichenden Greiferposition
wieder zurückzukehren [1, 2].

Der zusätzlich geprüfte Codepunkt betrifft BC-RNN: Der Datensatz kann
Sequenzenden auffüllen und eine Padding-Maske erzeugen [3]. Der Standardloader
fordert diese Maske nicht an, und der BC-RNN-Loss mittelt über alle Zeitschritte
[1, 4]. Das ist eine mögliche Verzerrung bei kurzen/variablen Trajektorien;
ihre tatsächliche Wirkung muss separat gemessen werden. Der aktuelle
Lift-Versuch nutzt feedforward BC mit `seq_length=1` und testet diesen Punkt
deshalb nicht.

## Methodenvergleich

| Ansatz | Mechanismus und möglicher Vorteil | Verhältnis zu robomimic | Aufwand / Grenze für dieses Projekt |
| --- | --- | --- | --- |
| Deterministisches BC | Direkte Abbildung Beobachtung → Aktion; schnell und einfache Hauptbaseline [1, 2] | Vorhanden | Keine gezielte Recovery-Supervision außerhalb der Demonstrationen |
| BC-GMM / BC-VAE | Stochastische oder multimodale Aktionsverteilungen [1] | Vorhanden | Hilft bei mehreren zulässigen Aktionen; löst Covariate Shift allein nicht nachweislich |
| BC-RNN / BC-Transformer | Nutzt Beobachtungshistorie und kann zeitliche Abhängigkeiten lernen [1] | Vorhanden | Zusätzliche Architekturfrage; BC-RNN-Padding gesondert untersuchen |
| Diffusion Policy | Generiert Aktionsfolgen iterativ; stark bei komplexen, multimodalen Aktionen [5] | UNet-Variante bereits integriert [1] | Mehr Rechen- und Inferenzaufwand; keine klare minimale neue Erweiterung |
| Diffusion Model-Augmented BC | Kombiniert einen konditionalen BC-Verlust mit einem Diffusionsmodell der gemeinsamen Expertenverteilung [11] | Nicht als diese Kombination integriert | Zusätzliches Modell und Trainingsziel; höherer Aufwand als ein einzelner BC-Loss |
| DiffClone | Konditionierte Diffusionspolicy für den TOTO-Benchmark [12] | Andere Benchmarkbasis als Lift PH | Ergebnisse nicht unmittelbar mit robomimic-Lift-Rollouts vergleichbar |
| ACT | Transformer-basiertes Action Chunking für bimanuelle Präzisionsaufgaben [6] | Nicht als Standard-BC-Variante integriert | Größerer Integrationsaufwand; Task und Hardware weichen vom Lift-Versuch ab |
| DART | Stört Demonstrationen, damit echte Korrekturhandlungen aufgezeichnet werden [7] | Datenerhebungsstrategie, nicht nur anderer Loss | Benötigt neue Demonstrationen/Experten, vorhandenes PH-Dataset reicht nicht |
| DAgger | Fragt Experten in von der Policy besuchten Zuständen ab [8] | Interaktives Lernen | Benötigt einen während des Rollouts verfügbaren Experten/Oracle |
| Stable-BC | Fügt zu BC eine Stabilitätsbedingung aus lokalen Fehlerdynamiken hinzu [9] | Interessante externe Methode | Modellannahmen und Robot-/Umgebungszustandsaufteilung müssen für Manipulation geprüft werden |
| Dieses Projekt: finite-difference Contraction-BC | Bestraft, wenn ein kleiner geschätzter Positionsfehler nach einem Schritt nicht schrumpft | Als neuer robomimic-Algorithmus registriert | Empirische Controller-Näherung, keine Stable-BC-Garantie; auf Low-Dim-Lift zugeschnitten |

**Entscheidung:** Der Lift-Versuch konzentriert sich auf eine
stabilitätsinspirierte Ergänzung von deterministischem BC. So bleibt die
Architektur gleich und die experimentelle Änderung ist auf einen Loss-Term
begrenzt. Die Idee ist von Stable-BC motiviert, **implementiert jedoch nicht
Gleichung 11 des Papers**. Die Arbeit darf deshalb nicht die Garantien von
Stable-BC für die hier verwendete Methode beanspruchen [9].

## Konkrete Integration und Daten

Der offizielle Lift-PH-Low-Dim-Datensatz ist 21 MB groß und enthält 200
Demonstrationen; seine vorhandenen Masken trennen 180 Trainings- und 20
Validierungsdemonstrationen. Er speichert Greiferposition,
Objektbeobachtungen, Aktionen und Folgezustände [10]. Die v1.5-Version nennt
robosuite 1.5.1 und einen Panda-Roboter mit OSC_POSE-Controller in den
Umgebungsmetadaten. Die ersten drei Aktionskomponenten steuern die
kartesische Verschiebung. Im Dataset entspricht `object[-3:]` exakt
`cube_pos - robot0_eef_pos`; der Perturbationscode aktualisiert dieses
relative Merkmal zusammen mit der Greiferposition.

Aus den **Trainingsdemonstrationen allein** wird eine lineare lokale Abbildung
`Δeef ≈ action[:3] @ K + b` geschätzt. Die auf den 20 zurückgehaltenen
Demonstrationen gemessenen R²-Werte sind ungefähr 0,84 / 0,58 / 0,94 für
die drei Raumachsen. Die schwächere mittlere Achse begrenzt, wie wörtlich
der simulierte Ein-Schritt-Kontraktionswert verstanden werden darf. Der
Trainingsloss verwendet nur `K`; der Achsenversatz `b` kürzt sich beim
Vergleich zweier Aktionen am selben Demonstrationszustand heraus.

Die neue Policy wird in `praxis/src/robomimic_ext/contraction_bc.py` als
`bc_contraction` registriert. `λ=0` erhält den ursprünglichen BC-Loss; positive
Werte ergänzen den Kontraktionsverlust. Baseline und Erweiterung verwenden
gleiche Trainingsdemonstrationen, MLP-Größe, Anzahl Updates und Rollout-Seeds.
Die Pilotgewichte werden separat von den finalen Evaluationsepisoden
betrachtet.

## Wie Ergebnisse zu vergleichen sind

Primär zählt die Erfolgsrate über gepaarte robosuite-Rollouts: unveränderte
Startzustände und dieselben Seeds mit 2 cm verschobener Würfelposition.
Validierungs-MSE, Erfolgszeit und der Kontraktionsverlust sind Zusatzgrößen.
Mindestens drei Trainings-Seeds zeigen, ob ein Unterschied reproduzierbar
ist. Bei 20 Rollouts pro Seed sind Unsicherheitsintervalle breit; kleine
Unterschiede dürfen nicht als gesicherter Vorteil dargestellt werden.

Die publizierten robomimic-Zahlen [2] sind nur Hintergrund: Die aktuelle
v1.5-Datasetversion und die bewusst kleinere Trainingskonfiguration können
andere Resultate ergeben [10]. Der faire quantitative Vergleich ist die
**lokal erneut trainierte** robomimic-BC-Baseline mit identischem Budget.
Die ursprüngliche Studie meldet für **Lift PH mit BC 100 % Erfolg** [2].
Bei voller Konvergenz ist auf diesem Task deshalb kaum noch absolute
Verbesserung möglich. Der zusätzliche 20-%-Demonstrationsversuch prüft
gezielt, ob der Loss bei knapperen Daten hilft; auch dort bleibt die lokal
trainierte BC-Policy die entscheidende Kontrollgruppe.

## Quellen

1. [robomimic: implementierte Algorithmen und BC-Code](https://github.com/ARISE-Initiative/robomimic/blob/master/docs/introduction/implemented_algorithms.md), [BC-Implementierung](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/algo/bc.py).
2. [Mandlekar et al. (2021), *What Matters in Learning from Offline Human Demonstrations for Robot Manipulation*](https://arxiv.org/abs/2108.03298).
3. [robomimic `SequenceDataset`: Padding und Masken](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/utils/dataset.py).
4. [robomimic `train_utils.py`: Dataset-Konfiguration](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/utils/train_utils.py).
5. [Chi et al., *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion*](https://arxiv.org/abs/2303.04137).
6. [Zhao et al., *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware*](https://arxiv.org/abs/2304.13705).
7. [Laskey et al., *DART: Noise Injection for Robust Imitation Learning*](https://proceedings.mlr.press/v78/laskey17a.html).
8. [Ross, Gordon und Bagnell, *A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning*](https://proceedings.mlr.press/v15/ross11a.html).
9. [Mehta et al., *Stable-BC: Controlling Covariate Shift with Stable Behavior Cloning*](https://arxiv.org/html/2408.06246v1).
10. [Offizielle robomimic-v0.1-Datasetdokumentation](https://robomimic.github.io/docs/datasets/robomimic_v0.1.html).
11. [Chen et al., *Diffusion Model-Augmented Behavioral Cloning*, ICML 2024](https://proceedings.mlr.press/v235/chen24as.html).
12. [Mani et al., *DiffClone: Enhanced Behaviour Cloning in Robotics with Diffusion-Driven Policy Learning*](https://arxiv.org/abs/2401.09243).
