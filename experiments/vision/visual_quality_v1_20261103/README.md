# Q1: Qualität von 3D-Vorschlägen

Gelernte Bewertung vorhandener Rekonstruktionsvorschläge. Q1 wählt zwischen Anfangsschätzung und Kandidaten aus zusätzlichen Seitenansichten; die Vision-Gewichte bleiben im beschriebenen Versuch eingefroren.

## Einstieg

- [TRAINING_PLAN.md](TRAINING_PLAN.md): Aufgabe, Splitregeln und Modell.
- [READINESS.md](READINESS.md): Historischer Vorbereitungsstand.
- [prepared_001/RUN_STATUS.md](prepared_001/RUN_STATUS.md): Dokumentierter Laufstand.
- [quality.py](quality.py): Öffentliche CLI.
- [test_quality.py](test_quality.py): Regressionstests.

## Einordnung

Dieser Q1 ist ein Vision-Qualitätsselektor, kein Actor-Critic-Q-Netz. Geometrischer Auswahlgewinn ist getrennt von Platzierungsstabilität und Aufgabenerfolg zu beurteilen.

[Zur Experimentübersicht](../../README.md).
