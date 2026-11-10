# Kameraplanung: geometrischer Prototyp

Basis fuer geometrisch gepruefte Handkameraansichten in der Simulation; hier wird kein Modell trainiert.

**Basisskript: [demo.py](demo.py).** Es enthaelt die kopierte Implementierung; es ist kein Weiterleitungs-Wrapper.

## Skripte

- `demo.py`: begrenzte Referenzdemonstration.
- `broad_view_demo.py`, `side_view_demo.py`: groessere Baselines und seitliche Ansichten.
- `visual_capture.py`: visuelle Freiraumevidenz aus Referenzaufnahmen.
- `register_side_views.py`: Aufbereitung fuer die bestehende Forschungsdarstellung.

## Verwendung

Aus dem Repository-Stamm kann die Hilfe ohne Trainingsstart geprueft werden:

```powershell
& praxis/.venv/Scripts/python.exe experiments/camera_planning/base/demo.py --help
```

Benutzt die gemeinsame Bibliothek `praxis/src/active_view` und den vorhandenen Vision-Szenengenerator. Demoausgaben werden relativ zu diesem Basisordner angelegt. Aufbereitungs-/Registrierungsskripte koennen dagegen die in ihrem Code explizit genannten Atlas- und Experimentpfade aktualisieren.

## Herkunft und Pflege

Die Hauptquelle ist [active_view_20261101](../active_view_20261101/). Einzelquellen, SHA-256 und Anpassungen stehen in [BASE_SOURCE.json](BASE_SOURCE.json). Die dortigen Kopie-Hashes dokumentieren den Erstellungsstand und sind keine unveraenderlichen Lauf-Siegel.

Dieser Ordner ist eine editierbare Basis fuer weitere Arbeit. Die datierten Originalskripte bleiben erhalten und importieren diese Kopien nicht automatisch. Spaetere Aenderungen werden nicht automatisch zwischen Kopie und Original synchronisiert. Neue wissenschaftliche Laeufe muessen ihren tatsaechlich verwendeten Quellstand erneut erfassen.

Daten, Gewichte, Ergebnisse, eingefrorene Quellen und alte Prozessdateien wurden nicht kopiert. Die Basisordner sind weiterhin auf die gemeinsamen Bibliotheken und oben genannten historischen Daten-/Modulabhaengigkeiten angewiesen.

[Zur Themenuebersicht](../README.md).
