# Critic: Actor-Critic-Kern und Laufsteuerung

Basis fuer Critic-Vortraining und den historischen Actor-Critic-Vergleich mit optionalem BC-Anker.

**Basisskript: [run.py](run.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `core.py`: Q-Netze, Learner, Zielwerte und Optimierung.
- `run.py`: Vorbereitung, Sammlung, Warmup, Training und technischer Smoke-Test.
- `config.json`: kopierte Ausgangskonfiguration; vor neuen Laeufen bewusst konfigurieren.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/base/run.py --help
```

Verwendet die vorhandenen Controller-, Collector- und Policy-Module sowie Elterncheckpoints unter `self_imitation/`. `--output` ist erforderlich; keine alten Laufverzeichnisse wiederverwenden. Der Actor-Critic-Loss ist von der vorgeschlagenen festen Critic-Gewichtung eigener Aktionen zu unterscheiden. Die separate Aktions-/Abschnitts-Machbarkeitsstudie bleibt unter `../il_action_feasibility_20261107/`.

## Herkunft und Pflege

Die Hauptquelle ist [critic_warmstart_20261104](../critic_warmstart_20261104/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
