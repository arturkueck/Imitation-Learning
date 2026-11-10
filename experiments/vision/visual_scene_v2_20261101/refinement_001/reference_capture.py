"""Bounded simulator-reference capture and evaluation; no model training.

Observations and privileged evaluation labels live in separate directories.
Rendered RGB must match existing images up to at most 32 isolated one-level
channel roundoff differences per scene. Original model RGB is never replaced.
"""
from pathlib import Path
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
os.environ.setdefault('OMP_NUM_THREADS','4')
import argparse,csv,json,time,shutil
import numpy as np
import ensemble_uncertainty as ensemble
import image_consistency as comparison
import reference_evidence as evidence

HERE=Path(__file__).resolve().parent


def verify_scene(regenerated,original):
    differences={}
    for key in ['positions','sizes','rotations','rays','active','count','kind','family']:
        a=np.asarray(regenerated[key]);b=np.asarray(original[key])
        differences[key]=float(np.max(np.abs(a.astype(float)-b.astype(float))))
        # MuJoCo can differ around numerical zero at ~1e-14. This is a strict
        # absolute physics/calibration tolerance, never an RGB pairing tolerance.
        same=np.allclose(a,b,rtol=0,atol=1e-7) if a.dtype.kind=='f' else np.array_equal(a,b)
        if not same:raise RuntimeError(f'Scene mismatch {key}: {differences[key]}')
    return differences


def verify_rgb_pair(regenerated,original):
    delta=np.abs(regenerated.astype(float)-original.astype(float))
    maximum=float(delta.max());changed=int(np.count_nonzero(delta))
    if maximum>1 or changed>32:
        raise RuntimeError(f'RGB mismatch: max={maximum}, changed_channels={changed}; refusing cached predictions')
    return dict(max_channel_delta=maximum,changed_channels=changed,exact=changed==0)


def segmentation_labels(segmentation,object_geoms,robot_geoms,geom_type):
    types=segmentation[...,0];ids=segmentation[...,1]
    robot=np.isin(ids,robot_geoms)&(types==geom_type)
    objects=np.zeros(ids.shape,dtype=np.uint8)
    for i,geoms in enumerate(object_geoms):objects[np.isin(ids,geoms)&(types==geom_type)]=i+1
    return robot,objects


def capture_pair(generator):
    """No physics step. Hide object render groups, keeping all camera state fixed."""
    import mujoco
    g=generator;names=['agentview','frontview','robot0_eye_in_hand']
    geoms=g.m.geom_group.copy();qpos=g.d.qpos.copy()
    robot_ids=[i for i in range(g.m.ngeom) if (mujoco.mj_id2name(g.m,mujoco.mjtObj.mjOBJ_GEOM,i) or '').startswith(('robot0_','gripper0_'))]
    objects=[];references=[];robot=[];actual=[];calibration=[]
    try:
        for name in names:
            image=g.env.sim.render(width=160,height=160,camera_name=name)[::-1].copy()
            seg=g.env.sim.render(width=160,height=160,camera_name=name,segmentation=True)[::-1].copy()
            _,oracle=segmentation_labels(seg,g.geoms,robot_ids,int(mujoco.mjtObj.mjOBJ_GEOM))
            actual.append(image);objects.append(oracle)
            cid=g.m.camera(name).id;f=80/np.tan(np.deg2rad(g.m.cam_fovy[cid]/2))
            calibration.append(dict(K=np.array([[f,0,80],[0,f,80],[0,0,1]]),
                                    rotation=g.d.cam_xmat[cid].reshape(3,3).copy(),position=g.d.cam_xpos[cid].copy()))
        for group in g.geoms:g.m.geom_group[group]=5
        for name in names:
            references.append(g.env.sim.render(width=160,height=160,camera_name=name)[::-1].copy())
            seg=g.env.sim.render(width=160,height=160,camera_name=name,segmentation=True)[::-1].copy()
            # Full robot silhouette from object-free reference, so unknown
            # object labels/occlusion cannot leak into the robot mask.
            mask,_=segmentation_labels(seg,[],robot_ids,int(mujoco.mjtObj.mjOBJ_GEOM));robot.append(mask)
    finally:
        g.m.geom_group[:]=geoms
    if not np.array_equal(g.d.qpos,qpos):raise RuntimeError('Capture changed robot/scene state')
    return dict(images=np.asarray(actual),empty_reference=np.asarray(references),
                robot_mask=np.asarray(robot),object_ids=np.asarray(objects),robot_qpos=qpos[:9].copy(),
                K=np.asarray([c['K'] for c in calibration]),
                camera_rotation=np.asarray([c['rotation'] for c in calibration]),
                camera_position=np.asarray([c['position'] for c in calibration]))


def mask_metric(mask,truth,valid):
    predicted=mask&valid;truth=truth&valid
    intersection=int((predicted&truth).sum());union=int((predicted|truth).sum())
    return dict(intersection=intersection,union=union,predicted=int(predicted.sum()),truth=int(truth.sum()),
                iou=intersection/union if union else 1.)


def aggregate(metrics):
    positive=[m for m in metrics if m['truth']>0];empty=[m for m in metrics if not m['truth']]
    intersect=sum(m['intersection'] for m in metrics);union=sum(m['union'] for m in metrics)
    pred=sum(m['predicted'] for m in metrics);truth=sum(m['truth'] for m in metrics)
    return dict(views=len(metrics),positive_views=len(positive),empty_views=len(empty),
                macro_iou_positive=float(np.mean([m['iou'] for m in positive])) if positive else None,
                micro_iou=intersect/union if union else 1.,precision=intersect/pred if pred else None,
                recall=intersect/truth if truth else None,
                empty_view_false_positive_fraction=float(np.mean([m['predicted']>0 for m in empty])) if empty else None)


def evaluate(out,data,observations,oracle,indices,split):
    thresholds=[8,16,24,32];calibration_scores={};cal_metrics={}
    for threshold in thresholds:
        metrics=[]
        for j,i in enumerate(indices):
            if split[i]!='calibration':continue
            for v in range(3):
                ev=evidence.foreground(data['images'][i,v],observations['empty_reference'][j,v],observations['robot_mask'][j,v],threshold)
                metrics.append(mask_metric(ev['mask'],oracle['object_ids'][j,v]>0,ev['valid']))
        cal_metrics[threshold]=aggregate(metrics)
        calibration_scores[threshold]=cal_metrics[threshold]['macro_iou_positive']
    eligible=[t for t in thresholds if calibration_scores[t] is not None]
    if not eligible:raise RuntimeError('No positive calibration views')
    chosen=max(eligible,key=lambda t:calibration_scores[t])
    per_view=[];masks=[];robot_gt_pixels=0;gt_pixels=0
    for j,i in enumerate(indices):
        scene_masks=[]
        for v in range(3):
            ev=evidence.foreground(data['images'][i,v],observations['empty_reference'][j,v],observations['robot_mask'][j,v],chosen)
            truth=oracle['object_ids'][j,v]>0
            metric=mask_metric(ev['mask'],truth,ev['valid'])
            per_view.append(dict(scene=int(i),view=v,kind=int(data['kind'][i]),split=split[i],**metric))
            scene_masks.append(ev['mask']);robot_gt_pixels+=int((truth&~ev['valid']).sum());gt_pixels+=int(truth.sum())
        masks.append(scene_masks)
    np.save(out/'observations/foreground_mask.npy',np.asarray(masks,dtype=bool))
    ensemble.write_csv(out/'segmentation_views.csv',per_view)
    held=[m for m in per_view if m['split']=='held_validation']
    segmentation=dict(threshold=chosen,calibration=cal_metrics,held=aggregate(held),
                      by_view={str(v):aggregate([m for m in held if m['view']==v]) for v in range(3)},
                      by_kind={str(k):aggregate([m for m in held if m['kind']==k]) for k in range(4)},
                      truth_pixels_excluded_by_robot_mask=robot_gt_pixels,truth_pixels_total=gt_pixels)
    ranking={}
    for arm in ['fixed','fixed_wrist']:
        predictions=[dict(np.load(HERE/'uncertainty_001'/f'{arm}_seed{s}_predictions.npz')) for s in [1,2,3]]
        rows=[];views=2 if arm=='fixed' else 3
        for j,i in enumerate(indices):
            groups=ensemble.group_predictions([{k:v[i] for k,v in p.items()} for p in predictions])
            cameras=[comparison.camera_from_rays(r) for r in data['rays'][i,:views]]
            features,_=evidence.features(data['images'][i,:views],observations['empty_reference'][j,:views],observations['robot_mask'][j,:views],cameras,groups,chosen)
            scored,_=ensemble.score_scene(groups,data,i,arm)
            for row,feature in zip(scored,features):row.update(feature,split=split[i]);rows.append(row)
        cal=[r for r in rows if r['split']=='calibration'];held_rows=[r for r in rows if r['split']=='held_validation']
        cs=comparison.rank_scores(cal,cal);hs=comparison.rank_scores(held_rows,cal)
        selected=max(['hybrid25','hybrid50','hybrid75'],key=lambda name:sum(comparison.top_budget(cal,cs[name],b)['detected_bad'] for b in [.05,.1]))
        report=dict(selected_recipe=selected,budgets={})
        for budget in [.05,.1,.2]:
            metrics={name:comparison.top_budget(held_rows,hs[name],budget) for name in ['ensemble','image',selected]}
            report['budgets'][str(budget)]={name:comparison.public_metrics(m) for name,m in metrics.items()}
            report['budgets'][str(budget)]['hybrid_delta_bootstrap95']=comparison.bootstrap_delta(held_rows,metrics['ensemble']['flag_mask'],metrics[selected]['flag_mask'])
        report['towers_10pct']={}
        ids=[k for k,r in enumerate(held_rows) if r['kind']==2];part=[held_rows[k] for k in ids]
        for name in ['ensemble','image',selected]:report['towers_10pct'][name]=comparison.public_metrics(comparison.top_budget(part,hs[name][ids],.1))
        common=[k for k,r in enumerate(held_rows) if r['support']==3 and r['spread_mm']<=3 and r['bad']]
        report['shared_errors']=dict(count=len(common),**{name:int(comparison.top_budget(held_rows,hs[name],.1)['flag_mask'][common].sum()) for name in ['ensemble','image',selected]})
        ranking[arm]=report
        ensemble.write_csv(out/f'{arm}_objects.csv',rows)
        comparison.make_plots(out,arm,held_rows,hs,selected)
    return segmentation,ranking


def examples(out,data,observations,oracle,indices,threshold):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selections=[i for i in [441,1445,1671] if i in indices]
    if not selections:selections=list(indices[:2])
    fig,axes=plt.subplots(len(selections)*3,5,figsize=(12,2.2*len(selections)*3),squeeze=False)
    for block,i in enumerate(selections):
        j=int(np.where(indices==i)[0][0])
        for v in range(3):
            ev=evidence.foreground(data['images'][i,v],observations['empty_reference'][j,v],observations['robot_mask'][j,v],threshold)
            truth=oracle['object_ids'][j,v]>0;mask=ev['mask'];valid=ev['valid']
            errors=np.zeros((160,160,3));errors[mask&truth&valid]=[.1,.8,.2];errors[mask&~truth&valid]=[1,.2,.1];errors[~mask&truth&valid]=[.1,.4,1]
            for col,img in enumerate([data['images'][i,v],observations['empty_reference'][j,v],observations['robot_mask'][j,v],mask,errors]):
                ax=axes[block*3+v,col];ax.imshow(img,cmap='gray' if col in [2,3] else None);ax.axis('off')
                if block==0 and v==0:ax.set_title(['RGB','Leere Referenz','Bekannte Robotermaske','RGB-Differenzmaske','Grün: Treffer / Rot: FP / Blau: FN'][col],fontsize=9)
                if col==0:ax.set_title(f'Szene {i}, Kamera {v}',fontsize=9)
    fig.suptitle('Objekt-Sollmasken ausschließlich zur Bewertung · keine Trainingsdaten / kein Training',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.98));fig.savefig(out/'reference_examples.png',dpi=130);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='reference_consistency_001');parser.add_argument('--limit',type=int,default=2000);args=parser.parse_args()
    out=HERE/args.name;out.mkdir(exist_ok=False);started=time.time()
    (out/'observations').mkdir();(out/'evaluation_only').mkdir()
    shutil.copyfile(Path(__file__),out/'capture_source.py');shutil.copyfile(HERE/'reference_evidence.py',out/'evidence_source.py')
    folder=HERE/'run_001/data/validation';data={p.stem:np.load(p,mmap_mode='r') for p in folder.glob('*.npy')}
    old=json.loads((HERE/'uncertainty_001/results.json').read_text())
    hashes={str(p.relative_to(HERE/'run_001')):ensemble.digest(p) for p in folder.glob('*.npy')}
    if hashes!=old['data_sha256']:raise RuntimeError('Existing validation changed')
    indices=np.arange(min(args.limit,len(data['images'])));observations={};oracle={}
    split={int(r['scene']):r['split'] for r in csv.DictReader((HERE/'uncertainty_001/split.csv').open())}
    from scene_data import Generator
    g=Generator();max_physical_deltas={};rgb_checks=[]
    try:
        for j,i in enumerate(indices):
            seed,index=map(int,data['family'][i]);regenerated=g.scene(seed,index)
            deltas=verify_scene(regenerated,{key:values[i] for key,values in data.items() if key!='images'})
            for key,delta in deltas.items():max_physical_deltas[key]=max(max_physical_deltas.get(key,0),delta)
            pair=capture_pair(g)
            rgb_check=verify_rgb_pair(pair['images'],data['images'][i]);rgb_checks.append(dict(scene=int(i),**rgb_check))
            if pair['images'].max()<20 or pair['empty_reference'].mean()<1:raise RuntimeError('Invalid render')
            for key,value in pair.items():
                if key=='images':continue  # Existing exact RGB is referenced, not duplicated.
                target=oracle if key=='object_ids' else observations
                section='evaluation_only' if key=='object_ids' else 'observations'
                if key not in target:target[key]=np.lib.format.open_memmap(out/section/f'{key}.npy',mode='w+',dtype=value.dtype,shape=(len(indices),)+value.shape)
                target[key][j]=value
            if j%100==0:
                for a in list(observations.values())+list(oracle.values()):a.flush()
                (out/'status.json').write_text(json.dumps(dict(stage='capture',completed=j+1,total=len(indices),training_started=False)),encoding='utf-8')
                print(f'Capture {j+1}/{len(indices)}: RGB pairing verified',flush=True)
    finally:g.close()
    for a in list(observations.values())+list(oracle.values()):a.flush()
    np.save(out/'observations/scene_indices.npy',indices)
    ensemble.write_csv(out/'rgb_pairing.csv',rgb_checks)
    segmentation,ranking=evaluate(out,data,observations,oracle,indices,split)
    examples(out,data,observations,oracle,indices,segmentation['threshold'])
    result=dict(training_started=False,optimizer_updates=0,new_model_inference_calls=0,scene_count=len(indices),
                existing_rgb_exactly_reproduced=all(c['exact'] for c in rgb_checks),data_sha256=hashes,
                rgb_pairing=dict(exact_scenes=sum(c['exact'] for c in rgb_checks),
                                 max_channel_delta=max(c['max_channel_delta'] for c in rgb_checks),
                                 max_changed_channels=max(c['changed_channels'] for c in rgb_checks),
                                 policy='max 1/255 per channel and <=32 changed channels across 3 images per scene; original RGB remains inference input'),
                max_physical_deltas=max_physical_deltas,physical_absolute_tolerance=1e-7,
                cached_predictions_sha256={p.name:ensemble.digest(p) for p in (HERE/'uncertainty_001').glob('*predictions.npz')},
                segmentation=segmentation,ranking=ranking,
                split='same previous calibration/held validation; developmental comparison, not independent test',
                rgb_source=str(folder/'images.npy'),
                oracle_policy='Object masks evaluation only; robot masks rendered from object-free scene',
                source_sha256={p.name:ensemble.digest(p) for p in [Path(__file__),HERE/'reference_evidence.py',HERE/'scene_data.py',HERE/'image_consistency.py',HERE/'ensemble_uncertainty.py']},
                elapsed_seconds=time.time()-started)
    result['artifact_sha256']={str(p.relative_to(out)):ensemble.digest(p) for section in ['observations','evaluation_only'] for p in (out/section).glob('*.npy')}
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    (out/'status.json').write_text(json.dumps(dict(stage='complete',training_started=False,scene_count=len(indices))),encoding='utf-8')
    print(json.dumps(dict(status='complete',segmentation=segmentation,ranking=ranking)),flush=True)


if __name__=='__main__':main()
