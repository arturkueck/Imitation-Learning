"""Common boundary metrics, per-demo paired reactions, direct versus diffusion."""
import json,os
import numpy as np
from direct_common import OUT,ROOT
from transport_data import summary
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
prior=ROOT/'experiments/stack_diagnostics/stack_switch_20261001';meta=json.loads((prior/'panel.json').read_text());panel=np.load(prior/'panel.npz');off=np.array([r['offset'] for r in meta]);names=np.array([r['demo'] for r in meta]);goal=panel['object'][:,-1,:2]-panel['robot0_eef_pos'][:,-1,:2];ex=panel['expected'][:,1];results={};profiles={};allpairs={}
for v in ('diffusion','direct'):
    if v=='diffusion':
        z=np.load(prior/'source/ddim10.npz');m=z['draw']<8;idx=z['panel_index'][m];draw=z['draw'][m];chunks=z['chunks'][m];paired=np.load(prior/'source/paired_ddim10.npz');pi=paired['panel_index'];pd=paired['draw'];pa=paired['chunks'][:,1,:3]
    else:
        chunks=np.load(OUT/'offline_predictions.npz')['chunks'];idx=np.arange(len(meta));draw=np.zeros(len(meta),int);pi=idx[np.isin(off,[-1,0])];pd=np.zeros(len(pi),int);pa=chunks[pi,1,:3]
    a=chunks[:,1];xy=np.linalg.norm(a[:,:2],axis=1);cos=(a[:,:2]*goal[idx]).sum(1)/np.maximum(xy*np.linalg.norm(goal[idx],axis=1),1e-9);r={}
    for name,offsets in [('lift',range(-10,-5)),('pre',[-2,-1]),('post',[0,1,2]),('transport',range(6,11))]:
        m=np.isin(off[idx],list(offsets));gt=ex[idx];em=np.linalg.norm(gt[:,:2],axis=1);active=m&(em>.1);align=(a[:,:2]*gt[:,:2]).sum(1)/np.maximum(xy*em,1e-9)
        r[name]=dict(n=int(m.sum()),xy=summary(xy[m]),z=summary(a[m,2]),xy_over_expert=summary(xy[active]/em[active]),expert_direction_cosine=summary(align[active]),wrong_direction_fraction=float((align[active]<0).mean()) if active.any() else None,lift_mode=float(((xy[m]<.12)&(a[m,2]>.02)&(a[m,-1]>0)).mean()),transport_mode=float(((xy[m]>.25)&(cos[m]>.5)&(a[m,2]<-.05)&(a[m,-1]>0)).mean()),opening=float((a[m,-1]<0).mean()),xyz_mse=float(((a[m,:3]-gt[m,:3])**2).mean()))
    pairs=[]
    for d in np.unique(pd):
        for demo in sorted(set(names)):
            ii=np.flatnonzero((pd==d)&(names[pi]==demo));ii=ii[np.argsort(off[pi[ii]])];assert len(ii)==2;delta=pa[ii[1]]-pa[ii[0]];need=ex[pi[ii[1]],:3]-ex[pi[ii[0]],:3];pairs.append(dict(demo=demo,draw=int(d),ratio=float(np.linalg.norm(delta)/np.linalg.norm(need)),aligned=float(delta@need/(need@need)),delta=delta.tolist()))
    per_demo={name:float(np.mean([x['ratio'] for x in pairs if x['demo']==name])) for name in sorted(set(names))}
    r['paired']=dict(n=len(pairs),ratio=summary([x['ratio'] for x in pairs]),aligned=summary([x['aligned'] for x in pairs]),mean_absolute_xyz_delta=np.mean(abs(np.array([x['delta'] for x in pairs])),axis=0).tolist(),per_demo_mean_ratio=per_demo);allpairs[v]=pairs
    onset=[]
    for d in np.unique(draw):
        for demo in sorted(set(names)):
            ii=np.flatnonzero((draw==d)&(names[idx]==demo));ii=ii[np.argsort(off[idx[ii]])];mask=(xy[ii]>.25)&(cos[ii]>.5);found=np.flatnonzero(np.convolve(mask.astype(int),np.ones(3,int),'valid')==3);onset.append(int(off[idx[ii[found[0]]]]) if len(found) else None)
    r['onset']=dict(n=len(onset),early_fraction=sum(x is not None and x<-2 for x in onset)/len(onset),on_time_fraction=sum(x is not None and abs(x)<=2 for x in onset)/len(onset),late_fraction=sum(x is not None and x>2 for x in onset)/len(onset),missing_fraction=sum(x is None for x in onset)/len(onset),steps=summary([x for x in onset if x is not None]))
    profiles[v]={o:dict(xy=float(xy[off[idx]==o].mean()),z=float(a[off[idx]==o,2].mean())) for o in range(-10,11)}
    path=OUT/v/'rollouts/results.json'
    if path.exists():
        rows=json.loads(path.read_text());groups={}
        for label,rr in [('first20',rows[:20]),('extra20',rows[20:]),('all',rows)]:
            keys=['grasp','lift','correct_lift','transport_started','premature_transport','near','position','lower','release','stack','sustained_success'];stats=dict(n=len(rr),counts={k:sum(x[k] for x in rr) for k in keys},full_lift_before_transport=sum(x['full_lift_end'] is not None and x['transport_start'] is not None and x['full_lift_end']<=x['transport_start'] for x in rr),max_cube_height=summary([x['max_cube_height_m'] for x in rr]),transport_height=summary([x['cube_height_at_transport_start_m'] for x in rr if x['transport_start'] is not None]))
            distance=[]
            for row in rr:
                if row['transport_start'] is not None:
                    t=np.load(OUT/v/'rollouts'/f"{row['seed']}.npz")['trace'];i=row['transport_start'];distance.append(np.linalg.norm(t[i,4:6]-t[i,1:3]))
            stats['xy_distance_at_transport_start']=summary(distance);groups[label]=stats
        r['rollouts']=groups
    results[v]=r
# Bootstrap over demos, not stochastic draws; two models use identical demos.
dp=np.array(list(results['diffusion']['paired']['per_demo_mean_ratio'].values()));direct=np.array(list(results['direct']['paired']['per_demo_mean_ratio'].values()));rng=np.random.default_rng(884);samples=rng.integers(20,size=(5000,20));delta=(direct-dp)[samples].mean(1);(OUT/'paired_demo_bootstrap.json').write_text(json.dumps(dict(demos=20,direct_minus_diffusion_mean_ratio=float((direct-dp).mean()),ci95=np.quantile(delta,[.025,.975]).tolist(),interpretation='uncertainty over fixed validation demos; one training seed, not training-seed uncertainty'),indent=2))
(OUT/'analysis.json').write_text(json.dumps(results,indent=2));(OUT/'paired_boundary_comparisons.json').write_text(json.dumps(allpairs,indent=2))
fig,axes=plt.subplots(1,2,figsize=(11,4));times=np.arange(-10,11)*.05
for j,key in enumerate(('xy','z')):
    for v in profiles:axes[j].plot(times,[profiles[v][o][key] for o in range(-10,11)],label=v)
    expected=[np.linalg.norm(ex[off==o,:2],axis=1).mean() if j==0 else ex[off==o,2].mean() for o in range(-10,11)];axes[j].plot(times,expected,'k--',label='Expert');axes[j].axvline(0,color='gray',alpha=.4);axes[j].set_xlabel('Seconds relative to expert switch');axes[j].set_ylabel(key.upper()+' action');axes[j].grid(alpha=.2);axes[j].legend()
fig.tight_layout();fig.savefig(OUT/'boundary_profiles.png',dpi=160);plt.close(fig);print(json.dumps(results,indent=2))
