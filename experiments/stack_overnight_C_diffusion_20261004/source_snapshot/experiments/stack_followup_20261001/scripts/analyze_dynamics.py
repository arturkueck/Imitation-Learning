"""Compare representations on the frozen validation boundary and full rollouts."""
import json,os
import numpy as np
from dynamics_common import OUT,ROOT
from transport_data import summary
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'mpl_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
prior=ROOT/'experiments/stack_switch_20261001';panel=json.loads((prior/'panel.json').read_text());data=np.load(prior/'panel.npz');off=np.array([r['offset'] for r in panel]);names=np.array([r['demo'] for r in panel]);goal=data['object'][:,-1,:2]-data['robot0_eef_pos'][:,-1,:2];expert=data['expected'][:,1];results={};profiles={}
for v in ('baseline','dynamics'):
    if not (OUT/v/'common_offline.npz').exists():continue
    z=np.load(OUT/v/'common_offline.npz');idx=z['panel_index'];draw=z['draw'];a=z['chunks'][:,1];xy=np.linalg.norm(a[:,:2],axis=1);cos=(a[:,:2]*goal[idx]).sum(1)/np.maximum(xy*np.linalg.norm(goal[idx],axis=1),1e-9)
    lift=(xy<.12)&(a[:,2]>.02)&(a[:,-1]>0);tr=(xy>.25)&(cos>.5)&(a[:,2]<-.05)&(a[:,-1]>0);mix=(xy>.25)&(a[:,2]>.02)&(a[:,-1]>0);res={}
    for region,offsets in [('lift',range(-10,-5)),('pre',[-2,-1]),('post',[0,1,2]),('transport',range(6,11))]:
        m=np.isin(off[idx],list(offsets))&(draw<8);em=np.linalg.norm(expert[idx,:2],axis=1);active=m&(em>.1)
        res[region]=dict(n=int(m.sum()),xy=summary(xy[m]),z=summary(a[m,2]),xy_over_expert=summary(xy[active]/em[active]),lift_mode=float(lift[m].mean()),transport_mode=float(tr[m].mean()),mixed_mode=float(mix[m].mean()),opening=float((a[m,-1]<0).mean()))
    co=[];sx=[];sz=[]
    for i in np.flatnonzero(np.isin(off,[-1,0])):
        m=idx==i;co.append(lift[m].mean()>=.15 and tr[m].mean()>=.15);sx.append(xy[m].std());sz.append(a[m,2].std())
    onset=[]
    for d in range(8):
        for n in sorted(set(names)):
            ii=np.flatnonzero((draw==d)&(names[idx]==n));ii=ii[np.argsort(off[idx[ii]])];sig=(xy[ii]>.25)&(cos[ii]>.5);runs=np.flatnonzero(np.convolve(sig.astype(int),np.ones(3,int),'valid')==3);onset.append(int(off[idx[ii[runs[0]]]]) if len(runs) else None)
    res['sampling']=dict(boundary_both_modes_fraction=float(np.mean(co)),boundary_xy_std=summary(sx),boundary_z_std=summary(sz),onset_found_fraction=sum(o is not None for o in onset)/len(onset),early_fraction=sum(o is not None and o<-2 for o in onset)/len(onset),on_time_fraction=sum(o is not None and abs(o)<=2 for o in onset)/len(onset),onset_steps=summary([o for o in onset if o is not None]),left_censored_fraction=sum(o==-10 for o in onset)/len(onset))
    pz=np.load(OUT/v/'paired_offline.npz');pi=pz['panel_index'];pd=pz['draw'];pa=pz['chunks'][:,1,:3];changes=[];ratios=[];deltas=[];aligned=[];transition=[]
    for d in range(32):
        for n in sorted(set(names)):
            ii=np.flatnonzero((pd==d)&(names[pi]==n));ii=ii[np.argsort(off[pi[ii]])];assert len(ii)==2
            delta=pa[ii[1]]-pa[ii[0]];ex=expert[pi[ii[1]],:3]-expert[pi[ii[0]],:3];changes.append(np.linalg.norm(delta));ratios.append(np.linalg.norm(delta)/np.linalg.norm(ex));deltas.append(delta);aligned.append(float(delta@ex/(ex@ex)))
            before,after=pa[ii];ga=goal[pi[ii[1]]];ac=np.dot(after[:2],ga)/max(np.linalg.norm(after[:2])*np.linalg.norm(ga),1e-9);transition.append(np.linalg.norm(before[:2])<.12 and before[2]>.02 and np.linalg.norm(after[:2])>.25 and ac>.5 and after[2]<-.05 and np.all(pz['chunks'][ii,1,-1]>0))
    res['paired']=dict(n=len(changes),xyz_change=summary(changes),model_over_expert_change=summary(ratios),aligned_response_over_expert=summary(aligned),strict_lift_to_transport_switch_fraction=float(np.mean(transition)),absolute_component_change={k:summary(abs(np.array(deltas)[:,j])) for j,k in enumerate(('x','y','z'))})
    profiles[v]={int(o):dict(xy=float(xy[(off[idx]==o)&(draw<8)].mean()),z=float(a[(off[idx]==o)&(draw<8),2].mean())) for o in range(-10,11)}
    rp=OUT/v/'rollouts/results.json'
    if rp.exists():
        rr=json.loads(rp.read_text());keys=['grasp','lift','correct_lift','transport_started','premature_transport','near','position','lower','release','stack','sustained_success']
        res['rollouts']=dict(n=len(rr),counts={k:sum(r[k] for r in rr) for k in keys},distance_after_full_lift={s:summary([r['relative_xy_distance_after_lift_end_m'][s] for r in rr if r['relative_xy_distance_after_lift_end_m'][s] is not None]) for s in ('0.5','1.0','2.0')},max_held_height=summary([r['max_held_cube_height_m'] for r in rr if r['max_held_cube_height_m'] is not None]),transport_start_height=summary([r['cube_height_at_transport_start_m'] for r in rr if r['cube_height_at_transport_start_m'] is not None]),transport_delay_steps=summary([r['transport_delay_steps'] for r in rr if r['transport_delay_steps'] is not None]),xy_reversals=summary([r['xy_action_reversals'] for r in rr]))
    results[v]=res
(OUT/'analysis.json').write_text(json.dumps(results,indent=2))
if len(profiles)==2:
    fig,axes=plt.subplots(1,2,figsize=(10,4));times=np.arange(-10,11)*.05
    for j,key in enumerate(('xy','z')):
        for v in profiles:axes[j].plot(times,[profiles[v][o][key] for o in range(-10,11)],label=v)
        ex=[np.linalg.norm(expert[off==o,:2],axis=1).mean() if j==0 else expert[off==o,2].mean() for o in range(-10,11)];axes[j].plot(times,ex,'k--',label='Expert');axes[j].axvline(0,color='gray',alpha=.4);axes[j].set_xlabel('Seconds relative to expert switch');axes[j].set_ylabel(key.upper()+' action');axes[j].grid(alpha=.2);axes[j].legend()
    fig.tight_layout();fig.savefig(OUT/'boundary_profiles.png',dpi=160);plt.close(fig)
print(json.dumps({v:dict(paired=r['paired'],sampling=r['sampling'],rollouts=r.get('rollouts')) for v,r in results.items()},indent=2))
