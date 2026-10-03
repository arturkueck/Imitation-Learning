"""Descriptive joint goal-projection/Z density peaks, conditional on each observation."""
import os
import numpy as np
from scipy.ndimage import maximum_filter
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

x=np.linspace(-1.5,1.5,61);z=np.linspace(-1.05,1.05,43);xx,zz=np.meshgrid(x,z);grid=np.stack([xx.ravel(),zz.ravel()],axis=1)
def density_peaks(v,scale=1.):
    cov=np.cov(v.T)*len(v)**(-1/3)*scale**2+np.eye(2)*1e-6;inv=np.linalg.inv(cov);delta=grid[:,None]-v[None]
    q=inv[0,0]*delta[:,:,0]**2+2*inv[0,1]*delta[:,:,0]*delta[:,:,1]+inv[1,1]*delta[:,:,1]**2
    density=np.exp(-q/2).mean(1).reshape(xx.shape)/(2*np.pi*np.sqrt(np.linalg.det(cov)))
    loc=(density==maximum_filter(density,size=5))&(density>=.15*density.max());loc[[0,-1],:]=False;loc[:,[0,-1]]=False;ii=np.argwhere(loc);ii=sorted(ii,key=lambda ij:density[tuple(ij)],reverse=True);peaks=[]
    for iz,ix in ii:
        p=np.array([x[ix],z[iz]])
        if all(np.linalg.norm(p-vv)>=.2 for vv in peaks):peaks.append(p)
    if peaks:
        nearest=np.argmin(np.linalg.norm(v[:,None]-np.array(peaks)[None],axis=-1),axis=1);mass=np.bincount(nearest,minlength=len(peaks))/len(v);peaks=[p.tolist() for p,m in zip(peaks,mass) if m>=.1]
    return density,peaks

rows=[];fig,axes=plt.subplots(3,2,figsize=(11,11),sharex=True,sharey=True);demo=sorted({r['demo'] for r in META})[0]
for row,seed in enumerate((1,2,3)):
    a=np.load(OUT/f'diffusion_seed{seed}_ddim10.npz')['chunks'];unit=GOAL/np.linalg.norm(GOAL,axis=1)[:,None];proj=(a[:,:,1,:2]*unit[:,None]).sum(-1)
    for i,meta in enumerate(META):
        v=np.stack([proj[i],a[i,:,1,2]],axis=1);sets=[];base_density=None
        for scale in (.7,1.,1.4):
            density,peaks=density_peaks(v,scale);sets.append(peaks)
            if scale==1:base_density=density
        rows.append(dict(seed=seed,panel_index=i,demo=meta['demo'],offset=meta['offset'],draws=64,peaks_bw07=sets[0],peaks_bw10=sets[1],peaks_bw14=sets[2],two_or_more_peaks_all_bandwidths=all(len(p)>=2 for p in sets),method='Gaussian joint KDE: Scott bandwidth × .7/1/1.4; local max 5x5 cells; density >=15% maximum; peak separation >=.20; nearest-peak sample mass >=10%; descriptive only'))
        if meta['demo']==demo and meta['offset'] in (0,8):
            ax=axes[row,0 if meta['offset']==0 else 1];ax.contourf(xx,zz,base_density,levels=15,cmap='Blues');ax.scatter(v[:,0],v[:,1],s=13,c='#e87524',alpha=.65);ex=PANEL['expected'][i,1];ax.scatter([ex[:2]@unit[i]],[ex[2]],marker='*',s=110,c='black');ax.scatter([v[:,0].mean()],[v[:,1].mean()],marker='X',s=70,c='#a02cab');ax.set_title(f"seed {seed}, {demo}, offset {meta['offset']}\nconditional KDE peaks (bw .7/1/1.4): "+'/'.join(str(len(p)) for p in sets));ax.set_xlim(-.7,1.5);ax.set_ylim(-1.05,1.05)
    print('SEED',seed,'transport robust 2D peak fraction',np.mean([r['two_or_more_peaks_all_bandwidths'] for r in rows if r['seed']==seed and r['offset']>=6]),flush=True)
for ax in axes[:,0]:ax.set_ylabel('Z command')
for ax in axes[-1]:ax.set_xlabel('Signed XY goal projection')
fig.suptitle('Conditional joint densities: 64 samples each; star = expert; purple X = mean; no formal modality test');fig.tight_layout();fig.savefig(OUT/'conditional_joint_density.png',dpi=170);plt.close(fig);dump('conditional_joint_density_modes.json',rows)
