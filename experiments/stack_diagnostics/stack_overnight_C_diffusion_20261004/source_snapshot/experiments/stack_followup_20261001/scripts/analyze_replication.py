"""Training seeds are replicates; fixed starts remain nested paired outcomes."""
import json,os
import numpy as np
from replication_common import OUT,ROOT,OLD,folder,rollouts
from transport_data import summary
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator,FuncFormatter
prior=ROOT/'experiments/stack_switch_20261001';meta=json.loads((prior/'panel.json').read_text());data=np.load(prior/'panel.npz');off=np.array([r['offset'] for r in meta]);names=np.array([r['demo'] for r in meta]);goal=data['object'][:,-1,:2]-data['robot0_eef_pos'][:,-1,:2];expert=data['expected'][:,1];results={};seed_records=[];profiles={}
for kind in ('diffusion','direct'):
    results[kind]={}
    for seed in (1,2,3):
        dest=folder(kind,seed)
        if kind=='direct':
            path=OLD/'offline_predictions.npz' if seed==1 else dest/'offline_predictions.npz'
            if not path.exists():continue
            chunks=np.load(path)['chunks'];idx=np.arange(len(meta));draw=np.zeros(len(meta),int);pi=idx[np.isin(off,[-1,0])];pd=np.zeros(len(pi),int);pa=chunks[pi,1,:3]
        else:
            path=prior/'source/ddim10.npz' if seed==1 else dest/'common_offline.npz'
            if not path.exists():continue
            z=np.load(path);m=z['draw']<8;idx=z['panel_index'][m];draw=z['draw'][m];chunks=z['chunks'][m];pp=prior/'source/paired_ddim10.npz' if seed==1 else dest/'paired_offline.npz';pz=np.load(pp);pi=pz['panel_index'];pd=pz['draw'];pa=pz['chunks'][:,1,:3]
        a=chunks[:,1];xy=np.linalg.norm(a[:,:2],axis=1);cos=(a[:,:2]*goal[idx]).sum(1)/np.maximum(xy*np.linalg.norm(goal[idx],axis=1),1e-9);pairs=[];aligned=[]
        for d in np.unique(pd):
            for n in sorted(set(names)):
                ii=np.flatnonzero((pd==d)&(names[pi]==n));ii=ii[np.argsort(off[pi[ii]])];assert len(ii)==2;delta=pa[ii[1]]-pa[ii[0]];need=expert[pi[ii[1]],:3]-expert[pi[ii[0]],:3];pairs.append(np.linalg.norm(delta)/np.linalg.norm(need));aligned.append(float(delta@need/(need@need)))
        onset=[]
        for d in np.unique(draw):
            for n in sorted(set(names)):
                ii=np.flatnonzero((draw==d)&(names[idx]==n));ii=ii[np.argsort(off[idx[ii]])];mask=(xy[ii]>.25)&(cos[ii]>.5);runs=np.flatnonzero(np.convolve(mask.astype(int),np.ones(3,int),'valid')==3);onset.append(int(off[idx[ii[runs[0]]]]) if len(runs) else None)
        m=np.isin(off[idx],list(range(6,11)));gt=expert[idx];em=np.linalg.norm(gt[:,:2],axis=1);align=(a[:,:2]*gt[:,:2]).sum(1)/np.maximum(xy*em,1e-9)
        r=dict(training_seed=seed,offline=dict(boundary_response=summary(pairs),aligned_boundary_response=summary(aligned),early_fraction=sum(o is not None and o<-2 for o in onset)/len(onset),on_time_fraction=sum(o is not None and abs(o)<=2 for o in onset)/len(onset),late_fraction=sum(o is not None and o>2 for o in onset)/len(onset),missing_fraction=sum(o is None for o in onset)/len(onset),xy_over_expert=summary(xy[m]/em[m]),direction_cosine=summary(align[m]),wrong_direction_fraction=float((align[m]<0).mean())))
        profiles[(kind,seed)]={o:dict(xy=float(xy[off[idx]==o].mean()),z=float(a[off[idx]==o,2].mean())) for o in range(-10,11)}
        path=rollouts(kind,seed)/'results.json'
        if path.exists():
            rows=json.loads(path.read_text());counts={k:sum(x[k] for x in rows) for k in ('grasp','lift','correct_lift','transport_started','premature_transport','near','position','lower','release','stack','sustained_success')};counts['full_height_before_transport']=sum(x['full_lift_end'] is not None and x['transport_start'] is not None and x['full_lift_end']<=x['transport_start'] for x in rows);r['rollout']=dict(n=len(rows),counts=counts,stack_rate=counts['sustained_success']/len(rows),max_height=summary([x['max_cube_height_m'] for x in rows]),transport_height=summary([x['cube_height_at_transport_start_m'] for x in rows if x['transport_start'] is not None]),successful_without_full_height=sum(x['sustained_success'] and not x['correct_lift'] for x in rows),successful_premature=sum(x['sustained_success'] and x['premature_transport'] for x in rows));r['start_success']={str(x['seed']):int(x['sustained_success']) for x in rows}
        results[kind][str(seed)]=r
        if r.get('rollout',{}).get('n')==40:seed_records.append(dict(model_class=kind,training_seed=seed,stack_rate=r['rollout']['stack_rate'],boundary_response=r['offline']['boundary_response']['q'][2],early_fraction=r['offline']['early_fraction'],on_time_fraction=r['offline']['on_time_fraction'],xy_strength=r['offline']['xy_over_expert']['q'][2],direction_cosine=r['offline']['direction_cosine']['mean'],wrong_direction_fraction=r['offline']['wrong_direction_fraction'],grasp_rate=r['rollout']['counts']['grasp']/40,lift_height=r['rollout']['max_height']['q'][2]))
aggregate={};state_tables={}
for kind in results:
    complete=[r for r in results[kind].values() if r.get('rollout',{}).get('n')==40];rates=np.array([r['rollout']['stack_rate'] for r in complete]);aggregate[kind]=dict(n_training_replicates=len(rates),individual_rates=rates.tolist(),mean=float(rates.mean()) if len(rates) else None,sample_std=float(rates.std(ddof=1)) if len(rates)>1 else None,min=float(rates.min()) if len(rates) else None,max=float(rates.max()) if len(rates) else None)
    if len(complete)==3:
        state_tables[kind]=[{ 'start_seed':s,'successes':[r['start_success'][str(s)] for r in complete],'success_rate':float(np.mean([r['start_success'][str(s)] for r in complete]))} for s in range(46000,46040)];aggregate[kind]['all_seeds_success_starts']=[x['start_seed'] for x in state_tables[kind] if x['success_rate']==1];aggregate[kind]['mixed_starts']=[x['start_seed'] for x in state_tables[kind] if 0<x['success_rate']<1];aggregate[kind]['all_seeds_failure_starts']=[x['start_seed'] for x in state_tables[kind] if x['success_rate']==0]
def corr(rows):
    y=np.array([r['stack_rate'] for r in rows]);out={}
    for key in ('boundary_response','early_fraction','on_time_fraction','xy_strength','direction_cosine','wrong_direction_fraction','grasp_rate','lift_height'):
        x=np.array([r[key] for r in rows]);out[key]=dict(n=len(rows),pearson=float(np.corrcoef(x,y)[0,1]) if len(rows)>1 and np.std(x)>0 and np.std(y)>0 else None,notes='descriptive only; no p-values; class-confounded when pooled')
    return out
correlations={'pooled':corr(seed_records),**{kind:corr([r for r in seed_records if r['model_class']==kind]) for kind in results}}
(OUT/'analysis.json').write_text(json.dumps(dict(per_seed=results,aggregate=aggregate,start_states=state_tables,seed_level_records=seed_records,correlations=correlations),indent=2))
fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey='col');time=np.arange(-10,11)*.05
for row,kind in enumerate(('diffusion','direct')):
    for seed in (1,2,3):
        if (kind,seed) not in profiles:continue
        for col,key in enumerate(('xy','z')):axes[row,col].plot(time,[profiles[(kind,seed)][o][key] for o in range(-10,11)],label=f'seed {seed}')
    for col in (0,1):
        ex=[np.linalg.norm(expert[off==o,:2],axis=1).mean() if col==0 else expert[off==o,2].mean() for o in range(-10,11)];axes[row,col].plot(time,ex,'k--',label='Expert');axes[row,col].axvline(0,color='gray',alpha=.4);axes[row,col].set_ylabel(kind+(' XY' if col==0 else ' Z'));axes[row,col].grid(alpha=.2);axes[row,col].legend()
for ax in axes[-1]:ax.set_xlabel('Seconds relative to expert switch')
fig.tight_layout();fig.savefig(OUT/'boundary_profiles.png',dpi=160);plt.close(fig)
if len(state_tables)==2:
    fig,axes=plt.subplots(2,1,figsize=(13,4),sharex=True)
    for ax,kind in zip(axes,('diffusion','direct')):
        matrix=np.array([r['successes'] for r in state_tables[kind]]).T;ax.imshow(matrix,vmin=0,vmax=1,cmap='RdYlGn',aspect='auto');ax.set_yticks([0,1,2],[1,2,3]);ax.set_ylabel(kind+' train seed')
    axes[-1].set_xticks(np.arange(40),np.arange(46000,46040),rotation=90);fig.suptitle('Same fixed starts: green = stable stack, red = failure');fig.tight_layout();fig.savefig(OUT/'start_state_success.png',dpi=160);plt.close(fig)
print(json.dumps(aggregate,indent=2))
if aggregate['direct']['n_training_replicates']==3:
    clearance=[]
    def vertical_extent(q):
        w,x,y,z=q
        return .02*np.abs([2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]).sum()
    for seed in (1,2,3):
        rows=json.loads((rollouts('direct',seed)/'results.json').read_text())
        for r in rows:
            if r['sustained_success'] and r['premature_transport']:
                t=np.load(rollouts('direct',seed)/f"{r['seed']}.npz")['trace'];p=t[r['premature_motion_start']]
                gap=float(p[6]-p[3]-vertical_extent(p[7:11])-vertical_extent(p[11:15]))
                clearance.append(dict(training_seed=seed,start_seed=r['seed'],cube_height_m=float(p[6]),vertical_bounding_box_gap_m=gap))
    (OUT/'early_success_clearance.json').write_text(json.dumps(dict(records=clearance,gap_summary=summary([r['vertical_bounding_box_gap_m'] for r in clearance]),geometry='4 cm cubes; orientation-aware world-Z box extents from saved wxyz quaternions'),indent=2))
if len(seed_records)==6:
    fig,ax=plt.subplots(figsize=(7,4))
    for j,kind in enumerate(('diffusion','direct')):
        rows=[r for r in seed_records if r['model_class']==kind]
        for i,r in enumerate(rows):
            ax.scatter(j+(i-1)*.08,100*r['stack_rate'],s=70,label=f"{kind}, seed {r['training_seed']}")
        g=aggregate[kind];ax.errorbar(j,100*g['mean'],yerr=100*g['sample_std'],color='black',fmt='_',capsize=7)
    ax.set_xticks([0,1],['Diffusion','Direct']);ax.set_ylim(-5,105);ax.set_ylabel('Stable stack rate on same 40 starts (%)');ax.set_title('Training seeds are the replicates; black: mean ± sample SD');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'seed_success.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    keys=['boundary_response','early_fraction','on_time_fraction','xy_strength','direction_cosine','grasp_rate']
    for ax,key in zip(axes.flat,keys):
        for r in seed_records:
            ax.scatter(r[key],100*r['stack_rate'],color='tab:blue' if r['model_class']=='direct' else 'tab:orange')
            ax.annotate(('R' if r['model_class']=='direct' else 'D')+str(r['training_seed']),(r[key],100*r['stack_rate']),xytext=(3,4+7*(r['training_seed']-1)),textcoords='offset points',fontsize=8)
        ax.set_xlabel(key);ax.set_ylabel('Stable stack (%)');ax.grid(alpha=.2);ax.set_ylim(-5,105);ax.margins(x=.15);ax.xaxis.set_major_locator(MaxNLocator(nbins=4));ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:g}'));ax.tick_params(axis='x',labelsize=9)
    fig.suptitle('Exploratory seed-level association; R=direct, D=diffusion; pooled values class-confounded');fig.tight_layout();fig.savefig(OUT/'offline_rollout.png',dpi=160);plt.close(fig)
