"""Frozen-seed uncertainty diagnostic. No training, rendering or test-set access."""
from pathlib import Path
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import time
import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_source(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corners(box):
    return np.asarray(list(itertools.product((-1, 1), repeat=3))) * box['size'] / 2 @ box['rotation'].T + box['position']


def corner_distance(a, b):
    # Assignment of physical corners avoids arbitrary local cuboid-axis labels.
    aa, bb = corners(a), corners(b)
    distances = np.linalg.norm(aa[:, None] - bb[None], axis=-1)
    i, j = linear_sum_assignment(distances ** 2)
    return float(np.sqrt(np.mean(distances[i, j] ** 2)))


def group_predictions(predictions, gate=.05, detection_threshold=.5):
    """GT-free union of detections; one member per seed, spatial association gate.

    Seeds are processed in fixed seed order. Hungarian assignment uses position
    and sorted side lengths; unmatched detections create new groups. A 50 mm
    association gate splits large disagreements rather than averaging objects.
    """
    groups = []
    for seed, prediction in enumerate(predictions):
        items = [dict(position=prediction['position'][i], size=prediction['size'][i],
                      rotation=prediction['rotation'][i], probability=float(p),
                      visibility=prediction['visibility'][i], seed=seed)
                 for i, p in enumerate(prediction['probability']) if p >= detection_threshold]
        assigned = set()
        if groups and items:
            centers = np.asarray([np.mean([v['position'] for v in g], axis=0) for g in groups])
            sizes = np.asarray([np.mean([np.sort(v['size']) for v in g], axis=0) for g in groups])
            distance = np.linalg.norm(centers[:, None] - np.asarray([v['position'] for v in items])[None], axis=-1)
            cost = distance + .2 * np.linalg.norm(sizes[:, None] - np.asarray([np.sort(v['size']) for v in items])[None], axis=-1)
            cost[distance > gate] = 1e6
            gi, ii = linear_sum_assignment(cost)
            for g, i in zip(gi, ii):
                if distance[g, i] <= gate:
                    groups[g].append(items[i]); assigned.add(i)
        groups.extend([[v] for i, v in enumerate(items) if i not in assigned])
    result = []
    for members in groups:
        pos = np.asarray([v['position'] for v in members]); center = pos.mean(0)
        pair = np.asarray([[corner_distance(a, b) for b in members] for a in members])
        representative = members[int(np.argmin(pair.sum(1)))]
        result.append(dict(position=center, size=representative['size'], rotation=representative['rotation'],
                           support=len(members), spread_mm=float(np.sqrt(np.mean(np.sum((pos-center)**2, axis=1))) * 1000),
                           axis_std_mm=pos.std(0) * 1000,
                           size_spread_mm=float(np.linalg.norm(np.std([np.sort(v['size']) for v in members], axis=0)) * 1000),
                           corner_disagreement_mm=float(pair.max() * 1000),
                           min_detection_score=min(v['probability'] for v in members),
                           visibility=np.mean([v['visibility'] for v in members], axis=0)))
    return result


def score_scene(groups, data, index, arm):
    """GT used only here, after inference and association, for evaluation."""
    views = 2 if arm == 'fixed' else 3
    gt = np.flatnonzero(data['active'][index] & (data['visibility'][index, :, :views] >= .05).any(-1))
    assignments = {}
    if groups and len(gt):
        dist = np.linalg.norm(np.asarray([g['position'] for g in groups])[:, None] - data['positions'][index, gt][None], axis=-1)
        ii, jj = linear_sum_assignment(dist)
        # A remote detection is an FP plus an FN, not a confidently correct match.
        assignments = {int(i): (int(gt[j]), float(dist[i, j] * 1000)) for i, j in zip(ii, jj) if dist[i, j] <= .05}
    rows = []
    for i, group in enumerate(groups):
        target, error = assignments.get(i, (-1, None))
        row = dict(scene=int(index), kind=int(data['kind'][index]), group=i,
                   support=group['support'], spread_mm=group['spread_mm'],
                   size_spread_mm=group['size_spread_mm'], corner_disagreement_mm=group['corner_disagreement_mm'],
                   min_detection_score=group['min_detection_score'], gt_index=target,
                   position_error_mm=error, bad=bool(error is None or error > 10),
                   x=float(group['position'][0]), y=float(group['position'][1]), z=float(group['position'][2]))
        row.update({f'std_{axis}_mm': float(s) for axis, s in zip('xyz', group['axis_std_mm'])})
        row.update({f'visibility_{v}': float(s) for v, s in enumerate(group['visibility'])})
        rows.append(row)
    return rows, dict(scene=int(index), observable_gt=len(gt), detected_groups=len(groups),
                      unmatched_gt=len(gt)-len(assignments), false_positive_groups=len(groups)-len(assignments),
                      all_seed_blind_scene=bool(len(gt) and not groups))


def wilson_upper(bad, n):
    if not n: return 1.
    z = 1.96; p = bad / n
    return float((p + z*z/(2*n) + z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1+z*z/n))


def rule_metrics(rows, threshold):
    accepted = [r for r in rows if r['support'] == 3 and r['spread_mm'] <= threshold]
    bad_total = sum(r['bad'] for r in rows); bad_accepted = sum(r['bad'] for r in accepted)
    return dict(threshold_mm=float(threshold), predictions=len(rows), accepted=len(accepted),
                retained_fraction=len(accepted)/max(1, len(rows)), accepted_bad=bad_accepted,
                accepted_bad_fraction=bad_accepted/len(accepted) if accepted else None,
                bad_fraction_upper95=wilson_upper(bad_accepted, len(accepted)),
                missed_bad_fraction=bad_accepted/bad_total if bad_total else None,
                flagged_bad_fraction=1-bad_accepted/bad_total if bad_total else None)


def summarize(rows, scenes):
    matched = [r for r in rows if r['position_error_mm'] is not None]
    full = [r for r in rows if r['support'] == 3]
    if len(matched) > 2:
        from scipy.stats import spearmanr
        correlation = float(spearmanr([r['spread_mm'] for r in matched], [r['position_error_mm'] for r in matched]).statistic)
    else: correlation = None
    return dict(scenes=len(scenes), predicted_groups=len(rows), three_seed_agreement=len(full),
                position_error_mean_mm=float(np.mean([r['position_error_mm'] for r in matched])) if matched else None,
                bad_groups=sum(r['bad'] for r in rows), spread_error_spearman=correlation,
                observable_gt=sum(s['observable_gt'] for s in scenes), unmatched_gt=sum(s['unmatched_gt'] for s in scenes),
                false_positive_groups=sum(s['false_positive_groups'] for s in scenes),
                all_seed_blind_scenes=sum(s['all_seed_blind_scene'] for s in scenes))


def write_csv(path, rows):
    if not rows: return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def plots(out, arm, held, sweep, selected):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    matched = [r for r in held if r['position_error_mm'] is not None]
    for support, color in [(3, 'tab:blue'), (2, 'tab:orange'), (1, 'tab:red')]:
        part = [r for r in matched if r['support'] == support]
        axes[0, 0].scatter([r['spread_mm'] for r in part], [r['position_error_mm'] for r in part], s=8, alpha=.25, c=color, label=f'{support}/3 Seeds')
    axes[0, 0].axhline(10, c='black', ls='--'); axes[0, 0].legend()
    axes[0, 0].set(xlabel='Positionsstreuung [mm]', ylabel='Positionsfehler [mm]', title='Streuung gegen tatsächlichen Fehler')
    axes[0, 1].plot([s['retained_fraction']*100 for s in sweep], [100*s['accepted_bad_fraction'] if s['accepted_bad_fraction'] is not None else np.nan for s in sweep])
    axes[0, 1].axhline(5, c='black', ls='--')
    axes[0, 1].set(xlabel='Beibehaltene Vorhersagen [%]', ylabel='Fehlerhafte darunter [%]', title='Zurückstellen unsicherer Vorhersagen')
    axes[1, 0].plot([s['retained_fraction']*100 for s in sweep], [100*s['missed_bad_fraction'] if s['missed_bad_fraction'] is not None else np.nan for s in sweep])
    axes[1, 0].set(xlabel='Beibehaltene Vorhersagen [%]', ylabel='Übersehene Fehler / alle Fehler [%]', title='Fehler >10 mm oder falsche Zusatzobjekte')
    bins = [0, 1, 2, 3, 5, 8, 12, 20, np.inf]; labels=[]; means=[]; errors=[]; counts=[]
    for a, b in zip(bins[:-1], bins[1:]):
        part=[r for r in matched if r['support']==3 and a<=r['spread_mm']<b]
        labels.append(f'{a}–{b:g}'); counts.append(len(part))
        means.append(np.mean([r['position_error_mm'] for r in part]) if part else np.nan)
        errors.append(np.percentile([r['position_error_mm'] for r in part], 90) if part else np.nan)
    axes[1, 1].plot(labels, means, 'o-', label='Mittlerer Fehler'); axes[1, 1].plot(labels, errors, 'o--', label='90. Perzentil')
    for i, n in enumerate(counts): axes[1, 1].annotate(f'n={n}', (i, means[i] if np.isfinite(means[i]) else 0), fontsize=7, xytext=(0, 8), textcoords='offset points')
    axes[1, 1].set(xlabel='Streuung [mm], nur 3/3 Seeds', ylabel='Positionsfehler [mm]', title='Empirische Zuverlässigkeit'); axes[1, 1].legend()
    for ax in axes.flat: ax.grid(alpha=.25)
    fig.suptitle(f'{arm} · explorative Validierungs-Hälfte · Schwelle Kalibrierung: {selected:g} mm\nKeine Fehlergarantie; keine unabhängige Schlussprüfung')
    fig.tight_layout(); fig.savefig(out/f'{arm}_uncertainty.png', dpi=150); fig.savefig(out/f'{arm}_uncertainty.svg'); plt.close(fig)


def main():
    import torch
    parser=argparse.ArgumentParser(); parser.add_argument('--name', default='uncertainty_001'); args=parser.parse_args()
    source=HERE/'run_001'; out=HERE/args.name; out.mkdir(exist_ok=False)
    torch.set_num_threads(4); torch.manual_seed(61101); torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cuda.enable_flash_sdp(False); torch.backends.cuda.enable_mem_efficient_sdp(False)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    started=time.time(); selection=json.loads((source/'selection.json').read_text())['models']
    model_source=load_source(source/'source/model_prototype.py', 'frozen_uncertainty_model')
    learning=load_source(source/'source/learning.py', 'frozen_uncertainty_learning')
    folder=source/'data/validation'; data={p.stem:np.load(p,mmap_mode='r') for p in folder.glob('*.npy')}
    # Check every scene, without loading the entire RGB dataset into RAM.
    for i in range(len(data['images'])):
        if data['images'][i].max()<20 or data['images'][i].mean()<1: raise RuntimeError(f'Invalid RGB scene {i}')
        if data['active'][i].any() and not (data['active'][i] & (data['visibility'][i].max(-1)>=.05)).any(): raise RuntimeError(f'No observable target {i}')
    families=[tuple(v) for v in data['family']]
    unique=sorted(set(families)); rng=np.random.default_rng(61101); rng.shuffle(unique)
    calibration=set(unique[:len(unique)//2]); split=['calibration' if f in calibration else 'held_validation' for f in families]
    write_csv(out/'split.csv', [dict(scene=i,family_seed=f[0],family_id=f[1],split=split[i]) for i,f in enumerate(families)])
    hashes={str(p.relative_to(source)):digest(p) for p in folder.glob('*.npy')}
    predictions={}
    with torch.inference_mode():
        for row in selection:
            path=source/'checkpoints'/f"{row['arm']}_seed{row['seed']}_best.pth"
            if digest(path)!=row['sha256']: raise RuntimeError(f'Checkpoint hash mismatch: {path}')
            model=model_source.ScenePerception().to(device)
            model.load_state_dict(torch.load(path,map_location=device,weights_only=False)['model']); model.eval()
            chunks={}
            for start in range(0,len(families),16):
                ids=np.arange(start,min(start+16,len(families)))
                batch={k:torch.as_tensor(data[k][ids],device=device) for k in ['images','rays']}
                raw,_=learning.run_model(model,batch,row['arm']); decoded=learning.decode(raw)
                for k,v in decoded.items(): chunks.setdefault(k,[]).append(v.cpu().numpy())
            pred={k:np.concatenate(v) for k,v in chunks.items()}; predictions[(row['arm'],row['seed'])]=pred
            np.savez_compressed(out/f"{row['arm']}_seed{row['seed']}_predictions.npz",**pred)
            if digest(path)!=row['sha256']: raise RuntimeError('Checkpoint changed during inference')
            print(f"Inference complete: {row['arm']} seed {row['seed']}",flush=True)
            del model
    results={}
    thresholds=np.r_[-1.,np.arange(0,20.01,.25),25.,35.,50.,100.]
    for arm in ['fixed','fixed_wrist']:
        rows=[]; scenes=[]
        for i in range(len(families)):
            groups=group_predictions([{k:v[i] for k,v in predictions[(arm,s)].items()} for s in [1,2,3]])
            rr,ss=score_scene(groups,data,i,arm)
            for r in rr: r['split']=split[i]
            ss['split']=split[i]; rows.extend(rr); scenes.append(ss)
        cal=[r for r in rows if r['split']=='calibration']; held=[r for r in rows if r['split']=='held_validation']
        cal_sweep=[rule_metrics(cal,t) for t in thresholds]
        # Fixed criterion; empirical Wilson upper bound, not a safety certificate.
        eligible=[s for s in cal_sweep if s['accepted']>=30 and s['bad_fraction_upper95']<=.05]
        chosen=max(eligible,key=lambda s:s['accepted']) if eligible else cal_sweep[0]
        threshold=chosen['threshold_mm']; held_sweep=[rule_metrics(held,t) for t in thresholds]
        results[arm]=dict(calibration=summarize(cal,[s for s in scenes if s['split']=='calibration']),
                          held_validation=summarize(held,[s for s in scenes if s['split']=='held_validation']),
                          selected_rule=chosen,held_rule=rule_metrics(held,threshold),
                          by_arrangement={str(kind):dict(summary=summarize([r for r in held if r['kind']==kind],[s for s in scenes if s['split']=='held_validation' and int(data['kind'][s['scene']])==kind]),rule=rule_metrics([r for r in held if r['kind']==kind],threshold)) for kind in range(4)})
        write_csv(out/f'{arm}_objects.csv',rows); write_csv(out/f'{arm}_scenes.csv',scenes)
        write_csv(out/f'{arm}_calibration_sweep.csv',cal_sweep); write_csv(out/f'{arm}_held_sweep.csv',held_sweep)
        plots(out,arm,held,held_sweep,threshold)
    report=dict(training_started=False,optimizer_updates=0,device=device,selection=selection,
                dataset='existing validation only; reserved IID/OOD test sets untouched',
                limitation='Checkpoints were selected using this validation set; held half is exploratory, not an independent final test. Three seeds can share systematic errors.',
                policy='Accept only support=3 and position spread <= threshold. Calibration: maximize retained groups with >=30 accepted and Wilson upper95 bad fraction <=5%. Otherwise reject all.',
                association_gate_mm=50,detection_threshold=.5,bad_definition='unmatched predicted group OR matched position error >10 mm; missing GT counted separately',
                random_seed=61101,data_sha256=hashes,source_sha256={p.name:digest(p) for p in [Path(__file__),source/'source/model_prototype.py',source/'source/learning.py']},
                results=results,elapsed_seconds=time.time()-started)
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(status='complete',results=results,elapsed_seconds=report['elapsed_seconds'])),flush=True)


if __name__=='__main__': main()
