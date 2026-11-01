"""Compare oriented cuboids and render transparent diagnostic overlays.

Input: JSON with ground_truth/predictions lists. Each box has center [m], size
(full edge lengths [m]), rotation (proper 3x3 local-to-world matrix), optional id.
No registration, fitting or GT-derived replacement of predicted dimensions.
--demo produces explicitly synthetic, hand-written predictions, NOT model results.
"""
from pathlib import Path
import argparse, itertools, json
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Patch

SIGNS=np.array(list(itertools.product((-1,1),repeat=3)))
FACES=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]


def validate(box):
    c=np.asarray(box['center'],dtype=float);s=np.asarray(box['size'],dtype=float)
    r=np.asarray(box['rotation'],dtype=float)
    if c.shape!=(3,) or s.shape!=(3,) or r.shape!=(3,3):raise ValueError('Invalid box dimensions')
    if not all(np.isfinite(a).all() for a in (c,s,r)) or not (s>0).all():raise ValueError('Invalid box numbers')
    if not np.allclose(r.T@r,np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(r),1,atol=1e-5):
        raise ValueError('Rotation must be proper orthonormal local-to-world matrix')
    return c,s,r


def corners(box):
    c,s,r=validate(box)
    return (SIGNS*s/2)@r.T+c


def planes(box):
    c,s,r=validate(box)
    normals=np.r_[r.T,-r.T]
    offsets=normals@c+np.r_[s/2,s/2]
    return normals,offsets


def iou3d(a,b):
    """Convex intersection from halfspaces; exact geometry up to floating precision."""
    na,ba=planes(a);nb,bb=planes(b);n=np.r_[na,nb];d=np.r_[ba,bb]
    ids=np.array(list(itertools.combinations(range(12),3)))
    matrices=n[ids];valid=np.abs(np.linalg.det(matrices))>1e-10
    if not valid.any():return 0.
    vertices=np.linalg.solve(matrices[valid],d[ids[valid]][...,None])[...,0]
    vertices=vertices[(vertices@n.T<=d+1e-9).all(axis=1)]
    vertices=np.unique(np.round(vertices,10),axis=0)
    if len(vertices)<4 or np.linalg.matrix_rank(vertices-vertices[0],tol=1e-9)<3:return 0.
    intersection=float(ConvexHull(vertices).volume)
    va=float(np.prod(a['size']));vb=float(np.prod(b['size']))
    intersection=min(intersection,va,vb)
    return float(np.clip(intersection/(va+vb-intersection),0,1))


def rotation_error(a,b):
    """Box-symmetry-aware angle for given local side-length convention."""
    _,size,ra=validate(a);_,_,rb=validate(b);best=180.
    for perm in itertools.permutations(range(3)):
        if not np.allclose(size[list(perm)],size,rtol=1e-6,atol=1e-8):continue
        for signs in itertools.product((-1,1),repeat=3):
            symmetry=np.eye(3)[:,perm]*np.array(signs)
            if np.linalg.det(symmetry)<.5:continue
            cosine=np.clip((np.trace((ra@symmetry).T@rb)-1)/2,-1,1)
            best=min(best,float(np.degrees(np.arccos(cosine))))
    return best


def compare(gt,pred,gate_m=.10):
    for box in gt+pred:validate(box)
    pairs=[];used_gt=set();used_pred=set()
    if gt and pred:
        distances=np.array([[np.linalg.norm(np.array(g['center'])-p['center']) for p in pred] for g in gt])
        gi,pi=linear_sum_assignment(distances)
        for i,j in zip(gi,pi):
            if distances[i,j]>gate_m:continue
            i=int(i);j=int(j);used_gt.add(i);used_pred.add(j)
            # Corner correspondence is unordered, avoiding artificial cube-axis penalties.
            ca,cb=corners(gt[i]),corners(pred[j])
            cd=np.linalg.norm(ca[:,None]-cb[None,:],axis=-1)
            ci,cj=linear_sum_assignment(cd)
            pairs.append(dict(gt_index=i,pred_index=j,position_error_mm=float(distances[i,j]*1000),
                size_sorted_mae_mm=float(np.abs(np.sort(gt[i]['size'])-np.sort(pred[j]['size'])).mean()*1000),
                rotation_error_deg=rotation_error(gt[i],pred[j]),iou_3d=iou3d(gt[i],pred[j]),
                matched_corner_mean_mm=float(cd[ci,cj].mean()*1000)))
    missing=sorted(set(range(len(gt)))-used_gt);extra=sorted(set(range(len(pred)))-used_pred)
    return dict(ground_truth_count=len(gt),prediction_count=len(pred),matching_gate_m=gate_m,
        pairs=pairs,missing_gt_indices=missing,extra_prediction_indices=extra,
        precision_at_matching_gate=len(pairs)/len(pred) if pred else None,
        recall_at_matching_gate=len(pairs)/len(gt) if gt else None,
        recall_position_10mm=sum(p['position_error_mm']<=10 for p in pairs)/len(gt) if gt else None,
        scene_iou_score=sum(p['iou_3d'] for p in pairs)/max(len(gt),len(pred)) if gt or pred else None,
        note='Scene IoU score is matched per-object IoU sum / max counts, not union-of-scene-volume IoU. Missing/extra objects lower this score.')


def render(scene,out):
    gt=scene['ground_truth'];pred=scene['predictions']
    observable=[i for i,box in enumerate(gt) if box.get('observable',True)]
    result=compare([gt[i] for i in observable],pred,scene.get('matching_gate_m',.10))
    for pair in result['pairs']:pair['gt_index']=observable[pair['gt_index']]
    result['missing_gt_indices']=[observable[i] for i in result['missing_gt_indices']]
    result['unobservable_gt_indices']=sorted(set(range(len(gt)))-set(observable))
    result['total_physical_objects']=len(gt)
    result['ground_truth_count_definition']='Observable ground truth objects for the available camera views'
    bounds=scene.get('bounds',[[-.18,.18],[-.18,.18],[.78,1.2]])
    fig,axes=plt.subplots(1,3,figsize=(15,5),subplot_kw={'projection':'3d'},layout='constrained')
    for ax,(elev,azim,title) in zip(axes,[(25,-55,'Schrägansicht'),(90,-90,'Draufsicht'),(8,0,'Seitenansicht')]):
        for boxes,color,is_gt in [(gt,'#0891b2',True),(pred,'#f97316',False)]:
            for i,box in enumerate(boxes):
                points=corners(box)
                edge='#be123c' if (is_gt and i in result['missing_gt_indices']) or (not is_gt and i in result['extra_prediction_indices']) else color
                collection=Poly3DCollection([points[face] for face in FACES],facecolors=color,
                    edgecolors=edge,linewidths=1.,alpha=.30)
                ax.add_collection3d(collection)
                c=box['center'];label=f"{'GT' if is_gt else 'P'}{i}"
                if is_gt and i in result['missing_gt_indices']:label+=' MISS'
                if is_gt and i in result['unobservable_gt_indices']:label+=' HIDDEN'
                if not is_gt and i in result['extra_prediction_indices']:label+=' EXTRA'
                ax.text(*c,label,color=edge,fontsize=7)
        for pair in result['pairs']:
            a=gt[pair['gt_index']]['center'];b=pred[pair['pred_index']]['center']
            ax.plot([a[0],b[0]],[a[1],b[1]],[a[2],b[2]],color='black',linestyle=':',linewidth=1)
        ax.set_xlim(bounds[0]);ax.set_ylim(bounds[1]);ax.set_zlim(bounds[2])
        ax.set_box_aspect([b[1]-b[0] for b in bounds]);ax.view_init(elev=elev,azim=azim)
        ax.set_proj_type('ortho')
        ax.set_xlabel('X [m]');ax.set_ylabel('Y [m]');ax.set_zlabel('Z [m]');ax.set_title(title)
        if elev==90:ax.set_zticks([]);ax.set_zlabel('')
        if azim==0:ax.set_xticks([]);ax.set_xlabel('')
    label=scene.get('label','3D-Geometrievergleich')
    fig.suptitle(label+'\nCyan: Simulation | Orange: Vorhersage | Rotrand: fehlend / zusätzlich',fontsize=12)
    fig.legend(handles=[Patch(facecolor='#0891b2',alpha=.3,label='Simulation'),Patch(facecolor='#f97316',alpha=.3,label='Vorhersage')],loc='lower center',ncol=2)
    out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out/'overlay.png',dpi=170);fig.savefig(out/'overlay.svg');plt.close(fig)
    (out/'metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'scene.json').write_text(json.dumps(scene,indent=2),encoding='utf-8')
    return result


def demo():
    def box(c,s,angle=0):
        c0=np.cos(angle);s0=np.sin(angle)
        return dict(center=c,size=s,rotation=[[c0,-s0,0],[s0,c0,0],[0,0,1]])
    gt=[box([-.06,0,.82],[.05,.05,.04]),box([-.06,0,.86],[.04,.04,.04]),
        box([-.06,0,.90],[.04,.04,.04]),box([.06,.03,.82],[.07,.04,.04]),
        box([.06,.03,.86],[.04,.04,.04])]
    pred=json.loads(json.dumps(gt[:4]))
    pred[1]['center'][0]+=.009
    pred[2]['size']=[.045,.035,.043]
    pred[3]=box([.067,.031,.822],[.07,.04,.04],np.deg2rad(12))
    pred.append(box([.12,-.10,.83],[.035,.035,.06]))
    return dict(label='ILLUSTRATION – künstliche Fehler, keine trainierten Modellvorhersagen',
        bounds=[[-.16,.16],[-.16,.16],[.78,1.02]],ground_truth=gt,predictions=pred)


def self_check():
    a=dict(center=[0,0,0],size=[.04]*3,rotation=np.eye(3).tolist())
    b=dict(center=[.02,0,0],size=[.04]*3,rotation=np.eye(3).tolist())
    assert np.isclose(iou3d(a,a),1,atol=1e-7)
    assert np.isclose(iou3d(a,b),1/3,atol=1e-7)
    far=dict(b,center=[1,0,0]);assert iou3d(a,far)==0
    rotated=dict(a,rotation=[[0,-1,0],[1,0,0],[0,0,1]])
    assert np.isclose(iou3d(a,rotated),1,atol=1e-7)
    assert np.isclose(rotation_error(a,rotated),0,atol=1e-7)
    assert compare([a],[])['missing_gt_indices']==[0]
    assert compare([],[a])['extra_prediction_indices']==[0]
    result=compare([a],[a]);assert np.isclose(result['scene_iou_score'],1,atol=1e-7)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scene',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--demo',action='store_true')
    args=parser.parse_args();self_check()
    scene=demo() if args.demo else json.loads(args.scene.read_text(encoding='utf-8'))
    result=render(scene,args.output)
    print(json.dumps(dict(output=str(args.output.resolve()),matched=len(result['pairs']),
        missing=result['missing_gt_indices'],extra=result['extra_prediction_indices'],self_check='passed')))
