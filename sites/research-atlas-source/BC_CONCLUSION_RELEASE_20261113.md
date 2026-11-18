# BC conclusion release · 13.11.2026

Published to the existing owner-private Research Atlas, version 28:
https://imitation-learning-research-artur.dearkoala257.chatgpt.site/curriculum.html#bc-correction

Source commit: `12a8c31233313a6a255c6044bc8e58fc1803d63f`.
Deployment: `appgdep_6af6fad5c0988191802f994ecc356377`, succeeded.
Existing audience preserved. Source and deployment provenance were confirmed
by native Sites operations; browser QA covered the local result page and the
component/task-success dashboard. Production remains behind its private access.

Scope: full A/B/C → phase diagnosis → expert intervention → individual phases →
BC correction-training narrative; 118/150 confirmation successes against B 85/150,
34 gains / 1 loss, 28 / 2 against Replay; per-seed results and source hashes;
36/9 accepted train/validation families, data split and limited execution gate;
separate action/completion copies and limits of the curriculum claim.

The dashboard now exposes 12 trained components, 60 recorded loss points and
separate development/confirmation success tables. Historical A/B/C is marked
complete. Only selected BC records changed; unrelated training entries remain
unchanged. Cache versioning ensures the updated dashboard script is loaded.

Checks: 1,050 recorded rollouts cross-checked; gains/losses and initial states
matched; links, IDs, JavaScript syntax and production build passed. All 175
original scientific input hashes still match. Archive scan excludes model
checkpoints and raw training arrays. No training, selection or scientific input
changes were performed during documentation/publication.

Local procedure: `experiments/curriculum/CONCLUSION_20261113.md`.
Exporter: `experiments/curriculum/publish_conclusion.py`; independent validation:
`experiments/curriculum/verify_conclusion.py`. The older `export_research.py`
is a historical exporter and must not be used to replace this current conclusion.
Screenshot: `output/bc_conclusion_20261113.png` (locally verified preview).
