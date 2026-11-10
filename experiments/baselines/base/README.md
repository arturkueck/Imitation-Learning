# Baselines: robomimic-Training

Gemeinsamer Trainingsadapter fuer konfigurierte robomimic-Policies. Ob BC, RNN, Transformer oder Diffusion trainiert wird, bestimmt die uebergebene Konfiguration.

**Basisskript: [train_model.py](train_model.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `train_model.py`: Training und vorhandene RNN-GMM-Validierungskorrektur.
- `runtime.py`: lokale Aufgabenregistrierung und Windows-Rendering.
- `evaluate.py`, `robustness_suite.py`: Auswertung und Stoerungspruefung.
- `task_metrics.py`, `robustness.py`, `video_views.py`, `atomic_json.py`: zugehoerige Hilfsmodule.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/baselines/base/train_model.py --help
```

Benutzt robomimic, robosuite sowie `praxis/src/task_extensions`. Datensaetze und neue Trainingskonfigurationen werden ausdruecklich angegeben; es werden keine historischen Gewichte kopiert. In der Konfiguration muss ein neuer Ausgabeordner stehen. Der Standard-Ausgabeordner von `evaluate.py` liegt in dieser Basiskopie.

## Herkunft und Pflege

Die Hauptquelle ist [square/scripts](../square/scripts/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
