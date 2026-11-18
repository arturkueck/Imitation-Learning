# Projektstruktur

## `latex/`

- `src/`: Einstiegspunkt und Kapitel der Ausarbeitung
- `figures/`: Abbildungen, Diagramme und Grafiken
- `bibliography/`: Literaturdatenbanken im `.bib`-Format
- `build/`: lokal erzeugte PDFs und LaTeX-Hilfsdateien (ignoriert durch Git)

## `praxis/`

- `src/`: wiederverwendbarer Programmcode
- `simulations/`: Simulationsumgebungen und zugehörige Skripte
- `notebooks/`: explorative Analysen und Versuche
- `configs/`: Konfigurationen für Training und Evaluation
- `data/`: lokale Datensätze (ignoriert durch Git)
- `results/`: Messwerte, Checkpoints und erzeugte Ausgaben (ignoriert durch Git)
- `results/curriculum/<Versuch>/<Lauf>/`: kanonische BC-/Curriculum-Laufdaten; alte Laufpfade bleiben über Junctions erreichbar
- `results/models/bc_curriculum/`: feste Modellversionen mit vollständigen Optimizerzuständen und Samplingreferenzen
- `tests/`: automatisierte Tests

## `experiments/curriculum/`

Quellcode und Protokolle der BC-/Curriculum-Untersuchungen, vorbereitete
A/B/C-Pipeline, Ergebnisberichte und ein SHA-geprüfter Modellkatalog.
Große Laufartefakte liegen getrennt unter `praxis/results/`.
Siehe [Bereichs-README](experiments/curriculum/README.md).
