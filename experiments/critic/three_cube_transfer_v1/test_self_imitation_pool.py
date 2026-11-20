"""Vertragsprüfungen für S-1 ohne Simulationsepisoden."""

import numpy as np
import pytest

import self_imitation_pool as pool


def test_split_and_cutoff():
    pool.check_split()
    assert len(pool.SCHEDULE) == len(set(map(tuple, pool.SCHEDULE))) == 1200
    assert pool.SCHEDULE[0] == [2100003250, 1]
    assert pool.SCHEDULE[-1] == [2100003649, 3]


@pytest.mark.parametrize("last_phase,finite,completed", [(2, True, False), (3, True, True), (3, False, False)])
def test_phase_boundaries(last_phase, finite, completed):
    after = np.zeros((4, pool.cd.CRITIC_DIM), dtype=np.float32)
    after[-1, pool.STAGE_2] = 1
    after[-1, pool.PHASE_0 + last_phase] = 1
    if not finite:
        after[-1] = np.nan
    arrays = {"stage": np.array([1, 1, 2, 2]), "phase": np.array([2, 2, 2, 2]), "next_critic_state": after}
    assert pool.phase_boundaries(arrays) == [
        dict(stage=1, phase=2, start_frame=0, last_frame=1, completed=True),
        dict(stage=2, phase=2, start_frame=2, last_frame=3, completed=completed),
    ]


def test_noise_stream_resume_at_episode_boundary():
    rng = np.random.default_rng(7801)
    std = pool.NOISE["std_xyz"]
    first = np.stack([rng.normal(0, np.full(3, std)) for _ in range(11)]).astype(np.float32)
    checkpoint = rng.bit_generator.state
    next_episode = rng.normal(0, std, size=(9, 3)).astype(np.float32)
    rng.normal(0, std, size=(2, 3))  # Teil einer später unterbrochenen Episode.
    resumed = np.random.default_rng(7801)
    pool.check_noise_stream(resumed, {"exploration_noise": first}, dict(frames=11, index=0, rng_after=checkpoint))
    assert np.array_equal(resumed.normal(0, std, size=(9, 3)).astype(np.float32), next_episode)


def test_incremental_log_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(pool, "OUT", tmp_path)
    path = tmp_path / "worker.log"
    path.write_bytes(b"info\nValueEr")
    log_id, offset, errors = pool.new_errors({})
    assert offset == 5
    assert errors == []
    with path.open("ab") as handle:
        handle.write(b"ror: broken\n")
    _, offset, errors = pool.new_errors(dict(log_id=log_id, log_offset=offset))
    assert errors == ["ValueError: broken"]
    assert pool.new_errors(dict(log_id=log_id, log_offset=offset))[2] == []
