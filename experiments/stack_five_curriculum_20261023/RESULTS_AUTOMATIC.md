# Five-cube curriculum pilot

State: COMPLETED

Only observed results are reported. Missing evaluations are not failures.



## Held-out complete stable towers

- final_test\curriculum_seed1_n2\result.json: 47/50, complete=True

- final_test\curriculum_seed1_n3\result.json: 27/50, complete=True

- final_test\curriculum_seed1_n4\result.json: 17/50, complete=True

- final_test\curriculum_seed1_n5\result.json: 7/100, complete=True

- final_test\curriculum_seed2_n2\result.json: 48/50, complete=True

- final_test\curriculum_seed2_n3\result.json: 28/50, complete=True

- final_test\curriculum_seed2_n4\result.json: 19/50, complete=True

- final_test\curriculum_seed2_n5\result.json: 8/100, complete=True

- final_test\curriculum_seed3_n2\result.json: 48/50, complete=True

- final_test\curriculum_seed3_n3\result.json: 18/50, complete=True

- final_test\curriculum_seed3_n4\result.json: 13/50, complete=True

- final_test\curriculum_seed3_n5\result.json: 5/100, complete=True

- final_test\direct_seed1_n2\result.json: 47/50, complete=True

- final_test\direct_seed1_n3\result.json: 29/50, complete=True

- final_test\direct_seed1_n4\result.json: 18/50, complete=True

- final_test\direct_seed1_n5\result.json: 10/100, complete=True

- final_test\direct_seed2_n2\result.json: 49/50, complete=True

- final_test\direct_seed2_n3\result.json: 27/50, complete=True

- final_test\direct_seed2_n4\result.json: 19/50, complete=True

- final_test\direct_seed2_n5\result.json: 7/100, complete=True

- final_test\direct_seed3_n2\result.json: 47/50, complete=True

- final_test\direct_seed3_n3\result.json: 16/50, complete=True

- final_test\direct_seed3_n4\result.json: 10/50, complete=True

- final_test\direct_seed3_n5\result.json: 6/100, complete=True

## Actual optimizer updates

- curriculum_n3_c0_seed1: {'state': 'TRAINING_COMPLETE', 'update': 30000}

- curriculum_n3_c0_seed2: {'state': 'TRAINING_COMPLETE', 'update': 30000}

- curriculum_n3_c0_seed3: {'state': 'TRAINING_COMPLETE', 'update': 30000}

- curriculum_n4_c0_seed1: {'state': 'TRAINING_COMPLETE', 'update': 30000}

- curriculum_n4_c0_seed2: {'state': 'TRAINING_COMPLETE', 'update': 30000}

- curriculum_n4_c0_seed3: {'state': 'TRAINING_COMPLETE', 'update': 30000}

## Collected dataset counts

- curriculum_n3_cycle0: 120 attempts, 52 training successes, 10 validation successes; complete=True

- curriculum_n4_cycle0: 120 attempts, 27 training successes, 8 validation successes; complete=True

- direct_n5_cycle0: 120 attempts, 6 training successes, 3 validation successes; complete=True

## Gates and decisions

```json

[
  {
    "height": 3,
    "gates": [
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed1\\best.pth",
        "seed": 1,
        "first": 37,
        "confirm": 31,
        "passed": true
      },
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed2\\best.pth",
        "seed": 2,
        "first": 33,
        "confirm": 29,
        "passed": false
      },
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed3\\best.pth",
        "seed": 3,
        "first": 28,
        "confirm": null,
        "passed": false
      }
    ]
  },
  {
    "height": 4,
    "gates": [
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed1\\best.pth",
        "seed": 1,
        "first": 15,
        "confirm": null,
        "passed": false
      },
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed2\\best.pth",
        "seed": 2,
        "first": 13,
        "confirm": null,
        "passed": false
      },
      {
        "path": "F:\\Desktop\\Programmieren\\IT\\Imitation Learning\\experiments\\stack_five_curriculum_20261023\\training\\curriculum_n3_c0_seed3\\best.pth",
        "seed": 3,
        "first": 12,
        "confirm": null,
        "passed": false
      }
    ]
  },
  {
    "height": 5,
    "reason": "no teacher confirmed previous-height 60% gate"
  },
  {
    "arm": "direct",
    "height": 5,
    "reason": "insufficient successful five-cube data; control remains unchanged parent"
  }
]

```

## Interpretation

Three-cube and higher successful self-generated actions are training data. This is not zero-shot transfer from two-cube demonstrations.

Fixed phase BC actions/completion, geometric prefix stability gate and learned phase-0 retreat reused between each pair. The external sequencer chooses the next pair; it is not learned.

At least 90/100 complete stable five-cube towers on EACH of three seeds is required for the 90% point target. A skipped stage or missing test is unproven, not 0/100.

See protocol.json, gate records, dataset manifests and learning curves for actual costs and decisions. A full agent-written analysis is due at the next hourly check.