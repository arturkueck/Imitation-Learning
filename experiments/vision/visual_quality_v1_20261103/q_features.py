"""48 causal observed features. This module never receives simulator GT."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'vision/visual_edge_refine_v1_20261103'))
from geometry import corners,surface_distance
from scipy.spatial.transform import Rotation
from scipy.optimize import linear_sum_assignment

NAMES=['phase','predicted_count','support','position_spread','size_spread','corner_disagreement','min_probability',
    'initial_size_min','initial_size_mid','initial_size_max','initial_log_aspect','initial_height','candidate_height',
    'delta_x','delta_y','delta_z','delta_position_norm','delta_rotation_angle','delta_log_size_x','delta_log_size_y','delta_log_size_z','delta_corner_distance',
    'candidate_table_clearance','candidate_log_aspect','distinct_points','median_track_length','median_reprojection','max_reprojection','median_parallax','min_parallax',
    'cloud_flatness','cloud_middle_ratio','cloud_candidate_residual','cloud_initial_residual','fit_views','heldout_views','fit_iterations','fit_converged',
    'heldout_reference_edge','heldout_candidate_edge','heldout_edge_gain','anchor_reference_edge','anchor_candidate_edge','anchor_edge_gain',
    'photometric_rejection_ratio','forward_backward_rejection_ratio','acquired_baseline','missing_evidence']
assert len(NAMES)==48

def box(v):return {k:np.asarray(v[k],float) for k in ['position','size','rotation']}

def extract(initial,candidate,group,phase,object_index,snapshot,object_record,observed_cameras,predicted_count,table_height):
    initial=box(initial);candidate=box(candidate);g=object_record['gate'];fit=object_record['fit'];missing=0
    def value(v):
        nonlocal missing
        if v is None or not np.isfinite(v):missing+=1;return 0.
        return float(v)
    cloud=[p for p in snapshot['triangulated_points'] if p['object_index']==object_index];xyz=np.array([p['point'] for p in cloud]).reshape(-1,3)
    lengths=[len(snapshot['tracks'][p['track']]['observations']) for p in cloud]
    reproj=[p['reprojection_px'] for p in cloud];parallax=[p['parallax_deg'] for p in cloud]
    median=lambda a:value(np.median(a) if len(a) else None)
    eigen=np.linalg.eigvalsh(np.cov(xyz.T)) if len(xyz)>=3 else np.zeros(3)
    denom=max(float(eigen[-1]),1e-12);sizes=np.sort(initial['size']);delta=candidate['position']-initial['position'];logsize=np.log(candidate['size']/initial['size'])
    d=np.linalg.norm(corners(initial)[:,None]-corners(candidate)[None],axis=-1);i,j=linear_sum_assignment(d*d);corner=float(np.sqrt(np.mean(d[i,j]**2)))
    reject=snapshot['rejections'];total=max(1,len(snapshot['tracks'])+sum(reject.values()));centers=np.array([c['position'] for c in observed_cameras])
    baseline=float(np.max(np.linalg.norm(centers-centers[0],axis=-1))) if len(centers) else 0.
    before=value(g['heldout_before']);after=value(g['heldout_after']);ab=value(g['anchor_before']);aa=value(g['anchor_after'])
    v=[phase/2,predicted_count/5,group['support']/3,group['spread_mm']/10,group['size_spread_mm']/10,group['corner_disagreement_mm']/20,group['min_detection_score'],
        sizes[0]/.05,sizes[1]/.05,sizes[2]/.15,np.log(sizes[-1]/sizes[0])/np.log(10),(initial['position'][2]-table_height)/.2,(candidate['position'][2]-table_height)/.2,
        *(delta/.015),np.linalg.norm(delta)/.015,Rotation.from_matrix(candidate['rotation']@initial['rotation'].T).magnitude()/np.pi,*logsize,corner/.01,
        (corners(candidate)[:,2].min()-table_height)/.02,np.log(candidate['size'].max()/candidate['size'].min())/np.log(10),len(cloud)/20,
        median(lengths)/20,median(reproj)/2,value(max(reproj) if reproj else None)/2,median(parallax)/20,value(min(parallax) if parallax else None)/20,
        eigen[0]/denom,eigen[1]/denom,value(np.sqrt(np.mean(surface_distance(xyz,candidate)**2)) if len(xyz) else None)/.005,
        value(np.sqrt(np.mean(surface_distance(xyz,initial)**2)) if len(xyz) else None)/.005,fit['fit_views']/56,len(snapshot['heldout_frames'])/56,fit['evaluations']/35,int(fit['status']=='fitted'),
        before/5,after/5,(before-after)/5,ab/5,aa/5,(ab-aa)/5,reject.get('photometric_rejected',0)/total,reject.get('forward_backward_rejected',0)/total,baseline/.3,missing/16]
    a=np.asarray(v,np.float32)
    if a.shape!=(48,) or not np.isfinite(a).all():raise ValueError('Invalid causal feature vector')
    hard=set(g['reasons'])-{'heldout_not_improved'}
    eligible=fit['status']=='fitted' and g['tracks']>=6 and not hard and np.linalg.norm(delta)<=.015 and np.max(np.abs(a[13:22]))>1e-7
    return a,bool(eligible)
