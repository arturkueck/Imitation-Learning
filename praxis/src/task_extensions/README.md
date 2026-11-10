# Lokale Simulationsaufgaben

Ein Import von `task_extensions` registriert `StackTwo`, `StackFour` und `CubeHandover` bei robosuite. Die Implementierung liegt in `environments.py`; Upstream-Dateien werden dafür nicht verändert.

`stack_expert.py` enthält einen zustandsbasierten Demonstrationscontroller. Dieser ist ein Datensammler und keine gelernte Policy; erzeugte Demonstrationen nur nach bestandener Erfolgsprüfung übernehmen.

Verwendung und Datensammlung: [additional_tasks](../../../experiments/baselines/additional_tasks/README.md). Die benötigte Simulationsumgebung ist unter [praxis/README.md](../../README.md) beschrieben. Aufgabenvarianten und Erfolgskriterien beim Vergleich von Ergebnissen ausdrücklich beachten.
