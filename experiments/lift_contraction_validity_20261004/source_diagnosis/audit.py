"""Train-demo cross-validation and reproducible action-response feasibility probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / 'praxis/data/lift/ph/low_dim_v15.hdf5'
SEED = 41004


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def save(name, result):
    path = HERE / name
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def read_arrays(f, names):
    a = np.concatenate([f[f'data/{n}/actions'][:, :3] for n in names])
    y = np.concatenate([f[f'data/{n}/next_obs/robot0_eef_pos'][:] - f[f'data/{n}/obs/robot0_eef_pos'][:] for n in names])
    return a, y


def fit(a, y):
    return np.linalg.lstsq(np.column_stack([a, np.ones(len(a))]), y, rcond=None)[0]


def predict(a, coefficients):
    return np.column_stack([a, np.ones(len(a))]) @ coefficients


def scores(y, prediction):
    error = np.linalg.norm(y - prediction, axis=1)
    return {'n': len(y), 'r2_by_axis': (1 - ((y-prediction)**2).sum(0) / ((y-y.mean(0))**2).sum(0)).tolist(),
            'error_m_median': float(np.median(error)), 'error_m_p90': float(np.quantile(error, .9)), 'error_m_mean': float(error.mean())}


def offline():
    started = time.monotonic()
    with h5py.File(DATA, 'r') as f:
        train = [n.decode() for n in f['mask/train'][:]]
        valid = [n.decode() for n in f['mask/valid'][:]]
        assert len(train) == 180 and len(valid) == 20 and not set(train) & set(valid)
        a, y = read_arrays(f, train)
        coefficients = fit(a, y)
        av, yv = read_arrays(f, valid)
        folds = np.array_split(np.random.default_rng(SEED).permutation(train), 5)
        predictions = {}
        fold_details = []
        for i, held in enumerate(folds):
            fit_names = sorted(set(train) - set(held))
            af, yf = read_arrays(f, fit_names)
            coef = fit(af, yf)
            ah, yh = read_arrays(f, held)
            fold_details.append({'fold': i, 'fit_demos': fit_names, 'heldout_demos': held.tolist(), 'metrics': scores(yh, predict(ah, coef))})
            for n in held:
                ad, yd = read_arrays(f, [n])
                predictions[str(n)] = predict(ad, coef)
        out_of_fold = np.concatenate([predictions[n] for n in train])
        residual = np.linalg.norm(y-out_of_fold, axis=1)
        np.savez(HERE / 'out_of_fold_residuals.npz', demo_names=np.array(train), offsets=np.cumsum([0]+[len(f[f'data/{n}/actions']) for n in train]), residual_m=residual)
        result = {'state': 'COMPLETE', 'seed': SEED, 'dataset': str(DATA), 'dataset_sha256': sha(DATA),
                  'source_sha256': sha(__file__), 'protocol_sha256': sha(HERE/'PROTOCOL.md'),
                  'train_demos': train, 'valid_demos': valid, 'training_transitions': len(a),
                  'dynamics_matrix': coefficients[:3].tolist(), 'intercept': coefficients[3].tolist(),
                  'in_sample': scores(y, predict(a, coefficients)), 'inner_out_of_fold': scores(y, out_of_fold),
                  'outer_valid_diagnostic_only': scores(yv, predict(av, coefficients)), 'folds': fold_details,
                  'residual_median_threshold': float(np.median(residual)), 'elapsed_seconds': time.monotonic()-started}
    save('offline.json', result)
    print(json.dumps({k: result[k] for k in ['state', 'training_transitions','in_sample','inner_out_of_fold','outer_valid_diagnostic_only','elapsed_seconds']}, indent=2), flush=True)


def intervention():
    started = time.monotonic()
    offline_result = json.loads((HERE/'offline.json').read_text())
    sys.path.insert(0, str(ROOT/'experiments/square/scripts'))
    import runtime  # noqa: F401
    from robomimic.utils import env_utils as EU, obs_utils as OU
    OU.initialize_obs_utils_with_obs_specs({'obs': {'low_dim': ['robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'object'], 'rgb': []}})
    rows = []
    result = {'state': 'RUNNING', 'seed': SEED, 'dataset_sha256': offline_result['dataset_sha256'],
              'source_sha256': sha(__file__), 'protocol_sha256': sha(HERE/'PROTOCOL.md'), 'rows': rows}
    save('intervention.json', result)
    K = np.asarray(offline_result['dynamics_matrix'])
    residuals = np.load(HERE/'out_of_fold_residuals.npz')
    residual_map = {str(n): residuals['residual_m'][residuals['offsets'][i]:residuals['offsets'][i+1]] for i,n in enumerate(residuals['demo_names'])}
    env = None
    try:
        with h5py.File(DATA, 'r') as f:
            metadata = json.loads(f['data'].attrs['env_args'])
            env = EU.create_env_from_metadata(metadata, render=False, render_offscreen=False)
            names = offline_result['train_demos']
            selected = [names[i] for i in np.linspace(0, len(names)-1, 12).astype(int)]
            result['selected_train_demos'] = selected
            for name in selected:
                d = f[f'data/{name}']
                actions, states = d['actions'][:], d['states'][:]
                xml = d.attrs['model_file']
                anchors = [int(frac*(len(actions)-1)) for frac in [.2,.5,.8]]
                for t in anchors:
                    if (HERE/'STOP_REQUESTED').exists():
                        raise InterruptedError('User or supervisor requested safe stop')
                    observations = []
                    restore_errors = []
                    actual_actions = []
                    variants = [('reference', None, 0.), ('reference_repeat', None, 0.)] + [(f'{axis}_{sign:+}',axis,sign*.1) for axis in range(3) for sign in [-1,1]]
                    for variant, axis, amount in variants:
                        env.reset_to({'model': xml, 'states': states[0]})
                        for prefix_action in actions[:t]:
                            env.step(prefix_action)
                        obs = env.reset_to({'states': states[t]})
                        restore_errors.append(float(np.linalg.norm(obs['robot0_eef_pos'] - d['obs/robot0_eef_pos'][t])))
                        action = actions[t].copy()
                        if axis is not None:
                            action[axis] = np.clip(action[axis]+amount,-1,1)
                        next_obs, _, _, _ = env.step(action)
                        observations.append(np.array(next_obs['robot0_eef_pos'],copy=True))
                        actual_actions.append(action)
                    reference_error = float(np.linalg.norm(observations[0] - d['next_obs/robot0_eef_pos'][t]))
                    repeat_error = float(np.linalg.norm(observations[0]-observations[1]))
                    axis_rows = []
                    for axis in range(3):
                        minus, plus = 2+axis*2, 3+axis*2
                        da = actual_actions[plus][:3]-actual_actions[minus][:3]
                        predicted = da @ K
                        observed = observations[plus]-observations[minus]
                        observed_norm = float(np.linalg.norm(observed))
                        degenerate = observed_norm < 1e-5
                        cosine = float(predicted @ observed / max(float(np.linalg.norm(predicted))*observed_norm, 1e-15))
                        relative_error = float(np.linalg.norm(predicted-observed)/max(observed_norm, 1e-15))
                        axis_rows.append({'axis': axis, 'action_difference_xyz': da.tolist(), 'predicted_response_m': predicted.tolist(), 'observed_response_m': observed.tolist(),
                                          'cosine': cosine, 'relative_error': relative_error, 'degenerate': degenerate, 'passes_response_gate': bool(not degenerate and cosine>=.8 and relative_error<=.5)})
                    row = {'demo': name, 't': t, 'length':len(actions), 'oof_prediction_error_m': float(residual_map[name][t]),
                           'restore_error_m_max': max(restore_errors), 'reference_repeat_error_m':repeat_error, 'reference_next_obs_error_m':reference_error,
                           'eef_m': d['obs/robot0_eef_pos'][t].tolist(), 'cube_relative_m': d['obs/object'][t,-3:].tolist(), 'axes': axis_rows}
                    rows.append(row)
                    result['elapsed_seconds'] = time.monotonic()-started
                    save('intervention.json', result)
                    print(f'{name} t={t}: replay={reference_error:.7f} m, response gates={[a["passes_response_gate"] for a in axis_rows]}', flush=True)
        axes = [a for r in rows for a in r['axes']]
        low = [a for r in rows if r['oof_prediction_error_m']<=offline_result['residual_median_threshold'] for a in r['axes']]
        def response_summary(items):
            return {'axis_probes':len(items), 'degenerate':sum(a['degenerate'] for a in items),
                    'pass_fraction_all':sum(a['passes_response_gate'] for a in items)/len(items) if items else 0.,
                    'pass_fraction_nondegenerate':sum(a['passes_response_gate'] for a in items)/max(1,sum(not a['degenerate'] for a in items)),
                    'relative_error_median':float(np.median([a['relative_error'] for a in items])) if items else None,
                    'cosine_median':float(np.median([a['cosine'] for a in items])) if items else None}
        reconstruction = max(r['restore_error_m_max'] for r in rows)<=1e-5 and max(r['reference_repeat_error_m'] for r in rows)<=1e-6 and np.median([r['reference_next_obs_error_m'] for r in rows])<=.0005
        overall, low_summary = response_summary(axes), response_summary(low)
        result.update(state='COMPLETE', overall=overall, low_oof_error_half=low_summary,
                      reconstruction_gate=bool(reconstruction), reference_next_obs_error_m_median=float(np.median([r['reference_next_obs_error_m'] for r in rows])),
                      overall_response_gate=overall['pass_fraction_nondegenerate']>=.8,
                      weighted_candidate_gate=bool(reconstruction and low_summary['axis_probes']>0 and low_summary['pass_fraction_nondegenerate']>=.8),
                      elapsed_seconds=time.monotonic()-started)
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc,InterruptedError) else 'FAILED', error=repr(exc), elapsed_seconds=time.monotonic()-started)
        raise
    finally:
        if env is not None:
            env.env.close()
        save('intervention.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','selected_train_demos']},indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['offline','intervention'])
    args = parser.parse_args()
    (offline if args.mode=='offline' else intervention)()
