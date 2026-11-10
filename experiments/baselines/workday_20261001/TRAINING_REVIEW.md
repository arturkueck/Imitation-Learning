# Prüfung der bisherigen Trainings

- Square BC: 0/20 Erfolge nach 50 Epochen. Als historische Referenz erneut auswerten, unverändertes Training aussetzen.
- Square RNN: 8/20 nach 300 Epochen; stärkster bisheriger Kandidat. Als Referenz auf neue Seeds prüfen und gezielt mit einem neu trainierten GMM-Aktionsmodell vergleichen.
- Square Transformer: bester bisher gemessener Zwischenstand 4/20 bei Epoche 200, zuletzt 2/20 bei Epoche 300. Früheren besseren Checkpoint erneut prüfen; keine unveränderte Fortsetzung.
- StackFour RNN und Transformer: je 0/50 bei Epoche 1000. Validierungsverlust zuletzt deutlich höher als Train-Loss und höher als bei früheren Minima. Beste Validierungs-Checkpoints bei Epochen 454/497 nachprüfen; neues Training auf StackTwo reduzieren.
- CubeHandover: Szene und Konfiguration vorhanden, aber kein Demonstrationsdatensatz. Noch kein trainiertes Modell vorhanden. Ein validierter Demonstrator ist der nächste notwendige Schritt, keine zusätzliche Trainingszeit.
- Frühere Preview- und Robustheits-Smokes sind technische Tests und werden nicht als unabhängige Trainingserfolge gewertet.

Rohdaten: `prior_results_audit.json` und `prior_training_losses.json`. Der bestehende Vierer-Stapel-Diagnosebericht liefert die überprüften Fehlerszenarien.
Neue Checkpoints werden anhand von Entwicklungsepisoden ausgewählt; der unabhängige Testsplit wird nicht zur Checkpointauswahl genutzt.

| Trainingslog | Letzte Epoche | Train-Loss | Validierungs-Loss |
|---|---:|---:|---:|
| bc_rnn_training.log | 50 | 0.03125 | 0.06593 |
| bc_training.log | 50 | 0.04256 | 0.05677 |
| bc_transformer_training.log | 50 | 0.02977 | 0.07344 |
| bc_rnn_to_epoch_100_training.log | 100 | 0.01981 | 0.07002 |
| bc_rnn_to_epoch_150_training.log | 150 | 0.01384 | 0.07883 |
| bc_rnn_to_epoch_200_training.log | 200 | 0.01073 | 0.09674 |
| bc_rnn_to_epoch_250_training.log | 250 | 0.01060 | 0.08467 |
| bc_rnn_to_epoch_300_training.log | 300 | 0.00743 | 0.07596 |
| bc_transformer_to_epoch_100_training.log | 100 | 0.01795 | 0.06162 |
| bc_transformer_to_epoch_150_training.log | 150 | 0.01322 | 0.07854 |
| bc_transformer_to_epoch_200_training.log | 200 | 0.00659 | 0.07684 |
| bc_transformer_to_epoch_250_training.log | 250 | 0.00933 | 0.06706 |
| bc_transformer_to_epoch_300_training.log | 300 | 0.00603 | 0.07198 |
| bc_rnn_training.log | 1000 | 0.00722 | 0.03185 |
| bc_transformer_training.log | 1000 | 0.00565 | 0.02974 |