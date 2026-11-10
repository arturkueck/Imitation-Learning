# Measured learning curve

| Algorithm | Epoch | Success Rate | Avg Return | Avg Length | Successes |
|---|---:|---:|---:|---:|---:|
| bc_rnn | 50 | 0.050 | 0.050 | 399.10 | 1/20 |
| bc_rnn | 100 | 0.000 | 0.000 | 400.00 | 0/20 |
| bc_rnn | 150 | 0.000 | 0.000 | 400.00 | 0/20 |
| bc_rnn | 200 | 0.000 | 0.000 | 400.00 | 0/20 |
| bc_rnn | 250 | 0.000 | 0.000 | 400.00 | 0/20 |
| bc_rnn | 300 | 0.400 | 0.400 | 309.45 | 8/20 |
| bc_transformer | 50 | 0.050 | 0.050 | 387.70 | 1/20 |
| bc_transformer | 100 | 0.000 | 0.000 | 400.00 | 0/20 |
| bc_transformer | 150 | 0.100 | 0.100 | 386.30 | 2/20 |
| bc_transformer | 200 | 0.200 | 0.200 | 356.15 | 4/20 |
| bc_transformer | 250 | 0.050 | 0.050 | 386.60 | 1/20 |
| bc_transformer | 300 | 0.100 | 0.100 | 377.15 | 2/20 |

Epoch 50 reuses measured baseline results. Later rows are written only after evaluation.
Matched seeds 6000–6019; horizon 400; repeated evaluation is a development set, not an independent final test.