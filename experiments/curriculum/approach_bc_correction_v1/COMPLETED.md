# Abgeschlossener BC-Korrekturlauf

Status: COMPLETE. Der wissenschaftliche Lauf `ready_001` ist abgeschlossen;
der Ordnername ist die erhaltene ursprüngliche Vorbereitungs-ID.
Das unveränderte README und die Konfiguration dieses Quellordners dokumentieren
das vorab eingefrorene Protokoll und gehören zu dessen SHA-Provenienz.

[Aktuelle Abschlussdokumentation](../CONCLUSION_20261113.md) beschreibt Vorgehen,
Resultate, Ausführungskontext, Datenabdeckung und Grenzen.

Lokal bleiben unter `praxis/results/curriculum/approach_bc_correction_v1/ready_001/`:

- `REPORT.md`, `summary.json`, `paired_changes.json`: Ergebnisse je Panel/Seed.
- `rollouts.jsonl` / `rollouts.json`: vollständige Einzelversuche.
- `collection_attempts.json`, `dataset_manifest.json`, Korrektur-NPZ:
  alle Sammelversuche und Split-/Familieninformationen.
- `mixed_s*_u30000_{replay,correction}_{actor,completion}/`:
  versionierte Checkpoints, latest, Trainingsvertrag, Loss und Validierung.
- `composition_mixed_s*_u30000.json`: benötigte Komponenten pro Ausführung
  einschließlich B-Vorfahren und Gate für zweites Anfahren ohne Rückzug.
- `plan.json`, `provenance.json`, `sources/`, `environment.json`:
  vorab fixiertes Protokoll und erfasste Umgebung/Quellen.

Die Kombination nutzt zwei separat gelernte Kopien. Nur die letzte Schicht zu
laden oder nur einen Komponentencheckpoint als fertige Policy zu verwenden
reproduziert dieses Ergebnis nicht. Gewichte, Optimizer, RNG und Samplerreferenz
sind vorhanden; das Laufverzeichnis muss für Fortsetzungen erhalten bleiben.
`restore_branch` und die Kompositionskarten sind der Einstieg. Neue Budgets
oder eine gemeinsame MLP benötigen ein neues versioniertes Protokoll.
