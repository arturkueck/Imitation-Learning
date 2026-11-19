"""Synthetische Tests des N2-1b-Rauschvertrags (ohne Simulation, ohne A-Parents)."""

import json

import numpy as np
import pytest
import torch

import critic_data_noisy as cn
from ac_smoke import make_bound
from test_critic_data import synthetic


class FakeParent(torch.nn.Module):
    """Deterministische 4er-Aktion (x, y, z, Greifer) und Abschlusslogit."""

    def forward(self, x, phase):
        return torch.tanh(x[..., :4] * 3), x[..., 4:5]


def noisy(n, success=False, seed=0):
    arrays, row = synthetic(n, success)
    rng = np.random.default_rng(seed)
    executor = cn.make_executor(torch, FakeParent(), make_bound(torch, 0.20, 0.02), rng, np.full(3, 0.05))
    executed = arrays["executed_action"]
    for t in range(n):
        x = torch.from_numpy(rng.normal(size=(1, 10)).astype(np.float32))
        action, _ = executor(x, torch.zeros(1, dtype=torch.long))
        executed[t, cn.IDX] = action[0].numpy().astype(np.float64)
    a_parent, action, bound, noise = (np.stack([e[k] for e in executor.log]) for k in range(4))
    arrays["parent_action"] = executed.copy()
    arrays["parent_action"][:, cn.IDX] = a_parent.astype(np.float64)
    arrays["exploration_noise"] = noise.astype(np.float32)
    arrays["action_bound"] = bound.astype(np.float32)
    return arrays, row


def test_valid_noisy_episode_roundtrip():
    arrays, row = noisy(80)
    cn.check_arrays(arrays, row)
    cn.check_arrays(cn.cd.decode(cn.cd.encode(arrays)), row)
    deviation = np.abs(arrays["executed_action"] - arrays["parent_action"])
    assert deviation[:, :3].max() > 0 and deviation[:, 3:].max() == 0
    assert cn.violations(arrays) == 0


def test_zero_noise_reproduces_parent_action():
    arrays, row = synthetic(30, True)
    executor = cn.make_executor(torch, FakeParent(), make_bound(torch, 0.20, 0.02),
                                np.random.default_rng(1), np.zeros(3))
    x = torch.from_numpy(np.random.default_rng(2).normal(size=(1, 10)).astype(np.float32))
    action, z = executor(x, torch.zeros(1, dtype=torch.long))
    parent, z_parent = FakeParent()(x, None)
    assert torch.equal(action, parent) and torch.equal(z, z_parent)


def test_bound_uses_widest_stage():
    arrays, row = noisy(200, seed=3)
    b = arrays["action_bound"]
    assert b[:, :3].max() <= 0.20 + 1e-7 and np.allclose(b[:, 3], 0.02)
    deviation = np.abs(arrays["executed_action"] - arrays["parent_action"])[:, :3]
    assert (deviation <= b[:, :3] + cn.TOLERANCE).all()


def test_rejects_violation_and_inconsistent_noise():
    arrays, row = noisy(40)
    arrays["executed_action"][5, 0] = arrays["parent_action"][5, 0] + 0.5
    with pytest.raises(ValueError):
        cn.check_arrays(arrays, row)
    arrays, row = noisy(40)
    arrays["exploration_noise"][7, 1] += 0.03
    with pytest.raises(ValueError, match="Rauschwert"):
        cn.check_arrays(arrays, row)


def test_rejects_gripper_or_rotation_change_and_wrong_bound():
    arrays, row = noisy(40)
    arrays["executed_action"][3, 6] += 0.01
    with pytest.raises(ValueError, match="Greifer"):
        cn.check_arrays(arrays, row)
    arrays, row = noisy(40)
    arrays["action_bound"][0, 0] += 0.01
    with pytest.raises(ValueError, match="Grenze"):
        cn.check_arrays(arrays, row)


def test_rejects_missing_noise_arrays():
    arrays, row = noisy(20)
    del arrays["exploration_noise"]
    with pytest.raises(ValueError, match="Arrays"):
        cn.check_arrays(arrays, row)


def test_episode_rng_is_per_scene_and_parent():
    a = np.random.default_rng([cn.NOISE["seed_base"] + 1, 2100003690]).normal(size=3)
    b = np.random.default_rng([cn.NOISE["seed_base"] + 1, 2100003690]).normal(size=3)
    c = np.random.default_rng([cn.NOISE["seed_base"] + 2, 2100003690]).normal(size=3)
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_split_is_v3_and_disjoint():
    assert cn.noisy_split() == (2100003690, 2100003989)
    splits = json.loads((cn.HERE / "splits_v3.json").read_text(encoding="utf-8"))
    assert splits["unassigned"]["first"] == 2100003990
    ranges = sorted((s["first"], s["last"]) for s in splits["splits"])
    assert all(a[1] < b[0] for a, b in zip(ranges, ranges[1:]))
    v2 = json.loads((cn.HERE / "splits_v2.json").read_text(encoding="utf-8"))["splits"]
    assert [s for s in splits["splits"] if s["id"] != cn.SPLIT] == v2


def test_preconditions_pass_with_granted_release():
    cn.preconditions()


def test_dashboard_entry():
    runs = json.loads((cn.ROOT / "monitor/training-runs.json").read_text(encoding="utf-8"))["runs"]
    entry = next(r for r in runs if r["id"] == "three-cube-transfer-v1-critic-data-noisy")
    assert entry["directory"] == cn.OUT.relative_to(cn.ROOT).as_posix()
    assert len({r["id"] for r in runs}) == len(runs)
