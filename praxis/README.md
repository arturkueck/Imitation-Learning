# Plan A implementation and experiment protocol

This directory contains a robomimic 0.5 research extension for the official
Lift proficient-human low-dimensional dataset. The tracked algorithm code is
in `src/robomimic_ext`; downloaded datasets, upstream checkouts, virtual
environments and results stay local. The adjacent research sketch, literature
comparison and measured results are in `../latex/plan_a/`.

## Pinned inputs

- robomimic source: `ARISE-Initiative/robomimic` at
  `d309eaecc18acf4152a830a895a6984b8ac71b05` (v0.5.0).
- robosuite source: `ARISE-Initiative/robosuite` `v1.5.1` at
  `a071383d53568ab798eb315c0e95357911be922d`.
- Dataset: [Lift PH low_dim v1.5](https://huggingface.co/datasets/robomimic/robomimic_datasets/tree/main/v1.5/lift/ph), saved at `data/lift/ph/low_dim_v15.hdf5`.
  SHA-256: `2067777cb8b532e9263dd09fd6448c41cc31224bb27be4a3b734010ae13eb540`.
- Python 3.12.14, PyTorch 2.11.0+cu128, MuJoCo 3.2.3 on the initial Windows run.

The upstream robomimic installation guide targets Linux/macOS. This Windows
setup trains and performs no-rendering Lift rollouts, but it is not a general
claim of Windows support for every robomimic environment.

## Local setup on Windows PowerShell

Run these commands from the repository root. A Python 3.12 installation and
CUDA-compatible PyTorch wheel are needed for GPU training. The current machine
used an RTX 5070. The `egl_probe` package is omitted because it fails to build
on this Windows setup; low-dimensional rollouts without video do not import it.

```powershell
git clone https://github.com/ARISE-Initiative/robomimic.git praxis/upstream/robomimic
git -C praxis/upstream/robomimic checkout d309eaecc18acf4152a830a895a6984b8ac71b05
git clone --branch v1.5.1 https://github.com/ARISE-Initiative/robosuite.git praxis/upstream/robosuite
python -m venv praxis/.venv
& praxis/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
& praxis/.venv/Scripts/python.exe -m pip install -e praxis/upstream/robomimic --no-deps
& praxis/.venv/Scripts/python.exe -m pip install h5py psutil tqdm termcolor tensorboard tensorboardX imageio imageio-ffmpeg matplotlib 'huggingface_hub==0.23.4' 'transformers==4.41.2' 'diffusers==0.11.1' pytest six
& praxis/.venv/Scripts/python.exe -m pip install -e praxis/upstream/robosuite
& praxis/.venv/Scripts/python.exe -m pip install 'mujoco==3.2.3'
Copy-Item praxis/.venv/Lib/site-packages/mujoco/mujoco.dll praxis/upstream/robosuite/robosuite/utils/mujoco.dll -Force
```

The DLL copy is a local workaround for robosuite v1.5.1's Windows import path.
MuJoCo 3.14.0 was tried and failed because the robosuite controller accesses
the older `MjData.qM` API. The installed latest `mink` package reports a
MuJoCo version conflict; the Panda Lift controller in this experiment does not
use Mink. Recheck these pins before moving to another simulator task.

Download the dataset from the linked source and verify its hash:

```powershell
New-Item -ItemType Directory -Path praxis/data/lift/ph -Force | Out-Null
Invoke-WebRequest 'https://huggingface.co/datasets/robomimic/robomimic_datasets/resolve/main/v1.5/lift/ph/low_dim_v15.hdf5' -OutFile praxis/data/lift/ph/low_dim_v15.hdf5
Get-FileHash praxis/data/lift/ph/low_dim_v15.hdf5 -Algorithm SHA256
```

Then set local caches and package path:

```powershell
$env:PYTHONPATH=(Resolve-Path praxis/src).Path
$env:MPLCONFIGDIR=(Join-Path (Resolve-Path praxis).Path '.cache/matplotlib')
$env:HF_HOME=(Join-Path (Resolve-Path praxis).Path '.cache/huggingface')
```

## Reproduce the experiment

The dataset's `mask/train` and `mask/valid` groups contain 180 and 20 distinct
demonstrations. `fit_lift_dynamics.py` uses only training trajectories to fit
the local translation matrix; the held-out per-axis R² is approximately
0.84, 0.58 and 0.94. The middle axis is an acknowledged model limitation.

```powershell
& praxis/.venv/Scripts/python.exe praxis/src/fit_lift_dynamics.py --dataset praxis/data/lift/ph/low_dim_v15.hdf5 --output praxis/configs/lift_ph_dynamics.json
& praxis/.venv/Scripts/python.exe praxis/src/make_lift_configs.py --template praxis/upstream/robomimic/robomimic/exps/templates/bc.json --dataset praxis/data/lift/ph/low_dim_v15.hdf5 --dynamics praxis/configs/lift_ph_dynamics.json --output-dir praxis/configs --results-dir praxis/results --seed 1 --epochs 20 --steps-per-epoch 100 --methods bc
& praxis/.venv/Scripts/python.exe praxis/src/make_lift_configs.py --template praxis/upstream/robomimic/robomimic/exps/templates/bc.json --dataset praxis/data/lift/ph/low_dim_v15.hdf5 --dynamics praxis/configs/lift_ph_dynamics.json --output-dir praxis/configs --results-dir praxis/results --seed 1 --epochs 20 --steps-per-epoch 100 --methods bc_contraction --weight 1.0 --tag w1
& praxis/.venv/Scripts/python.exe -m robomimic_ext.train --config praxis/configs/lift_ph_bc_seed1.json
& praxis/.venv/Scripts/python.exe -m robomimic_ext.train --config praxis/configs/lift_ph_bc_contraction_w1_seed1.json
& praxis/.venv/Scripts/python.exe -m pytest -q praxis/tests/test_contraction.py
```

Repeat config generation and training for seeds 2 and 3. Checkpoints and logs
are saved under `praxis/results/`. After all six checkpoints exist, run:

```powershell
& praxis/.venv/Scripts/python.exe -u praxis/src/evaluate_matrix.py --results-dir praxis/results --episodes 20 --rollout-seed 6000 --horizon 400
```

The evaluator applies identical episode seeds per policy. The shifted
condition moves the cube by +2 cm in x after reset and keeps its orientation
and velocity. It writes a JSON file per model and condition with every episode
result. The 20 episodes per training seed are a useful comparison, though
confidence intervals remain wide.

The reported main experiment repeats config generation and training with
`--epochs 100 --steps-per-epoch 100`, baseline tag `e100`, and extension tag
`w1e100` with `--weight 1.0` for seeds 1, 2 and 3. Once all checkpoints exist,
the five matched conditions can be evaluated and summarized with:

```powershell
& praxis/.venv/Scripts/python.exe -u praxis/src/evaluate_matrix.py --results-dir praxis/results --episodes 20 --rollout-seed 8000 --horizon 400 --epoch 100 --bc-tag e100 --extension-tag w1e100 --output-subdir final_eval_100 --conditions nominal offset_x_2cm offset_x_minus_2cm impulse_x_1 impulse_x_minus_1
& praxis/.venv/Scripts/python.exe praxis/src/summarize_lift.py --eval-dir praxis/results/final_eval_100 --output praxis/results/final_eval_100/summary.json --bc-tag e100 --extension-tag w1e100
```

For the low-data experiment, fit `lift_ph_20pct_dynamics.json` with
`fit_lift_dynamics.py --filter-key 20_percent_train`, then generate all six
100-epoch configs with `--train-filter 20_percent_train --valid-filter
20_percent_valid`, the new dynamics file, baseline tag `d20e100`, extension
tag `w1d20e100`, and the same `--weight 1.0`. Evaluate with rollout seed
`9000`, `--bc-tag d20e100 --extension-tag w1d20e100` and output subdirectory
`final_eval_20pct`. This subset is defined by the dataset's official mask;
neither the dynamics fit nor policy training reads its validation demos.

The ±2 cm conditions move the cube along x after environment reset. The ±1
impulse conditions add one clipped x-action at step 20. The summarizer checks
that paired policies received identical initial cube and gripper states.

## Interpretation limits

The regularizer uses a finite-difference one-step translation approximation,
not Stable-BC's exact eigenvalue objective. It does not guarantee stability
through contact or large deviations. The 20- and 100-epoch, 100-step/epoch,
256×256 MLP budgets are shared by both methods but are smaller than published
robomimic configurations. Published benchmark scores provide context;
the matched locally trained BC model is the quantitative control.
