"""GT-after-acquisition diagnostics, paired subsets and explicit denominators."""
from pathlib import Path
import csv,json,collections
import numpy as np
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from geometry import corners
from run import read,save

VARIANTS=['initial','one_side','two_sides','adaptive','neural_extra']

def metric(row,name):return row['metrics'][name] if name=='neural_extra' else row['stage_metrics'][name]

def summary(rows):
    if not rows:return dict(count=0)
    result={}
    initial=np.array([r['stage_metrics']['initial']['error_mm'] for r in rows])
    for name in VARIANTS:
        metrics=[metric(r,name) for r in rows];error=np.array([m['error_mm'] for m in metrics]);positions=[x for m in metrics for x in m['position_mm']]
        result[name]=dict(count=len(rows),mean=float(error.mean()),median=float(np.median(error)),p95=float(np.percentile(error,95)),
            worse_any_count=int((error>initial+1e-6).sum()),worse_over_1mm_count=int((error>initial+1.).sum()),better_over_1mm_count=int((error<initial-1.).sum()),
            missing=sum(m['missing'] for m in metrics),extra=sum(m['extra'] for m in metrics),matched_position_count=len(positions),matched_position_mean_mm=float(np.mean(positions)) if positions else None)
    return result

def fixed_matches(boxes,truth):
    ids=np.flatnonzero(truth['active'])
    if not boxes or not len(ids):return {}
    d=np.linalg.norm(np.array([b['position'] for b in boxes])[:,None]-truth['positions'][None,ids],axis=-1)
    a,b=linear_sum_assignment(d)
    return {int(i):int(ids[j]) for i,j in zip(a,b) if d[i,j]<=.05}

def object_error(box,truth,index):
    b={k:np.asarray(v) for k,v in box.items()};target=dict(position=truth['positions'][index],size=truth['sizes'][index],rotation=truth['rotations'][index])
    d=np.linalg.norm(corners(b)[:,None]-corners(target)[None],axis=-1);i,j=linear_sum_assignment(d*d)
    return float(np.linalg.norm(b['position']-target['position'])*1000+.25*np.sqrt(np.mean(d[i,j]**2))*1000)

def report(run):
    run=Path(run);rows=read(run/'results.json')['scenes'];updates=[];diagnostics=collections.Counter();scenes=[]
    for r in rows:
        folder=run/'development'/f'scene_{r["index"]:04d}';truth=np.load(folder/'sample.npz',allow_pickle=False)
        matches=fixed_matches(r['initial'],truth);previous=r['initial'];last=r['stage_metrics']['initial']['error_mm']
        for step in range(1,len(r['completed_sides'])+1):
            snapshot=read(folder/f'analysis_after_sweep_{step}.json')
            for obj in snapshot['objects']:
                diagnostics['fit:'+obj['fit']['status']]+=1
                for reason in obj['gate']['reasons']:diagnostics['gate:'+reason]+=1
                i=obj['object_index']
                if i not in matches:diagnostics['unmatched_initial_detection_excluded_from_object_labels']+=1;continue
                before=object_error(previous[i],truth,matches[i]);raw=object_error(snapshot['raw'][i],truth,matches[i]);after=object_error(snapshot['adopted'][i],truth,matches[i])
                g=obj['gate'];updates.append(dict(scene=r['index'],step=step,object_index=i,accepted=g['accepted'],before=before,raw=raw,after=after,
                    heldout_gain=None if g['heldout_before'] is None or g['heldout_after'] is None else g['heldout_before']-g['heldout_after'],
                    raw_harmful=raw>before+1.,raw_beneficial=raw<before-1.,accepted_harmful=bool(g['accepted'] and raw>before+1.),rejected_beneficial=bool(not g['accepted'] and raw<before-1.)))
            diagnostics['tracks']+=len(snapshot['tracks']);diagnostics['distinct_triangulated_points']+=len(snapshot['triangulated_points'])
            diagnostics['passes_with_zero_triangulation']+=int(not snapshot['triangulated_points'])
            for key,value in snapshot['rejections'].items():diagnostics['tracking:'+key]+=value
            previous=snapshot['adopted']
        truth.close()
        scenes.append(dict(index=r['index'],count=r['evaluation_stratum']['count'],kind=r['evaluation_stratum']['kind'],long=r['evaluation_stratum']['long'],
            one_available=r['stage_available']['one_side'],two_available=r['stage_available']['two_sides'],initial_request=r['initial_decision']['requested_sides'],adaptive_stage=r['adaptive_chosen_stage'],
            adaptive_supported=r['adaptive_supported'],**{v:metric(r,v)['error_mm'] for v in VARIANTS},failure=r['failure'] or ''))
    paired=[r for r in rows if r['stage_available']['two_sides']]
    accepted=[u for u in updates if u['accepted']];rejected=[u for u in updates if not u['accepted']]
    second_deltas=[r['stage_metrics']['two_sides']['error_mm']-r['stage_metrics']['one_side']['error_mm'] for r in paired]
    result=dict(development_only=True,scenes=len(rows),both_sides_available=len(paired),one_side_available=sum(r['stage_available']['one_side'] for r in rows),
        all_scenes_with_explicit_fallback=summary(rows),nonempty_scenes=summary([r for r in rows if r['evaluation_stratum']['count']>0]),paired_both_available=summary(paired),
        second_side=dict(denominator=len(paired),worse_over_1mm=sum(d>1. for d in second_deltas),better_over_1mm=sum(d< -1. for d in second_deltas),mean_delta=float(np.mean(second_deltas)) if second_deltas else None),
        update_gate=dict(matched_object_update_denominator=len(updates),accepted=len(accepted),accepted_harmful=sum(u['accepted_harmful'] for u in updates),rejected=len(rejected),rejected_beneficial=sum(u['rejected_beneficial'] for u in updates)),
        adaptive_stages=dict(collections.Counter(str(r['adaptive_chosen_stage']) for r in rows)),
        supported_but_materially_worse_count=sum(r['adaptive_supported'] and r['stage_metrics']['adaptive']['error_mm']>r['stage_metrics']['initial']['error_mm']+1. for r in rows),
        strata={name:{str(value):summary([r for r in rows if r['evaluation_stratum'][name]==value]) for value in sorted({r['evaluation_stratum'][name] for r in rows},key=str)} for name in ['count','kind','long']},
        diagnostics=dict(diagnostics),optimizer_updates=0,heldout_endtests_used=False)
    save(run/'summary.json',result);save(run/'object_updates.json',updates)
    with (run/'scenes.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(scenes[0]));writer.writeheader();writer.writerows(scenes)
    fig,axes=plt.subplots(1,3,figsize=(14,4));labels=['Initial','One side','Both sides','Adaptive','Neural endpoints']
    for j,name in enumerate(VARIANTS):
        values=np.sort([metric(r,name)['error_mm'] for r in rows]);axes[0].plot(values,np.arange(1,len(values)+1)/len(values),label=labels[j])
    axes[0].set(xlabel='Set error [mm-equivalent]',ylabel='Scene fraction',title='All scenes; unavailable views use fallback');axes[0].legend(fontsize=7)
    axes[1].bar(labels,[result['all_scenes_with_explicit_fallback'][v]['worse_over_1mm_count'] for v in VARIANTS]);axes[1].set(ylabel='Scenes worse by >1 mm-equivalent',title='Harm relative to initial')
    for accepted_flag,color,label in [(True,'#c65840','Accepted'),(False,'#4b83b5','Rejected')]:
        group=[u for u in updates if u['accepted']==accepted_flag and u['heldout_gain'] is not None]
        axes[2].scatter([u['heldout_gain'] for u in group],[u['before']-u['raw'] for u in group],s=10,alpha=.5,c=color,label=label)
    axes[2].axhline(0,color='gray',lw=.7);axes[2].axvline(0,color='gray',lw=.7);axes[2].set(xlabel='Heldout RGB edge improvement [px]',ylabel='Raw candidate GT improvement [mm-eq]',title='Does the image gate predict true benefit?');axes[2].legend(fontsize=7)
    fig.tight_layout();fig.savefig(run/'benchmark.png',dpi=140);plt.close(fig)
    lines=['# Frozen development evaluation','',f'Completed scenes: {len(rows)}. Both sides available: {len(paired)}. No training or endtest evaluation.','',
        '| Variant | Mean set error | Median | P95 | Worse than initial by >1 |', '|---|---:|---:|---:|---:|']
    for v in VARIANTS:
        s=result['all_scenes_with_explicit_fallback'][v];lines.append(f'| {v} | {s["mean"]:.3f} | {s["median"]:.3f} | {s["p95"]:.3f} | {s["worse_over_1mm_count"]}/{len(rows)} |')
    lines+=['',f'Second-side changes among paired scenes: {result["second_side"]}.',f'Update gate, fixed initial GT association: {result["update_gate"]}.','',
        'Set error includes geometry and FP/FN, not robot placement accuracy. Object-update labels use uncapped center error +0.25×corner RMSE on a fixed initial association and are a separate diagnostic. Unmatched detections remain in scene metrics but are excluded from object-label denominators.',
        'All-scene metrics include explicitly recorded fallback for inaccessible views; paired-only results and strata are in summary.json. Shadow-only second images are never supplied to earlier adaptive decisions. Geometry/policy thresholds were frozen before collection.',
        'Neural endpoints use the original model input budget: initial view plus acquired end images. Geometric variants use outbound video; this is not an equal-image-count architecture ablation.',
        'Current families are development data and must not later enter request-head training or final tests. No automatic follow-up training is authorized by this report.']
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
