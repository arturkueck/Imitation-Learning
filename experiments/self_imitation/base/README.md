# Selbstimitation: gewichteter BC-Pilot

Basis fuer den vierarmigen Vergleich von Original-BC, Erfolgs-Replay und bestaetigten eigenen Abschnitten mit optionaler Qualitaetsgewichtung.

**Basisskript: [pilot.py](pilot.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `pilot.py`: Datenpruefung, vier Trainingsarme und gepaarte Evaluation.
- `transition_pilot.py`: Abschnittspool, Datenaudits und `weighted_loss`.
- `native_collector.py`, `state_replay.py`, `online_evaluation.py`: Sammlung und physische Pruefung.
- `diagnose.py`, `monitor.py`, `supervise.py`: Diagnose und Laufaufsicht.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/self_imitation/base/pilot.py --help
```

Originaldemos, Trainingsarrays und Elternmodelle werden weiterhin aus ihren dokumentierten Experimentpfaden gelesen. Der Collector verwendet die vorhandene Curriculum-/Policy-Implementierung. Die lokalen Loss- und Collector-Kopien werden von `pilot.py` verwendet. `--output` muss auf einen neuen Laufordner zeigen. Die Gewichte stammen bisher aus einer geometrischen Qualitaetsheuristik, nicht aus dem Critic; siehe [Formelzuordnung](../../../praxis/LOSS_FORMEL.md).

## Herkunft und Pflege

Die Hauptquelle ist [partial_self_imitation_20261104](../partial_self_imitation_20261104/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
