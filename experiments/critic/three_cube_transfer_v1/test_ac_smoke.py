"""Tests für N2-3 (synthetische Daten und eingefrorene Parents, keine Smoke-Familien)."""

import copy
import json

import numpy as np
import pytest
import torch

import ac_smoke as smoke
import critic_validation as cv


def parent_model(seed=1):
    registry = smoke.load_module("ac_smoke_registry_test", smoke.cd.CURRICULUM / "registry.py")
    return registry.restore_abc_a_for_inference(seed, registry.frozen_abc_a()[seed])


def test_projection_identity_bounds_and_zero_width():
    project = smoke.make_bound(torch, 0.05, 0.02)
    a_parent = torch.tensor([[0.3, -0.04, 0.0, 0.9], [-0.99, 0.2, 0.01, -1.0]])
    action, b = project(a_parent.clone(), a_parent)
    assert torch.equal(action, a_parent)
    assert torch.allclose(b, torch.tensor([[0.05, 0.02, 0.0, 0.02], [0.05, 0.05, 0.005, 0.02]]))
    raw = torch.tensor([[1.0, 1.0, 1.0, -1.0], [1.0, -1.0, -1.0, 1.0]], requires_grad=True)
    action, b = project(raw, a_parent)
    assert ((action - a_parent).abs() <= b + 1e-7).all() and (action.abs() <= 1).all()
    assert action[0, 2] == 0.0  # b = 0: exakt Parentaktion
    action.sum().backward()
    assert torch.isfinite(raw.grad).all() and raw.grad[0, 2] == 0


def test_executor_starts_exactly_at_parent_and_respects_bound():
    model, threshold, cap = parent_model()
    actor = copy.deepcopy(model).requires_grad_(True)
    project = smoke.make_bound(torch, 0.05, 0.02)
    rng = np.random.default_rng(0)
    executor = smoke.make_executor(torch, actor, model, project, rng, np.array([0.05, 0.05, 0.05, 0.0]))
    x = torch.from_numpy(np.random.default_rng(1).normal(size=(1, 10)).astype(np.float32))
    for phase in range(7):
        p = torch.tensor([phase])
        action, z = executor(x, p)
        a_parent, z_parent = model(x, p)
        assert torch.equal(action, a_parent) and torch.equal(z, z_parent)
    executor.explore = True
    for phase in range(7):
        executor(x, torch.tensor([phase]))
    count, max_xyz, max_gripper = smoke.violations(executor.log, 1e-6)
    assert count == 0 and max_xyz <= 0.05 + 1e-6 and max_gripper == 0.0


def synthetic_replay(n=600, seed=0):
    rng = np.random.default_rng(seed)
    terminal = np.zeros(n, np.float32)
    terminal[[199, 399, 599]] = 1
    reward = np.zeros(n, np.float32)
    reward[199] = 1
    return dict(state=rng.normal(size=(n, smoke.cd.CRITIC_DIM)).astype(np.float32),
                action=rng.uniform(-0.5, 0.5, size=(n, 4)).astype(np.float32), reward=reward, terminal=terminal,
                next_state=rng.normal(size=(n, smoke.cd.CRITIC_DIM)).astype(np.float32),
                x=rng.normal(size=(n, 10)).astype(np.float32), phase=rng.integers(7, size=n),
                next_x=rng.normal(size=(n, 10)).astype(np.float32), next_phase=rng.integers(7, size=n))


def make_learner(model, seed=7201):
    core = smoke.load_module("critic_base_core_test", smoke.BASE_CORE)
    torch.manual_seed(7101)
    critic = core.TwinQ(np.zeros(smoke.cd.CRITIC_DIM), np.ones(smoke.cd.CRITIC_DIM), 256)
    actor = copy.deepcopy(model).requires_grad_(True)
    project = smoke.make_bound(torch, 0.05, 0.02)
    return smoke.Learner(torch, actor, model, critic, project, smoke.hyper(), smoke.SMOKE, np.random.default_rng(seed))


def test_learner_updates_are_deterministic_and_counted():
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    model, *_ = parent_model()
    replay = synthetic_replay()
    runs = []
    for _ in range(2):
        learner = make_learner(model)
        metrics = [learner.update(replay) for _ in range(50)]
        runs.append((learner, metrics))
    (a, ma), (b, mb) = runs
    assert a.critic_updates == 50 and a.actor_updates == 25
    assert [m["critic_loss"] for m in ma] == [m["critic_loss"] for m in mb]
    assert all(torch.equal(a.actor.state_dict()[k], b.actor.state_dict()[k]) for k in a.actor.state_dict())
    summary = smoke.aggregate(ma)
    assert summary["all_finite"] and summary["actor_updates"] == 25 and 1 <= summary["ess_mean"] <= 256
    assert summary["weight_max"] <= 20
    # Der eingefrorene Parent bleibt unverändert, der Actor ändert sich.
    fresh, *_ = parent_model()
    assert all(torch.equal(model.state_dict()[k], fresh.state_dict()[k]) for k in fresh.state_dict())
    assert not all(torch.equal(a.actor.state_dict()[k], fresh.state_dict()[k]) for k in fresh.state_dict())
    json.dumps(smoke.clean(summary), allow_nan=False)


def test_new_critic_equals_n2_2_initialization(monkeypatch, tmp_path):
    """AC-neu: gleiche Initialisierung und Normierung wie der IL-Critic vor dem ersten Vortrainingsupdate."""
    core = cv.load_module("critic_base_core_test", cv.BASE_CORE)
    monkeypatch.setitem(cv.PRETRAIN, "updates", 0)
    states = np.random.default_rng(0).normal(size=(500, smoke.cd.CRITIC_DIM)).astype(np.float32)
    actions = np.zeros((500, 4), np.float32)
    reference, *_ = cv.pretrain(torch, core, states, actions, np.zeros(500), 2, 1e12, tmp_path)
    state = reference.state_dict()
    torch.manual_seed(7102)
    critic = core.TwinQ(state["mean"].numpy(), state["std"].numpy(), 256)
    assert all(torch.equal(critic.state_dict()[k], state[k]) for k in state)


def test_transitions_mask_terminal_and_shift_actor_input():
    n = 4
    arrays = dict(frame=np.arange(n), terminal=np.array([0, 0, 0, 1], bool), reward=np.zeros(n, np.float32),
                  critic_state=np.zeros((n, smoke.cd.CRITIC_DIM), np.float32),
                  next_critic_state=np.zeros((n, smoke.cd.CRITIC_DIM), np.float32),
                  actor_input=np.arange(n * 10, dtype=np.float32).reshape(n, 10),
                  actor_phase=np.array([0, 0, 1, 1], np.int8), executed_action=np.ones((n, 7)))
    arrays["next_critic_state"][-1] = np.nan
    t = smoke.transitions(arrays)
    assert np.isfinite(t["next_state"]).all() and t["action"].shape == (n, 4)
    assert np.array_equal(t["next_x"][:3], arrays["actor_input"][1:]) and list(t["next_phase"]) == [0, 1, 1, 1]
    arrays["next_critic_state"][1] = np.nan
    with pytest.raises(ValueError):
        smoke.transitions(arrays)


def fake_run(lost=0, ess=100.0, q=(0.0, 1.0), violations=0, finite=True):
    rounds = [dict(round=r, updates=dict(all_finite=finite, q_min=q[0], q_max=q[1], ess_mean=ess),
                   drift=dict(finite=True, q_parent_min=q[0], q_parent_max=q[1], q_actor_min=q[0], q_actor_max=q[1],
                              mean_xyz=0.01, max_xyz=0.04),
                   replay_q=dict(finite=True, min=q[0], max=q[1])) for r in (1, 2)]
    development = [dict(scene_seed=s, success=not (s < lost)) for s in range(20)]
    return dict(history=[dict(round=0)] + rounds, critic_updates=500, actor_updates=250, development=development,
                development_successes=sum(r["success"] for r in development), bound_violations=violations,
                online_successes=3)


def baselines():
    return {p: dict(rows=[dict(scene_seed=s, success=True) for s in range(20)], successes=20) for p in smoke.PARENTS}


def stage(overrides=None):
    runs = {(v, p): fake_run() for v in smoke.VARIANTS for p in smoke.PARENTS}
    runs.update(overrides or {})
    return smoke.assess_stage(0.05, runs, baselines())


def test_assess_stage_rules():
    assert stage()["passed"]
    assert not stage({("neu", 1): fake_run(violations=1)})["passed"]
    assert not stage({("il", 2): fake_run(ess=20.0)})["passed"]
    assert not stage({("il", 2): fake_run(q=(-0.2, 0.5))})["passed"]
    assert not stage({("neu", 3): fake_run(finite=False)})["passed"]
    # Je Parent ≤ 2 und gesamt ≤ 3 verlorene Parent-Erfolge (Lesart B entscheidet).
    assert stage({("neu", 1): fake_run(lost=2)})["passed"]
    assert not stage({("neu", 1): fake_run(lost=3)})["passed"]
    disagreement = stage({("neu", 1): fake_run(lost=2), ("il", 2): fake_run(lost=2)})
    assert not disagreement["passed"] and disagreement["readings_disagree"]
    assert all(disagreement["retention_reading_a"].values())
    # Neue Erfolge verrechnen Verluste nicht.
    run = fake_run(lost=3)
    run["development"][10]["success"] = True
    assert stage({("neu", 1): run})["lost_total"] == 3
    json.dumps(stage(), allow_nan=False)


def test_splits_disjoint_and_no_test_families():
    smoke_families = smoke.split_range("smoke_interaction")
    development = smoke.split_range("constraint_development")
    assert len(smoke_families) == len(development) == 20 and not set(smoke_families) & set(development)
    splits = json.loads((smoke.HERE / "splits_v2.json").read_text(encoding="utf-8"))["splits"]
    for entry in splits:
        if entry["id"].startswith("test"):
            assert not set(range(entry["first"], entry["last"] + 1)) & set(smoke_families + development)


@pytest.mark.skipif(not (smoke.cd.calibration.OUT / "episodes/000.json").is_file(), reason="Kalibrierung lokal nicht vorhanden")
def test_executor_reproduces_calibration_episode_and_zero_drift(tmp_path):
    """Technische Integrationsprüfung auf der bereits verwendeten Kalibrierungsfamilie 2100000000
    (Parent 1, eingefroren, ohne Rauschen, 0 Updates): gleicher Trajektorienhash wie N1-4."""
    reference = smoke.read(smoke.cd.calibration.OUT / "episodes" / "000.json")
    registry, base, torch_, controller, adapter = smoke.cd.setup(tmp_path)
    model, threshold, cap = registry.restore_abc_a_for_inference(1, registry.frozen_abc_a()[1])
    actor = copy.deepcopy(model).requires_grad_(True)
    executor = smoke.make_executor(torch, actor, model, smoke.make_bound(torch, 0.20, 0.02),
                                   np.random.default_rng(0), np.array([0.05, 0.05, 0.05, 0.0]))
    row, arrays = smoke.cd.episode(base, controller, adapter, torch, executor, threshold, cap, 2100000000, 1,
                                   1e12, tmp_path)
    assert (row["trajectory_sha256"], row["frames"], row["success"]) == (
        reference["trajectory_sha256"], reference["frames"], reference["success"])
    assert len(executor.log) == row["frames"] and smoke.violations(executor.log, 1e-6)[0] == 0
    replay = smoke.transitions(arrays)
    assert len(replay["state"]) == row["frames"]
    learner = make_learner(model)
    probe = smoke.probe_frames(1)
    assert len(probe["x"]) == 7 * 64
    measured = smoke.drift(torch, learner, probe)
    assert measured["max_xyz"] == 0 and measured["max_gripper"] == 0 and measured["finite"]


def test_dashboard_entry():
    runs = json.loads((smoke.ROOT / "monitor/training-runs.json").read_text(encoding="utf-8"))["runs"]
    entry = next(r for r in runs if r["id"] == "three-cube-transfer-v1-ac-smoke")
    assert entry["directory"] == smoke.OUT.relative_to(smoke.ROOT).as_posix()
    assert len({r["id"] for r in runs}) == len(runs)
