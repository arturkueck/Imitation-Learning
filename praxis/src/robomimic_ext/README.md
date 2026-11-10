# Lokale robomimic-Erweiterungen

Der Paketimport registriert die zusätzlichen Algorithmus- und Konfigurationsklassen.

- `contraction_bc.py`: BC mit finiter Differenz und angenäherter lokaler Lift-Dynamik.
- `sensor_bc.py`: gepaarte saubere/verrauschte Beobachtungen für ein definiertes EEF-Messfehlermodell.
- `train.py`: CLI-Adapter für das robomimic-Training.

Setup und konkrete Konfigurationen: [praxis/README.md](../../README.md). Aus dem Repository-Stamm:

```powershell
$env:PYTHONPATH=(Resolve-Path praxis/src).Path
& praxis/.venv/Scripts/python.exe -m robomimic_ext.train --help
```

Die Kontraktionsapproximation ist keine Stabilitätsgarantie durch Kontakte. Die Sensoraugmentation ändert Messwerte, nicht die physische Demonstration oder das Aktionslabel. Passende Tests: `test_contraction.py` und `test_sensor_bc.py` unter [tests/](../../tests/README.md).
