# Geometrische Kameraplanung

Deterministische Bausteine zur Planung und Prüfung von Handkameraansichten in der Simulation. Hier wird kein Wahrnehmungsmodell trainiert.

| Modul | Aufgabe |
|---|---|
| `geometry.py` | Boxen, konvexe Hüllen und konservative Abstandsgrenzen |
| `collision.py` | Ganzarm- und Kantenprüfung mit explizitem Weltmodell |
| `planner.py` | IK, Pfadsuche, Blickbewertung und zeitliche Abtastung |
| `side_views.py` | Seitliche Ansichten mit Ausrichtung auf das Ziel |
| `view_sweep.py` | Größere Kamerabaselines und Erkundungsvorschläge |
| `camera_guidance.py` | Bewegungsumhüllungen und Blickverfeinerung |
| `visual_map.py` | Beobachtungsbasierte Karte; unbekannte Bereiche bleiben gesperrt |
| `capture_requests.py` | Aufnahmeabsicht, geplante/tatsächliche Pose und Journal |

Beispiele: [Active-View-Experimente](../../../experiments/camera_planning/active_view_20261101/README.md). Regressionstests: [praxis/tests/](../../tests/README.md).

Geometrische Scores sind Heuristiken. Kinematische Wiedergabe belegt keine reale Regler- oder Kollisionssicherheit; eine protokollierte Aufnahmeabsicht ist kein Kollisionszertifikat.
