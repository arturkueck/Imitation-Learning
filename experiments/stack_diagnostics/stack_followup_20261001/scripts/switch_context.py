"""Additional physical cue scales and exact duplicate check."""
import json,numpy as np
from switch_data import OUT,flat
from transport_data import demos,history,summary
from balance_common import event
rows=[];normal=[];boundary=[];angles=[];relative=[];directions={}
for d in demos():
    k=event(d)
    for region,offsets in [('clear_lift',range(-20,-10)),('pre',range(-3,0)),('post',range(0,3)),('transport',range(6,11))]:
        for off in offsets:
            i=k+off
            if d['phase'][i]!=(3 if off<0 else 4):continue
            axy=d['actions'][i,:2];vec=d['obs']['object'][i,:2]-d['obs']['robot0_eef_pos'][i,:2]
            if np.linalg.norm(axy)>.01:directions.setdefault(region,[]).append(float(np.dot(axy,vec)/max(1e-9,np.linalg.norm(axy)*np.linalg.norm(vec))))
    for i in range(k-10,k+11):rows.append((flat(d,i).ravel(),d['actions'][i]))
    for i in range(k-20,k-10):
        if d['phase'][i]!=3:continue
        h=history(d,i);normal.append(dict(eef_vz=float(np.diff(h['robot0_eef_pos'][:,2])[0]/.05),eef_frame_change_mm=float(np.linalg.norm(np.diff(h['robot0_eef_pos'],axis=0))*1000)))
    b=history(d,k-1);a=history(d,k);q0=b['robot0_eef_quat'][-1];q1=a['robot0_eef_quat'][-1];angles.append(float(np.degrees(2*np.arccos(np.clip(abs(np.dot(q0,q1)/(np.linalg.norm(q0)*np.linalg.norm(q1))),0,1)))))
    rb=b['object'][-1,:2]-b['object'][-1,3:5];ra=a['object'][-1,:2]-a['object'][-1,3:5];relative.append(float(np.linalg.norm(ra-rb)*1000))
    for label,i in [('last_lift',k-1),('first_transport',k)]:
        h=history(d,i);boundary.append(dict(label=label,eef_vz=float(np.diff(h['robot0_eef_pos'][:,2])[0]/.05),eef_frame_change_mm=float(np.linalg.norm(np.diff(h['robot0_eef_pos'],axis=0))*1000)))
x=np.stack([r[0] for r in rows]);a=np.stack([r[1] for r in rows]);unique,idx,counts=np.unique(x,axis=0,return_inverse=True,return_counts=True);conflicts=0
for group in np.flatnonzero(counts>1):
    aa=a[idx==group];conflicts+=int(np.max(np.linalg.norm(aa-aa[0],axis=1))>.1)
out=dict(normal_lift=dict(eef_vz=summary([r['eef_vz'] for r in normal]),eef_frame_change_mm=summary([r['eef_frame_change_mm'] for r in normal])),boundary={label:{key:summary([r[key] for r in boundary if r['label']==label]) for key in ('eef_vz','eef_frame_change_mm')} for label in ('last_lift','first_transport')},orientation_change_degrees=summary(angles),relative_B_goal_xy_change_mm=summary(relative),exact_observation_duplicates=int((counts>1).sum()),exact_observation_action_conflicts=conflicts,samples=len(rows),expert_goal_cosine={k:summary(v) for k,v in directions.items()})
(OUT/'context_analysis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
