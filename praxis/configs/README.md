# Lift-Konfigurationen

- `lift_ph_dynamics.json`: geschätzte Dynamik für den vollständigen Lift-PH-Trainingssplit.
- `lift_ph_20pct_dynamics.json`: entsprechende Schätzung für den 20-Prozent-Split.
- `lift_ph_bc*.json`: lokal generierte Trainingskonfigurationen; diese sind teilweise Git-ignoriert.

Fit und Erzeugung erfolgen mit `fit_lift_dynamics.py` bzw. `make_lift_configs.py` aus [src/](../src/README.md). Vollständige Befehle stehen in [praxis/README.md](../README.md).

Dynamikschätzung, Datensplit und Policy-Konfiguration müssen zueinander passen. Historische Konfigurationen laufender oder abgeschlossener Versuche nicht nachträglich ändern.
