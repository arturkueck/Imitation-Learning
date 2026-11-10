"""An actual agent-invoked audit; never scheduled independently as an agent check."""
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import time
import tomllib
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ATTEMPT = HERE / 'attempts/attempt_002'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

now = time.time()
identity = read(HERE / 'coordinator_pid.json')
process = psutil.Process(identity['pid'])
assert process.is_running() and abs(process.create_time() - identity['create_time']) < .1
assert time.time() - read(HERE / 'status.json')['updated_unix'] < 15
assert read(HERE / 'session.json')['deadline_unix'] > time.time()
automation_path = Path.home() / '.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml'
automation = tomllib.loads(automation_path.read_text(encoding='utf-8'))
assert automation['status'] == 'ACTIVE' and automation['rrule'] == 'FREQ=MINUTELY;INTERVAL=30'
assert read(ATTEMPT / 'pairing_audit.json')['passed']
assert read(ATTEMPT / 'worker_result.json')['paired_initial_states']
dataset = read(ATTEMPT / 'dataset_manifest.json')
assert sha(Path(dataset['path'])) == dataset['sha256']
sources = read(ATTEMPT / 'source_hashes.json')
for name, digest in sources.items():
    assert sha(ROOT / name) == digest, name
assets_path = HERE.parent / 'runtime_preflight/dependency_assets_hashes.json'
assets = read(assets_path)
for name, digest in assets.items():
    assert sha(ROOT / name) == digest, name
archived_preflight = ATTEMPT / 'preflight_script.py'
if not archived_preflight.exists():
    assert sha(HERE / 'gpu_preflight.py') == read(ATTEMPT / 'attempt.json')['preflight_script_sha256']
    shutil.copy2(HERE / 'gpu_preflight.py', archived_preflight)
assert sha(archived_preflight) == read(ATTEMPT / 'attempt.json')['preflight_script_sha256']
for arm in ['B0', 'B1']:
    train = read(ATTEMPT / arm / 'training_result.json')
    assert train['state'] == 'COMPLETED' and train['optimizer_updates'] == 2000
    assert sha(ATTEMPT / arm / 'model_final.pth') == train['final_checkpoint_sha256']
    with (ATTEMPT / arm / 'losses.csv').open(encoding='utf-8') as f:
        updates = [int(r['optimizer_update']) for r in csv.DictReader(f) if r['split'] == 'train']
    assert updates == list(range(1, 2001))
paired = []
episodes = 0
for update, condition, count in [(500, 'nominal', 6), (1000, 'nominal', 6), (2000, 'nominal', 10),
                               (2000, 'sensor_y_plus5mm', 10), (2000, 'sensor_y_minus5mm', 10),
                               (2000, 'action_impulse_x_plus0.5', 10)]:
    ev = [read(ATTEMPT / arm / 'evaluation' / f'{update}_{condition}.json') for arm in ['B0', 'B1']]
    outcomes = {'both_success': 0, 'only_B0': 0, 'only_B1': 0, 'both_failure': 0}
    for r in ev:
        assert r['state'] == 'COMPLETED' and r['episodes_completed'] == count
        assert sha(Path(r['checkpoint'])) == r['checkpoint_sha256']
        assert sum(e['success'] for e in r['rollouts']) == r['successes']
        episodes += count
    for a, b in zip(ev[0]['rollouts'], ev[1]['rollouts']):
        assert a['seed'] == b['seed'] and a['initial_cube_qpos'] == b['initial_cube_qpos'] and a['initial_eef_pos'] == b['initial_eef_pos']
        key = 'both_success' if a['success'] and b['success'] else 'only_B0' if a['success'] else 'only_B1' if b['success'] else 'both_failure'
        outcomes[key] += 1
    paired.append({'updates': update, 'condition': condition, **outcomes})
workers = []
for p in psutil.process_iter(['pid', 'cmdline']):
    try:
        args = p.info['cmdline'] or []
        if any(str(ATTEMPT / 'run.py').lower() == str(a).lower() for a in args):
            workers.append(p.pid)
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
assert not workers, workers
result = {'state': 'VERIFIED', 'actor': 'agent', 'scheduled': False,
          'reason': 'Immediate user-triggered setup, recovery and completed-pilot verification',
          'unix': now, 'utc': datetime.fromtimestamp(now, timezone.utc).isoformat(),
          'berlin': datetime.fromtimestamp(now, timezone(timedelta(hours=2))).isoformat(),
          'coordinator_identity': identity, 'heartbeat_status': automation['status'],
          'optimizer_updates_per_arm': 2000, 'evaluation_episodes_completed': episodes,
          'source_files_verified': len(sources), 'runtime_assets_verified': len(assets),
          'dataset_sha256': dataset['sha256'], 'paired_outcomes': paired, 'active_pilot_workers': workers,
          'decision': 'Keep supervision ACTIVE to the original deadline; continue state/action diagnosis; do not repeat a completed pilot.'}
path = HERE / f'verification_{int(now)}.json'
with path.open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2, allow_nan=False)
with (HERE / 'agent_checks.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(result, allow_nan=False) + '\n')
print(json.dumps(result, indent=2))
