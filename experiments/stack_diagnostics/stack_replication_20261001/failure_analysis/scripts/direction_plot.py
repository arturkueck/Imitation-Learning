"""Conditional XY directions on a preselected demo, with strength and direction thresholds."""
import os
import numpy as np
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

demo=sorted({r['demo'] for r in META})[0]
fig,axes=plt.subplots(3,3,figsize=(12,11),sharex=True,sharey=True)
for row,seed in enumerate((1,2,3)):
    a=np.load(OUT/f'diffusion_seed{seed}_ddim10.npz')['chunks']
    for col,offset in enumerate((-1,0,8)):
        i=next(i for i,r in enumerate(META) if r['demo']==demo and r['offset']==offset)
        unit=GOAL[i]/np.linalg.norm(GOAL[i]);side=np.array([-unit[1],unit[0]])
        xy=a[i,:,1,:2];parallel=xy@unit;perp=xy@side
        norm=np.linalg.norm(xy,axis=1);cos=parallel/np.maximum(norm,1e-9);ok=(norm>.25)&(cos>.5)
        ax=axes[row,col]
        ax.scatter(parallel,perp,c=np.where(ok,'#2374ab','#e87524'),s=20,alpha=.7)
        expert=PANEL['expected'][i,1,:2]
        ax.scatter([expert@unit],[expert@side],marker='*',c='black',s=120,label='expert')
        ax.scatter([parallel.mean()],[perp.mean()],marker='X',c='#a02cab',s=65,label='sample mean')
        angle=np.linspace(0,2*np.pi,180)
        ax.plot(.25*np.cos(angle),.25*np.sin(angle),':',color='gray',linewidth=.8)
        ax.plot([0,.8],[0,.8*np.sqrt(3)],':',color='gray',linewidth=.8)
        ax.plot([0,.8],[0,-.8*np.sqrt(3)],':',color='gray',linewidth=.8)
        ax.axhline(0,color='gray',linewidth=.5);ax.axvline(0,color='gray',linewidth=.5)
        ax.set_aspect('equal');ax.set_xlim(-.75,1.5);ax.set_ylim(-1.2,1.2)
        ax.set_title(f'seed {seed}, {demo}, offset {offset}\nP(strong + targeted)={ok.mean():.1%}')
for ax in axes[:,0]:ax.set_ylabel('XY perpendicular to frozen goal direction')
for ax in axes[-1]:ax.set_xlabel('XY parallel to frozen EEF → goal direction')
axes[0,0].legend(fontsize=8)
fig.suptitle('64 samples per identical observation; blue: XY > .25 and goal cosine > .5; index 1')
fig.tight_layout();fig.savefig(OUT/'conditional_xy_direction.png',dpi=170);plt.close(fig)
