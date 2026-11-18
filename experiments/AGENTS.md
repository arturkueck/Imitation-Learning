# Agentenhinweise · experiments/

Ergänzt die Root-`AGENTS.md`; deren Forschungsregeln haben Vorrang.

## Aufbau

- `<thema>/README.md`: Überblick und Status der Familien eines Themas.
- `<thema>/<familie>_<YYYYMMDD>/` oder `<familie>_v<N>/`: ein Versuch mit
  README, Plan/Protokoll, `config.json`, Skripten, Tests und Berichten
  (`RESULTS.md`, `FINDINGS.md`, `COMPLETED.md`, `ASSESSMENT.md`).
- `<thema>/base/`: editierbare Skriptkopien plus `BASE_SOURCE.json`
  (Herkunft). Ausgangspunkt für neuen Code eines Themas.
- `layout.json`: Zuordnung alter zu neuen Pfaden (Umzug 10.11.2026).

## Einen Versuch verstehen (Lesereihenfolge)

1. `README.md` der Familie, danach das Ergebnisdokument
   (`COMPLETED.md`/`RESULTS.md`/`FINDINGS.md`), falls vorhanden.
2. Erst bei Bedarf: Protokoll, `config.json`, Manifeste zu Splits/Seeds/Budget.
3. Code nur bei konkreter Frage. Logs (`*.log`) und Ausgabeordner
   (`run_*`, `smoke_*`, `preflight_*`, `*_001` …) nicht vollständig lesen,
   gezielt mit `Select-String`/`grep` suchen.

## Ändern

- **Datierte bzw. versiegelte Familien nicht bearbeiten.** Ihre Quellen sind
  über SHA-Manifeste (`frozen_components.json`, `SOURCE_*`, `VERIFICATION.json`)
  an Ergebnisse gebunden; Änderungen brechen Provenienz und Fortsetzbarkeit.
  Ausnahme nur für ausdrücklich freigegebene technische Reparaturen.
- Neuer Versuch = **neues Verzeichnis** mit eigener README, Konfiguration und
  Quellsiegel. Code aus `base/` oder `praxis/src/` übernehmen, nicht aus
  einer datierten Familie importieren und dort verändern.
- `base/` und die datierten Originale werden nicht automatisch synchronisiert.
  Vor dem Bearbeiten klären, welche der Kopien gemeint ist.
- Status-JSON im Versuchsordner ist kein Beleg für einen laufenden Prozess.

## Ausführen

Aus dem Repository-Stamm mit `praxis/.venv/Scripts/python.exe` und gesetztem
`PYTHONPATH` (siehe Root-`AGENTS.md`). Tests einer Familie:
`& praxis/.venv/Scripts/python.exe -m pytest -q experiments/<thema>/<familie>/test_*.py`.
Kein Training starten ohne ausdrückliche Freigabe; `--help` und Tests sind
unbedenklich.
