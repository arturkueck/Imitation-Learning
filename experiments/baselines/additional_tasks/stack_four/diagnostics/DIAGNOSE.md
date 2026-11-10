# StackFour: Diagnose nach dem Nachtlauf

Stand: 01.10.2026. Bestehende Trainingsdaten und Modelle unverändert; kein neues Training gestartet.

## Befund

Beide finalen Modelle erreichen in den vorhandenen 50 nominalen Rollouts jeweils 0 erfolgreiche Vierer-Türme. Zusätzlich wurden die Seeds 6000–6002 pro Modell mit 1000 Schritten erneut ausgeführt und Objektpositionen, Greifkontakte und Teilstapel gemessen. Die Kontaktbilder der vorhandenen Videos von Seed 6000 wurden ebenfalls gesichtet.

| Prüfung der drei Detail-Rollouts | RNN | Transformer |
|---|---:|---:|
| Grüner Würfel B mindestens einmal gegriffen | 2/3 | 2/3 |
| Grüner Würfel B deutlich angehoben | 2/3 | 2/3 |
| B korrekt auf A abgelegt, mit Kontakt und beide losgelassen | 0/3 | 0/3 |
| Blauen oder gelben Würfel gegriffen | 0/3 | 0/3 |
| Vollständiger gültiger Turm | 0/3 | 0/3 |

Das Scheitern beginnt damit bereits beim Greifen oder ersten Ablegen, nicht erst beim vierten Würfel. Beim RNN, Seed 6000, melden die Greifprüfungen nach dem ersten Transfer gleichzeitig Kontakt zu A und B; beide werden angehoben. Der vorgesehene Basiswürfel bleibt somit nicht auf dem Tisch. Beim Transformer wird B zeitweise gegriffen und angehoben, aber kein korrekt losgelassener Zweierstapel erreicht. In Seed 6001 greifen beide Modelle überhaupt keinen Würfel. Die Detail-Stichprobe ist klein; die Teilschrittquoten gelten nur für diese drei Seeds pro Modell.

## Trainingsverluste

| Modell | Trainings-Loss, Epoche 1000 | Validierungs-Loss, Epoche 1000 | Bester Validierungs-Loss |
|---|---:|---:|---:|
| RNN | 0,00722 | 0,03185 | 0,02015, Epoche 454 |
| Transformer | 0,00565 | 0,02974 | 0,02117, Epoche 497 |

Am Ende liegt der Validierungsfehler etwa 4,4- bzw. 5,3-mal über dem Trainingsfehler. Er ist auch schlechter als beim jeweils besten früheren Checkpoint. Das spricht für begrenzte Generalisierung und Überanpassung. Die Validierung nutzt zufällige Sequenz-Stichproben; einzelne Minima schwanken. Ein niedriger Action-Loss garantiert keine erfolgreiche geschlossene Regelung. Die bisherigen 50-Episoden-Tests verwenden ausschließlich Epoche 1000; frühere Checkpoints sind damit noch nicht als erfolgreich oder erfolglos bewertet.

## Daten und plausible Ursachen

- 200 akzeptierte Demonstrationen, 180 Training / 20 Validierung; 105.193 Schritte. Alle gespeicherten Trajektorien enden mit positivem Erfolgsreward. Längen: 449–940 Schritte, Median 504,5. Der Expert schaffte 200 von 293 Versuchen. Keine fehlenden Demos erkennbar; dies ersetzt keine vollständige Replay-Prüfung.
- Die Policy sieht nur eine 64×64-Agentview-Kamera und Roboterpropriozeption. Die vier Perspektiven dienen ausschließlich den Videos. Kleine Würfel und enge Ablagepositionen können dadurch schwer erkennbar sein; das ist eine Hypothese, kein nachgewiesener Kamera-Fehler.
- Beide Modelle haben nur fünf Schritte Kontext. Das RNN setzt seinen Zustand alle fünf Schritte zurück; bei 20 Hz entspricht das einem kurzen Fenster von ungefähr 0,25 Sekunden. Der Expert besitzt dagegen explizite Phasen, Würfelindex und gespeicherte Zielpositionen. Fehlende längerfristige Phaseninformation ist ein weiterer plausibler Engpass.
- Gesammelt wurden nur erfolgreiche Expert-Verläufe. Zustände nach ungenauem Greifen oder verrutschten Würfeln sind deshalb wahrscheinlich schwach abgedeckt. Die Modelle können eigene Fehler damit schlechter korrigieren. Eine gezielte Ablation ist zur Ursachenbestätigung nötig.

## Empfohlene nächste Tests

1. Ohne weiteres Training die besten Validierungs-Checkpoints (RNN 454, Transformer 497) auf denselben Seeds vergleichen. Erfolg und korrekt losgelassenen Zweierstapel getrennt messen.
2. Eine einfachere Zweier-Stapelaufgabe als Basis prüfen. Greifen, Anheben, Platzieren und Loslassen separat auswerten, bevor wieder vier Würfel trainiert werden.
3. Mit einer kurzen kontrollierten Ablation prüfen, ob Objektpositionen als zusätzliche Eingabe den ersten Stapel zuverlässig ermöglichen. Dann lässt sich ein Wahrnehmungsproblem besser von einem Steuerungs-/Phasenproblem unterscheiden. Anschließend je nach Befund Bildauflösung, zeitlichen Kontext oder Korrektur-Demos verbessern.

Weitere 15 Stunden mit unverändertem Setup sind durch diese Ergebnisse derzeit nicht begründet.

## Lokale Evidenz

- `statistics.json`: Datenprüfung und Loss-Werte aus den Trainingslogs.
- `rollout_diagnosis.json`: Positionen und Teilschrittmetriken für sechs reproduzierte Rollouts.
- `bc_rnn_video_grid.png`, `bc_transformer_video_grid.png`: Kontaktbilder der vorhandenen Vierer-Ansicht-Videos.
- `inspect_rollouts.py`, `inspect_statistics.py`: reproduzierbare Diagnoseskripte.
