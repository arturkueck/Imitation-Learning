"""Paired trajectories and stage counts from stored rollouts, no simulation."""
import json,os
import numpy as np
from dynamics_common import OUT,extra_metrics
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'mpl_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
rr={v:json.loads((OUT/v/'rollouts/results.json').read_text()) for v in ('baseline','dynamics')}
assert all(len(r)==20 for r in rr.values())
by={v:{r['seed']:r for r in rows} for v,rows in rr.items()};matched=[s for s in by['baseline'] if by['baseline'][s]['correct_lift'] and by['dynamics'][s]['correct_lift']]
comparisons=dict(full_lift_in_both_seeds=matched,phase_differences={})
for key in ('grasp','lift','correct_lift','transport_started','premature_transport','near','position','lower','release','stack'):
    comparisons['phase_differences'][key]=dict(both=sum(by['baseline'][s][key] and by['dynamics'][s][key] for s in by['baseline']),baseline_only=sum(by['baseline'][s][key] and not by['dynamics'][s][key] for s in by['baseline']),dynamics_only=sum(not by['baseline'][s][key] and by['dynamics'][s][key] for s in by['baseline']))
(OUT/'rollout_matched.json').write_text(json.dumps(comparisons,indent=2))
full=[r for r in rr['baseline'] if r['correct_lift']];best=max(full,key=lambda r:(r['stack'],r['position'],r['near']))['seed'] if full else 46002
seeds=json.loads((OUT/'representative_seeds.json').read_text()) if (OUT/'representative_seeds.json').exists() else sorted(set([best,46004]));(OUT/'representative_seeds.json').write_text(json.dumps(seeds))
for seed in seeds:
    fig,axes=plt.subplots(4,2,figsize=(13,10),sharex=True)
    for col,v in enumerate(('baseline','dynamics')):
        z=np.load(OUT/v/'rollouts'/f'{seed}.npz');t=z['trace'];time=(t[:,0]+1)*.05;r=next(x for x in rr[v] if x['seed']==seed)
        axes[0,col].plot(time,t[:,6],label='Cube B height');axes[0,col].plot(time,t[:,17],label='EEF height',alpha=.7);axes[0,col].axhline(1.045,color='black',ls='--',label='Full lift B threshold');axes[0,col].set_ylabel('Height (m)');axes[0,col].set_title(f'{v}, seed {seed}')
        axes[1,col].plot(time,np.linalg.norm(t[:,4:6]-t[:,1:3],axis=1)*100,label='Cube-target XY');axes[1,col].axhline(3,color='black',ls='--',label='3 cm');axes[1,col].set_ylabel('XY distance (cm)')
        axes[2,col].plot(time,np.linalg.norm(t[:,20:22],axis=1),label='XY action');axes[2,col].plot(time,t[:,22],label='Z action',alpha=.7);axes[2,col].set_ylabel('Action')
        axes[3,col].plot(time,z['zz_dynamics'][:,-1,0],label='EEF dynamics');axes[3,col].plot(time,z['zz_dynamics'][:,-1,2],label='Cube dynamics',alpha=.7);axes[3,col].set_ylabel('Normalized delta Z');axes[3,col].set_xlabel('Seconds after reset')
        for row in range(4):
            ax=axes[row,col];ax.grid(alpha=.2);ax.legend(fontsize=8)
            if r['full_lift_end'] is not None:ax.axvline((r['full_lift_end']+1)*.05,color='green',ls=':')
            if r['transport_start'] is not None:ax.axvline((r['transport_start']+1)*.05,color='red',ls=':')
    fig.tight_layout();fig.savefig(OUT/f'rollout_pair_{seed}.png',dpi=150);plt.close(fig)
stages=['grasp','lift','correct_lift','transport_started','near','position','lower','release','sustained_success'];fig,ax=plt.subplots(figsize=(12,4));x=np.arange(len(stages))
for j,v in enumerate(rr):ax.bar(x+(j-.5)*.36,[sum(r[k] for r in rr[v]) for k in stages],width=.36,label=v)
ax.set_xticks(x,stages,rotation=20,ha='right');ax.set_ylim(0,20);ax.set_ylabel('Count / 20 fixed starts');ax.legend();fig.tight_layout();fig.savefig(OUT/'rollout_stages.png',dpi=150);plt.close(fig)
