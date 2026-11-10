# Ergebnisse des Arbeitstags-Laufs

Status: COMPLETED_WITH_ERRORS; Laufzeit 120.7 Minuten.

Alle neuen Videos: vier Perspektiven, anschließend zwei Sekunden Fortsetzung. Alte Experimente bleiben erhalten.
Modellauswahl: 15 Entwicklungsepisoden ab Seed 6000; unabhängiger Abschlusstest: 50 Episoden ab Seed 26000.
Robustheit: 10 gepaarte Episoden je Bedingung ab Seed 36000. Kleine Stichproben liefern Hinweise, keine sicheren Rangfolgen.

| Modell / Checkpoint | Split | Erfolg | B gegriffen | B angehoben | Zweierstapel abgelegt | Basis angehoben |
|---|---|---:|---:|---:|---:|---:|
| stack_two_vision_short_best_validation | development (15) | 7% | 33% | 33% | 7% | 0% |
| stack_two_vision_short_last | development (15) | 20% | 40% | 33% | 20% | 0% |
| stack_two_vision_short | test (50) | 4% | 66% | 50% | 6% | 0% |
| stack_two_vision_long_best_validation | development (15) | 0% | 33% | 20% | 0% | 0% |
| stack_two_vision_long_last | development (15) | 0% | 40% | 27% | 0% | 0% |
| stack_two_vision_long | test (50) | 0% | 30% | 22% | 0% | 0% |
| stack_two_state_long_last | development (15) | 0% | 20% | 13% | 0% | 0% |
| stack_two_state_long | test (50) | 0% | 20% | 18% | 0% | 2% |
| square_rnn_gmm_best_validation | development (15) | 0% | – | – | – | – |
| square_rnn_gmm_last | development (15) | 27% | – | – | – | – |
| square_rnn_gmm | test (50) | 20% | – | – | – | – |
| square_old_bc | development (15) | 0% | – | – | – | – |
| square_old_bc | test (50) | 0% | – | – | – | – |
| square_old_rnn | development (15) | 20% | – | – | – | – |
| square_old_rnn | test (50) | 12% | – | – | – | – |
| square_old_transformer_epoch200 | development (15) | 7% | – | – | – | – |
| square_old_transformer_epoch200 | test (50) | 12% | – | – | – | – |
| stack_four_bc_rnn_best_validation | development (15) | 0% | 40% | 40% | 0% | 0% |
| stack_four_bc_transformer_best_validation | development (15) | 0% | 40% | 40% | 7% | 0% |

## Interpretation

Die Objektpositions-Variante verwendet privilegierte Simulatorinformationen. Sie dient zur Diagnose und ist nicht direkt als visuelle Roboter-Policy vergleichbar.
Kurz/Lang-Vision nutzen dieselben Daten, Eingaben und 80 Bild-Zeitschritte pro Trainingsbatch (16×5 bzw. 4×20). Sequenzlänge, RNN-Zustandsdauer und Anzahl unterschiedlicher Sequenzen pro Batch ändern sich gemeinsam.
Square-GMM verändert gegenüber dem bisherigen RNN die Aktionsverteilung (Mischmodell statt MSE-Punktvorhersage). Seine Trainingsverluste sind deshalb nicht numerisch mit MSE-Loss vergleichbar.

Auch mit Objektpositionen bleibt die Leistung niedrig. Phasensteuerung, Demonstrationsabdeckung und Aktionsmodell sollten vor weiterer Skalierung untersucht werden.
Vision mit längerem Kontext: 0%; kurzer Kontext: 4%. Ein Unterschied gilt zunächst für diese Trainingsinitialisierung und Teststichprobe.
Square-GMM: 20%; bisheriges RNN: 12% auf denselben 50 neuen Seeds. Unterschiede in Trainingsdauer und Initialisierung verhindern eine reine Aussage über den GMM-Kopf allein.

## Robustheit

| Modell | Bedingung | Erfolg | Abfall gegenüber nominal (Prozentpunkte) |
|---|---|---:|---:|
| stack_two_vision_short | nominal | 20% | 0.0 |
| stack_two_vision_short | action_impulse_x | 0% | 20.0 |
| stack_two_vision_short | object_push_x | 0% | 20.0 |
| stack_two_vision_short | mass_150pct | 0% | 20.0 |
| stack_two_vision_short | mass_70pct | 0% | 20.0 |
| stack_two_vision_short | friction_50pct | 10% | 10.0 |
| stack_two_vision_short | controller_gain_80pct | 30% | -10.0 |
| stack_two_vision_short | proprio_noise_5mm | 10% | 10.0 |
| stack_two_vision_short | observation_delay_2steps | 10% | 10.0 |
| stack_two_vision_short | image_dark_50pct | 0% | 20.0 |
| stack_two_vision_short | image_occlusion_25pct_width | 0% | 20.0 |
| stack_two_vision_short | camera_shift_x_2cm | 10% | 10.0 |

## Fehler / ausgelassene Schritte

- Square robustness: robustness_square_rnn_gmm: exit 1, see logs/robustness_square_rnn_gmm.log

Übergabeaufgabe: geprüft, aber kein Demonstrationsdatensatz / validierter Expert vorhanden. Kein blindes Training eingeplant.
Vierer-Stapel: frühere beste Validierungs-Checkpoints werden geprüft; unverändertes Weitertraining ist ausgesetzt.
Robustheitsdetails stehen in den Unterordnern `robustness/`, Rohdaten in `evaluation/`, Videos in `videos/`.