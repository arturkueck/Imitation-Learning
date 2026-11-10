"""Reconstruct native post-action grasp from saved states; never advance physics.

Writes hash-linked sidecars only. Last post-state is unknown, never invented.
Only the two permitted collection manifests are accepted (no held-out tests).
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments/self_imitation/stack_five_curriculum_20261023'))
import runner as legacy

ALLOWED = [ROOT / 'experiments/self_imitation/stack_five_curriculum_20261023/datasets' /
           f'curriculum_n{n}_cycle0/manifest.json' for n in (3, 4)]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def restore_post(env, a, t, count):
    if t + 1 >= len(a['pre_state']):
        raise ValueError('Last post-action simulator state is unavailable')
    if not np.array_equal(a['post_obs'][t], a['pre_obs'][t+1]):
        raise ValueError('Post/pre-state alignment broken')
    env.sim.set_state_from_flattened(a['pre_state'][t+1])
    env.sim.forward()
    positions = np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    if not np.allclose(positions.reshape(-1), a['post_obs'][t, :3*count], atol=1e-9, rtol=0):
        raise ValueError('Restored cube positions do not reproduce saved post-observation')
    contacts = np.array([env.check_contact(env.cubes[i], env.cubes[i+1]) for i in range(count-1)])
    fingers = np.array([env.check_contact(env.robots[0].gripper, c) for c in env.cubes])
    prefixes = np.array([legacy.old.prefix_valid(env, k) for k in range(2, count+1)])
    # Exact contact/prefix agreement is deliberately fail-closed. Floating
    # collision-boundary differences must be investigated, never relabelled.
    if not np.array_equal(contacts, a['contacts'][t]):
        raise ValueError('Restored cube contacts do not match collector')
    if not np.array_equal(fingers, a['fingers'][t]):
        raise ValueError('Restored finger contacts do not match collector')
    if not np.array_equal(prefixes, a['prefix_valid'][t]):
        raise ValueError('Restored prefix validity does not match collector')
    return np.array([env._check_grasp(env.robots[0].gripper, c) for c in env.cubes], dtype=bool)


def enrich_episode(env, episode, count, destination, deadline):
    episode = Path(episode); destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Preserve existing sidecars; choose a new output folder')
    source_hash = digest(episode)
    with np.load(episode, allow_pickle=False) as raw:
        a = {k: raw[k].copy() for k in raw.files}
    held = np.zeros((len(a['x']), count), dtype=bool)
    known = np.zeros(len(a['x']), dtype=bool)
    for t in range(len(a['x'])-1):
        if time.time() >= deadline:
            raise TimeoutError('Reconstruction time cap')
        held[t] = restore_post(env, a, t, count); known[t] = True
    assert not known[-1] and digest(episode) == source_hash
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, held_post=held, held_known=known)
    meta = dict(schema='native-grasp-post-v1', source_path=str(episode),
                source_sha256=source_hash, xml_sha256=digest(episode.parent/'model.xml'),
                sidecar_sha256=digest(destination), count=count,
                restored_frames=int(known.sum()), unknown_last_post_state=True,
                contact_and_prefix_exact_match=True,
                semantics='held_post[t] from pre_state[t+1]; no physics steps; unknown mask mandatory')
    destination.with_suffix('.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT/'grasp_sidecars_preflight')
    parser.add_argument('--max-episodes', type=int, default=2)
    parser.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Output directory must be new')
    if args.max_episodes < 1 or not 1 <= args.seconds <= 600:
        raise ValueError('Bound episode count and reconstruction time explicitly')
    args.output.mkdir(parents=True)
    start = time.time(); rows = []
    try:
        for manifest in ALLOWED:
            rawrows = json.loads(manifest.read_text())['rows']
            count = int(rawrows[0]['count']); env = legacy.make_env(count)
            try:
                env.reset_from_xml_string((manifest.parent/'model.xml').read_text(encoding='utf-8'))
                for r in rawrows:
                    if len(rows) >= args.max_episodes:
                        break
                    if Path(r['path']).resolve().parent != manifest.parent.resolve():
                        raise ValueError('Episode escaped permitted collection')
                    dst = args.output/f"n{count}_{r['seed']}.npz"
                    meta = enrich_episode(env, r['path'], count, dst, start+args.seconds)
                    meta.update(split=r['split'], seed=r['seed'])
                    rows.append(meta)
                    (args.output/'manifest.json').write_text(json.dumps(dict(complete=False, rows=rows), indent=2))
            finally:
                env.close()
        complete = len(rows) == sum(len(json.loads(p.read_text())['rows']) for p in ALLOWED)
        report = dict(state='BOUNDED_RECONSTRUCTION_PASSED', complete_collection=complete,
                      episodes=len(rows), seconds=time.time()-start, rows=rows)
        (args.output/'manifest.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({k:v for k,v in report.items() if k != 'rows'}))
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps(dict(error=repr(error), completed_episodes=len(rows)), indent=2))
        raise


if __name__ == '__main__':
    main()
