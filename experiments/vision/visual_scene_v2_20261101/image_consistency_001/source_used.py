"""RGB reprojection diagnostic from frozen predictions; no training or test access.

Scoring consumes only RGB, calibrated rays and predictions. Truth is used by the
evaluation layer only. Neutral/dark ambiguous pixels remain unknown: there are
no saved robot masks, and appearance masks are not a reliable segmentation.
"""
from pathlib import Path
import argparse
import csv
import json
import time
import numpy as np
from scipy.ndimage import gaussian_filter, sobel, distance_transform_edt, binary_erosion
import ensemble_uncertainty as ensemble

HERE=Path(__file__).resolve().parent


def camera_from_rays(rays):
    """Recover pixel projection from known ray calibration, not object labels."""
    dirs=rays[...,:3].reshape(-1,3).astype(float)
    y,x=np.mgrid[:20,:20]; u=x.ravel()*8+.5; v=y.ravel()*8+.5
    # Fixed last coefficient avoids a large SVD; lstsq is overdetermined.
    design=np.zeros((len(dirs)*2,9)); target=np.zeros(len(dirs)*2)
    design[::2,:3]=dirs; design[::2,6:]=-u[:,None]*dirs
    design[1::2,3:6]=dirs; design[1::2,6:]=-v[:,None]*dirs
    _,_,vt=np.linalg.svd(design,full_matrices=False); projection=vt[-1].reshape(3,3)
    if np.median(dirs@projection[2])<0: projection=-projection
    projection/=np.linalg.norm(projection[2])
    fitted=dirs@projection.T; fitted=fitted[:,:2]/fitted[:,2,None]
    residual=float(np.max(np.linalg.norm(fitted-np.c_[u,v],axis=1)))
    if residual>.002: raise ValueError(f'Invalid camera calibration: {residual} pixels')
    origins=rays[...,3:].reshape(-1,3).astype(float)*.1+np.array([0.,0.,.8])
    if np.ptp(origins,axis=0).max()>1e-6: raise ValueError('Inconsistent camera origin')
    return dict(origin=origins.mean(0),projection=projection,residual=residual)


def full_directions(camera):
    yy,xx=np.mgrid[:160,:160]
    full=np.stack([xx,yy,np.ones_like(xx)],axis=-1)@np.linalg.inv(camera['projection']).T
    return full/np.linalg.norm(full,axis=-1,keepdims=True)


def ray_box(camera,box):
    origin=(camera['origin']-box['position'])@box['rotation']
    directions=camera.get('directions')
    if directions is None:directions=full_directions(camera)
    directions=directions@box['rotation']; half=np.asarray(box['size'])/2
    parallel=np.abs(directions)<1e-10
    safe=np.where(parallel,1.,directions)
    a=(-half-origin)/safe; b=(half-origin)/safe
    low=np.minimum(a,b); high=np.maximum(a,b)
    low=np.where(parallel,-np.inf,low); high=np.where(parallel,np.inf,high)
    near=low.max(-1); far=high.min(-1)
    outside=(parallel & (np.abs(origin)>half)).any(-1)
    valid=(far>=np.maximum(near,0)) & (near>0) & ~outside
    return np.where(valid,near,np.inf),np.argmax(low,axis=-1)


def rasterize(camera,boxes):
    if not boxes: return np.full((160,160),-1),np.full((160,160),np.inf),np.zeros((160,160),int),[]
    camera=dict(camera,directions=full_directions(camera))
    hits=[ray_box(camera,b) for b in boxes]
    depths=np.asarray([h[0] for h in hits]); winner=depths.argmin(0)
    depth=np.take_along_axis(depths,winner[None],axis=0)[0]
    faces=np.take_along_axis(np.asarray([h[1] for h in hits]),winner[None],axis=0)[0]
    return np.where(np.isfinite(depth),winner,-1),depth,faces,depths


def rgb_evidence(rgb):
    image=rgb.astype(float)/255; chroma=image.max(-1)-image.min(-1)
    # Conservative appearance heuristics, not GT or exact robot/object masks.
    foreground=(chroma>.075)&(image.max(-1)>.12)
    background=(image.min(-1)>.90)&(chroma<.035)
    # Dark/neutral robot, gripper, shadows and gray objects remain ambiguous.
    unknown=~(foreground|background)
    smoothed=gaussian_filter(image,sigma=(.65,.65,0))
    magnitude=np.sqrt(sum(sobel(smoothed,axis=a)**2 for a in [0,1])).max(-1)
    edges=magnitude>.32
    return dict(foreground=foreground,background=background,unknown=unknown,
                edge_distance=distance_transform_edt(~edges),edges=edges)


def expected_edges(owner,faces,index):
    mask=owner==index
    # Outer silhouette only against background; neighboring predicted objects
    # can hide the target's boundary, so do not demand an edge behind them.
    boundary=np.zeros_like(mask)
    for axis in [0,1]:
        for step in [-1,1]:
            other=np.roll(owner,step,axis); face=np.roll(faces,step,axis)
            boundary |= mask & ((other==-1)|((other==index)&(face!=faces)))
    boundary[[0,-1],:]=False;boundary[:,[0,-1]]=False
    return boundary


def image_features(images,cameras,groups):
    per_group=[[] for _ in groups]; debug=[]
    for rgb,camera in zip(images,cameras):
        evidence=rgb_evidence(rgb); owner,depth,faces,raw_depths=rasterize(camera,groups)
        debug.append((owner,faces,evidence))
        for i,group in enumerate(groups):
            visible=owner==i; pixels=int(visible.sum()); projected=int(np.isfinite(raw_depths[i]).sum())
            boundary=expected_edges(owner,faces,i)
            # Only observable appearance supports RGB edge matching. Neutral
            # pixels are unknown, rather than silently evidence of agreement.
            checkable=visible & ~evidence['unknown']
            edge_checkable=boundary & ~evidence['unknown']
            valid=pixels>=9 and int(checkable.sum())>=4 and int(edge_checkable.sum())>=3
            edge_error=float(np.mean(np.minimum(evidence['edge_distance'][edge_checkable],8))/8) if valid else None
            contradiction=float(evidence['background'][visible].mean()) if pixels else None
            per_group[i].append(dict(valid=valid,visible_pixels=pixels,projected_pixels=projected,
                                     predicted_visible_fraction=pixels/max(1,projected),
                                     evidence_fraction=float(checkable.sum()/max(1,pixels)),
                                     edge_error=edge_error,background_contradiction=contradiction))
    features=[]
    for views in per_group:
        valid=[v for v in views if v['valid']]
        # Require >=2 usable views to resolve 3D ambiguity. Unknown is explicitly
        # output and ranked as a request for evidence, not a proven wrong pose.
        unknown=len(valid)<2
        edge=float(np.mean([v['edge_error'] for v in valid])) if valid else 1.
        contradiction=float(np.max([v['background_contradiction'] for v in valid])) if valid else 0.
        score=.5*edge+.5*contradiction
        features.append(dict(image_score=score,image_unknown=unknown,usable_views=len(valid),
                             edge_error=edge,background_contradiction=contradiction,
                             predicted_occlusion=float(np.mean([1-v['predicted_visible_fraction'] for v in views if v['projected_pixels']])) if any(v['projected_pixels'] for v in views) else 1.,
                             evidence_fraction=float(np.mean([v['evidence_fraction'] for v in views]))))
    return features,debug,per_group


def percentile(values,reference):
    return np.searchsorted(np.sort(reference),values,side='right')/max(1,len(reference))


def rank_scores(rows,calibration):
    missing=np.array([r['support']<3 for r in rows],float)
    spread=percentile([r['spread_mm'] for r in rows],[r['spread_mm'] for r in calibration])
    corner=percentile([r['corner_disagreement_mm'] for r in rows],[r['corner_disagreement_mm'] for r in calibration])
    size=percentile([r['size_spread_mm'] for r in rows],[r['size_spread_mm'] for r in calibration])
    image=percentile([r['image_score'] for r in rows],[r['image_score'] for r in calibration])
    unknown=np.array([r['image_unknown'] for r in rows],float)
    # Fixed recipes, no fitted network, no labels in percentile normalization.
    return dict(ensemble=2*missing+spread,corner=2*missing+corner,size=2*missing+size,
                image=2*missing+image+.5*unknown,
                hybrid25=2*missing+.75*spread+.25*(image+.5*unknown),
                hybrid50=2*missing+.5*spread+.5*(image+.5*unknown),
                hybrid75=2*missing+.25*spread+.75*(image+.5*unknown))


def top_budget(rows,scores,reject_fraction):
    # Equal alert budgets for offline comparison; deterministic ties by row ID.
    count=int(round(len(rows)*reject_fraction)); order=np.argsort(-scores,kind='stable')
    flagged=np.zeros(len(rows),bool);flagged[order[:count]]=True
    bad=np.array([r['bad'] for r in rows]); accepted=~flagged
    return dict(predictions=len(rows),flagged=int(flagged.sum()),bad=int(bad.sum()),
                detected_bad=int((bad&flagged).sum()),accepted_bad=int((bad&accepted).sum()),
                flagged_bad_fraction=float((bad&flagged).sum()/max(1,bad.sum())),
                accepted_bad_fraction=float((bad&accepted).sum()/max(1,accepted.sum())),
                flag_mask=flagged)


def public_metrics(metric): return {k:v for k,v in metric.items() if k!='flag_mask'}


def bootstrap_delta(rows,base_flags,new_flags,replicates=1000):
    scenes=sorted(set(r['scene'] for r in rows)); sums=[]
    for scene in scenes:
        ids=[i for i,r in enumerate(rows) if r['scene']==scene]
        bad=np.array([rows[i]['bad'] for i in ids],int)
        sums.append([bad.sum(),(bad*base_flags[ids]).sum(),(bad*new_flags[ids]).sum()])
    sums=np.asarray(sums);rng=np.random.default_rng(61102)
    draws=sums[rng.integers(0,len(sums),(replicates,len(sums)))].sum(1)
    delta=(draws[:,2]-draws[:,1])/np.maximum(1,draws[:,0])
    return np.percentile(delta,[2.5,97.5]).tolist()


def make_plots(out,arm,rows,scores,selected):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4.5))
    for name,label in [('ensemble','Seed-Streuung'),('corner','Eckenstreuung'),('size','Größenstreuung'),('image','Bildkonsistenz'),(selected,'Kombination (Kalibrierung)')]:
        budgets=np.linspace(0,.3,61); metrics=[top_budget(rows,scores[name],b) for b in budgets]
        axes[0].plot(budgets*100,[100*m['flagged_bad_fraction'] for m in metrics],label=label)
        axes[1].plot(budgets*100,[100*m['accepted_bad_fraction'] for m in metrics],label=label)
    matched=[r for r in rows if r['position_error_mm'] is not None]
    for kind,color in [(0,'tab:blue'),(1,'tab:orange'),(2,'tab:red'),(3,'tab:green')]:
        part=[r for r in matched if r['kind']==kind]
        axes[2].scatter([r['image_score'] for r in part],[r['position_error_mm'] for r in part],s=7,alpha=.25,c=color,label=['Verstreut','Gemischt','Turm','Wand'][kind])
    axes[2].axhline(10,c='black',ls='--')
    axes[0].set(xlabel='Zurückgestellte Vorhersagen [%]',ylabel='Erkannte Fehler [%]',title='Gleiches Aufnahme-/Prüfbudget')
    axes[1].set(xlabel='Zurückgestellte Vorhersagen [%]',ylabel='Fehler unter beibehaltenen [%]',title='Verbleibende Fehler')
    axes[2].set(xlabel='Bildwiderspruch (heuristisch)',ylabel='Positionsfehler [mm]',title='Keine kalibrierte Fehlerwahrscheinlichkeit')
    axes[0].legend(fontsize=8);axes[2].legend(fontsize=8)
    for ax in axes: ax.grid(alpha=.25)
    fig.suptitle(f'{arm} · zurückgehaltene Validierung · keine unabhängige Schlussprüfung')
    fig.tight_layout();fig.savefig(out/f'{arm}_comparison.png',dpi=150);fig.savefig(out/f'{arm}_comparison.svg');plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='image_consistency_001');args=parser.parse_args()
    started=time.time();out=HERE/args.name;out.mkdir(exist_ok=False)
    original=HERE/'uncertainty_001'; datafolder=HERE/'run_001/data/validation'
    data={p.stem:np.load(p,mmap_mode='r') for p in datafolder.glob('*.npy')}
    old=json.loads((original/'results.json').read_text())
    # Bind cached model outputs and the calibration to exactly the prior inputs.
    data_hashes={str(p.relative_to(HERE/'run_001')):ensemble.digest(p) for p in datafolder.glob('*.npy')}
    if data_hashes!=old['data_sha256']:raise RuntimeError('Validation data changed')
    split={int(r['scene']):r['split'] for r in csv.DictReader((original/'split.csv').open())}
    input_hashes={p.name:ensemble.digest(p) for p in original.glob('*predictions.npz')}
    # Never open weights or import torch: use only cached, frozen predictions.
    outputs={}; details={}; examples={};max_residual=0.
    all_cameras=[]
    for i,rays in enumerate(data['rays']):
        cams=[camera_from_rays(r) for r in rays];all_cameras.append(cams)
        max_residual=max(max_residual,max(c['residual'] for c in cams))
    for arm in ['fixed','fixed_wrist']:
        predictions=[dict(np.load(original/f'{arm}_seed{s}_predictions.npz')) for s in [1,2,3]]
        rows=[];per_view=[];gt_diagnostics=[]
        for i in range(len(data['images'])):
            groups=ensemble.group_predictions([{k:v[i] for k,v in p.items()} for p in predictions])
            views=2 if arm=='fixed' else 3
            features,_,view_features=image_features(data['images'][i,:views],all_cameras[i][:views],groups)
            rr,_=ensemble.score_scene(groups,data,i,arm)
            for j,(row,feature) in enumerate(zip(rr,features)):
                row.update(feature);row['split']=split[i];rows.append(row)
                for view,v in enumerate(view_features[j]):per_view.append(dict(scene=i,group=j,view=view,**v))
            # GT diagnostic is explicitly separate and NEVER used in scoring.
            for row in rr:
                gt=row['gt_index']
                if gt>=0:gt_diagnostics.append(dict(scene=i,group=row['group'],truth_visibility=float(data['visibility'][i,gt,:views].max()),split=split[i]))
            if i%500==0:print(f'{arm}: {i}/{len(data["images"])} scenes',flush=True)
        cal=[r for r in rows if r['split']=='calibration'];held=[r for r in rows if r['split']=='held_validation']
        cal_scores=rank_scores(cal,cal);held_scores=rank_scores(held,cal)
        candidates=['hybrid25','hybrid50','hybrid75']
        selected=max(candidates,key=lambda name:sum(top_budget(cal,cal_scores[name],b)['detected_bad'] for b in [.05,.10]))
        summary=dict(selected_recipe=selected,calibration_recipe_objectives={name:sum(top_budget(cal,cal_scores[name],b)['detected_bad'] for b in [.05,.10]) for name in candidates},budgets={},by_arrangement={})
        for budget in [.05,.10,.20]:
            key=f'{int(budget*100)}pct';metrics={name:top_budget(held,score,budget) for name,score in held_scores.items()}
            summary['budgets'][key]={name:public_metrics(value) for name,value in metrics.items()}
            summary['budgets'][key]['hybrid_vs_ensemble_cluster_bootstrap95']=bootstrap_delta(held,metrics['ensemble']['flag_mask'],metrics[selected]['flag_mask'])
        for kind in range(4):
            ids=[i for i,r in enumerate(held) if r['kind']==kind];part=[held[i] for i in ids]
            # Per-arrangement equal budgets; no threshold refitting on labels.
            summary['by_arrangement'][str(kind)]={name:public_metrics(top_budget(part,scores[ids],.10)) for name,scores in held_scores.items()}
        truth_visibility={(r['scene'],r['group']):r['truth_visibility'] for r in gt_diagnostics}
        for tag,condition in [('occluded',lambda x:x<.8),('well_visible',lambda x:x>=.8)]:
            ids=[i for i,r in enumerate(held) if (r['scene'],r['group']) in truth_visibility and condition(truth_visibility[(r['scene'],r['group'])])]
            part=[held[i] for i in ids]
            summary[tag]={name:public_metrics(top_budget(part,held_scores[name][ids],.10)) for name in ['ensemble','image',selected]}
        common=[i for i,r in enumerate(held) if r['support']==3 and r['spread_mm']<=3 and r['bad']]
        flags=top_budget(held,held_scores[selected],.10)['flag_mask']
        base_flags=top_budget(held,held_scores['ensemble'],.10)['flag_mask']
        summary['shared_error_subset']=dict(definition='support=3, spread<=3mm, bad position/FP',count=len(common),hybrid_flagged=int(flags[common].sum()),ensemble_flagged=int(base_flags[common].sum()))
        summary['unknown_image_evidence_fraction']=float(np.mean([r['image_unknown'] for r in held]))
        for name,score in rank_scores(rows,cal).items():
            for r,s in zip(rows,score):r[f'rank_{name}']=float(s)
        ensemble.write_csv(out/f'{arm}_objects.csv',rows);ensemble.write_csv(out/f'{arm}_views.csv',per_view)
        make_plots(out,arm,held,held_scores,selected)
        outputs[arm]=summary;details[arm]=held
        examples[arm]=dict(rows=held,scores=held_scores,selected=selected,predictions=predictions)
    report=dict(training_started=False,optimizer_updates=0,model_inference_calls=0,
                dataset='same 2000 validation scenes, same disjoint calibration/held families; no reserved tests',
                calibration_max_reprojection_residual_pixels=max_residual,results=outputs,
                data_sha256=data_hashes,prediction_sha256=input_hashes,source_sha256=ensemble.digest(Path(__file__)),
                limitations=['existing validation used for checkpoint selection; exploratory only',
                             'no saved exact robot/object masks; dark/neutral pixels unknown, bright-neutral heuristic can fail',
                             'predicted boxes z-buffer each other; real unpredicted occluders are not modeled',
                             'equal-budget curves use held score quantiles without labels; not deployed thresholds',
                             'RGB scoring detects disagreement, not guaranteed correctness or collision-free space'],
                elapsed_seconds=time.time()-started)
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    qualitative(out,data,all_cameras,examples)
    print(json.dumps(dict(status='complete',elapsed_seconds=time.time()-started)),flush=True)


def qualitative(out,data,cameras,examples):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    item=examples['fixed_wrist'];rows=item['rows'];scores=item['scores'];selected=item['selected']
    flags=top_budget(rows,scores[selected],.10)['flag_mask'];base=top_budget(rows,scores['ensemble'],.10)['flag_mask']
    categories=[('Zusätzlich erkannt',lambda i:rows[i]['bad'] and flags[i] and not base[i]),
                ('Gemeinsamer Fehler übersehen',lambda i:rows[i]['bad'] and not flags[i] and rows[i]['support']==3),
                ('Unnötig zurückgestellt',lambda i:not rows[i]['bad'] and flags[i])]
    selected_rows=[];seen=set()
    for label,condition in categories:
        candidates=[i for i in range(len(rows)) if condition(i)]
        candidates.sort(key=lambda i:rows[i]['image_score'],reverse=True)
        for i in candidates:
            if rows[i]['scene'] in seen:continue
            selected_rows.append((label,rows[i]));seen.add(rows[i]['scene'])
            if sum(x[0]==label for x in selected_rows)>=2:break
    fig,axes=plt.subplots(len(selected_rows),3,figsize=(10,3.1*len(selected_rows)),squeeze=False)
    metadata=[]
    for panel,(label,row) in enumerate(selected_rows):
        scene=row['scene'];groups=ensemble.group_predictions([{k:v[scene] for k,v in p.items()} for p in item['predictions']]);box=groups[row['group']]
        for view in range(3):
            ax=axes[panel,view];ax.imshow(data['images'][scene,view]);camera=cameras[scene][view]
            for shape,color in [(box,'orange')]+([(dict(position=data['positions'][scene,row['gt_index']],size=data['sizes'][scene,row['gt_index']],rotation=data['rotations'][scene,row['gt_index']]),'cyan')] if row['gt_index']>=0 else []):
                points=ensemble.corners(shape);p=(points-camera['origin'])@camera['projection'].T
                if (p[:,2]<=0).any():continue
                pixels=p[:,:2]/p[:,2,None]
                for a in range(8):
                    for bit in [1,2,4]:
                        b=a^bit
                        if a<b:ax.plot(pixels[[a,b],0],pixels[[a,b],1],c=color,lw=1)
            ax.set(xlim=(0,159),ylim=(159,0));ax.axis('off')
            if view==0:
                error='FP' if row['position_error_mm'] is None else f"{row['position_error_mm']:.1f} mm"
                ax.set_title(f"{label} · Szene {scene}\nFehler {error}, Streuung {row['spread_mm']:.1f} mm",fontsize=9)
        metadata.append(dict(category=label,**row))
    fig.suptitle('Ausgewählte Diagnosebeispiele, keine Zufallsstichprobe · Orange: Vorhersage, Cyan: Soll\nDrahtkanten zeigen auch verdeckte Flächen; Bewertung nutzt sichtbare Vorhersageflächen',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/'qualitative_examples.png',dpi=140);plt.close(fig)
    ensemble.write_csv(out/'qualitative_examples.csv',metadata)


if __name__=='__main__':main()
