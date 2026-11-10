# Diffusion-Sanity-Test: Greifen, Lift und kurzer Transport

Ein frischer Trainingslauf mit Seed 1 und 30.000 echten Optimizer-Updates. Unverändert gegenüber C: UNet, AdamW, Learning Rate, Scheduler, EMA, Batchgröße, Action-Repräsentation, zwei History-Slots, 16×7 Prediction-Chunks und zehn DDIM-Schritte. Im Rollout werden unverändert zwei Actions an Chunkpositionen 1 und 2 ausgeführt. Observation-Statistiken werden exakt aus C übernommen; keine Action-Normalisierung.

## Einzige Lernaufgabenänderung

Alle 180 Trainings- und 20 Validierungsdemos bleiben im ursprünglichen Split. Jede Demo wird beim ersten Erreichen von 3 cm projiziertem Transportfortschritt in Expert-Phase 4 abgeschnitten. Der Fortschritt wird vom Beginn dieser Phase entlang der dortigen Richtung von Objekt B zu Zielobjekt A gemessen. Es verbleiben 17.423 Trainings- und 1.854 Validierungsframes. Actions und verwendete Low-Dimensional-Observations sind unveränderte Präfixe; ungenutzte RGB-Datasets werden nicht kopiert. Die native End-Padding-Regel bleibt erhalten, einschließlich Wiederholung der letzten Action. Keine synthetischen Actions, Gewichte oder neuen Features.

Die Skalierung wird nicht auf den gekürzten Daten neu angepasst: Die eingefrorenen Statistiken aus den ursprünglichen 180 C-Trainingsdemos gelten für Training, Validierung und Rollout. Initialgewichte müssen vor dem ersten Update denselben Hash wie C/Seed 1 haben. Durch gekürzte Demos ändern sich notwendigerweise Trainingsindexbereiche und die Gewichtung früher Phasen.

## Vorab definierter vereinfachter Erfolg

Ein Rollout wird erfolgreich beendet, sobald alle Bedingungen erfüllt sind:

1. Objekt B wurde gegriffen und gehalten über z > 0,88 m angehoben, für mindestens drei aufeinanderfolgende Frames.
2. Danach wurde Transport gestartet: gehaltenes B bei z > 0,98 m, XY-Geschwindigkeit > 0,02 m/s und Bewegungs-Cosinus zum Ziel > 0,5, für drei aufeinanderfolgende Frames.
3. Vom Frame unmittelbar vor diesem Transportbeginn wurde mindestens 0,02 m projizierter Fortschritt entlang der dortigen Zielrichtung erzielt.
4. B bleibt vom Transportbeginn bis zum Erfolg durchgehend gehalten und oberhalb 0,98 m.
5. Mindestens drei Frames bewegen sich mit XY-Geschwindigkeit > 0,005 m/s; in mindestens 80 % dieser bewegten Frames ist der Cosinus der tatsächlichen Bewegung zum jeweils aktuellen Ziel > 0,5.

Kein präzises Positionieren, Absenken, Release, Kontakt mit dem Zielobjekt oder stabiler Stack erforderlich. Dieselben 40 Startseeds 46000–46039 und SHA-256-Startzustände wie zuvor. Maximal 500 Frames, dt = 0,05 s; Ende unmittelbar bei vereinfachtem Erfolg. Kein Stabilitätstail. Eine zu niedrige oder ungerichtete Bewegung erfüllt den Erfolg nicht.

## Kennzahlen

- Pro Rollout: Grasp, Lift (gehalten >0,88 m für drei Frames), Transport gestartet, projizierte Transportdistanz, Anteil korrekt gerichteter bewegter Frames, mittlerer Bewegungs-Ziel-Cosinus, mittlerer XY-Action-Ziel-Cosinus bei gehaltenem B >0,98 m und Action-Norm >0,01, maximale Objekthöhe und vereinfachter Erfolg.
- Historische Phasenindikatoren werden zusätzlich unverändert mitgespeichert; maßgeblich sind `grasp_success`, `lift_success`, `transport_started_sanity` und `simplified_success`.
- XY/Expert und Ziel-Cosinus: exakt der bisherige Offline-Validierungspanel-Vergleich, Chunkposition 1, Transportfenster +6 bis +10 nach Expert-Umschaltpunkt, dieselben acht Rauschsamples. Das Panel besteht aus ursprünglichen Validierungsbeobachtungen und kann über die gekürzten Präfixe hinausgehen; dieser Wert ist eine ergänzende Diagnose, kein vereinfachtes Erfolgskriterium.
- Anteil vereinfachter Erfolge = erfolgreiche Starts / 40. Loss pro Update, Trainingszeit und Normalisierungsprüfungen werden gesichert.

## Ablauf und Abschluss

`start.ps1` startet einen versteckten unabhängigen Windows-Prozess. `scripts/run.py` führt genau einmal Training, die zugehörige Offline-Diagnose und die 40 Rollouts aus. Keine weiteren Seeds, Experimente oder automatische Interpretation. Der Agent wartet nicht auf diese Schritte.

- Hauptlog: `run.log`; Startinformationen: `launch.json`, tatsächliche Worker-PID: `worker_started.json`.
- Laufstatus: `worker_status.json`; Trainingsstatus: `C/diffusion/seed_1/status.json`.
- Erfolg des gesamten Prozesses: `complete.json` mit `state=COMPLETED` und `verified=true`, erst nach Training, Evaluation und Hash-Sicherung geschrieben.
- Fehler: `failed.json`, außerdem gegebenenfalls `C/diffusion/seed_1/aborted.json`. Bei NaNs, falscher Normalisierung, falscher Initialisierung oder ungültigen Actions wird der Prozess beendet; keine automatischen Neustarts.
- Ergebnisse: `results.json`, `rollout_metrics.csv`, `offline_metrics.csv`, `training_losses.csv`; rohe Actions und Zustände in `C/diffusion/seed_1/rollouts/*.npz`.
- Hashes vor Start: `prepared_hashes.json`, Quellen/Datenherkunft: `provenance.json`; nach Ende: `hashes.json`. Laufendes Hauptlog und letzter Abschlussmarker sind vom finalen Hashmanifest ausgenommen.

Auswerteprompt: „Werte experiments/stack_diagnostics/diffusion_sanity_lift_transport_20261002 aus. Prüfe zuerst complete.json und verification.json. Vergleiche die vorab definierte Teilaufgabe und ihre Diagnosen mit C/Seed 1. Unterscheide Grundfähigkeit der Diffusion-Pipeline von Problemen der präzisen Stack-Sequenz. Starte keine weiteren Läufe.“
