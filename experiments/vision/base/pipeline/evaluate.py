"""Identical observable-context validation for both A/B model weights."""
import sys
import numpy as np
import torch
from .common import ROOT,EXPERIMENT,check_stop
from .samples import batch_pairs,pair
from .engine import tensors,forward
sys.path.insert(0,str(EXPERIMENT));sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'));sys.path.insert(0,str(ROOT/'experiments/vision/visual_active_v3_20261101'))
from paired_learning import paired_criterion
from learning import decode
from followup_core import scene_error

def evaluate(model,store,run,indices=None,device='cuda'):
    indices=list(range(len(store.records))) if indices is None else list(indices);model.eval();contexts={}
    with torch.inference_mode():
        for kind in ['initial','old','side']:
            losses=[];strata={};parts={};before_errors=[];after_errors=[];matched_errors=[];count_correct=[];recall_hits=0;observable_count=0;newly_visible=0;side_present=0
            for at in range(0,len(indices),8):
                check_stop(run,15);rows=[store[i] for i in indices[at:at+8]];arrays=batch_pairs(rows,'B',epoch=0,seed=0,kind=kind)
                decoded=[];raws=[];availabilities=[]
                for j,a in enumerate(arrays):
                    batch=tensors(a,device);raw,av=forward(model,batch);loss,components,_=paired_criterion(raw,batch,av);d=decode(raw)
                    if not torch.isfinite(loss):raise RuntimeError('Nonfinite validation loss')
                    decoded.append({k:v.cpu().numpy() for k,v in d.items()});raws.append(raw);availabilities.append(av)
                    for k,v in components.items():parts[k]=parts.get(k,0.)+float(v)*len(rows)/2
                # Per-family losses are necessary for arrangement-balanced selection.
                for i,row in enumerate(rows):
                    loss_i=0.
                    for j,a in enumerate(arrays):
                        b=tensors({k:v[i:i+1] for k,v in a.items()},device);o={k:v[i:i+1] for k,v in raws[j].items()};l,_,_=paired_criterion(o,b,availabilities[j][i:i+1]);loss_i+=float(l)/2
                    losses.append(loss_i);strata.setdefault(str(int(row['kind'])),[]).append(loss_i)
                    mask=arrays[0]['target_observable_override'][i]
                    data={k:np.asarray(row[k])[None] for k in ['positions','sizes','rotations','active']}
                    errors=[]
                    for output in decoded:
                        p={k:v[i] for k,v in output.items()};errors.append(scene_error(p,data,0,mask))
                    before_errors.append(errors[0]['error_mm']);after_errors.append(errors[1]['error_mm']);matched_errors.extend(errors[1]['position_mm'])
                    active_predictions=decoded[1]['probability'][i]>=.5;count_correct.append(int(active_predictions.sum())==int(mask.sum()))
                    obs=arrays[0]['active'][i]&(arrays[0]['visibility'][i]>=.05).any(-1);newly_visible+=int((mask&~obs).sum())
                    observable_count+=int(mask.sum())
                    # Recall is based on all observable GT; FP/FN remain in set error.
                    if mask.any() and active_predictions.any():
                        from scipy.optimize import linear_sum_assignment
                        dist=np.linalg.norm(decoded[1]['position'][i,active_predictions,None]-row['positions'][None,mask],axis=-1)
                        ii,jj=linear_sum_assignment(dist);recall_hits+=int((dist[ii,jj]<=.01).sum())
                    side_present+=int(len(pair(row,'B',kind=kind)[2])>1)
            n=max(1,len(indices));contexts[kind]=dict(loss=float(np.mean(losses)),balanced_loss=float(np.mean([np.mean(v) for v in strata.values()])),
                components={k:v/n for k,v in parts.items()},stratum_losses={k:float(np.mean(v)) for k,v in strata.items()},
                before_set_error_mm=float(np.mean(before_errors)),after_set_error_mm=float(np.mean(after_errors)),
                assignment_position_mm=float(np.mean(matched_errors)) if matched_errors else None,count_accuracy=float(np.mean(count_correct)),
                recall_at_10mm=recall_hits/max(1,observable_count),observable_objects=observable_count,newly_visible_objects=newly_visible,
                families=len(indices),families_with_extra_view=side_present)
    return dict(loss=float(np.mean([v['loss'] for v in contexts.values()])),balanced_loss=float(np.mean([v['balanced_loss'] for v in contexts.values()])),contexts=contexts)
