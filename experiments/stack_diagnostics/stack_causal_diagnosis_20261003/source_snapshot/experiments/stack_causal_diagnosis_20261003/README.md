# Kontrollierte Ursachenanalyse, C / Seed 1

Zuerst `DIAGNOSE.md`, dann Datenaudit und separater UNet-Config-Fix, dann technische Vorprüfung. Kein Training, keine neuen Daten und keine automatische Folge nach Experiment 1.

Einziger Startbefehl aus dem Projektordner:

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\stack_causal_diagnosis_20261003\run.py
```

Der Launcher startet einen eigenen versteckten Windows-Prozess außerhalb des Shell-Jobs. Worker-PID: `launch.json` und `worker_started.json`; aktiver Child-Prozess: `status.json`. Keine sichtbaren Simulatorfenster. `run.log` enthält Evaluationen, `startup.log` frühe Fehler. Rechner muss eingeschaltet bleiben; Worker hält Windows während der Ausführung wach.

1. Exp0: unverändertes C-Diffusionsmodell, 40 historische Starts, 500+40 Schritte, gleiche Observation-Normalisierung, EMA und DDIM10, execute2. Original/effective config werden getrennt gesichert. Keine Checkpointauswahl oder neues Training.
2. Exp1: fünf vorab gewählte Validierungsdemos × sechs Expert-Anker × Expert/C-Direct/C-Diffusion = 90 Fortsetzungen. Pro Fall 120+40 Schritte. Initiale Teilgeometrie explizit separat; vollständige stabile Stacks sind die Hauptmetrik.
3. Danach Prozessende. Exp2-Gripper und Exp3-Horizonte werden erst nach Interpretation separat durchgeführt. Kein Sweep.

Abschluss: `complete.json`, `status.json` = COMPLETED, `RESULTS.md`, `results.json`, `output_hashes.json`. Abbruch: `failed.json` bzw. `<stage>_failed.json`; vorhandene einzelne Episoden bleiben erhalten und werden nicht als vollständige Auswertung dargestellt. Doppelte Starts / vorhandene Ergebnisordner werden verweigert.

Phase-Starts: gespeichert ist jeder pre-action-Expert-Zustand, aber kein vollständiger Controllerzustand. Deshalb Replay ab Original-XML/state[0] bis zum Anker, statt bloß qpos/qvel mitten in der Sequenz zu restaurieren. Nach Rekonstruktion der Controller-/Gripper-Erinnerung wird exakt der gespeicherte state[k] wiederhergestellt, der OSC-achieved-goal aktualisiert und die gespeicherte t−1,t-History eingesetzt. Gültigkeit erfordert initialen Grasp, Position-/Fingerabweichung <2mm gegenüber Demo und bitidentische gespeicherte/aktive Start-Hashes zwischen Modellen. Expert muss denselben Anker anschließend stabil abschließen, sonst Abbruch. Expert-FSM wird aus den gespeicherten Beobachtungen rekonstruiert; der Expert hat zusätzlich interne Phase/Ziele. Sein Erfolg ist eine Schnittstellenkontrolle, kein gelernter Benchmark.

NPZ pro Episode: `trace` mit historischem 37-Spalten-Schema, post-action; `states` post-action; vier Policy-Observation-Arrays pre-action; `initial_state`; `measured`. Diffusion zusätzlich alle vollständigen 16×7 `chunks` sowie ihre Replanning-Schritte, sodass Vorhersage vs Ausführung geprüft werden kann. In dieser Runde sind vorgeschlagene/ausgeführte Actions identisch. Slice- und Inversionsparität wird pro Schritt geprüft. First-step-Observation-Normalisierung wird gegen die eingefrorenen C-Statistiken geprüft. Jede Action muss endlich, 7-dimensional und innerhalb ±1 sein.

`preflight_v3/` ist ein technischer Test ab einem Prä-Release-Anker: Expert-Kontrollabschluss, dann je zwei Hauptschritte plus Tail von Direct/Diffusion. **Keine neue belastbare Erfolgsquote** aus diesem Test ableiten. `audit_summary.json`, `C_gripper_episodes.csv/json`, `C_grasp_loss_events.json`, `phase_counts.json`, `quaternion_audit.json`, `temporal_alignment.json`, `normalization_channels.json` und drei Expert-Verlaufsbilder sind ausschließlich Auswertungen vorhandener Daten/Traces. Hypothesen im Diagnosebericht und Auditgrenzen beachten.

`unet_config_fix_verified.json`: separate Korrektur des Config-Forwardings mit bitgleichen Default-Initialgewichten und realer Prüfung abweichender kleiner UNet-Config. Aktuelle C-Architektur bleibt gleich. Originale Datensätze und Gewichte sind unverändert. `input_hashes.json` / `source_hashes.json` sichern Eingaben, Quellen und Configs.

Nach Abschluss als Prompt verwenden: „Werte experiments/stack_causal_diagnosis_20261003 aus. Prüfe zuerst vollständige Outputs, Expert-Kontrollen und Paaridentität. Berichte Exp0-Reproduktion und Failure Points je Phase; trenne bereits initial erfüllte Teilmetriken von neuem Fortschritt. Entscheide dann anhand der Evidenz, ob der nächste isolierte Test Gripper oder Replanning sein soll. Starte kein Training.“

Alle 30 Expert-Kontrollen in `anchor_preflight_v3/` abgeschlossen und stabil erfolgreich. Ältere technische Vorversuche (`preflight/`, `anchor_preflight/`, `anchor_preflight_v2/` und zugehörige Logs/Fehler) bleiben erhalten; sie gelten nicht als finale Vorprüfung. `object_orientation_audit.json` und `geometric_coverage.json` ergänzen die statische Diagnose.
