"""Prefix-only analysis of acquired outbound sweeps; return images are display-only."""
import numpy as np
from tracking import track
from refine import fit_one,prepare_views,gate,score

def analyze(images,cameras,segments,initial,reference,anchor_images,anchor_cameras):
    fit_ids=[];heldout_ids=[];tracks=[];points=[];rejections={}
    for ids in segments:
        fit=[i for local,i in enumerate(ids) if local>0 and local%3!=0]
        held=[i for local,i in enumerate(ids) if local>0 and local%3==0]
        fit_ids+=fit;heldout_ids+=held
        tr,cloud,stats=track(images,cameras,fit,initial);offset=len(tracks)
        for p in cloud:p['track']+=offset
        tracks+=tr;points+=cloud
        for key,value in stats.items():rejections[key]=rejections.get(key,0)+value
    # A corner lost/reseeded several times must not count as independent support.
    distinct=[]
    for p in sorted(points,key=lambda p:p['reprojection_px']):
        if not any(p['object_index']==q['object_index'] and np.linalg.norm(p['point']-q['point'])<.002 for q in distinct):distinct.append(p)
    raw=[];adopted=[];objects=[]
    for obj,(original,prior) in enumerate(zip(initial,reference)):
        cloud=np.array([p['point'] for p in distinct if p['object_index']==obj]).reshape(-1,3)
        fit=fit_one(prior,reference,images,cameras,fit_ids,cloud)
        held=prepare_views(images,cameras,heldout_ids,prior,reference);anchors=prepare_views(anchor_images,anchor_cameras,[0,1,2],prior,reference)
        decision=gate(prior,fit['candidate'],held,anchors,len(cloud))
        if fit['status']!='fitted':decision['accepted']=False;decision['reasons'].append(fit['status'])
        original_views=prepare_views(anchor_images,anchor_cameras,[0,1,2],original,initial)
        original_score=score(original,original_views);candidate_score=score(fit['candidate'],original_views)
        if original_score is None or candidate_score is None or candidate_score>original_score+.25:
            decision['accepted']=False;decision['reasons'].append('original_anchors_degraded')
        if np.linalg.norm(fit['candidate']['position']-original['position'])>.015:
            decision['accepted']=False;decision['reasons'].append('total_position_change_too_large')
        raw.append(fit['candidate']);adopted.append(fit['candidate'] if decision['accepted'] else prior)
        objects.append(dict(object_index=obj,fit=fit,gate=decision))
    return dict(raw=raw,adopted=adopted,objects=objects,tracks=tracks,triangulated_points=distinct,raw_triangulated_count=len(points),
        fitting_frames=fit_ids,heldout_frames=heldout_ids,rejections=rejections)
