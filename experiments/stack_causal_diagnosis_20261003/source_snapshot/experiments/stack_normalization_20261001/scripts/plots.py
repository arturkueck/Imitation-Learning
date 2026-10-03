"""Descriptive training-seed points; no inference draws counted as replicates."""
import os
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def make(cells):
    fig,ax=plt.subplots(figsize=(9,4.5))
    for i,v in enumerate(('A','B','C','D')):
        for kind,delta,color in (('direct',-.14,'tab:blue'),('diffusion',.14,'tab:orange')):
            rows=[c for c in cells if c['variant']==v and c['model_class']==kind]
            if not rows:continue
            vals=[r['rollout']['counts']['sustained_success']/40*100 for r in rows]
            ax.bar(i+delta,np.mean(vals),width=.25,color=color,alpha=.3,label=kind if i==0 else None)
            for j,val in enumerate(vals):ax.scatter(i+delta+(j-(len(vals)-1)/2)*.035,val,color=color,s=35,zorder=4)
            label=', '.join(str(r['rollout']['counts']['sustained_success']) for r in rows)+'/40'
            ax.text(i+delta,max(vals)+3,label,ha='center',fontsize=8)
    ax.set_xticks(range(4),['A\nnone','B\nactions','C\nobservations','D\nboth']);ax.set_ylim(-3,108)
    ax.set_ylabel('Stable stacks (%)');ax.set_title('Normalization only; each point is one training seed')
    ax.grid(axis='y',alpha=.2);ax.legend();fig.tight_layout();fig.savefig(OUT/'normalization_success.png',dpi=160);plt.close(fig)
    rows=[r for r in read(OUT/'normalization_stats.json')['raw_channel_statistics'] if r['group']=='action']
    fig,ax=plt.subplots(figsize=(8,3.8));vals=[r['std'] for r in rows]
    ax.bar(range(7),vals,color=['tab:blue']*3+['gray']*3+['tab:orange'])
    for i,v in enumerate(vals):ax.text(i,v+.02,f'{v:.3f}' if v else 'constant 0',ha='center',fontsize=9)
    ax.set_xticks(range(7),['X','Y','Z','Rot X','Rot Y','Rot Z','Gripper']);ax.set_ylim(0,1.12)
    ax.set_ylabel('Population standard deviation');ax.set_title('27,322 train frames; raw controller actions')
    ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(OUT/'action_channel_std.png',dpi=160);plt.close(fig)
