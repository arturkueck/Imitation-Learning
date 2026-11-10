# Visuomotorischer Behavior-Cloning-Vergleich: Square

Fuer neue Laeufe ist die finale Robustheits-Evaluation automatisch eingebunden;
Details und Eingriffsparameter stehen in `experiments/ROBUSTNESS.md`.

## Forschungsfrage und Learning Objective

Wie unterscheiden sich Feed-Forward BC, BC-RNN und BC-Transformer bei derselben
visuellen Manipulationsaufgabe und einem kleinen, gemeinsamen Trainingsbudget?

Learn a visuomotor policy pi(a_t | o_t) from expert demonstrations that maps
visual observations and proprioceptive state to robot actions completing the task.
BC-RNN nutzt einen rekurrenten Zustand; der kausale Transformer nutzt die letzten
fuenf Beobachtungen. BC sieht die aktuelle Beobachtung.

## Datensatz und Environment

- Aufgabe: `NutAssemblySquare` (Panda, robosuite / MuJoCo).
- Quelle: offizieller robomimic PH-Datensatz `v1.5/square/ph/low_dim_v15.hdf5`.
- Download: vorhandenes `praxis/upstream/robomimic/robomimic/scripts/download_datasets.py`.
- Ursprungsdatei: `praxis/data/square/ph/low_dim_v15.hdf5` im Projekt.
- Trainingsdatei: `praxis/data/square/ph/image_64_v15.hdf5` im Projekt.
- Kamera: `agentview_image`, RGB, 64 x 64. Offizielle
  `dataset_states_to_obs`-Funktion rendert die gespeicherten Simulatorzustaende.
- 200 Demonstrationen; offizielle Masken: 180 `train`, 20 `valid`.
- `dataset_info.json` speichert absolute Pfade, SHA-256 der Quelle, komplette
  Split-Zuordnung, vorhandene Observation Shapes und Environment-Metadaten.
- Policy-Propriozeption: `robot0_eef_pos` (3), `robot0_eef_quat` (4),
  `robot0_gripper_qpos` (2). Keine privilegierten Objektzustaende als Policy-Eingang.
- Aktionen: 7 kontinuierliche Werte; delta-Endeffektorsteuerung (Translation,
  Rotation) und Greifer, gemaess gespeichertem OSC_POSE-Controller.
- Stack wurde uebersprungen: kein passender simulierter Stack-Datensatz in der
  installierten offiziellen Download-Registry. Square ist die angeforderte Alternative.

## Modelle und Loss

Alle drei verwenden unveraendertes robomimic `algo/bc.py`, deterministische
Aktionsausgaben und `torch.nn.MSELoss`, L2-Gewicht 1, L1/Cosinus-Gewichte 0:

`L = mean((predicted_action - demonstrated_action)^2)`.

Dies entspricht Maximum Likelihood unter einer isotropen Gaussian-Verteilung
mit fixer Varianz (bis auf konstante Skalierung und additive Konstanten).
MSE wird ueber Batch und Aktionsdimensionen gemittelt, bei Sequenzmodellen
zusaetzlich ueber alle fuenf Zeitschritte. GMM/Gaussian/VAE sind deaktiviert.

| Parameter | BC | BC-RNN | BC-Transformer |
|---|---|---|---|
| Zeitkontext | 1 | 5, LSTM | 5, kausale Attention |
| Kopf | MLP 256/256 | LSTM 256, 1 Layer, MLP 256/256 | Embedding 128, 2 Blocks, 4 Heads |
| Dataset seq_length | 1 | 5 | 1 |
| Dataset frame_stack | 1 | 1 | 5 |
| Supervision | aktuelle Aktion | alle Sequenzaktionen | alle Kontextaktionen |

Gemeinsam: zufaellig initialisierter ResNet18Conv + SpatialSoftmax (32 Keypoints,
64 Features), Adam 1e-4, Batch 16, Seed 1, 50 Epochen, 100 Trainingsbatches und
20 Validierungsbatches pro Epoche. Checkpoints alle 10 Epochen sowie bei besserem
Validation-Loss; `last.pth` wird von robomimic zusaetzlich geschrieben.
TensorBoard und robomimic Textlogs sind aktiviert. Die gespeicherten Configs sind
massgeblich. Modelle unterscheiden sich in Parameterzahl und pro Update
verarbeiteten Frames; das Budget gleicht Updates an, nicht FLOPs oder Laufzeit.

## Umgebung

Windows, RTX 5070 (12 GB), NVIDIA-Treiber 591.86. Verwendet wird die bestehende
`praxis/.venv`: Python 3.12.14, torch 2.11.0+cu128, CUDA-Runtime 12.8,
robomimic 0.5.0, robosuite 1.5.1, MuJoCo 3.2.3.

- robomimic Commit: `d309eaecc18acf4152a830a895a6984b8ac71b05`.
- robosuite Commit: `a071383d53568ab798eb315c0e95357911be922d`.
- Vollstaendige installierte Pakete: `requirements-frozen.txt`.
- `runtime.py` waehlt lokal GLFW fuer Windows-Offscreen-Rendering und umgeht
  die Linux-EGL-Geraeteenumeration mit einer leeren Geraeteliste. Keine Aenderung
  der robomimic-/robosuite-Quelldateien, keine sichtbaren Simulatorfenster.
- Die vorhandene MuJoCo-DLL-Kopie im upstream-Verzeichnis wird weiterverwendet.

## Ausfuehrung und Artefakte

PowerShell im Projektverzeichnis, Vorbereitung und reproduzierbare Configs:

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\baselines\square\scripts\prepare.py
& .\praxis\.venv\Scripts\python.exe .\experiments\baselines\square\scripts\configure.py
& .\experiments\baselines\square\scripts\run_all_experiments.ps1
```

Der letzte Befehl startet `pipeline.py` als unabhaengigen Windows-Prozess
(DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP, CREATE_BREAKAWAY_FROM_JOB).
`launch.json` verhindert versehentliche Doppelstarts. Alle Pythonpfade, Configs,
Datensatz- und Ausgabeziele werden absolut aufgeloest. `run_experiment.ps1`
kann alternativ einen einzelnen Algorithmus im Vordergrund trainieren und evaluieren.

Die Pipeline arbeitet sequentiell: BC, BC-RNN, BC-Transformer. Pro Modell werden
der Epoch-50-Checkpoint als `final.pth` und das beste gespeicherte Validation-Modell
als `best_validation.pth` im jeweiligen Modellordner abgelegt. Evaluation verwendet
fuer alle Modelle einheitlich `final.pth`, nicht nach Test-Erfolg selektierte Modelle.

Evaluation: 20 Rollouts, Seeds 6000 bis 6019, Horizont 400, Ende bei Erfolg oder
Environment-done. Pro Rollout werden Return, tatsaechliche Laenge und Erfolg
gespeichert. Alle 20 Rollouts werden als MP4 aufgezeichnet (256 x 256, jeder
fuenfte Simulationsschritt, 20 fps), dadurch bleiben auch alle beobachteten Erfolge
erhalten. Evaluation und Videoaufzeichnung erfolgen im selben Durchlauf.

- Modelle/Config: `bc/`, `bc_rnn/`, `bc_transformer/`; Rohcheckpoints in `runs/`.
- Logs: `logs/<algorithm>_training.log`, `logs/<algorithm>_evaluation.log`.
- Pipeline: `logs/pipeline.log` und `logs/pipeline.stderr.log`.
- TensorBoard: jeweiliges `runs/<algorithm>/<timestamp>/logs/`.
- Videos: `videos/<algorithm>/rollout_00.mp4` bis `rollout_19.mp4`.
- Einzelmetriken: `evaluation/<algorithm>/evaluation_results.json`.
- Abschluss: `evaluation_results.json`, `evaluation_results.csv`, `RESULTS.md`.
- Status: `status.json`, atomar aktualisiert; Fehler mit Traceback und FAILED.
- Start und Uebergabe: `launch.json`, `AGENT_HANDOFF.md`.
- Technische Kurztests: `smoke.log` und `smoke/`; keine Benchmark-Ergebnisse.

## Einschraenkungen

Ein Trainingsseed und 20 Evaluationsepisoden sind ein technischer Erstvergleich,
kein belastbarer wissenschaftlicher Benchmark. Niedrige Bildaufloesung und das
reduzierte Trainingsbudget koennen die Erfolgsrate begrenzen. Die Videos sind
Simulationen; eine Uebertragung auf den physischen Panda wird nicht getestet.
Windows-GLFW wurde auf dieser aktiven Windows-Sitzung getestet; das ist kein
Nachweis fuer einen displaylosen Linux-Server oder einen Windows-Dienst.
Der detached Prozess ueberlebt Shell-/Agent-Ende, aber keinen Neustart oder Sleep.

Quellen: [offizielle Datensatzdokumentation](https://robomimic.github.io/docs/datasets/robomimic_v0.1.html),
[Transformer-Konfiguration](https://robomimic.github.io/docs/tutorials/training_transformers.html).
