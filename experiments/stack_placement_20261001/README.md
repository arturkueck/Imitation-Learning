# Placement diagnosis, 2026-10-01

Controlled inference interventions on the unchanged corrected-scheduler epoch-300 state checkpoint. Action horizon remains 2. Seeds 46000–46019 and 500-step horizon match the previous best evaluation. Each initial simulation state is checked against its saved SHA-256 hash. No additional training.

`baseline`: original actions. `release_gate`: after held lift, suppress negative gripper commands outside the placement window (XY <9 mm, height difference 40±8 mm); all arm actions unchanged. `xy_feedback`: after held lift, replace only XY actions with clipped proportional feedback towards the base cube; Z, rotation and gripper unchanged. These are diagnostic controllers, not retrained policy improvements.

Every NPZ contains `states` (post-action simulator state) and `trace` (post-action measurements, actions applied on that step). Columns:

| Columns | Meaning |
|---|---|
| 0 | zero-based step |
| 1–3 / 4–6 | base / manipulated cube world position, meters |
| 7–10 / 11–14 | base / manipulated cube quaternion, wxyz |
| 15–17 | end-effector world position |
| 18–19 | finger joint positions |
| 20–26 | executed action (XYZ, rotation XYZ, gripper) |
| 27–33 | unmodified policy action |
| 34 | contact-based grasp predicate for cube B |
| 35 | cube A/B contact predicate |
| 36 | original environment task-success predicate |

Phases are event metrics, not assumed expert labels: lift means B center > table +80 mm; position means after lift, XY <9 mm and B at least 32 mm above A; lowering additionally requires height 40±8 mm; release additionally requires cube contact and no B grasp. Full success is the original environment predicate, including 0.5 s stable tower. A single-step position/release metric does not prove stable positioning/release.

Runs without held lift cannot activate either intervention; their exact baseline trajectories may be reused and are explicitly tagged in `results.json`. No stochastic resampling is needed for these unchanged cases. Changed trajectories are simulated from the same seeded initial states.

Run with `praxis/.venv/Scripts/python.exe experiments/stack_followup_20261001/scripts/placement_diagnosis.py --variant baseline` (or `release_gate`, `xy_feedback`). Summarize with `analyze_placement.py`; data audit with `audit_placement_data.py` from the same script directory.
