# Datenbeschreibung

Alle Dateien gehören zur Inferenzanalyse der sechs bestehenden finalen Checkpoints. Es gibt keine Trainingsergebnisse aus neuen Gewichten.

## Offline

- `diffusion_seed{s}_ddim{t}.npz`: `chunks` mit Form `[420,64,16,7]`. Achsen: eingefrorene Observation, Sample, rohe Chunkposition, Aktionskanal. Observation-Reihenfolge aus dem vorhandenen `stack_switch_20261001/panel.json`.
- `noise64.npy`: festes Initialrauschen in derselben Form. Identisch für alle Trainingsseeds und Schrittzahlen. DDIM eta=0.
- Aktionskanäle: Translation XYZ, Rotation XYZ, Gripper. Translation und Normen sind dimensionslose Controllerkommandos. Positive Gripperwerte schließen, negative öffnen.
- Chunkindex 0 ist die Aktion zum vorherigen Frame. Index 1 ist die erste ausgeführte Aktion. `position_1based=chunk_index+1` bezeichnet die Position im rohen Chunk, nicht die Ausführungsreihenfolge.
- `chunk_position_metrics.csv/.json`: eine Zeile je Modell, Seed, DDIM-Bedingung, Phase und Position. Normmittel sind Mittelwerte der Sample-Normen. `mean_action_xy_mean` ist dagegen die gemittelte Norm des zustandsbedingten Aktionsmittelwerts. Die Quantile **dieser Chunktabelle** poolen die Zustände einer Phase und sind deskriptive Mischungsquantile.
- `sample_observation_metrics.csv`: eine Zeile je identischer Observation, Seed, DDIM-Bedingung und Chunkposition. Quantile und Varianzen sind hier ausdrücklich **zustandsbedingt über 64 Samples**. `sample_summary.json` mittelt diese Kennzahlen über Zustände; seine Quantile sind Mittelwerte bedingter Quantile.
- Samplevarianz: ddof=1, je Aktionskanal. Direct ist deterministisch und hat Samplingvarianz 0. XYZ-Varianzspur ist die Summe der drei Kanalvarianzen, nicht die Varianz der Norm.
- Zielcosinus offline: XY-Kommandorichtung gegen EEF→Basiswürfel A im letzten eingefrorenen Frame. Für alle 16 Positionen gilt derselbe eingefrorene Vektor.
- „Stark und zielgerichtet“: XY-Norm>0,25 und Cosinus>0,5. Dies ist ein Diagnosekriterium, keine Stackgarantie. Eine alternative Spalte verwendet >50% der jeweiligen Expert-XY-Norm.
- Expert-Abweichung: MSE über sieben Kanäle; XYZ-RMSE über drei Translationskanäle. Die zukünftigen Expertaktionen sind positionsgenau aus dem HDF5 abgeglichen.
- `conditional_density_modes.json` und `conditional_joint_density_modes.json`: explorative 1D- beziehungsweise 2D-KDE-Gipfelanalyse bei drei Bandbreiten. Aktionsregime und Dichtegipfel sind verschiedene Aussagen; kein formaler Modalitätstest.

## Closed loop

- `baseline_failures.csv/.json` und `baseline_events.json`: historische 240 Starts, Messphase entsprechend dem Originalprotokoll.
- `closed_loop_failures.csv/.json`, `closed_loop_events.json`: neue Vergleiche. `comparison_group` unterscheidet Replanning und DDIM. Die identische neue h=2/DDIM-10-Baseline wird für beide Gruppen gezeigt und ist kein zusätzliches unabhängiges Experiment.
- `closed_loop_summary.json`: Kennzahlen je Trainingsseed und Konfiguration. Die Trainingsseeds sind die unabhängigen Replikate; Starts sind gepaarte Aufgabenfälle.
- `closed_loop_paired_changes.json`: gerettete/verlorene Start-IDs und gepaarte Höhenänderungen gegenüber der gemeinsamen Baseline.
- Ein Messhorizont endet bei erster nativer Success-Erkennung, Environment-Ende oder nach 500 Aktionen. Danach folgen 40 Stabilitätsframes bei 20 Hz. Neue Traces speichern alle diese Frames.
- Traceindex i enthält den Zustand **nach** Aktion i. Zeit seit Reset ist `(i+1)*0,05 s`. Ein Vorfehlerkommando ist Aktion i−1, ein Ereigniskommando Aktion i.
- Trace-Spalten: 0 Schrittindex; 1–3 Position A; 4–6 Position B; 7–10 Quaternion A; 11–14 Quaternion B; 15–17 EEF-Position; 18–19 Finger-Gelenkpositionen; 20–26 vorgeschlagene Aktion; 27–33 ausgeführte Aktion; 34 natives Grasp-Prädikat; 35 Würfelkontakt; 36 native Task-Success. Positionswerte sind Meter. In diesen Tests sind vorgeschlagene und ausgeführte Aktionen identisch.
- Objektverlust: native Grasp-Transition wahr→falsch. Zusätzlich gespeichert: Dauer ohne Grasp, Abstand EEF–B und Höhenänderung nach fünf Frames. Eine kurze Prädikattransition beweist keinen physischen Fall.
- `task_valid_release` verlangt XY<9 mm, relative B−A-Höhe 4 cm±8 mm und Würfelkontakt zum Ereignis. Alle anderen Grasp-Verluste sind operationalisiert als nicht regelgerechte Freigabe.
- `error_anchor` benennt das beobachtete Ereignis: erster Success-Verlust im Stabilitätstail oder erster nicht regelgerechter Grasp-Verlust. Es bezeichnet **keine kausale Fehlerursache**. Nie erreichte Phasen bleiben am Horizont zensiert.
- `max_cube_height_m` und `min_xy_distance_m`: Messphase. Zusätzliche `*_full_trace_m`-Spalten verwenden alle verfügbaren Frames. Mindestabstände bei gehaltenem/geliftetem Objekt werden separat ausgewiesen.
- Fehlende Werte: JSON `null`, leere CSV-Zelle. Die ersten 20 historischen Diffusion-Seed-1-NPZs enthalten keine Tailframes; `available_stability_tail_frames` weist dies aus. Neue Rollouts haben vollständige Tails.
- Alle erreichten Phasen, erste Ereigniszeiten, Gripperwechsel, Verlustereignisse und Aktionsamplituden bleiben pro Start erhalten. Exakte Phasenschwellen stehen im Hauptbericht.

## Technischer Audit

`protocol.json` und `final_input_verification.json` dokumentieren Checkpoint-, Dataset- und Rauschidentität. `stream_episode_parity_v5.json` prüft zwei vollständige native Episoden gegen den verwendeten einzelnen GPU-Stream. `graph_live_parity.json` je Konfiguration enthält zusätzliche Vergleiche an erreichten Zuständen. Vier parallele Streams haben die Paritätsprüfung nicht bestanden und sind von den Vergleichen ausgeschlossen.
