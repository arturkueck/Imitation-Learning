import json
import numpy as np
from transport_data import demos,ROOT,OUT
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ds=demos(); time=np.arange(81)/20; expert_dist=[];expert_eef=[];expert_height=[];pol_dist=[];pol_eef=[];pol_height=[]; pol_records=[]
for d in ds:
    o=d['obs']['object']; e=d['obs']['robot0_eef_pos']; ids=np.flatnonzero(o[:,5]>.88)
    if not len(ids):continue
    idx=np.minimum(ids[0]+np.arange(81),len(o)-1); dist=np.linalg.norm(o[idx,:2]-o[idx,3:5],axis=1)
    expert_dist.append(dist/dist[0]);expert_eef.append(np.linalg.norm(o[idx,:2]-e[idx,:2],axis=1));expert_height.append(o[idx,5]-.8)
for p in sorted((ROOT/'experiments/stack_diagnostics/stack_placement_20261001/baseline').glob('*.npz')):
    t=np.load(p)['trace'];ids=np.flatnonzero((t[:,6]>.88)&(t[:,34]>0))
    if not len(ids):continue
    idx=np.minimum(ids[0]+np.arange(81),len(t)-1);dist=np.linalg.norm(t[idx,1:3]-t[idx,4:6],axis=1)
    pol_dist.append(dist/dist[0]);pol_eef.append(np.linalg.norm(t[idx,1:3]-t[idx,15:17],axis=1));pol_height.append(t[idx,6]-.8)
    pol_records.append(dict(seed=int(p.stem),start_distance_mm=float(dist[0]*1000),distance_after_2s_mm=float(dist[40]*1000),distance_after_4s_mm=float(dist[-1]*1000)))
fig,ax=plt.subplots(1,3,figsize=(14,4.5))
for arrays,label,color in (([expert_dist,expert_eef,expert_height],'Expert, 200 demos','tab:blue'),([pol_dist,pol_eef,pol_height],'Policy, 13 held lifts','tab:orange')):
    for j,array in enumerate(arrays):
        a=np.array(array);lo,mid,hi=np.quantile(a,[.1,.5,.9],axis=0);scale=1000 if j else 1
        ax[j].plot(time,mid*scale,label=label,color=color);ax[j].fill_between(time,lo*scale,hi*scale,color=color,alpha=.15)
for j,label in enumerate(['Cube-target distance / initial distance','EEF-target distance (mm)','Cube above table (mm)']):
    ax[j].set_ylabel(label);ax[j].set_xlabel('Seconds after crossing +80 mm');ax[j].grid(alpha=.3)
ax[0].legend();fig.suptitle('Same lift event; median and 10–90% range, no correction')
fig.tight_layout();fig.savefig(OUT/'lift_to_transport_comparison.png',dpi=160);plt.close(fig)
data=json.loads((OUT/'data_behavior.json').read_text())
fig,axs=plt.subplots(1,3,figsize=(14,4))
vec=np.array([r['goal_vector'] for r in data['demos']]);axs[0].scatter(vec[:,0]*1000,vec[:,1]*1000,s=15,alpha=.7);axs[0].axhline(0,color='gray',lw=.5);axs[0].axvline(0,color='gray',lw=.5);axs[0].set_aspect('equal');axs[0].set_xlabel('A-B X (mm)');axs[0].set_ylabel('A-B Y (mm)')
axs[1].hist([r['distance_m']*1000 for r in data['demos']],bins=15);axs[1].set_xlabel('Initial transport distance (mm)')
axs[2].bar(range(8),[data['direction_sectors'][str(i)] for i in range(8)]);axs[2].set_xlabel('Direction sector (45 degrees)')
fig.suptitle('200 demonstration starts');fig.tight_layout();fig.savefig(OUT/'transport_distribution.png',dpi=160);plt.close(fig)
pred=np.load(OUT/'baseline_teacher_predictions.npz'); phase=pred['phase']; sp=pred['split']; expected=pred['expected'];y=pred['predictions'][:,:,0]
mask=(phase==4)&(sp=='valid');e=np.linalg.norm(expected[mask,:2],axis=1);p=np.linalg.norm(y[:,mask,:2],axis=2)
fig,axs=plt.subplots(1,2,figsize=(11,4))
axs[0].scatter(np.tile(e,3),p.ravel(),s=10,alpha=.3);axs[0].plot([0,1.5],[0,1.5],'k:');axs[0].set_xlabel('Expert XY action magnitude');axs[0].set_ylabel('Policy on exact expert observations')
probe=json.loads((OUT/'baseline_prediction_analysis.json').read_text())['rollout_observation_probe']; rr=[probe[k]['xy_magnitude_ratio']['q'][2] for k in ('original','raised_to_expert_height')]
axs[1].bar(['Recorded height','Expert transport height'],rr);axs[1].set_ylabel('Median predicted XY / desired XY');axs[1].set_ylim(0,1)
fig.tight_layout();fig.savefig(OUT/'action_prediction_comparison.png',dpi=160);plt.close(fig)
result=dict(expert_distance_ratio_after_2s=np.quantile(np.array(expert_dist)[:,40],[.1,.5,.9]).tolist(),policy_distance_ratio_after_2s=np.quantile(np.array(pol_dist)[:,40],[.1,.5,.9]).tolist(),
    expert_distance_ratio_after_4s=np.quantile(np.array(expert_dist)[:,-1],[.1,.5,.9]).tolist(),policy_distance_ratio_after_4s=np.quantile(np.array(pol_dist)[:,-1],[.1,.5,.9]).tolist(),policy_rollouts=pol_records,
    caveat='Expert arrays hold last recorded sample after demo termination. Policy curves include grip loss after initial held lift; starts differ between demo set and fixed rollout set.')
(OUT/'aligned_trajectories.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='policy_rollouts'},indent=2))
fig,axs=plt.subplots(1,3,figsize=(14,4.5));matches=[]
for ax,seed in zip(axs,(46000,46006,46014)):
    t=np.load(ROOT/f'experiments/stack_diagnostics/stack_placement_20261001/baseline/{seed}.npz')['trace'];i=np.flatnonzero((t[:,6]>.88)&(t[:,34]>0))[0]
    vector=t[0,1:3]-t[0,4:6]
    d=min(ds,key=lambda d:np.linalg.norm(d['obs']['object'][0,:2]-d['obs']['object'][0,3:5]-vector))
    o=d['obs']['object'];e=d['obs']['robot0_eef_pos'];first=np.flatnonzero(o[:,5]>.88)[0];end=np.flatnonzero(d['phase']==6)[0]
    pp=t[i:min(i+80,len(t))];de=o[first:end+1];ee=e[first:end+1]
    for path,label,color,style in ((de[:,3:5]-de[:,:2],'Expert cube','tab:blue','-'),(ee[:,:2]-de[:,:2],'Expert EEF','tab:blue','--'),(pp[:,4:6]-pp[:,1:3],'Policy cube','tab:orange','-'),(pp[:,15:17]-pp[:,1:3],'Policy EEF','tab:orange','--')):
        ax.plot(path[:,0]*1000,path[:,1]*1000,label=label,color=color,ls=style);ax.scatter(path[0,0]*1000,path[0,1]*1000,color=color,s=20)
    ax.scatter(0,0,color='black',marker='x',s=70);ax.set_aspect('equal');ax.grid(alpha=.3);ax.set_xlabel('X relative to target A (mm)');ax.set_ylabel('Y relative to target A (mm)');ax.set_title(f'Seed {seed} / {d["name"]}')
    matches.append(dict(seed=seed,matched_demo=d['name'],initial_vector_difference_m=float(np.linalg.norm(d['obs']['object'][0,:2]-d['obs']['object'][0,3:5]-vector))))
axs[0].legend(fontsize=8);fig.suptitle('Nearest initial goal vector; expert lift-to-release vs policy first 4 s after held lift')
fig.tight_layout();fig.savefig(OUT/'relative_xy_paths.png',dpi=160);plt.close(fig)
(OUT/'relative_path_matches.json').write_text(json.dumps(matches,indent=2))
