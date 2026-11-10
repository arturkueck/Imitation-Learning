# Vision snapshot · 2026-11-01

This branch preserves the current vision implementation, active-view planner,
regression tests, experiment protocols, frozen source/configuration snapshots,
data manifests, learning curves, evaluation tables and selected figures. The
Research Atlas sources and their published evidence assets are included as well.

Datasets, model weights, checkpoints, logs, caches, temporary process files,
smoke runs and the large per-epoch geometry image series remain local. The
training register can therefore reference local-only geometry previews; a fresh
checkout does not contain that image archive or trained models. Published web
evidence is retained under `sites/research-atlas-source/public/vision-evidence`.
The active-view GIF is stored there once rather than duplicated in demo folders.

Results retain their original experimental scope: the stopped V1 overnight run
has no final tests; the V2 corrected final evaluation is in
`experiments/vision/visual_scene_v2_20261101/run_001/test_repair_001`. Geometric box
refinement and active camera planning do not establish additional neural training.

No experiment parameters or running training processes were changed while
preparing this snapshot. Excluded files are retained on disk.
