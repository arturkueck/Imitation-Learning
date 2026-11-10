# Retired session helpers (2026-11-09)

The session ended on 2026-10-04 (`status.json`: `WINDOW_FINISHED`).
The top-level `build_*` (except `build_domain_worker.py`), `freeze_*`,
`finish_*`, `prepare_*`, `record_*`, and `repair_*` Python scripts were removed.
They were one-off setup, patching, reporting, and check-recording commands for
that session. Their generated workers, repairs, reports, and event records remain.
The retained code has no references to the removed helpers; the historical
`archive/.../snapshot_before.json` inventory remains unchanged.

`build_domain_worker.py` remains because source-hash audits depend on it.
Experiment workers, analyses, frozen sources, manifests, and results remain.
The removed helpers are available in Git at commit `f6770eb`; for example:

```sh
git show f6770eb:experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/build_error_margin.py
```
