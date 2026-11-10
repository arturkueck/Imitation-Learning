# Stack-Diagnosen: Dynamikpruefung

Basis fuer die Train-Demo-Kreuzvalidierung und die kontrollierte Aktionsantwortpruefung des Lift-Dynamikmodells.

**Basisskript: [audit.py](audit.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `audit.py`: Offline-Auswertung und Simulatorinterventionen; der Modus ist ein Pflichtargument.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/stack_diagnostics/base/audit.py --help
```

Benutzt den lokalen Lift-Datensatz und die vorhandene Simulationsumgebung unter `praxis/`. Dies ist der Einstieg fuer die Dynamikdiagnose; andere historische Stack-Diagnosen sind weiterhin bei ihren Versuchen dokumentiert. Die erzeugten Auditdateien liegen hier im Basisordner.

## Herkunft und Pflege

Die Hauptquelle ist [lift_contraction_validity_20261004](../lift_contraction_validity_20261004/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
