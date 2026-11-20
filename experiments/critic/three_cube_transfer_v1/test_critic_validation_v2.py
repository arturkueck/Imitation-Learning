import numpy as np
import pytest

import critic_validation as cv
import critic_validation_v2 as v2


def test_exact_resume_at_partial_loss_window(tmp_path):
    torch, core = v2.torch_core()
    rng = np.random.default_rng(5)
    data = tuple(rng.random(shape, dtype=np.float32) for shape in ((128, 3), (128, 4), 128))
    recipe = dict(cv.PRETRAIN, updates=120, log_every=60)
    full, full_opt, full_history = v2.train(
        torch, core, data, 1, tmp_path / "full.pt", "config", lambda: None, lambda *_: None, recipe)
    checkpoint = tmp_path / "resume.pt"
    checks = iter((False, True))

    def pause():
        if next(checks):
            raise InterruptedError

    with pytest.raises(InterruptedError):
        v2.train(torch, core, data, 1, checkpoint, "config", pause, lambda *_: None, recipe)

    saved = torch.load(checkpoint, weights_only=True)
    assert saved["updates"] == 100
    assert len(saved["window"]) == 40
    resumed, resumed_opt, resumed_history = v2.train(
        torch, core, data, 1, checkpoint, "config", lambda: None, lambda *_: None, recipe)
    assert full_history == resumed_history
    for name, value in full.state_dict().items():
        assert torch.equal(value, resumed.state_dict()[name])
    for name, slots in full_opt.state_dict()["state"].items():
        for key, value in slots.items():
            assert torch.equal(value, resumed_opt.state_dict()["state"][name][key])


def test_training_uses_executed_actions_and_pools_both_datasets(monkeypatch):
    def episode_arrays(directory, index, row, contract):
        value = 1 if directory == v2.cd.OUT else 2
        return dict(critic_state=np.full((1, 3), value), parent_action=np.zeros((1, 7)),
                    executed_action=np.full((1, 7), value), discounted_return=np.array([value / 2]),
                    stage=np.array([0]), phase=np.array([0]))

    monkeypatch.setattr(v2, "episode_arrays", episode_arrays)
    config, rows = {"inputs": {}}, {}
    for index, (task, *_) in enumerate(v2.TRAINING):
        config["inputs"][task] = {"schedule": [[index, 1]]}
        rows[task] = [dict(scene_seed=index, parent_seed=1, index=0, initial_sha256="sha", success=bool(index))]
    (states, actions, returns), (baseline, overall) = v2.training_data(config, rows, 1, lambda: None)
    assert states[:, 0].tolist() == [1, 2]
    assert actions.tolist() == [[1] * 4, [2] * 4]
    assert returns.tolist() == [0.5, 1.0]
    assert next(iter(baseline.values()))["mean_return"] == 0.75
    assert overall == 0.5
