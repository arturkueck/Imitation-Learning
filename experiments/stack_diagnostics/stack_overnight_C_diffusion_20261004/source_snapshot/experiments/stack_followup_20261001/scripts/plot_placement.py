from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[3]
os.environ['MPLCONFIGDIR']=str(ROOT/'praxis/.cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=ROOT/'experiments/stack_placement_20261001'
for seed in (46000,46003,46006):
    fig,axs=plt.subplots(4,1,figsize=(11,10),sharex=True)
    for variant in ('baseline','release_gate','xy_feedback'):
        p=OUT/variant/f'{seed}.npz'
        if not p.exists(): continue
        t=np.load(p)['trace']; time=t[:,0]/20; delta=t[:,4:7]-t[:,1:4]
        axs[0].plot(time,np.linalg.norm(delta[:,:2],axis=1)*1000,label=variant)
        axs[1].plot(time,delta[:,2]*1000,label=variant)
        axs[2].plot(time,t[:,26],label=variant,alpha=.7)
        axs[3].plot(time,abs(t[:,18]-t[:,19])*1000,label=variant)
    axs[0].axhline(9,color='k',ls=':'); axs[1].axhspan(32,48,color='green',alpha=.1)
    for ax,label in zip(axs,['XY error (mm)','B above A (mm)','Gripper action (+ close)','Finger separation (mm)']):
        ax.set_ylabel(label); ax.grid(alpha=.3)
    axs[0].legend(); axs[-1].set_xlabel('Simulation time (s)')
    fig.suptitle(f'Paired placement interventions — seed {seed}')
    fig.tight_layout(); fig.savefig(OUT/f'trace_{seed}.png',dpi=150); plt.close(fig)
