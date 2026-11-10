"""Observed commands around first non-task-valid grasp loss; descriptive event selection."""
import os
import numpy as np
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base=json.loads((OUT/'baseline_failures.json').read_text());events=json.loads((OUT/'baseline_events.json').read_text())
bykey={(r['model'],r['training_seed'],r['start_seed']):r for r in base}
windows={'direct':[],'diffusion':[]};rows=[];offsets=np.arange(-10,11)
for r in events:
    lost=[e for e in r['losses'] if not e['task_valid_release']]
    if not lost:continue
    e=lost[0];kind=r['model'];seed=r['training_seed'];start=r['start_seed'];b=bykey[kind,seed,start]
    t=np.load(rollouts(kind,seed)/f'{start}.npz')['trace'][:r['measured_steps']]
    ids=e['post_step_index']+offsets;valid=(ids>=0)&(ids<len(t));w=np.full((21,3),np.nan)
    actions=t[ids[valid],20:27];w[valid]=np.stack([np.linalg.norm(actions[:,:2],axis=1),actions[:,2],actions[:,6]],axis=1)
    windows[kind].append(w)
    rows.append(dict(model=kind,training_seed=seed,start_seed=start,stable_case=b['sustained_success'],**e))
csvwrite('loss_first_events.csv',rows)
summaries=[]
for kind in ('direct','diffusion'):
    for seed in (1,2,3):
        rr=[r for r in rows if r['model']==kind and r['training_seed']==seed]
        summaries.append(dict(model=kind,seed=seed,first_events=len(rr),opening_at_event=sum(r['opening_at_event'] for r in rr),sustained3_frames=sum(r['sustained_at_least3_frames'] for r in rr),xy_before_median=float(np.median([r['xy_before'] for r in rr])),xyz_before_median=float(np.median([r['xyz_before'] for r in rr])),target_distance_cm_median=float(np.median([r['xy_distance_m'] for r in rr])*100)))
all_diff=[e for r in events if r['model']=='diffusion' for e in r['losses'] if not e['task_valid_release']]
dump('loss_event_summary.json',dict(first_event_by_seed=summaries,diffusion_all_events=len(all_diff),diffusion_events_farther_than3cm=sum(e['xy_distance_m']>.03 for e in all_diff),diffusion_opening_events_farther_than3cm=sum(e['opening_at_event'] and e['xy_distance_m']>.03 for e in all_diff),selection='First non-task-valid native grasp loss per start; conditional event selection; descriptive medians and IQR, no confidence interval or causal estimate'))
fig,axes=plt.subplots(1,4,figsize=(16,4.5));colors={'direct':'#2374ab','diffusion':'#e87524'}
for kind in ('direct','diffusion'):
    a=np.array(windows[kind]);color=colors[kind]
    for j,ax in enumerate(axes[:3]):
        med=np.nanmedian(a[:,:,j],axis=0);lo,hi=np.nanquantile(a[:,:,j],[.25,.75],axis=0)
        ax.plot(offsets*.05,med,color=color,label=f'{kind}, {len(a)} starts');ax.fill_between(offsets*.05,lo,hi,color=color,alpha=.15)
    for opening,marker in [(True,'^'),(False,'o')]:
        rr=[r for r in rows if r['model']==kind and r['opening_at_event']==opening]
        axes[3].scatter([r['xy_before'] for r in rr],[r['xy_distance_m']*100 for r in rr],color=color,marker=marker,s=24,alpha=.65,label=f'{kind}, '+('opens at loss' if opening else 'closed at loss'))
for ax,label in zip(axes[:3],['XY norm','Signed Z command','Gripper command']):
    ax.axvline(0,color='black',linestyle=':',linewidth=.8);ax.set_xlabel('Time relative to grasp loss (s)');ax.set_ylabel(label);ax.grid(alpha=.15)
axes[2].set_ylim(-1.1,1.1);axes[0].legend(fontsize=8)
axes[3].set_xlabel('XY norm immediately before loss');axes[3].set_ylabel('B→A XY distance at loss (cm)');axes[3].axhline(3,color='gray',linestyle=':',linewidth=.8);axes[3].legend(fontsize=7);axes[3].grid(alpha=.15)
fig.suptitle('Historical first non-task-valid grasp loss; median and IQR across selected starts; no causal estimate')
fig.tight_layout();fig.savefig(OUT/'loss_aligned_actions.png',dpi=170);plt.close(fig)
print(json.dumps(summaries));print('Diffusion loss events >3cm:',sum(e['xy_distance_m']>.03 for e in all_diff),'/',len(all_diff))
