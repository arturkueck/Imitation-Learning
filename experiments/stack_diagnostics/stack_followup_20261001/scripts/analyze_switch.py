"""Separate observational cues, mode sampling, and sampler effects."""
import json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[4]/'experiments/stack_diagnostics/stack_switch_20261001/mpl_cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from switch_data import OUT
from transport_data import summary
panel=json.loads((OUT/'panel.json').read_text());data=np.load(OUT/'panel.npz');off=np.array([r['offset'] for r in panel]);goal=data['object'][:,-1,:2]-data['robot0_eef_pos'][:,-1,:2];expected=data['expected'][:,1]
def modes(a,idx):
    xy=np.linalg.norm(a[:,:2],axis=1);cos=(a[:,:2]*goal[idx]).sum(1)/np.maximum(xy*np.linalg.norm(goal[idx],axis=1),1e-9)
    lift=(xy<.12)&(a[:,2]>.02)&(a[:,-1]>0);transport=(xy>.25)&(cos>.5)&(a[:,2]<-.05)&(a[:,-1]>0);mixed=(xy>.25)&(a[:,2]>.02)&(a[:,-1]>0)
    return xy,cos,lift,transport,mixed
configs=json.loads((OUT/'protocol.json').read_text())['configs'];result={};paired={};forward={};profiles={};mode_trials=[]
for v in ('source','uniform','balanced'):
    result[v]={};paired[v]={};forward[v]={};profiles[v]={}
    for name in configs:
        path=OUT/v/(name+'.npz')
        if not path.exists():continue
        z=np.load(path);idx=z['panel_index'];draw=z['draw'];a=z['chunks'][:,1];xy,cos,lift,tr,mixed=modes(a,idx);score={};profiles[v][name]={}
        for region,oset in [('lift',range(-10,-5)),('pre',[-2,-1]),('post',[0,1,2]),('transport',range(6,11))]:
            mask=np.isin(off[idx],list(oset))&(draw<8);em=np.linalg.norm(expected[idx,:2],axis=1);active=mask&(em>.1)
            score[region]=dict(n=int(mask.sum()),xy=summary(xy[mask]),z=summary(a[mask,2]),ratio=summary(xy[active]/em[active]),lift_mode=float(lift[mask].mean()),transport_mode=float(tr[mask].mean()),mixed_mode=float(mixed[mask].mean()),opening=float((a[mask,-1]<0).mean()),goal_cosine=summary(cos[mask]))
        coexisting=[];stdxy=[];stdz=[]
        for i in np.flatnonzero(np.isin(off,[-1,0])):
            mask=idx==i;lp=float(lift[mask].mean());tp=float(tr[mask].mean());coexisting.append(lp>=.15 and tp>=.15);stdxy.append(float(xy[mask].std()));stdz.append(float(a[mask,2].std()));mode_trials.append(dict(model=v,sampler=name,demo=panel[i]['demo'],offset=int(off[i]),n=int(mask.sum()),lift_probability=lp,transport_probability=tp,xy_std=stdxy[-1],z_std=stdz[-1]))
        onset=[]
        for d in range(8):
            for demo in sorted(set(r['demo'] for r in panel)):
                ii=np.flatnonzero((draw==d)&np.array([panel[i]['demo']==demo for i in idx]));ii=ii[np.argsort(off[idx[ii]])];sig=(xy[ii]>.25)&(cos[ii]>.5);runs=np.flatnonzero(np.convolve(sig.astype(int),np.ones(3,int),'valid')==3);onset.append(int(off[idx[ii[runs[0]]]]) if len(runs) else None)
        score['sampling']=dict(boundary_states_with_both_modes_fraction=float(np.mean(coexisting)),xy_std=summary(stdxy),z_std=summary(stdz),onset_found_fraction=sum(o is not None for o in onset)/len(onset),premature_fraction=sum(o is not None and o<-2 for o in onset)/len(onset),on_time_fraction=sum(o is not None and abs(o)<=2 for o in onset)/len(onset),onset_steps=summary([o for o in onset if o is not None]))
        for o in range(-10,11):
            mask=(off[idx]==o)&(draw<8);profiles[v][name][o]=dict(xy=float(xy[mask].mean()),z=float(a[mask,2].mean()),lift=float(lift[mask].mean()),transport=float(tr[mask].mean()))
        result[v][name]=score
    for name in ('paired_ddim10','paired_ddim100'):
        path=OUT/v/(name+'.npz')
        if not path.exists():continue
        z=np.load(path);idx=z['panel_index'];draw=z['draw'];paired_chunks=z['chunks'];changes=[];expertchanges=[]
        for d in range(32):
            for demo in sorted(set(r['demo'] for r in panel)):
                ii=np.flatnonzero((draw==d)&np.array([panel[i]['demo']==demo for i in idx]));ii=ii[np.argsort(off[idx[ii]])];assert len(ii)==2
                changes.append(float(np.linalg.norm(paired_chunks[ii[1],1,:3]-paired_chunks[ii[0],1,:3])));expertchanges.append(float(np.linalg.norm(expected[idx[ii[1]],:3]-expected[idx[ii[0]],:3])))
        # At the first denoising step the two inputs have identical noisy actions.
        pathids=z['path_sample_index'];ep=z['epsilon_paths'];ratios=[]
        tim=int(z['timesteps'][0]);config=json.loads((OUT/v/(name+'_scheduler.json')).read_text())['scheduler'];from diffusers import DDIMScheduler
        sch=DDIMScheduler.from_config(config);alpha=float(sch.alphas_cumprod[tim]);factor=np.sqrt(alpha/(1-alpha))
        for d in range(8):
            for demo in sorted(set(panel[i]['demo'] for i in idx[pathids])):
                jj=np.flatnonzero((draw[pathids]==d)&np.array([panel[i]['demo']==demo for i in idx[pathids]]));jj=jj[np.argsort(off[idx[pathids[jj]]])];assert len(jj)==2
                got=np.linalg.norm(ep[jj[1],0,1,:3]-ep[jj[0],0,1,:3]);need=factor*np.linalg.norm(expected[idx[pathids[jj[1]]],:3]-expected[idx[pathids[jj[0]]],:3]);ratios.append(float(got/need))
        paired[v][name]=dict(action_xyz_change=summary(changes),expert_xyz_change=summary(expertchanges),model_change_over_expert_change=summary(np.array(changes)/np.array(expertchanges)),first_epsilon_response_over_deterministic_expert_required_response=summary(ratios))
    path=OUT/v/'forward_denoiser.npz'
    if path.exists():
        z=np.load(path)
        for j,t in enumerate(z['timesteps']):
            a=z['decoded'][j,:,1];xy,cos,lift,tr,mix=modes(a,np.arange(len(panel)));pre=np.isin(off,[-2,-1]);post=np.isin(off,[0,1,2]);forward[v][str(t)]=dict(pre_lift=float(lift[pre].mean()),post_transport=float(tr[post].mean()),xyz_mae=float(abs(a[:,:3]-expected[:,:3]).mean()),epsilon_mse=float(z['epsilon_squared_error'][j].mean()))
(OUT/'sampling_analysis.json').write_text(json.dumps(result,indent=2));(OUT/'paired_analysis.json').write_text(json.dumps(paired,indent=2));(OUT/'forward_analysis.json').write_text(json.dumps(forward,indent=2));(OUT/'mode_trials.json').write_text(json.dumps(mode_trials,indent=2))
fig,axes=plt.subplots(3,2,figsize=(11,10),sharex=True)
for row,v in enumerate(('source','uniform','balanced')):
    for name in ('ddim10','ddim100','ddpm100'):
        if name not in profiles[v]:continue
        pr=profiles[v][name];time=np.arange(-10,11)*.05
        for col,key in enumerate(('xy','z')):axes[row,col].plot(time,[pr[o][key] for o in range(-10,11)],label=name)
    ex=np.array([[np.linalg.norm(expected[off==o,:2],axis=1).mean(),expected[off==o,2].mean()] for o in range(-10,11)])
    for col in (0,1):axes[row,col].plot(time,ex[:,col],color='black',ls='--',label='Expert');axes[row,col].axvline(0,color='black',alpha=.3);axes[row,col].grid(alpha=.2);axes[row,col].legend();axes[row,col].set_ylabel(v)
axes[0,0].set_title('XY-Aktionsbetrag');axes[0,1].set_title('Z-Aktion')
for ax in axes[-1]:ax.set_xlabel('Sekunden relativ zum Expert-Wechsel')
fig.tight_layout();fig.savefig(OUT/'sampler_profiles.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(10,8))
for row,v in enumerate(('source','balanced')):
    for col,name in enumerate(('ddim10','ddim100')):
        path=OUT/v/(name+'.npz')
        if not path.exists():continue
        z=np.load(path);idx=z['panel_index'];a=z['chunks'][:,1];xy,cos,lift,tr,mix=modes(a,idx)
        for offset,color in [(-1,'#3977b7'),(0,'#d65b26')]:
            mask=(idx==(9 if offset==-1 else 10));proj=(a[mask,:2]*goal[idx[mask]]).sum(1)/np.linalg.norm(goal[idx[mask]],axis=1);axes[row,col].scatter(proj,a[mask,2],color=color,alpha=.65,label=f'offset {offset}, 32 draws')
        for i in (9,10):axes[row,col].scatter(np.dot(expected[i,:2],goal[i])/np.linalg.norm(goal[i]),expected[i,2],marker='X',s=100,color='black')
        axes[row,col].set_title(v+' '+name+' '+panel[9]['demo']);axes[row,col].set_xlabel('XY-Aktion zum Ziel projiziert');axes[row,col].set_ylabel('Z-Aktion');axes[row,col].grid(alpha=.2);axes[row,col].legend(fontsize=8)
fig.tight_layout();fig.savefig(OUT/'mode_scatter.png',dpi=160);plt.close(fig)
print(json.dumps(paired,indent=2))
