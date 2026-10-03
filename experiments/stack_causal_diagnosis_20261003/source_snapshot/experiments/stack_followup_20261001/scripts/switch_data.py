"""Observation separability and expert action discontinuity; no policy training."""
import json
import numpy as np
from scipy.spatial import cKDTree
from transport_data import ROOT,KEYS,demos,history,summary
from balance_common import event,digest,DATA,SOURCE,EXP as PREVIOUS
OUT=ROOT/'experiments/stack_switch_20261001';OUT.mkdir(exist_ok=True)
def flat(d,i):return np.concatenate([history(d,i)[k] for k in KEYS],axis=1)
def features(x):
    # Input order: EEF3, quaternion4, fingers2, object A3 B3.
    last=x[:,-1];delta=(x[:,1]-x[:,0])/.05
    return np.c_[last[:,[2,14]],last[:,7:9],last[:,9:11]-last[:,:2],last[:,12:14]-last[:,9:11],delta[:,[0,1,2,12,13,14,7,8]]]
def run():
    ds=demos();rows=[];pairs=[];regions={};panel=[]
    for d in ds:
        k=event(d)
        for off in range(-10,11):
            i=k+off;rows.append(dict(demo=d['name'],split=d['split'],offset=off,x=flat(d,i),a=d['actions'][i],label=int(off>=0)))
            if d['split']=='valid':panel.append(dict(demo=d['name'],split=d['split'],step=i,event=k,offset=off))
        before=flat(d,k-1);after=flat(d,k);physical=[0,1,2,7,8,9,10,11,12,13,14]
        pairs.append(dict(demo=d['name'],split=d['split'],history_physical_distance_mm=float(np.linalg.norm(after[:,physical]-before[:,physical])*1000),eef_height_change_mm=float((after[-1,2]-before[-1,2])*1000),B_height_change_mm=float((after[-1,14]-before[-1,14])*1000),finger_change_mm=float(np.linalg.norm(after[-1,7:9]-before[-1,7:9])*1000),eef_velocity_before=((before[1,:3]-before[0,:3])/.05).tolist(),eef_velocity_after=((after[1,:3]-after[0,:3])/.05).tolist(),xy_jump=float(np.linalg.norm(d['actions'][k,:2]-d['actions'][k-1,:2])),z_jump=float(d['actions'][k,2]-d['actions'][k-1,2]),eef_before=float(before[-1,2]),eef_after=float(after[-1,2])))
        for name,offsets in [('clear_lift',range(-20,-10)),('pre',range(-3,0)),('post',range(0,3)),('transport',range(6,11))]:
            for off in offsets:
                i=k+off
                if d['phase'][i]!=(3 if off<0 else 4):continue
                regions.setdefault(name,[]).append(d['actions'][i])
    x=np.array([r['x'] for r in rows]);y=np.array([r['label'] for r in rows]);train=np.array([r['split']=='train' for r in rows]);f=features(x)
    separability={}
    for name,a in [('one_frame',x[:,1]),('two_frames',x.reshape(len(x),-1)),('derived_relative_and_velocities',f),('heights_only',f[:,[0,1]]),('heights_and_vertical_velocities',f[:,[0,1,10,13]])]:
        mean=a[train].mean(0);std=np.maximum(a[train].std(0),1e-5);aa=(a-mean)/std;dist,idx=cKDTree(aa[train]).query(aa[~train]);pred=y[train][idx]
        offsets=np.array([r['offset'] for r in rows])[~train];border=np.isin(offsets,[-1,0])
        separability[name]=dict(valid_accuracy=float((pred==y[~train]).mean()),boundary_accuracy=float((pred[border]==y[~train][border]).mean()),offset_accuracy={str(o):float((pred[offsets==o]==y[~train][offsets==o]).mean()) for o in range(-10,11)},valid_pre_accuracy=float((pred[y[~train]==0]==0).mean()),valid_post_accuracy=float((pred[y[~train]==1]==1).mean()),median_neighbor_distance=float(np.median(dist)))
    # Purely diagnostic threshold chosen on training boundary pairs only.
    pairtrain=[r for r in pairs if r['split']=='train'];pv=np.array([[r['eef_before'],r['eef_after']] for r in pairtrain]);thresholds=np.unique(pv);scores=[((pv[:,0]<t).sum()+(pv[:,1]>=t).sum())/(2*len(pv)) for t in thresholds];threshold=float(thresholds[np.argmax(scores)])
    validpairs=[r for r in pairs if r['split']=='valid'];acc=np.mean([r['eef_before']<threshold for r in validpairs]+[r['eef_after']>=threshold for r in validpairs])
    actions={}
    for name,aa in regions.items():
        a=np.array(aa);xy=np.linalg.norm(a[:,:2],axis=1);actions[name]=dict(n=len(a),xy=summary(xy),z=summary(a[:,2]),abs_z=summary(abs(a[:,2])),xy_absz_ratio=summary(xy/np.maximum(abs(a[:,2]),.01)),opening_fraction=float((a[:,-1]<0).mean()))
    # Opposite-phase nearest neighbors, excluding the same demonstration.
    tridx=np.flatnonzero(train);std=np.maximum(f[train].std(0),1e-5);ff=f/std;neighbors=[]
    for j in np.flatnonzero(~train):
        candidates=tridx[y[tridx]!=y[j]];distance=np.linalg.norm(ff[candidates]-ff[j],axis=1);n=candidates[np.argmin(distance)];neighbors.append(dict(demo=rows[j]['demo'],offset=rows[j]['offset'],neighbor_demo=rows[n]['demo'],neighbor_offset=rows[n]['offset'],scaled_distance=float(distance.min()),action_distance=float(np.linalg.norm(rows[j]['a']-rows[n]['a']))))
    out=dict(window_seconds=[-.5,.5],demos=200,observation_features_per_frame=15,velocity_inputs='not explicit; differences derivable from two frames at 20 Hz',pair_distance_mm=summary([r['history_physical_distance_mm'] for r in pairs]),eef_height_change_mm=summary([r['eef_height_change_mm'] for r in pairs]),B_height_change_mm=summary([r['B_height_change_mm'] for r in pairs]),finger_change_mm=summary([r['finger_change_mm'] for r in pairs]),xy_action_jump=summary([r['xy_jump'] for r in pairs]),z_action_jump=summary([r['z_jump'] for r in pairs]),nearest_neighbor_separability=separability,boundary_height_threshold=dict(threshold_m=threshold,train_accuracy=max(scores),valid_accuracy=float(acc)),expert_actions=actions,expert_label_max_error=float(max(d['label_error'].max() for d in ds)),boundary_pairs=pairs,opposite_phase_neighbors=neighbors)
    (OUT/'data_analysis.json').write_text(json.dumps(out,indent=2));(OUT/'panel.json').write_text(json.dumps(panel,indent=2))
    byname={d['name']:d for d in ds};obs={key:np.stack([history(byname[r['demo']],r['step'])[key] for r in panel]) for key in KEYS};expected=np.stack([byname[r['demo']]['actions'][np.clip(np.arange(r['step']-1,r['step']+15),0,len(byname[r['demo']]['actions'])-1)] for r in panel]);np.savez_compressed(OUT/'panel.npz',expected=expected,**obs)
    oldmeta=json.loads((PREVIOUS/'uniform/offline_samples.json').read_text());old=np.load(PREVIOUS/'uniform/offline_predictions.npz');lookup={(r['demo'],r['step']):i for i,r in enumerate(oldmeta)};checks=0
    for j,r in enumerate(panel):
        if (r['demo'],r['step']) in lookup:
            for key in KEYS:assert np.array_equal(obs[key][j],old[key][lookup[(r['demo'],r['step'])]])
            checks+=1
    protocol=dict(training=False,architecture_changes=False,checkpoints=dict(source=SOURCE['checkpoint'],uniform=str(PREVIOUS/'uniform/model_final.pth'),balanced=str(PREVIOUS/'balanced/model_final.pth')),panel='all 20 validation demos, offsets -10..10',draws=8,configs=['ddim10','ddim20','ddim50','ddim100','ddim10_eta1','ddim100_eta1','ddpm100'],extra_draws_at_offsets=[-1,0],extra_draws=32,shared_saved_observations_verified=checks,dataset_sha256=digest(DATA))
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ('boundary_pairs','opposite_phase_neighbors')},indent=2))
if __name__=='__main__':run()
