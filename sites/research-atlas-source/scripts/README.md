# Website-Werkzeuge

Aus dem Website-Stamm ausführen; die öffentlichen npm-Befehle stehen in [package.json](../package.json).

- `serve-local.mjs`: lokaler Leseserver für den Atlas.
- `training-monitor.mjs`: registrierte Trainingsdateien lesen und Dashboard-Snapshot exportieren.
- `export-vision-research.mjs`: Vision-Forschungsartefakte aufbereiten.
- `sync-navigation.mjs`: gemeinsame Navigation synchronisieren.
- `verify-vision-docs.mjs`, `verify-actor-critic.mjs`: spezifische Inhaltsprüfungen.
- `*.test.mjs`: Regressionstests.
- `run-framework.mjs`, Installations-/Umgebungsskripte, `vite/` und `connector-preview/`: Build- und Laufzeitintegration.

Start: [LOCAL_START.md](../LOCAL_START.md). Monitoring: [TRAINING_MONITOR.md](../TRAINING_MONITOR.md). Build und lokales Ansehen veröffentlichen keine Änderungen automatisch.
