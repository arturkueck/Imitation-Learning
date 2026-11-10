# Vision: gepaarte V4-Pipeline

Basis fuer den kontrollierten A/B-Vergleich mit zusaetzlichen seitlichen Handkamerabildern. Hier liegt die implementierte V4-Pipeline; V2, V3 und Q1 bleiben als eigene Verfahren dokumentiert.

**Basisskript: [pipeline.py](pipeline.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `pipeline.py`: CLI fuer Vorbereitung, Pruefung, Sammlung, Training und Monitoring.
- `pipeline/`: getrennte Module fuer Daten, Protokoll, Training, Evaluation, Ressourcen und Laufzustand.
- `paired_learning.py`, `pilot.py`, `pilot_bank.py`: gepaarte Lern- und Pilotlogik.
- Weitere kopierte Skripte: Kamerafuehrung, Replay, Berichte und unabhaengiger Laufstart.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/vision/base/pipeline.py --help
```

Liest historische Vision-Daten, Kalibrierungen und Startgewichte weiterhin an ihren bestehenden Pfaden. Neue Vorbereitungen werden relativ zu diesem Basisordner angelegt. Fuer Basiskopien wurde ein eigener Monitoring-ID-Praefix eingerichtet, damit gleichnamige Laufordner den historischen Registereintrag nicht ersetzen.

## Herkunft und Pflege

Die Hauptquelle ist [visual_side_v4_20261102](../visual_side_v4_20261102/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
