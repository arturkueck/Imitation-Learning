# Single fresh C diffusion training result

Status: **INTERRUPTED_TRAINING**.

Reason: **explicit cancellation by the user**, to refocus the project on algorithmic BC improvements. This was neither a timeout nor a numerical training failure. The preserved traceback uses the generic text "Safe stop requested by 15-hour watchdog" because the same safe-stop path handles both causes; `user_cancellation.json` records the actual reason.

Training seed: 2. Budget: 30,000 optimizer updates. Recorded updates: 16800.
Elapsed since launch: 1052.7 seconds. Maximum: 54000 seconds.

Stable stacks: unavailable / evaluation incomplete or not started.
Partial phase counts (separate): {}.

No evaluation was started. The preserved final checkpoint contains the weights after 16,800 updates and is an interrupted-run artifact, not a completed 30,000-update result. Last training epsilon loss: 0.0066266861; mean of the last 500: 0.0183633968. These are denoising losses, not stable-stack performance.

Final checkpoint SHA-256: `f9e97394b27e16f663a8b697c9abe5a0fb99edda43a9ce2c16df257a26632f25`. The hash and 16,800 training-loss rows were independently checked. Worker and watchdog processes exited, their process job closed, the awake request was released, and the completion heartbeat was paused. Verification: `cancellation_verified.json`. No resume or replacement run.

This is one fresh training seed with unchanged learning settings. It neither establishes a robust training improvement nor explains the Direct–diffusion gap. The research conclusion in RESEARCH_REVIEW.md is unchanged.

Exact process status: run_result.json. Losses: C/diffusion/seed_2/losses.csv. Configuration: C/diffusion/seed_2/config.json. Dataset/source manifests and checkpoint hashes are preserved. No automatic retry.

Current scientific objective and next steps: `../../FORSCHUNGSPLAN.md`.
