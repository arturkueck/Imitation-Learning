"""Synthetische Tests des N2-1-Datenvertrags (ohne Simulation, ohne Modelle)."""

import json

import numpy as np
import pytest

import critic_data as cd


def synthetic(n, success, termination=None):
    rng = np.random.default_rng(0)
    states = rng.normal(size=(n + 1, cd.CRITIC_DIM)).astype(np.float32)
    action = rng.uniform(-1, 1, size=(n, 7))
    reward, terminal, value = cd.returns(n, success)
    arrays = dict(
        frame=np.arange(n, dtype=np.int32), stage=np.ones(n, np.int8), phase=np.zeros(n, np.int8),
        retreat=np.zeros(n, np.bool_), phase_steps=np.arange(n, dtype=np.int32),
        retreat_actions=np.zeros(n, np.int32), critic_state=states[:-1].copy(),
        actor_input=np.zeros((n, 10), np.float32), actor_phase=np.zeros(n, np.int8),
        executed_action=action, parent_action=action.copy(), next_critic_state=states[1:].copy(),
        reward=reward, terminal=terminal, discounted_return=value)
    row = dict(frames=n, success=success, max_stable_frames=cd.STABLE if success else 3,
               termination=termination or ("success" if success else "horizon"))
    return arrays, row


def test_columns_documented_and_unique():
    # 9 Würfelpositionen, 12 Würfelquaternionen, 3+4+2 Greifer, Stufe, 7 Phasen, Rückzug, Restzeit
    assert cd.CRITIC_DIM == 40 and len(set(cd.CRITIC_COLUMNS)) == cd.CRITIC_DIM
    assert len(cd.ACTOR_COLUMNS) == 10 and len(cd.ACTION_COLUMNS) == 7


def test_returns_success_and_failure():
    reward, terminal, value = cd.returns(4, True)
    assert reward.tolist() == [0, 0, 0, 1] and terminal.tolist() == [False, False, False, True]
    assert np.allclose(value, [cd.GAMMA ** 3, cd.GAMMA ** 2, cd.GAMMA, 1.0])
    reward, terminal, value = cd.returns(3, False)
    assert reward.sum() == 0 and terminal[-1] and value.sum() == 0


@pytest.mark.parametrize("success", [True, False])
def test_valid_episode_roundtrip(success):
    arrays, row = synthetic(60, success)
    cd.check_arrays(arrays, row)
    cd.check_arrays(cd.decode(cd.encode(arrays)), row)


def test_rejects_broken_next_state():
    arrays, row = synthetic(20, False)
    arrays["next_critic_state"][3, 0] += 1
    with pytest.raises(ValueError, match="Folgezustand"):
        cd.check_arrays(arrays, row)


def test_rejects_deviating_action_and_wrong_return():
    arrays, row = synthetic(20, False)
    arrays["executed_action"][0, 0] += 0.1
    with pytest.raises(ValueError, match="Parent"):
        cd.check_arrays(arrays, row)
    arrays, row = synthetic(20, False)
    arrays["reward"][-1] = 1
    with pytest.raises(ValueError, match="Reward"):
        cd.check_arrays(arrays, row)


def test_instability_is_failure_with_nan_next_state_only_there():
    arrays, row = synthetic(10, False, "simulator_instability")
    arrays["next_critic_state"][-1] = np.nan
    cd.check_arrays(arrays, row)
    row["termination"] = "horizon"
    with pytest.raises(ValueError):
        cd.check_arrays(arrays, row)


def test_only_critic_data_split():
    assert cd.critic_split() == (2100000100, 2100000399)


def test_dashboard_entry():
    runs = json.loads((cd.ROOT / "monitor/training-runs.json").read_text(encoding="utf-8"))["runs"]
    entry = next(r for r in runs if r["id"] == "three-cube-transfer-v1-critic-data")
    assert entry["directory"] == cd.OUT.relative_to(cd.ROOT).as_posix()
    assert len({r["id"] for r in runs}) == len(runs)
