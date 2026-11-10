# Fixed-data partial self-imitation pilot

Fresh paired 50-start tests, fixed update5000; three parent checkpoints. No RL or vision-training claim.

| Model | Success /50 |
|---|---:|
| parent_seed1 | 32 |
| parent_seed2 | 29 |
| parent_seed3 | 29 |
| A_seed1 | 31 |
| B_seed1 | 32 |
| C_seed1 | 31 |
| D_seed1 | 30 |
| A_seed2 | 27 |
| B_seed2 | 31 |
| C_seed2 | 31 |
| D_seed2 | 31 |
| A_seed3 | 30 |
| B_seed3 | 30 |
| C_seed3 | 30 |
| D_seed3 | 29 |

C/D use identical sampled examples. B/C compare a data-selection strategy, not an isolated effect of section provenance. Quality weighting uses a hand-defined outcome score.

Parent checkpoints originate from the earlier pilot. Fixed pooled teacher data do not demonstrate improvement from exact self-copy. Test results must not be reused for checkpoint selection.