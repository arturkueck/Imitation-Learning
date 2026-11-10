# Regressionstests

Die Tests prüfen BC-Lossterme, Messfehleraugmentation, visuelle Evidenz, Datenverträge und geometrische Kameraplanung. Sie trainieren keine vollständigen Forschungsmodelle; einige benötigen aber die installierte Simulationsumgebung und lokale Abhängigkeiten.

Aus dem Repository-Stamm beispielsweise:

```powershell
& praxis/.venv/Scripts/python.exe -m pytest -q praxis/tests/test_contraction.py praxis/tests/test_sensor_bc.py
& praxis/.venv/Scripts/python.exe -m pytest -q praxis/tests/test_active_view.py praxis/tests/test_side_views.py praxis/tests/test_view_sweep.py
```

Weitere Tests liegen direkt bei den [Experimenten](../../experiments/README.md), etwa für Critic, Vision-Q1 und V4. Setup: [praxis/README.md](../README.md).

Bestandene Regressionstests belegen die geprüften Eigenschaften; sie ersetzen keine reservierte Evaluation der Policy oder Wahrnehmungsqualität.
