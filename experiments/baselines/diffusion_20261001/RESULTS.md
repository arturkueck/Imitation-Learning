# Diffusion Policies und reparierte Störungsprüfung

Status: COMPLETED; Laufzeit: 159.9 Minuten.
Square-GMM-Störungsprüfung: COMPLETED.

| Modell | Split | Erfolg | Stabil nach Nachlauf |
|---|---|---:|---:|
| stack_two_diffusion_vision_best_saved_validation | development (15) | 0% | 0% |
| stack_two_diffusion_vision | test (50) | 2% | 0% |
| stack_two_diffusion_state_best_saved_validation | development (15) | 0% | 0% |
| stack_two_diffusion_state | test (50) | 0% | 0% |
| square_diffusion_vision_best_saved_validation | development (15) | 7% | 7% |
| square_diffusion_vision_last | development (15) | 0% | 0% |
| square_diffusion_vision | test (50) | 4% | 4% |

## Vergleich und Grenzen

Neue Modelle: UNet-Diffusion Policy mit EMA, zwei Beobachtungen, 16 vorhergesagten Aktionen und acht ausgeführten Aktionen pro Neuplanung. DDIM mit zehn Entrauschungsschritten. 300 Epochen à 100 Batches, Batchgröße 8.
Datensätze und Aufteilung bleiben identisch: jeweils 180 Trainings- und 20 Validierungstrajektorien. Alle 100 Epochen wird ein Checkpoint gespeichert.
Checkpointauswahl auf 15 Entwicklungsepisoden (Seeds 6000–6014); unabhängiger Vergleich auf 50 Tests (Seeds 26000–26049), identisch zu den bisherigen BC-Tests.
Bisherige Ergebnisse auf diesen Test-Seeds: StackTwo Vision kurz 4 %, Vision lang 0 %, Objektpositionen-RNN 0 %; Square GMM 20 %, RNN 12 %, Transformer 12 %. Unterschiede in Modellgröße, Trainingsbudget und Initialisierung verhindern eine reine isolierte Algorithmen-Aussage.
Objektpositionen sind privilegierte Simulatorinformationen; die State-Policy dient der Diagnose und ist keine visuelle Roboter-Policy. Eine Trainingsinitialisierung je Modell; Erfolg ist nicht vorab garantiert.

Gemessen: stack_two_diffusion_vision erreicht 2% in 50 Tests.
Gemessen: stack_two_diffusion_state erreicht 0% in 50 Tests.
Gemessen: square_diffusion_vision erreicht 4% in 50 Tests.

## Robustheit

| Modell | Bedingung | Erfolg | Abfall (Prozentpunkte) |
|---|---|---:|---:|
| square_rnn_gmm_repaired | nominal | 10% | 0.0 |
| square_rnn_gmm_repaired | action_impulse_x | 10% | 0.0 |
| square_rnn_gmm_repaired | object_push_x | 20% | -10.0 |
| square_rnn_gmm_repaired | mass_150pct | 0% | 10.0 |
| square_rnn_gmm_repaired | mass_70pct | 10% | 0.0 |
| square_rnn_gmm_repaired | friction_50pct | 0% | 10.0 |
| square_rnn_gmm_repaired | controller_gain_80pct | 0% | 10.0 |
| square_rnn_gmm_repaired | proprio_noise_5mm | 10% | 0.0 |
| square_rnn_gmm_repaired | observation_delay_2steps | 10% | 0.0 |
| square_rnn_gmm_repaired | image_dark_50pct | 0% | 10.0 |
| square_rnn_gmm_repaired | image_occlusion_25pct_width | 0% | 10.0 |
| square_rnn_gmm_repaired | camera_shift_x_2cm | 0% | 10.0 |
| square_diffusion_vision | nominal | 0% | 0.0 |
| square_diffusion_vision | action_impulse_x | 0% | 0.0 |
| square_diffusion_vision | object_push_x | 20% | -20.0 |
| square_diffusion_vision | mass_150pct | 0% | 0.0 |
| square_diffusion_vision | mass_70pct | 0% | 0.0 |
| square_diffusion_vision | friction_50pct | 0% | 0.0 |
| square_diffusion_vision | controller_gain_80pct | 0% | 0.0 |
| square_diffusion_vision | proprio_noise_5mm | 0% | 0.0 |
| square_diffusion_vision | observation_delay_2steps | 10% | -10.0 |
| square_diffusion_vision | image_dark_50pct | 0% | 0.0 |
| square_diffusion_vision | image_occlusion_25pct_width | 0% | 0.0 |
| square_diffusion_vision | camera_shift_x_2cm | 0% | 0.0 |
| stack_two_diffusion_vision | nominal | 0% | 0.0 |
| stack_two_diffusion_vision | action_impulse_x | 10% | -10.0 |
| stack_two_diffusion_vision | object_push_x | 0% | 0.0 |
| stack_two_diffusion_vision | mass_150pct | 0% | 0.0 |
| stack_two_diffusion_vision | mass_70pct | 0% | 0.0 |
| stack_two_diffusion_vision | friction_50pct | 0% | 0.0 |
| stack_two_diffusion_vision | controller_gain_80pct | 0% | 0.0 |
| stack_two_diffusion_vision | proprio_noise_5mm | 0% | 0.0 |
| stack_two_diffusion_vision | observation_delay_2steps | 0% | 0.0 |
| stack_two_diffusion_vision | image_dark_50pct | 0% | 0.0 |
| stack_two_diffusion_vision | image_occlusion_25pct_width | 0% | 0.0 |
| stack_two_diffusion_vision | camera_shift_x_2cm | 0% | 0.0 |

## Fehler

Keine bisher.

Videos: `videos/` und `repair/robustness/`; vier Perspektiven plus zwei Sekunden Nachlauf.
Die vorherige Square-Prüfung brach beim atomaren Ersetzen einer Statusdatei mit WinError 5 ab. Die Reparatur verwendet eindeutige Temporärdateien und bis zu zehn Wiederholungsversuche bei kurzfristigen Dateisperren. Eine echte Windows-Sperre wurde im Vorabtest nachgestellt und erfolgreich überbrückt.
Die bisherigen vier Trainings waren technisch abgeschlossen; sie werden nicht unverändert wiederholt. Die schwachen Stapelergebnisse werden mit einem anderen Aktionsmodell untersucht.