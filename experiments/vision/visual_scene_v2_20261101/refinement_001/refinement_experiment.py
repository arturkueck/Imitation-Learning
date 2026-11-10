"""Small preregistered fresh-scene geometric refinement experiment. No training."""
from pathlib import Path
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
os.environ.setdefault('OMP_NUM_THREADS','4')
import argparse,json,time,shutil
import numpy as np
import ensemble_uncertainty as ensemble
import image_consistency as geometry
from reference_capture import capture_pair
from box_refinement import CONFIG,refine

HERE=Path(__file__).resolve().parent
PLAN=dict(development_seed=9301101,evaluation_seed=9301102,
          development_scenes_per_kind=2,evaluation_scenes_per_kind=4,
          kinds=['scattered','mixed','tower','wall'],min_objects=2,max_scene_attempts=1000,
          camera_variant='fixed_wrist',model_seeds=[1,2,3],config=CONFIG,
          metrics=['paired position error','paired corner RMSE','size MAE','recall at 10mm','worsened objects'],
          updates='geometric parameters only; no neural optimizer',
          selection='all eligible scenes in deterministic order until each kind quota; no selection by model error')


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def collect(out):
    from scene_data import Generator,stack
    g=Generator();rows=[];references=[];robots=[];splits=[];families=[]
    try:
        for split,seed,quota in [('development',PLAN['development_seed'],PLAN['development_scenes_per_kind']),('evaluation',PLAN['evaluation_seed'],PLAN['evaluation_scenes_per_kind'])]:
            counts=[0]*4
            for index in range(PLAN['max_scene_attempts']):
                row=g.scene(seed,index);kind=int(row['kind'])
                if int(row['count'])<PLAN['min_objects'] or counts[kind]>=quota:continue
                pair=capture_pair(g)
                if not np.array_equal(pair['images'],row['images']):raise RuntimeError('Capture RGB differs from actual model input')
                if row['images'].max()<20 or row['images'].mean()<1:raise RuntimeError('Invalid fresh RGB')
                counts[kind]+=1;rows.append(row);references.append(pair['empty_reference']);robots.append(pair['robot_mask']);splits.append(split);families.append([seed,index])
                if min(counts)>=quota:break
            if min(counts)<quota:raise RuntimeError(f'Insufficient scenes: {split}/{counts}')
    finally:g.close()
    data=stack(rows)
    np.savez_compressed(out/'observations.npz',images=data['images'],rays=data['rays'],references=np.asarray(references),robot_masks=np.asarray(robots),families=np.asarray(families),splits=np.asarray(splits))
    np.savez_compressed(out/'evaluation_only.npz',**{k:v for k,v in data.items() if k not in ['images','rays']})
    return data,np.asarray(references),np.asarray(robots),splits


def paired_metrics(before,after,data,index):
    rows,_=ensemble.score_scene(before,data,index,'fixed_wrist')
    output=[]
    for row,old,new in zip(rows,before,after):
        target=row['gt_index'];item=dict(scene=index,group=row['group'],kind=int(data['kind'][index]),gt_index=target,support=old['support'])
        item.update({f'{metric}_{when}_{suffix}':None for metric,suffix in [('position','mm'),('corner','mm'),('size','mae_mm')] for when in ['before','after']})
        item['position_change_mm']=None
        if target>=0:
            truth=dict(position=data['positions'][index,target],size=data['sizes'][index,target],rotation=data['rotations'][index,target])
            for label,box in [('before',old),('after',new)]:
                item[f'position_{label}_mm']=float(np.linalg.norm(box['position']-truth['position'])*1000)
                item[f'corner_{label}_mm']=ensemble.corner_distance(box,truth)*1000
                item[f'size_{label}_mae_mm']=float(np.mean(np.abs(np.sort(box['size'])-np.sort(truth['size'])))*1000)
            item['position_change_mm']=item['position_after_mm']-item['position_before_mm']
        output.append(item)
    # Re-match independently as a secondary detection metric, not as the paired
    # error comparison above: paired GT identities remain frozen from baseline.
    after_rows,scene=ensemble.score_scene(after,data,index,'fixed_wrist')
    gt_count=scene['observable_gt']
    return output,dict(observable_gt=gt_count,
                       recall10_before=sum(r['gt_index']>=0 and r['position_error_mm']<=10 for r in rows)/max(1,gt_count),
                       recall10_after=sum(r['gt_index']>=0 and r['position_error_mm']<=10 for r in after_rows)/max(1,gt_count),
                       false_positive_after=scene['false_positive_groups'],unmatched_gt_after=scene['unmatched_gt'])


def summary(rows,scenes):
    matched=[r for r in rows if r['gt_index']>=0]
    if not matched:return dict(objects=0)
    result=dict(objects=len(matched),scenes=len(scenes),
                improved_over_1mm=sum(r['position_change_mm']< -1 for r in matched),
                worsened_over_1mm=sum(r['position_change_mm']>1 for r in matched),
                essentially_unchanged=sum(abs(r['position_change_mm'])<=1 for r in matched),
                updated_scenes=sum(s['updated'] for s in scenes),ambiguous_scenes=sum(s['ambiguous'] for s in scenes),
                recall10_before=float(np.mean([s['recall10_before'] for s in scenes])),
                recall10_after=float(np.mean([s['recall10_after'] for s in scenes])))
    for metric in ['position','corner','size']:
        suffix='mae_mm' if metric=='size' else 'mm'
        for when in ['before','after']:result[f'{metric}_{when}_mean_mm']=float(np.mean([r[f'{metric}_{when}_{suffix}'] for r in matched]))
    scene_ids=sorted(set(r['scene'] for r in matched));totals=[]
    for scene in scene_ids:
        part=[r for r in matched if r['scene']==scene];totals.append([sum(r['position_change_mm'] for r in part),len(part)])
    rng=np.random.default_rng(9301103);a=np.asarray(totals);samples=a[rng.integers(0,len(a),(2000,len(a)))].sum(1)
    result['paired_position_delta_bootstrap95_mm']=np.percentile(samples[:,0]/samples[:,1],[2.5,97.5]).tolist()
    return result


def plot(out,rows,scenes,examples,data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matched=[r for r in rows if r['split']=='evaluation' and r['gt_index']>=0]
    fig,axes=plt.subplots(1,3,figsize=(14,4.2))
    for kind,label in enumerate(PLAN['kinds']):
        part=[r for r in matched if r['kind']==kind]
        axes[0].scatter([r['position_before_mm'] for r in part],[r['position_after_mm'] for r in part],label=label,alpha=.7,s=22)
    limit=max([r['position_before_mm'] for r in matched]+[r['position_after_mm'] for r in matched]+[10])
    axes[0].plot([0,limit],[0,limit],'k--');axes[0].set(xlabel='Position vorher [mm]',ylabel='Position nachher [mm]',title='Unter Diagonale = verbessert');axes[0].legend(fontsize=8)
    for x,metric in enumerate(['position','corner','size']):
        suffix='mae_mm' if metric=='size' else 'mm'
        axes[1].bar(x-.17,np.mean([r[f'{metric}_before_{suffix}'] for r in matched]),width=.34,color='tab:orange',label='Vorher' if x==0 else None)
        axes[1].bar(x+.17,np.mean([r[f'{metric}_after_{suffix}'] for r in matched]),width=.34,color='tab:blue',label='Nachher' if x==0 else None)
    axes[1].set(xticks=[0,1,2],xticklabels=['Position','Ecken-RMSE','Größe MAE'],ylabel='Mittlerer Fehler [mm]');axes[1].legend()
    part=[s for s in scenes if s['split']=='evaluation']
    axes[2].scatter([s['objective_before'] for s in part],[s['objective_after'] for s in part]);axes[2].plot([0,1],[0,1],'k--')
    axes[2].set(xlabel='Bildziel vorher',ylabel='Bildziel nachher',title='Bildverbesserung ≠ 3D-Verbesserung')
    for ax in axes:ax.grid(alpha=.25)
    fig.suptitle('Frischer begrenzter Diagnosepilot · eingefrorene Modelle · kein Training');fig.tight_layout();fig.savefig(out/'paired_quality.png',dpi=150);plt.close(fig)
    candidates=sorted(matched,key=lambda r:r['position_change_mm'])
    selected=[candidates[0],candidates[-1]];fig,axes=plt.subplots(2,3,figsize=(10,7))
    for row_index,row in enumerate(selected):
        scene=row['scene'];before,after=examples[scene];index=row['group'];truth_id=row['gt_index']
        truth=dict(position=data['positions'][scene,truth_id],size=data['sizes'][scene,truth_id],rotation=data['rotations'][scene,truth_id])
        for view in range(3):
            ax=axes[row_index,view];ax.imshow(data['images'][scene,view]);camera=geometry.camera_from_rays(data['rays'][scene,view])
            for box,color in [(before[index],'orange'),(after[index],'magenta'),(truth,'cyan')]:
                p=geometry.camera_from_rays(data['rays'][scene,view]);xyz=(ensemble.corners(box)-p['origin'])@p['projection'].T;uv=xyz[:,:2]/xyz[:,2,None]
                for a in range(8):
                    for bit in [1,2,4]:
                        b=a^bit
                        if a<b:ax.plot(uv[[a,b],0],uv[[a,b],1],c=color,lw=1)
            ax.set(xlim=(0,159),ylim=(159,0));ax.axis('off')
            if view==0:ax.set_title(f"Szene {scene}: {row['position_before_mm']:.1f} → {row['position_after_mm']:.1f} mm",fontsize=10)
    fig.suptitle('Größte Verbesserung / größte Verschlechterung · bewusst ausgewählt\nOrange vorher · Magenta nachher · Cyan Soll (nur Auswertung)');fig.tight_layout(rect=(0,0,1,.93));fig.savefig(out/'best_worst_examples.png',dpi=140);plt.close(fig)


def main():
    import torch
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='refinement_001');args=parser.parse_args()
    out=HERE/args.name;out.mkdir(exist_ok=False);started=time.time()
    save(out/'locked_plan.json',PLAN);plan_hash=ensemble.digest(out/'locked_plan.json')
    for source in [Path(__file__),HERE/'box_refinement.py',HERE/'reference_evidence.py',HERE/'reference_capture.py']:
        shutil.copyfile(source,out/source.name)
    torch.set_num_threads(4);torch.manual_seed(9301101);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.enable_flash_sdp(False);torch.backends.cuda.enable_mem_efficient_sdp(False)
    data,refs,robots,splits=collect(out);save(out/'status.json',dict(stage='inference',training_started=False))
    selection=json.loads((HERE/'run_001/selection.json').read_text())['models'];model_source=ensemble.load_source(HERE/'run_001/source/model_prototype.py','frozen_refine_model');learning=ensemble.load_source(HERE/'run_001/source/learning.py','frozen_refine_learning')
    predictions=[];hashes={};device='cuda' if torch.cuda.is_available() else 'cpu'
    with torch.inference_mode():
        for seed in [1,2,3]:
            row=next(r for r in selection if r['seed']==seed and r['arm']=='fixed_wrist');path=HERE/'run_001/checkpoints'/f'fixed_wrist_seed{seed}_best.pth'
            if ensemble.digest(path)!=row['sha256']:raise RuntimeError('Checkpoint mismatch')
            hashes[path.name]=row['sha256'];model=model_source.ScenePerception().to(device);model.load_state_dict(torch.load(path,map_location=device,weights_only=False)['model']);model.eval();chunks={}
            for start in range(0,len(splits),8):
                batch={k:torch.as_tensor(data[k][start:start+8],device=device) for k in ['images','rays']}
                raw,_=learning.run_model(model,batch,'fixed_wrist');decoded=learning.decode(raw)
                for k,v in decoded.items():chunks.setdefault(k,[]).append(v.cpu().numpy())
            pred={k:np.concatenate(v) for k,v in chunks.items()};predictions.append(pred);np.savez_compressed(out/f'seed{seed}_predictions.npz',**pred);del model
    rows=[];scenes=[];examples={}
    for i,split in enumerate(splits):
        before=ensemble.group_predictions([{k:v[i] for k,v in p.items()} for p in predictions]);cameras=[geometry.camera_from_rays(r) for r in data['rays'][i]]
        after,report=refine(data['images'][i],refs[i],robots[i],cameras,before,PLAN['config'])
        paired,scene=paired_metrics(before,after,data,i)
        for row in paired:row['split']=split;rows.append(row)
        scene.update(report,scene=i,kind=int(data['kind'][i]),split=split);scenes.append(scene);examples[i]=(before,after)
        serial=lambda groups:[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items()} for g in groups]
        save(out/f'scene_{i:03d}.json',dict(family=data['family'][i].tolist(),split=split,before=serial(before),after=serial(after),report=scene))
        save(out/'status.json',dict(stage='geometric_optimization',completed=i+1,total=len(splits),training_started=False,neural_optimizer_updates=0))
        print(f'{i+1}/{len(splits)} {split}: image gain={report["objective_gain"]:.4f}; ambiguous={report["ambiguous"]}',flush=True)
    for name,sha in hashes.items():
        if ensemble.digest(HERE/'run_001/checkpoints'/name)!=sha:raise RuntimeError('Checkpoint changed')
    if ensemble.digest(out/'locked_plan.json')!=plan_hash:raise RuntimeError('Plan changed')
    result=dict(training_started=False,neural_optimizer_updates=0,geometric_objective_calls=sum(s['objective_calls'] for s in scenes),
                plan_sha256=plan_hash,checkpoint_sha256=hashes,
                development=summary([r for r in rows if r['split']=='development'],[s for s in scenes if s['split']=='development']),
                evaluation=summary([r for r in rows if r['split']=='evaluation'],[s for s in scenes if s['split']=='evaluation']),
                by_kind={str(k):summary([r for r in rows if r['split']=='evaluation' and r['kind']==k],[s for s in scenes if s['split']=='evaluation' and s['kind']==k]) for k in range(4)},
                limitations=['small balanced fresh simulation pilot, not real-world validation','no objects added/removed; count correction not implemented','ambiguity flag is heuristic, not a calibrated probability','paired errors lock baseline GT identities; recall is independently rematched'],
                elapsed_seconds=time.time()-started)
    ensemble.write_csv(out/'objects.csv',rows);ensemble.write_csv(out/'scenes.csv',[{k:v for k,v in s.items() if not isinstance(v,dict)} for s in scenes]);plot(out,rows,scenes,examples,data)
    save(out/'results.json',result);save(out/'status.json',dict(stage='complete',training_started=False,neural_optimizer_updates=0));print(json.dumps(result),flush=True)


if __name__=='__main__':main()
