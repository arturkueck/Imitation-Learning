"""Descriptive conditional density peaks and chunk coherence; no policy fitting."""
import numpy as np
from scipy.signal import find_peaks
from common import *

rows=[];coherence=[]
for seed in (1,2,3):
    path=OUT/f'diffusion_seed{seed}_ddim10.npz'
    if not path.exists():continue
    a=np.load(path)['chunks'];xy,xyz,cos=fields(a);unit=GOAL/np.linalg.norm(GOAL,axis=1)[:,None];project=(a[:,:,1,:2]*unit[:,None]).sum(-1)
    for i,meta in enumerate(META):
        v=project[i];std=float(v.std(ddof=1));h=max(.035,1.06*std*len(v)**(-.2));grid=np.linspace(-1.6,1.6,321);peaksets=[]
        for scale in (.7,1.,1.4):
            bw=h*scale;density=np.exp(-.5*((grid[:,None]-v[None])/bw)**2).mean(1)/(bw*np.sqrt(2*np.pi));peaks,_=find_peaks(density,prominence=.1*density.max(),distance=20)
            peaksets.append(grid[peaks].tolist())
        rows.append(dict(training_seed=seed,panel_index=i,demo=meta['demo'],offset=meta['offset'],chunk_index=1,draws=len(v),projection_std=std,kde_bandwidth=h,peak_locations_bw07=peaksets[0],peak_locations_bw10=peaksets[1],peak_locations_bw14=peaksets[2],two_or_more_peaks_all_bandwidths=all(len(x)>=2 for x in peaksets),method='Gaussian KDE of signed goal projection; grid .01, peak distance >=.20, prominence >=10% global max; descriptive, no significance test'))
    for group,mask in [('before_switch',OFFSETS<0),('after_switch_0_2',(OFFSETS>=0)&(OFFSETS<=2)),('transport_6_10',OFFSETS>=6)]:
        strong=(xy[mask]>.25)&(cos[mask]>.5)&(a[mask,:,:,6]>0);p1=float(strong[:,:,1].mean());angle=(a[mask,:,1,:2]*a[mask,:,3,:2]).sum(-1)/np.maximum(xy[mask,:,1]*xy[mask,:,3],1e-9);active=(xy[mask,:,1]>.05)&(xy[mask,:,3]>.05)
        coherence.append(dict(seed=seed,group=group,p_strong_targeted_closed_first=p1,p_all_first2_strong_targeted_closed=float(strong[:,:,1:3].all(-1).mean()),p_all_first4_strong_targeted_closed=float(strong[:,:,1:5].all(-1).mean()),p_four_coherent_given_first_strong=float(strong[:,:,1:5].all(-1).sum()/max(strong[:,:,1].sum(),1)),mean_cosine_index1_vs3_when_active=float(angle[active].mean()) if active.any() else None,p_gripper_sign_change_inside_first4=float((np.sign(a[mask,:,1:4,6])!=np.sign(a[mask,:,2:5,6])).any(-1).mean())))
dump('conditional_density_modes.json',rows);dump('chunk_coherence.json',coherence)
print(json.dumps([dict(seed=s,transport_observations=100,robust_multiple_kde_peak_fraction=float(np.mean([r['two_or_more_peaks_all_bandwidths'] for r in rows if r['training_seed']==s and r['offset']>=6]))) for s in (1,2,3) if any(r['training_seed']==s for r in rows)]))
