# Plan A: Implementierung und experimentelle Ergebnisse

*Stand: 30. September 2026. Reproduzierbarer lokaler Versuch mit robomimic 0.5,
Lift PH low_dim v1.5 und robosuite 1.5.1. Die Literaturauswahl und die
Forschungsfrage stehen in [RESEARCH_SKETCH.md](RESEARCH_SKETCH.md) und
[COMPARATIVE_REVIEW.md](COMPARATIVE_REVIEW.md).*

## Forschungsfrage und Auswahl

Die deterministische BC-Policy in robomimic minimiert den Aktionsfehler auf
Demonstrationszuständen. Das Ziel dieses Versuchs war, eine zusätzliche lokale
Korrekturreaktion zu trainieren und ihren Nutzen im geschlossenen Regelkreis
gegen dieselbe, lokal neu trainierte BC-Policy zu prüfen. BC-GMM, BC-VAE,
BC-RNN/Transformer und Diffusion Policy sind bereits im Framework vertreten;
weitere Ansätze und die Begründung der Methodenauswahl stehen im
[Literaturvergleich](COMPARATIVE_REVIEW.md).

## Implementierung

[`contraction_bc.py`](../../praxis/src/robomimic_ext/contraction_bc.py)
registriert `bc_contraction` als robomimic-Algorithmus. Der vorhandene
deterministische BC-Actor und sein Imitationsverlust bleiben erhalten. Im
Training wird die Greiferposition in einer Beobachtung um einen zufällig
gerichteten Vektor von 5 mm verändert; das relative Würfelmerkmal wird
konsistent angepasst. Der zusätzliche Verlust bestraft, wenn die aus beiden
Policy-Aktionen und einer aus **Trainingsdemonstrationen** geschätzten lokalen
Aktionsantwort berechnete Ein-Schritt-Abweichung nicht mindestens auf 0,99
des ursprünglichen Abstands sinkt. Der Gesamtverlust lautet
`L_BC + λ L_contraction`, hier mit `λ=1`.

Dies ist eine empirische Finite-Difference-Approximation für Lift. Es ist
**keine Implementierung der Stable-BC-Eigenwertbedingung** und trägt keine
Stabilitätsgarantie für Kontakt, große Verschiebungen oder andere Tasks. Die
gefittete Aktionsantwort erklärt im zurückgehaltenen Validierungssplit pro
Raumachse ungefähr 84 %, 58 % und 94 % der EEF-Positionsänderungsvarianz.

## Daten und Versuchsdesign

| Merkmal | Festlegung |
| --- | --- |
| Aufgabe | Lift, Panda/Franka, OSC_POSE, niedrigdimensionale Beobachtungen |
| Datensatz | Offizielle Lift-PH-Datei v1.5; 200 Demonstrationen, davon 180 Training / 20 Validierung |
| Weitere Datenbedingung | Offizieller `20_percent_train`/`20_percent_valid`-Split: 36 / 4 Demonstrationen; Aktionsantwort nur auf den 36 Trainingsdemonstrationen neu gefittet |
| Policy | Feedforward-MLP mit zwei verborgenen Schichten à 256 Einheiten |
| Training | Für beide Methoden dieselben Splits, Architektur, Seeds 1/2/3, Adam mit Lernrate 0,0001, Batchgröße 100 und 100 Updates je Epoche; Hauptauswertung nach 100 Epochen, zusätzliche Auswertung nach 20 Epochen |
| Parameterauswahl | Gewichte 0,01 / 0,1 / 1,0 in einem Pilot mit separaten Rollout-Seeds getestet; `λ=1` für den finalen Vergleich festgelegt |
| Evaluation | 20 gepaarte Rollouts pro Trainings-Seed, Methode und Bedingung; maximal 400 Schritte; identische Episoden-Seeds je Policy-Paar |
| Störungen | Würfel nach Reset um ±2 cm in x verschoben; separat einmalige Änderung der x-Aktionskomponente um ±1 bei Schritt 20 (auf [-1, 1] begrenzt) |

Die Auswertung speichert Anfangspositionen von Würfel und Greifer. Das
Zusammenfassungsskript prüft ihre Gleichheit paarweise und vergleicht Erfolge
bei denselben Episoden-Seeds. Ein erfolgreicher Rollout endet beim ersten
positiven `env.is_success()["task"]`-Signal.

## Resultate: voller Trainingssplit

Die Zahlen sind **Erfolge / 60 Episoden** über drei Trainings-Seeds; jede
Policy hat 20 Episoden pro Bedingung und Seed.

| Trainingsdauer | Bedingung | robomimic-BC | BC + Kontraktionsverlust | Differenz |
| --- | --- | ---: | ---: | ---: |
| 20 Epochen | Nominal | 23/60 (38,3 %) | 36/60 (60,0 %) | +13/60 |
| 20 Epochen | Würfel +2 cm x | 18/60 (30,0 %) | 36/60 (60,0 %) | +18/60 |
| 20 Epochen | x-Aktionsimpuls +1 | 26/60 (43,3 %) | 38/60 (63,3 %) | +12/60 |
| 100 Epochen | Nominal | 44/60 (73,3 %) | 56/60 (93,3 %) | +12/60 |
| 100 Epochen | Würfel +2 cm x | 47/60 (78,3 %) | 55/60 (91,7 %) | +8/60 |
| 100 Epochen | Würfel −2 cm x | 37/60 (61,7 %) | 57/60 (95,0 %) | +20/60 |
| 100 Epochen | x-Aktionsimpuls +1 | 41/60 (68,3 %) | 59/60 (98,3 %) | +18/60 |
| 100 Epochen | x-Aktionsimpuls −1 | 48/60 (80,0 %) | 55/60 (91,7 %) | +7/60 |

Bei 100 Epochen lauten die nominalen Erfolge je Trainings-Seed für BC
`16/20, 15/20, 13/20` und für die Erweiterung `18/20, 20/20, 18/20`.
Die Gewichtsnull-Ablation erzeugte nach 20 Epochen für Seed 1 exakt dieselben
sechs Policy-Netz-Tensoren wie die unveränderte BC-Baseline
(`max_abs_diff=0`). Damit ist der Integrationspfad ohne Zusatzterm geprüft.

## Resultate: 20 % Trainingsdemonstrationen

Bei nur 36 Trainings- und vier Validierungsdemonstrationen wurde die lokale
Aktionsantwort neu gefittet. Beide Policies erhielten denselben reduzierten
Split und wiederum 100 Epochen mit je 100 Updates. Die Stärke `λ=1` wurde aus
dem vollen Pilot übernommen, ohne neue Suche auf diesem Split.

| Bedingung | robomimic-BC | BC + Kontraktionsverlust | Differenz |
| --- | ---: | ---: | ---: |
| Nominal | 49/60 (81,7 %) | 58/60 (96,7 %) | +9/60 |
| Würfel +2 cm x | 43/60 (71,7 %) | 54/60 (90,0 %) | +11/60 |
| Würfel −2 cm x | 48/60 (80,0 %) | 59/60 (98,3 %) | +11/60 |
| x-Aktionsimpuls +1 | 46/60 (76,7 %) | 60/60 (100 %) | +14/60 |
| x-Aktionsimpuls −1 | 47/60 (78,3 %) | 56/60 (93,3 %) | +9/60 |

Die nominalen Erfolge je Seed sind für BC `15/20, 16/20, 18/20` und für die
Erweiterung `19/20, 20/20, 19/20`. Auch mit 20 % Daten ist Lift in diesem
Setup für BC schon relativ leicht; der Versuch ist deshalb kein Nachweis einer
allgemeinen Daten-Effizienzsteigerung. Er zeigt einen Vorteil auf genau diesem
reduzierten Lift-Split und diesen Evaluationszuständen.

## Einordnung und Grenzen

Das Vorzeichen der Unterschiede ist in den drei geprüften Trainings-Seeds bei
allen fünf 100-Epochen-Bedingungen positiv. Die Stichprobe von drei Seeds und
20 Episoden je Seed ist für einen belastbaren Signifikanzanspruch klein; die
Ergebnisse sind ein lokaler Machbarkeits- und Vergleichsbefund. Die positiven
x-Störungen wurden nach einem Pilot betrachtet. Die ergänzten negativen
x-Störungen zeigen ebenfalls einen Vorteil, ohne daraus eine Aussage über
andere Störungsarten abzuleiten.

Die ursprüngliche robomimic-Studie berichtet für Lift PH mit BC 100 % Erfolg
([Mandlekar et al., 2021](https://arxiv.org/abs/2108.03298)). Das ist ein
wichtiger Deckeneffekt. Der hier verwendete v1.5-Datensatz, die Architektur
und das bewusst kleinere Trainingsbudget sind nicht identisch mit der
veröffentlichten Versuchsanordnung. **Die publizierten 100 % sind deshalb
kein direkter Zahlenvergleich.** Die faire Kontrollgruppe ist die im selben
lokalen Setup neu trainierte BC-Policy.

Noch offen ist, ob die Approximation auf weiteren Manipulationstasks, mit
anderen Controllern oder Bildbeobachtungen hilft. Auch der relativ schwache
Fit der y-Achse, die fehlende theoretische Kontraktionsgarantie und die kleine
Anzahl unabhängiger Trainings-Seeds begrenzen die Interpretation.

Die in der Forschungsskizze genannte H2 (Abstand des Rollouts zu einer
vergleichbaren Demonstration) wurde nicht operationalisiert und ist durch
diese Erfolgsraten nicht beantwortet. Auch H3 ist nur über den Pilot zur
Gewichtswahl berührt; eine systematische Pareto-Kurve aus Erfolgsrate,
Imitationsfehler und Regularisierungsstärke fehlt. Ein nächster Versuch sollte
beide Punkte mit vordefinierten Metriken und zusätzlichen Tasks prüfen.

## Reproduktion und Artefakte

Setup, Befehle und Versions-Pins stehen in
[`praxis/README.md`](../../praxis/README.md). Die lokale Auswertung verwendet
[`evaluate_matrix.py`](../../praxis/src/evaluate_matrix.py) und
[`summarize_lift.py`](../../praxis/src/summarize_lift.py). Die Roh-Checkpoints,
Rollout-JSONs und Logs liegen aus Platzgründen im ignorierten
`praxis/results/`; die drei kompakten JSON-Zusammenfassungen stehen in
[`praxis/reports/`](../../praxis/reports). Der Gradiententest für den Zusatzverlust und der Test
des konsistenten relativen Würfelmerkmals stehen in
[`test_contraction.py`](../../praxis/tests/test_contraction.py).

Die [Ergebnisgrafiken und ausdrücklich hypothetischen Trends](../../praxis/reports/GRAFIKEN.md)
zeigen die Messwerte und drei mögliche weitere Entwicklungen bis 300 Epochen.
