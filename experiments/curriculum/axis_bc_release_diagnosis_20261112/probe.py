"""Bounded diagnostic intervention on phase-six elapsed-time input only."""
from pathlib import Path
import hashlib
import json
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = HERE.with_name('axis_bc_completion_10h_20261111')
sys.path.insert(0, str(SOURCE))
import night as study
base, torch, np = study.runtime.libraries()
RUN = SOURCE/'ready_001'
TRACES = RUN/'diagnosis/replays'


def episode(model, cfg, seed, out, deadline, step_cap=None):
    controller = base.backend()
    historical = controller.native.historical
    env = historical.make_env(3)
    seq = controller.GuardedSequencer(model, 3, controller.Clearance(env))

    class ObservedPolicy(base.DevicePolicy):
        def action(self, obs, target, source):
            phase, elapsed = self.phase, self.steps
            intervene = phase == 6 and seq.stage == 2 and step_cap is not None
            if intervene:
                self.steps = min(elapsed, step_cap)
            anchor = (source if phase < 4 else target) if self.anchor is None else self.anchor
            self.last_x = historical.vector(obs, anchor, self.steps)
            self.raw_steps = elapsed
            self.intervened = intervene and elapsed > step_cap
            result = super().action(obs, target, source)
            if intervene:
                self.steps = elapsed+1
            return result

    seq.policy = ObservedPolicy(model, historical, cfg['completion_threshold'])
    rows, extra, inputs = [], [], []
    model.eval()
    tail = 0
    try:
        random.seed(seed)
        np.random.seed(seed)
        env.reset()
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        initial = env.sim.get_state().flatten().copy()
        with torch.no_grad():
            for frame in range(1000):
                base.check_stop(out, deadline)
                stage = seq.stage
                positions = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                action, phase, probability = seq.policy.action(obs, positions[stage-1], positions[stage])
                inputs.append(seq.policy.last_x.copy())
                elapsed, intervention = seq.policy.raw_steps, seq.policy.intervened
                env.step(action)
                env.sim.forward()
                obs = env._get_observations(force_update=True)
                fingers = [controller.native.finger_contact(env, c) for c in env.cubes]
                valid = [historical.old.prefix_valid(env, count) and not any(fingers[:count]) for count in (2, 3)]
                event = seq.advance(valid[stage-1], env.sim.data.body_xpos[env.cube_ids[stage]])
                tail = tail+1 if valid[-1] else 0
                held = [env._check_grasp(env.robots[0].gripper, c.contact_geoms) for c in env.cubes]
                positions = np.concatenate([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                rows.append(np.r_[frame, stage, phase, seq.policy.phase, probability, event, tail,
                                  seq.clearance.gap(2), obs['robot0_eef_pos'], positions, action, held, valid])
                velocities = np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes])
                contacts = [env.check_contact(env.cubes[i], env.cubes[i+1]) for i in range(2)]
                extra.append(np.r_[elapsed, intervention, fingers, contacts, velocities])
                if tail >= 50 or seq.timed_out:
                    break
        return dict(seed=seed, success=tail >= 50, frames=len(rows), stable_tail_frames=tail,
                    initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest()), dict(
                        trace=np.asarray(rows), extra=np.asarray(extra), inputs=np.asarray(inputs), initial=initial)
    finally:
        env.close()


def main():
    out = HERE/'probe_001'
    out.mkdir(exist_ok=False)
    study.runtime.verify(RUN)
    cfg = study.read(RUN/'base_config.json')
    controls = study.read(RUN/'controls.json')
    cases = study.read(TRACES/'report.json')['cases']
    with np.load(base.ARRAYS, allow_pickle=False) as archive:
        time_max = float(archive['train_x'][archive['train_p'] == 6, 9].max())
    step_cap = int(round(time_max*20))
    assert step_cap == 17
    plan = dict(schema='release-clock-diagnostic-v1', phase=6, task_stage=2,
                step_cap=step_cap, cap_source='maximum phase-six time input in training demonstrations',
                success_criterion='unchanged 50 consecutive strict valid frames', models='unchanged ordinary 60k controls',
                dataset_unchanged=True, optimizer_updates=0, cases='all 24 preselected historical replay cases; outcome-stratified, not held-out confirmation',
                wall_clock_cap_seconds=900, no_automatic_retry=True,
                source_sha256=base.sha(Path(__file__)), parent_provenance_sha256=base.sha(RUN/'provenance.json'))
    study.write(out/'plan.json', plan)
    started = time.time()
    deadline = started+900
    base.configure(1)
    results = []
    # First validate the richer recorder against one full historical baseline.
    first = next(r for r in cases if r['group'] == 'loss')
    model = study.load_model(study.ROOT/controls[first['model']]['path'], cfg, 'cuda')
    result, arrays = episode(model, cfg, first['seed'], out, deadline)
    expected = first['replay']['extended']
    with np.load(TRACES/f'{first["model"]}_{first["group"]}_{first["seed"]}_extended.npz') as old:
        assert np.array_equal(arrays['trace'], old['trace']), 'Recorder changed historical trajectory'
    assert result['success'] == expected['success'] and result['initial_sha256'] == expected['initial_sha256']
    np.savez_compressed(out/'verified_baseline.npz', **arrays)
    study.write(out/'baseline_check.json', dict(model=first['model'], seed=first['seed'], exact_trace_match=True, result=result))
    for case in cases:
        model = study.load_model(study.ROOT/controls[case['model']]['path'], cfg, 'cuda')
        study.write(out/'status.json', dict(state='DIAGNOSTIC_SIMULATION', pid=study.os.getpid(),
            model=case['model'], seed=case['seed'], completed=len(results), updated_unix=time.time()))
        result, arrays = episode(model, cfg, case['seed'], out, deadline, step_cap=step_cap)
        with np.load(TRACES/f'{case["model"]}_{case["group"]}_{case["seed"]}_extended.npz') as old:
            reference = old['trace']
        changed = np.flatnonzero(arrays['extra'][:, 1])
        prefix = int(changed[0]) if len(changed) else min(len(reference), len(arrays['trace']))
        assert result['initial_sha256'] == case['initial_sha256'], 'Initial scene changed'
        assert np.array_equal(reference[:prefix], arrays['trace'][:prefix]), 'History differs before the intervention'
        np.savez_compressed(out/f'{case["model"]}_{case["group"]}_{case["seed"]}.npz', **arrays)
        results.append(dict(model=case['model'], group=case['group'], seed=case['seed'],
            control_success=case['extended_success'], probe_success=result['success'],
            first_intervention_frame=int(changed[0]) if len(changed) else None,
            matched_history_frames=prefix, **{k: v for k, v in result.items() if k not in ('seed','success')}))
        study.write(out/'results.json', dict(cases=results))
    summary = dict(n=len(results), controls_successes=sum(r['control_success'] for r in results),
        probe_successes=sum(r['probe_success'] for r in results),
        gains=sum(not r['control_success'] and r['probe_success'] for r in results),
        losses=sum(r['control_success'] and not r['probe_success'] for r in results),
        selected_regression_scene=[r for r in results if r['group'] == 'loss'],
        interpretation='Exploratory causal intervention on the final-release time input in selected existing scenes; not a population success estimate or fresh confirmation.')
    study.write(out/'summary.json', summary)
    study.write(out/'status.json', dict(state='COMPLETE', completed=len(results), elapsed_seconds=time.time()-started, updated_unix=time.time()))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
