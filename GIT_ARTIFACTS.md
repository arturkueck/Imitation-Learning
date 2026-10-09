# Welche Artefakte gehören ins Repository?

Versioniert werden Projektcode und Tests, Experiment-Skripte und Konfigurationen,
Protokolle, Berichte, Auswertungen, Lernkurven sowie Dataset-, Checkpoint- und
Quellcode-Hash-Manifeste. Die eingefrorenen `source_snapshot/`-Verzeichnisse
bleiben erhalten: Experiment-Worker importieren daraus Projektcode, und die
zugehörigen Manifeste dokumentieren den tatsächlich verwendeten Quellstand.
Auch die vorhandenen Dokumentationsarchive gehören zur Versuchshistorie.
`.gitattributes` verhindert automatische Zeilenumwandlungen in `experiments/`,
damit Git die Bytes der eingefrorenen Artefakte und deren SHA256 erhält.

Lokal bleiben Datensätze, Checkpoints, Videos, Trainingsverzeichnisse, Logs,
temporäre Schreibdateien und aktuelle Prozessidentitäten (`*_pid.json`,
`*_process.json`, `*.pid`). Bestehende versionierte historische Prozessdateien
bleiben erhalten; `.gitignore` wirkt auf neue, noch nicht versionierte Dateien.
Status- und Ergebnisdateien werden nicht pauschal ausgeschlossen.

Zehn große `result.json`-Dateien der Session
`experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/`
enthalten detaillierte Simulator-Trajektorien. Diese konkreten Dateien sind
in `.gitignore` aufgeführt und bleiben unverändert auf dem lokalen Rechner.
Jeweils daneben enthält `result_summary.json` alle ursprünglichen Felder außer
`rows`, ergänzt um den relativen Rohdatenpfad, Dateigröße, SHA256 und Anzahl der
ausgelassenen Zeilen. Diese Zusammenfassungen ersetzen keine Rohdatenprüfung.
Skripte, die `result.json` lesen oder deren Hash prüfen, benötigen weiterhin
die zugehörigen lokalen Rohdateien sowie die bereits ausgeschlossenen
Datensätze, Modelle und vollständigen Simulator-Abhängigkeiten.

Neue große Rohartefakte vor dem Commit prüfen und gezielt ausschließen;
keine allgemeine Regel für `*.json`, `result.json`, alle Experimente oder
alle Snapshots verwenden. Für einen späteren vollständigen Datenaustausch
müssen die ausgeschlossenen Artefakte zusätzlich separat bereitgestellt werden.

Unter Windows kann dieses Projekt Pfade mit mehr als 260 Zeichen enthalten.
Im lokalen Checkout deshalb einmal ausführen:

```powershell
git config --local core.longpaths true
```
