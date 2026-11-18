"""Read-only baseline audit: no torch, simulator, training or live-run access."""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import distributions
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT/'praxis/results/curriculum/abc_comparison_20261112/ready_001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    plan = read(RUN/'plan.json')
    summary = read(RUN/'result_summary.json')
    frozen = read(RUN/'confirmation/frozen.json')
    reuse = read(RUN/'reuse_audit.json')
    assert read(RUN/'status.json')['state'] == 'COMPLETE'
    assert read(RUN/'supervisor_status.json')['state'] == 'COMPLETE'
    assert len(frozen) == 9 and summary['clock_corrected'] and not summary['technical_only']
    assert all(row['batch_multiset_equal'] and row['initialization_equal'] for row in reuse.values())
    starts, unique, panels, checked = {}, {}, {}, {}
    for model, entry in frozen.items():
        checkpoint = RUN/'confirmation'/f'{model}.pth'
        digest = sha(checkpoint)
        assert digest == entry['sha256'], model+' checkpoint changed'
        checked[model] = digest
        panels[model] = {}
        for count, seed_key in ((2, 'two_cube_seeds'), (3, 'confirmation_seeds')):
            panel = read(RUN/'confirmation'/f'{model}_count{count}.json')
            expected = set(range(plan[seed_key][0], plan[seed_key][1]+1))
            assert len(panel['rows']) == panel['n'] == len(expected)
            assert {r['seed'] for r in panel['rows']} == expected
            successes = sum(row['success'] for row in panel['rows'])
            assert successes == panel['successes'] == summary['models'][model][str(count)]['successes']
            for row in panel['rows']:
                assert bool(row['success']) == (row['max_stable_frames'] >= 50)
                key, identity = (count, row['seed']), (count, row['initial_sha256'])
                assert key not in starts or starts[key] == row['initial_sha256'], 'Unpaired starts'
                assert identity not in unique or unique[identity] == row['seed'], 'Duplicate physical scenario'
                starts[key], unique[identity] = row['initial_sha256'], row['seed']
            panels[model][str(count)] = dict(n=panel['n'], successes=successes)
    installed = {d.metadata['Name'].lower():d.version for d in distributions() if d.metadata['Name']}
    task = read(ROOT/'experiments/baselines/additional_tasks/stack_two/task_info.json')['environment']['env_kwargs']
    inputs = [RUN/'plan.json', RUN/'result_summary.json', RUN/'reuse_audit.json', RUN/'confirmation/frozen.json',
              ROOT/'praxis/src/task_extensions/environments.py', ROOT/'experiments/self_imitation/stack_composition_20261023/run.py',
              ROOT/'experiments/curriculum/abc_comparison_20261112/train.py', ROOT/'experiments/critic/critic_warmstart_20261104/core.py',
              ROOT/'experiments/critic/critic_warmstart_20261104/README.md']
    evidence = dict(checked_utc=datetime.now(timezone.utc).isoformat(), training_or_simulation_started=False,
        scope='Existing A/B/C end points and raw panels, local task contract and known critic warmstart family; not a global proof of algorithm absence.',
        completed_abc_run_verified=True, frozen_checkpoints_verified=checked, panel_counts_verified=panels,
        total_episode_records_verified=sum(p['n'] for m in panels.values() for p in m.values()),
        paired_initial_states_verified=True, distinct_physical_scenarios=dict(two_cube=40, three_cube=100),
        bc_ordering_control_initialization_and_batch_multiset_audit=reuse,
        library_versions={name:installed.get(name, 'not installed') for name in ('stable-baselines3', 'gymnasium', 'gym', 'robosuite', 'torch')},
        local_reward_contract=dict(control_freq=task['control_freq'], metadata_reward_shaping=task['reward_shaping'],
            native_success_frames=int(.5*task['control_freq']), common_primary_success_frames=50,
            native_reward='binary _check_success; local override does not implement dense shaping',
            native_vs_common_finger_contact_check='native forbids grasp; common evaluator additionally forbids gripper/finger contact'),
        rl_from_scratch_baseline='No qualified baseline verified in the inspected inventory; the examined critic actors start from BC.',
        input_sha256={str(path.relative_to(ROOT)):sha(path) for path in inputs})
    (HERE/'evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(dict(checkpoints_verified=len(checked), episode_records_verified=evidence['total_episode_records_verified'],
        paired_starts=True, native_success_frames=evidence['local_reward_contract']['native_success_frames'], primary_success_frames=50,
        three_cube={model:value['3']['successes'] for model,value in panels.items()})))


if __name__ == '__main__':
    main()
