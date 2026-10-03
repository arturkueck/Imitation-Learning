"""Controlled inference interventions; plot each training replicate separately."""
import os
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rs=json.loads((OUT/'closed_loop_summary.json').read_text())
colors=['#275d91','#dc8436','#678c41']
fig,axes=plt.subplots(2,3,figsize=(13,8))
keys=['stable_stacks','max_height_m_median','held_lifted_min_distance_m_median'];labels=['Stable stacks / same 40 starts','Median maximum cube B height (m)','Median minimum XY distance\nwhile held and lifted (m)']
for row,kind in enumerate(('direct','diffusion')):
    for col,(key,label) in enumerate(zip(keys,labels)):
        ax=axes[row,col]
        for seed,color in zip((1,2,3),colors):
            rr=sorted([r for r in rs if r['model']==kind and r['training_seed']==seed and r['comparison_group']=='replanning'],key=lambda r:r['executed_actions'])
            rr=[r for r in rr if r[key] is not None]
            if rr:ax.plot([r['executed_actions'] for r in rr],[r[key] for r in rr],'-o',color=color,label=f'train seed {seed}')
        ax.set_title(kind);ax.set_xlabel('Actions executed per predicted chunk');ax.set_xticks([1,2,4]);ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=8)
        if key=='stable_stacks':ax.set_ylim(-1,41)
fig.suptitle('Execution horizon only; same weights, starts and DDIM-10; each line = one training replicate')
fig.tight_layout();fig.savefig(OUT/'replanning_closed_loop.png',dpi=170);plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(13,4.5))
for ax,key,label in zip(axes,keys,labels):
    for seed,color in zip((1,2,3),colors):
        rr=sorted([r for r in rs if r['model']=='diffusion' and r['training_seed']==seed and r['comparison_group']=='ddim'],key=lambda r:r['ddim_steps']);rr=[r for r in rr if r[key] is not None]
        if rr:ax.plot([r['ddim_steps'] for r in rr],[r[key] for r in rr],'-o',color=color,label=f'train seed {seed}')
    ax.set_xticks([5,10,50]);ax.set_xlabel('DDIM inference steps (2 actions executed)');ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=8)
    if key=='stable_stacks':ax.set_ylim(-1,41)
fig.suptitle('Offline-selected endpoints and fresh matched DDIM-10 baseline; same 40 starts')
fig.tight_layout();fig.savefig(OUT/'ddim_closed_loop.png',dpi=170);plt.close(fig)

# Replanning-related reversals are descriptive event counts, not significance tests.
path=OUT/'closed_loop_action_coherence.json'
if path.exists():
    data=json.loads(path.read_text());fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,metric,label in zip(axes,['xy_reversals','gripper_sign_switches'],['XY direction reversals / eligible pair','Gripper sign switches / eligible pair']):
        for h in (1,2,4):
            for loc,style in [('replan_boundary','-'),('within_chunk','--')]:
                values=[]
                for seed in (1,2,3):
                    rows=[r for r in data if r['model']=='diffusion' and r['training_seed']==seed and r['executed_actions']==h and r['comparison_group']=='replanning'];pairs=[p for r in rows for p in r['pairs'] if p['location']==loc];total=sum(p['n_pairs'] for p in pairs)
                    values.append(sum(p[metric] for p in pairs)/total if total else np.nan)
                if np.isfinite(values).any():ax.plot([1,2,3],values,style+'o',label=f'h={h}, {loc}')
        ax.set_xticks([1,2,3]);ax.set_xlabel('Training seed');ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('Eligible = held and lifted in both frames, both XY norms > .05; no causal interpretation')
    fig.tight_layout();fig.savefig(OUT/'replanning_action_reversals.png',dpi=170);plt.close(fig)
