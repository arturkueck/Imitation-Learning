# Agentenhinweise · sites/

Research Atlas (Projektwebsite). Ergänzt die Root-`AGENTS.md`.

## Welche Kopie bearbeiten

**Nur `research-atlas-source/` ist maßgeblich.** Alle anderen Einträge sind
Editor-/Deploymentkopien oder Archive und werden nicht bearbeitet oder
durchsucht: `research-*-editor/`, `research-atlas-editorial/`,
`research-atlas-update/`, `research-refinement-20261101/`,
`research-server-starter/`, `research-workspace/`, `sites/`, `*.tar.gz`.

## Aufbau von research-atlas-source/

- `public/`: statische HTML/JS/CSS-Seiten und exportierte Evidenz; die meisten
  Inhaltsänderungen passieren hier (`public/README.md`).
- `public/training-data/`, `public/training-assets/`: vom Trainingsmonitor
  erzeugt (`npm run training:export`, liest `monitor/training-runs.json`);
  nicht von Hand pflegen.
- `app/`, `components/`, `lib/`, `worker/`, `db/`: Vinext/Next-App und API.
- `scripts/`: lokaler Server, Exporte, Prüfungen (`scripts/README.md`).
- `*_DEPLOYMENT.json`, `*_RELEASE_*.md`, `SOURCE_PROVENANCE.json`:
  Veröffentlichungsprotokolle, nicht umschreiben.
- `vendor/`, `node_modules/`, `dist/`, `.next/`: nicht durchsuchen.

## Befehle (aus `research-atlas-source/`)

| Zweck | Befehl |
|---|---|
| Lokal ansehen (kein Build nötig) | `npm start` → `http://127.0.0.1:4173` |
| Trainingsdaten exportieren | `npm run training:export` |
| Navigation synchronisieren | `npm run navigation:sync` |
| Monitor-Tests | `node --test scripts/training-monitor.test.mjs` |
| Build | `npm run build` |

Nichts veröffentlichen oder deployen ohne ausdrückliche Freigabe. Zahlen auf
Seiten müssen aus den Experimentberichten stammen; nach Änderungen an
Ergebnissen `experiments/curriculum/verify_conclusion.py` bzw. die
`scripts/verify-*.mjs` passend ausführen.
