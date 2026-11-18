# Diagnostic trace columns

Each `.npz` contains one float64 matrix `trace`, one row per physics/control
step after applying the recorded action. Boolean/integer values are represented
as numeric 0/1 or integral floats. Cube order is fixed: table base, first placed
cube, second placed cube. World positions are metres; joint velocities follow
MuJoCo free-joint ordering (3 linear, 3 angular) for each cube.

## Isolated BC and expert control (49 columns, zero-based)

| Columns | Meaning |
|---|---|
| 0 | Frame within isolated phase |
| 1 | Placement stage, 1 or 2 |
| 2 | Tested phase, 3/4/5/6 |
| 3 | Completion probability (expert: binary transition indicator) |
| 4 | Phase completion predicted |
| 5 | Physical phase criterion at this frame |
| 6 | Consecutive frames satisfying physical criterion |
| 7..9 | End-effector XYZ |
| 10..18 | Three cube XYZ positions |
| 19..25 | Applied action XYZ, rotation XYZ (zero), gripper |
| 26..28 | Finger contact for three cubes |
| 29..30 | Strict two-/three-cube stacking valid |
| 31..48 | Three cube joint velocities |

## Complete rollout (51 columns, zero-based)

| Columns | Meaning |
|---|---|
| 0 | Episode frame |
| 1 | Placement stage before action |
| 2 | Phase before action |
| 3 | Guarded retreat active before action |
| 4 | Completion probability |
| 5 | Actual elapsed phase steps used to construct action |
| 6 | Effective elapsed phase steps after clock adapter |
| 7 | Sequencer event: 0 none, 1 begin retreat, 2 next placement |
| 8 | Consecutive strict three-cube-valid frames |
| 9..11 | End-effector XYZ |
| 12..20 | Three cube XYZ positions |
| 21..27 | Applied action XYZ, rotation XYZ (zero), gripper |
| 28..30 | Finger contact for three cubes |
| 31..32 | Strict two-/three-cube stacking valid |
| 33..50 | Three cube joint velocities |

Isolated traces are retained for the first of five development scenes; all
complete-rollout traces are retained. JSON records cover every trial. A phase
completion indicator is not a task-success label. Expert Open is held beyond
its native duration only to evaluate the fixed stability criterion.
