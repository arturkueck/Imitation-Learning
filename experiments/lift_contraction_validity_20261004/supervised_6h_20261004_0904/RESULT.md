# Beaufsichtigter BC-Methodenpilot

Status: COMPLETED. Versuch: `attempt_002`. Seed 41004, je 2.000 Updates.

| Updates | Bedingung | BC | Sensor-Augmentation | Episoden pro Arm |
|---:|---|---:|---:|---:|
| 500 | nominal | 0 | 0 | 6 |
| 1000 | nominal | 0 | 0 | 6 |
| 2000 | nominal | 4 | 3 | 10 |
| 2000 | sensor_y_plus5mm | 3 | 4 | 10 |
| 2000 | sensor_y_minus5mm | 3 | 4 | 10 |
| 2000 | action_impulse_x_plus0.5 | 3 | 3 | 10 |

Sensorbedingungen zusammen: BC 6/20, Augmentation 8/20. Pilotregel bestanden: True.

Trainingszeit BC: 8.9 s; Augmentation: 11.4 s. Evaluation: 182.1 s.

Lift-Nativerfolg; Sensorbias und echter Aktionsimpuls getrennt. Keine Auswahl eines Zwischencheckpoints. Hashes sowie Anfangsgewichts-, Batch- und Start-Paarung überprüft.

Ein Entwicklungsseed: kein Nachweis robuster Trainingsverbesserung, physischer Stabilität oder allgemeiner schnellerer Konvergenz. Kein weiterer Lauf nur wegen schwacher Resultate.

Rohdaten/Hashes im angegebenen Versuch; vollständige Lernkurve und Kosten in pilot_summary.json. Technische Versuche und Reparaturen bleiben in attempts und repairs.jsonl erhalten.

Die sechs Stunden lange Forschungsaufsicht bleibt bis zur fixierten Deadline aktiv. Der Agent-Heartbeat soll jetzt Auswertung und nächste fachlich begründete Diagnose bearbeiten.
