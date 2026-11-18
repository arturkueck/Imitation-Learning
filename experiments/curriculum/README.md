# BC, Curriculum und Freigabephase

Dieser Themenordner enthält Quellcode, Konfigurationen, Prüfungen und die
wissenschaftliche Einordnung der Untersuchungen vom 10.–13.11.2026.

## Aktueller Stand

- [Restfehlerdiagnose vom 18.11.](residual_phase_diagnosis_v1/FINDINGS.md):
  abgeschlossen, 112 Episoden ohne Training. Bewegung und Abschluss getrennt
  untersucht; lokale Phasenfortschritte und vollständiger Erfolg separat.
- [Nachtlauf 17./18.11.: Methodik v2, Abschluss](targeted_correction_budget_v2/COMPLETED.md):
  abgeschlossen. Gezielte Datenherkunft 359/450 gegenüber normalen neuen
  Expertenbeispielen 362/450; kein Genauigkeitsvorteil nachgewiesen.
  150 gemeinsame Szenen und drei bestehende Parents, keine 450 unabhängigen Szenen.
- [Abschluss: Vorgehen, Ergebnisse und Grenzen](CONCLUSION_20261113.md):
  vollständige Untersuchungskette bis zur neuen BC-Bestätigung, 118/150
  statt 85/150 bei B; kein Curriculum-Reihenfolgevorteil nachgewiesen.
- [BC-Korrekturtraining für zweites Anfahren](approach_bc_correction_v1/README.md):
  abgeschlossen mit neuen Expertenkorrekturen und getrenntem Aktions-/Abschlusslernen;
  trainierte Kombination verbessert alle drei Modellseeds gegenüber Replay.
- [Einzelphasen des zweiten Greifens](grasp_phase_ablation_v1/README.md):
  abgeschlossen, 300 Episoden ohne Training; nur Anfahren erreicht wie die
  vollständige Expertenhilfe 45/60 statt 26/60 Gesamterfolgen.
- [Gesamtergebnisse und Grenzen](RESULTS.md): getrennte Panels und Forschungsfragen.
- [Zweiter Greifprozess: Ergebnis](phase_skill_audit_v1/GRASP_PROBE_RESULTS.md):
  abgeschlossen; 26/60 BC-Erfolge gegenüber 45/60 mit Expertenübernahme,
  19 gepaarte Gewinne, keine Verluste; keine Optimizer-Updates.
- [Phasendiagnose](phase_skill_audit_v1/README.md): abgeschlossen, 220 Versuche;
  trennt Expertenstarts von Zuständen aus vollständigen BC-Ausführungen.
- [A/B/C-Vergleich](abc_comparison_20261112/README.md): abgeschlossen;
  drei neue Standard-BC-Modelle A, sechs 30k-B/C-Modelle wiederverwendet.
- [Modellkatalog](models.json): 21 versionierte Initial-/30k-/60k-/Abschlussmodelle
  einschließlich vollständiger Optimizerzustände und Samplingreferenzen.
- [Zeitkorrektur](axis_bc_clock_validation_20261112/README.md): abgeschlossene
  frische Simulation, 60 zusätzliche gepaarte Erfolge ohne verlorenen Erfolg.

## Verzeichnisaufteilung

| Ort | Inhalt |
|---|---|
| `experiments/curriculum/<Familie>/` | Skripte, Konfiguration, Tests, README und Prüfberichte |
| `experiments/curriculum/reporting/` | Kleine versionierbare Messwert-/Website-Exporte |
| `praxis/results/curriculum/<Familie>/<Lauf>/` | Kanonische Laufdaten: Status, Logs, Modelle, Samplepläne, eingefrorene Quellen und Rohresultate |
| `praxis/results/models/bc_curriculum/<Verlauf>/seed_<s>/update_<u>/` | Stabile Modellversion: Checkpoint, Metadaten, README |
| `praxis/results/models/bc_curriculum/sampling/` | Zugeordnete unveränderte Samplingpläne |

Die elf bisherigen Laufverzeichnisse wurden physisch in die kanonische
Ergebnisablage verschoben. An ihren alten Stellen stehen NTFS-Junctions.
Dadurch bleiben ursprüngliche Dateipfade, Byteinhalte und SHA-Manifeste gültig;
es werden keine historischen Protokolle umgeschrieben. Neue A/B/C-Läufe schreiben
direkt in die kanonische Ablage. Kein Modell oder Datensatz wurde gelöscht.

[Umzugsmanifest](layout_20261112.json) und [Byte-/Provenienzprüfung](layout_verification_20261112.json)
dokumentieren 839 erhaltene Dateien und die geprüften Eingänge. Junctions nicht
als zweite Datenkopie behandeln und nicht rekursiv löschen. Für einen Transfer
auf einen anderen Rechner die kanonischen Verzeichnisse übertragen und die
Kompatibilitätspfade bewusst neu einrichten; ein Git-Checkout allein enthält
keine lokalen Checkpoints oder Datensätze.

## Versuchskette

| Familie | Status / Zweck |
|---|---|
| `axis_bc_20261110` | Abgeschlossen: ursprünglicher 30k-B/C-Reihenfolgevergleich |
| `axis_bc_extension_20261110` | Abgeschlossen: gewöhnliche Fortsetzung auf 60k |
| `axis_bc_completion_20261111` | Frühere Acht-Stunden-Vorbereitung, nicht als wissenschaftlicher Lauf gestartet |
| `axis_bc_completion_10h_20261111` | Abgeschlossen: Austauschtests und Training mit fester Abschlussfunktion |
| `axis_bc_release_diagnosis_20261112` | Abgeschlossen: ausgewählte Trajektorien und kausaler Zeit-Eingriff |
| `axis_bc_clock_validation_20261112` | Abgeschlossen: neue gepaarte Bestätigung mit festen Gewichten |
| `abc_comparison_20261112` | Abgeschlossen: A/B/C mit einheitlicher Zeitbehandlung |
| `phase_skill_audit_v1` | Abgeschlossen: isolierte Phasenprüfung und gepaarter Eingriff beim zweiten Greifen |
| `grasp_phase_ablation_v1` | Abgeschlossen: einzelne Experteneingriffe; stärkster Ansatzpunkt zweites Anfahren |
| `approach_bc_correction_v1` | Abgeschlossen: BC-Korrekturen, neue Bestätigung 118/150 gegenüber B 85/150 |

## Modelle laden und weitertrainieren

```python
# Aus dem Projektstamm; Module nicht aus einem historischen Snapshot umschreiben.
import sys
sys.path.insert(0, "experiments/curriculum")
import resume
model, optimizer, checkpoint = resume.load("mixed_s1_u30000", device="cuda", restore_rng=True)
start_update = checkpoint["update"]
```

`resume.load()` prüft Checkpoint- und Samplinghashes und lädt Gewichte und AdamW-Momente.
Bei Abschlussvarianten wird auch die unveränderte Referenz geladen. Die
Metadaten nennen Datensatz-/Featurevertrag und Sampleplan. Für ein exaktes
Sampling-Replay sind diese Pläne erforderlich; für weitere Updates nach einem
bereits ausgeschöpften Budget ist ein neuer, dokumentierter Plan nötig.

Die neue A-Pipeline speichert außerdem nächsten Batchindex, kompletten Plan,
Python-/NumPy-/Torch-/CUDA-Zustand und die Samplingdatei. Die Wiederherstellung
eines identischen nächsten CPU-Optimizer-Schritts ist geprüft. Exakte
CUDA-Wiederholbarkeit über andere Bibliotheks-/GPU-Versionen wird nicht behauptet.
Fortsetzungen schreiben in neue Laufverzeichnisse; archivierte Modelle werden
nicht ersetzt. Gewichte und Datensätze bleiben lokal und werden nicht auf die
Website oder ins Git-Repository hochgeladen.

`registry.py build` verifiziert/kopiert die bisherigen festen Modellversionen;
es startet kein Training. `export_research.py` erzeugt ausschließlich Berichte,
öffentliche Messdaten und Einträge im lokalen Trainingsregister.
