# Wiederverwendbarer Python-Code

Die [Zuordnung der Self-Imitation-Formel zum Code](../LOSS_FORMEL.md) erklaert
Policyvorhersage, BC-Fehler, Gewichtung und die bisher separate Critic-Pruefung.

- [robomimic_ext/](robomimic_ext/README.md): registrierte BC-Erweiterungen und Trainingsadapter.
- [task_extensions/](task_extensions/README.md): lokale robosuite-Aufgaben und Demonstrationscontroller.
- [active_view/](active_view/README.md): Geometrie, Kollisionsprüfung und Kameraplanung.
- `fit_lift_dynamics.py`: lokale Lift-Dynamik aus Demonstrationen schätzen.
- `make_lift_configs.py`: Vergleichskonfigurationen erzeugen.
- `evaluate_lift.py`, `evaluate_matrix.py`: einzelne Checkpoints und gepaarte Lift-Vergleiche auswerten.
- `summarize_lift.py`, `plot_results.py`: Ergebnisse zusammenfassen und darstellen.

Setup und vollständige Reproduktionsbefehle: [praxis/README.md](../README.md). Für lokale Imports muss `praxis/src` im Python-Suchpfad liegen. Versuchsspezifische Runner gehören zu [experiments/](../../experiments/README.md); eingefrorene Quellkopien dort nicht mit diesem Arbeitsstand überschreiben.
