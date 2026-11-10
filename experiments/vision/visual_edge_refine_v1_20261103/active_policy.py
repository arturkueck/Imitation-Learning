"""Explicit GT-free, untrained acquisition rules and a fixed world-space focus."""
import numpy as np
from geometry import corners,project,edge_samples,visible
from refine import prepare_views,score

def group_focus(boxes,table_height):
    if not boxes:return None
    points=np.concatenate([corners(b) for b in boxes]);low=points.min(0);high=points.max(0)
    low[2]=max(low[2],table_height);high[2]=max(high[2],low[2]+.01)
    center=(low+high)/2;center[2]=max(center[2],table_height+.015)
    radius=float(np.linalg.norm(points-center,axis=1).max())+.005
    return dict(center=center,radius=radius,table_height=float(table_height),source='initial_predicted_cuboid_union_above_known_table')

def overlap(boxes,cameras):
    ratios=[]
    for camera in cameras:
        rect=[]
        for box in boxes:
            uv,z=project(corners(box),camera)
            if np.all(z>.02):rect.append((uv.min(0),uv.max(0)))
        for i,(a,b) in enumerate(rect):
            for c,d in rect[i+1:]:
                area=np.prod(np.maximum(0,np.minimum(b,d)-np.maximum(a,c)))
                ratios.append(float(area/max(1.,min(np.prod(b-a),np.prod(d-c)))))
    return max(ratios,default=0.)

def initial_decision(boxes,groups,images,cameras):
    if not boxes:return dict(action='unresolved',requested_sides=0,reasons=['no_consensus_focus'],features=dict(count=0))
    features=dict(count=len(boxes),max_overlap=overlap(boxes,cameras),max_spread_mm=max(g['spread_mm'] for g in groups),min_support=min(g['support'] for g in groups))
    costs=[score(b,prepare_views(images,cameras,[0,1,2],b,boxes)) for b in boxes]
    features['initial_edge_px']=float(np.mean([c for c in costs if c is not None])) if any(c is not None for c in costs) else None
    reasons=[]
    if features['count']>=3:reasons.append('multiple_objects')
    if features['max_overlap']>.25:reasons.append('predicted_overlap')
    if features['max_spread_mm']>4:reasons.append('ensemble_disagreement')
    if features['min_support']<3:reasons.append('incomplete_ensemble_support')
    confident=(len(boxes)==1 and features['min_support']==3 and features['max_spread_mm']<=1 and features['initial_edge_px'] is not None and features['initial_edge_px']<=.6)
    n=2 if reasons else 0 if confident else 1
    return dict(action=['keep_initial','one_side','two_sides'][n],requested_sides=n,reasons=reasons or ['strong_initial_consistency' if confident else 'verify_initial_geometry'],features=features)

def second_decision(initial,first_quality,completed_sides):
    if len(completed_sides)>=2:return dict(required=False,reasons=['two_side_budget_exhausted'])
    reasons=[]
    if initial['requested_sides']==2:reasons.append('two_sides_requested_initially')
    if not first_quality['supported']:reasons.append('first_side_insufficient')
    return dict(required=bool(reasons),reasons=reasons,observed_sides=list(completed_sides),quality=first_quality)

def quality(objects):
    failures=[]
    for obj in objects:
        g=obj['gate'];chosen=g['heldout_after'] if g['accepted'] else g['heldout_before']
        if g['tracks']<6 or chosen is None or chosen>1.5 or obj['fit']['status'] not in ['fitted','insufficient_geometric_support']:failures.append(obj['object_index'])
    return dict(supported=bool(objects) and not failures,uncertain_objects=failures,criterion='>=6 distinct triangulated points and heldout edge <=1.5px; no optimizer limit')

def prefer_side(checker,start,focus,boxes,base):
    from centered_sweep import orbit_positions,transport_rotation
    p,R=checker.camera_pose(start);scores={}
    for side in ['right','left']:
        pc=orbit_positions(p,focus['center'],base,side,28,2)[-1];rotation=transport_rotation(pc,focus['center'],R)
        f=160/np.tan(np.deg2rad(checker.m.cam_fovy[checker.camera]/2))
        camera=dict(position=pc,rotation=rotation,f=f,cx=160,cy=160,width=320,height=320)
        scores[side]=sum(int(visible(edge_samples(b),camera,boxes).sum()) for b in boxes)
    return max(scores,key=scores.get),dict(source='predicted_visible_edges_only_no_candidate_RGB',scores=scores)
