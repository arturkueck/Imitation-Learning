# Agentenhinweise · experiments/curriculum/

Aktivster Forschungsbereich (BC, Curriculum, Freigabephase). Ergänzt
`../AGENTS.md` und die Root-`AGENTS.md`.

## Wo steht was

- Aktueller Stand: `README.md`, Abschnitt „Aktueller Stand“ (neueste zuerst).
- Nächste Schritte: `targeted_correction_budget_v2/NEXT_STEPS_20261118.md`.
- Gesamteinordnung: `RESULTS.md`, `CONCLUSION_20261113.md`.
- Versuchskette mit Status je Familie: Tabelle „Versuchskette“ in `README.md`.

## Gemeinsame Werkzeuge

| Datei | Zweck |
|---|---|
| `models.json` | Modellkatalog: versionierte Checkpoints inkl. Optimizer und Samplingreferenz |
| `registry.py` | hashgeprüfte Checkpoint-Bundles anlegen/lesen |
| `resume.py` | Gewichte/AdamW/RNG nach Hashprüfung wiederherstellen |
| `export_research.py` | Berichte und pfadfreie Website-Evidenz erzeugen (→ `reporting/`) |
| `verify_conclusion.py` | veröffentlichte Aggregate gegen Rohpaare prüfen |
| `<familie>/monitor.py` | inkrementeller Laufmonitor (Prozessidentität, neue Logzeilen) |

Modelle nur über `registry.py`/`resume.py` laden, nicht Checkpointpfade
direkt zusammensetzen. Keine Gewichte oder `.npz`-Daten in den Kontext lesen.

## Ablage und Junctions

- Code/Protokolle hier; Laufdaten kanonisch unter
  `praxis/results/curriculum/<familie>/<lauf>/`, Modelle unter
  `praxis/results/models/bc_curriculum/`.
- Alte Laufpfade sind **NTFS-Junctions** auf die kanonische Ablage. Nie
  rekursiv löschen, verschieben oder als zweite Kopie behandeln.
- `layout_20261112.json` / `layout_verification_20261112.json` dokumentieren
  den Umzug; nicht neu schreiben.

## Regeln speziell hier

- Abgeschlossene Familien (siehe Statustabelle) sind eingefroren;
  `pipeline.py` prüft eingefrorene Komponenten per SHA und bricht bei
  Änderungen ab. Neue Fragestellung → neue Familie `<name>_v<N>/`.
- Der v2-Nachtlauf ist abgeschlossen (`targeted_correction_budget_v2/COMPLETED.md`);
  seine Drei-Seed-Ausnahme gilt für keine Folgestudie.
- Ergebnisse immer mit vollständigem Nenner (z. B. `359/450`) und Angabe,
  ob Szenen geteilt sind, wiedergeben, so wie es die bestehenden Berichte tun.
