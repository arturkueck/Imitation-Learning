"""Additional scalar audits and plots; no policy or training modification."""
import json,os
import numpy as np
from dynamics_common import OUT,ROOT,KEYS,raw_features
from transport_data import summary,demos
from balance_common import event
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'mpl_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
features=np.load(OUT/'training_features.npz');raw=features['raw'];scaled=features['normalized'];phase=features['phase'];result={};dataset=demos()
original_scale={}
for key in KEYS:
    values=np.concatenate([d['obs'][key] for d in dataset if d['split']=='train'])
    original_scale[key]=dict(min=values.min(0).tolist(),max=values.max(0).tolist(),mean=values.mean(0).tolist(),std=values.std(0).tolist())
(OUT/'original_feature_scales.json').write_text(json.dumps(original_scale,indent=2))
for v in ('baseline','dynamics'):
    z=np.load(OUT/v/'training_audit.npz');result[v]=dict(loss_first500_mean=float(z['loss'][:500].mean()),loss_last500_mean=float(z['loss'][-500:].mean()),sampled_phase_counts={str(k):int(np.sum(phase[z['sample_indices']]==k)) for k in np.unique(phase)})
    rp=OUT/v/'rollouts/results.json'
    if rp.exists():
        rows=json.loads(rp.read_text());vals=[]
        for r in rows:
            d=np.load(OUT/v/'rollouts'/f"{r['seed']}.npz");held=d['trace'][:,34]>0
            if held.any():vals.append(raw_features({k:d[k] for k in KEYS})[held])
        if vals:
            rv=np.concatenate(vals);lo=np.quantile(raw,.01,axis=0);hi=np.quantile(raw,.99,axis=0);result[v]['held_rollout_features']={k:dict(distribution=summary(rv[:,j]),outside_train_1_99_percentiles=float(((rv[:,j]<lo[j])|(rv[:,j]>hi[j])).mean())) for j,k in enumerate(('deef','veef','dcube','vcube'))}
meta_path=OUT/'train_boundary_panel.json'
if meta_path.exists():
    meta=json.loads(meta_path.read_text());ds={d['name']:d for d in dataset};ex=np.array([ds[r['demo']]['actions'][event(ds[r['demo']])+r['offset'],:3] for r in meta]);off=np.array([r['offset'] for r in meta])
    for v in ('baseline','dynamics'):
        path=OUT/v/'train_paired_offline.npz'
        if not path.exists():continue
        z=np.load(path);idx=z['panel_index'];a=z['chunks'][:,1,:3];ratios=[];aligned=[]
        for draw in range(8):
            ii=np.flatnonzero(z['draw']==draw);assert len(ii)==len(meta)
            for j in range(0,len(ii),2):
                before,after=ii[j:j+2];delta=a[after]-a[before];need=ex[idx[after]]-ex[idx[before]];ratios.append(np.linalg.norm(delta)/np.linalg.norm(need));aligned.append(float(delta@need/(need@need)))
        result[v]['train_paired']=dict(n=len(ratios),model_over_expert_change=summary(ratios),aligned_response_over_expert=summary(aligned))
(OUT/'diagnostics.json').write_text(json.dumps(result,indent=2))
fig,ax=plt.subplots(2,2,figsize=(9,6))
for col,j in enumerate((0,2)):
    for ph,name in ((3,'Lift'),(4,'Transport')):
        ax[0,col].hist(raw[phase==ph,j]*1000,bins=55,density=True,histtype='step',label=name);ax[1,col].hist(scaled[phase==ph,j],bins=55,density=True,histtype='step',label=name)
    ax[0,col].set_xlabel(('EEF' if j==0 else 'Cube')+' delta Z (mm)');ax[1,col].set_xlabel('Standardized delta Z / velocity');ax[0,col].legend();ax[1,col].legend()
fig.tight_layout();fig.savefig(OUT/'feature_distributions.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3))
for v in ('baseline','dynamics'):
    z=np.load(OUT/v/'training_audit.npz');ax.plot(np.arange(50)*100+100,z['loss'].reshape(50,100).mean(1),label=v)
ax.set_xlabel('Gradient updates');ax.set_ylabel('Diffusion epsilon MSE, 100-update means');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'training_loss.png',dpi=160);plt.close(fig)
print(json.dumps(result,indent=2))
