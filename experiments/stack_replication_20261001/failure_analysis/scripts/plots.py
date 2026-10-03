"""Static scientific figures; conditional distributions never pool differing states."""
import os
from common import *
os.environ['MPLCONFIGDIR']=str(OUT/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm

plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
COL={'direct':'#2374ab','diffusion':'#e87524'}

def save(fig,name):
    fig.tight_layout();fig.savefig(OUT/name,dpi=170);plt.close(fig)

def chunkplots():
    rs=json.loads((OUT/'chunk_position_metrics.json').read_text());fig,axes=plt.subplots(3,2,figsize=(13,11),sharex=True)
    metrics=[('xyz_mean','XYZ command norm'),('xy_mean','XY command norm'),('z_mean','Signed Z command'),('goal_cosine_mean','Cosine to frozen EEF → goal XY'),('gripper_mean','Gripper command (+ = close)'),('expert_rmse_xyz','XYZ RMSE against expert chunk')]
    styles=['-','--',':']
    for ax,(key,label) in zip(axes.flat,metrics):
        for kind in ('direct','diffusion'):
            for seed in (1,2,3):
                rows=sorted([r for r in rs if r['model']==kind and r['training_seed']==seed and r['group']=='transport_6_10' and (kind=='direct' or r['ddim_steps']==10)],key=lambda r:r['chunk_index'])
                if len(rows)!=16:continue
                ax.plot(range(16),[r[key] for r in rows],color=COL[kind],linestyle=styles[seed-1],label=f'{kind} seed {seed}')
        if key in ('xyz_mean','xy_mean','z_mean','gripper_mean'):
            ek={'xyz_mean':'expert_xyz_mean','xy_mean':'expert_xy_mean','z_mean':'expert_z_mean','gripper_mean':'expert_gripper_mean'}[key]
            er=sorted([r for r in rs if r['model']=='direct' and r['training_seed']==1 and r['group']=='transport_6_10'],key=lambda r:r['chunk_index']);ax.plot(range(16),[r[ek] for r in er],color='black',linewidth=2,label='expert future chunk')
        ax.axvspan(.6,2.4,color='#bbcddd',alpha=.25);ax.set_ylabel(label);ax.grid(alpha=.2)
        if key=='gripper_mean':ax.set_ylim(-1.05,1.05)
    axes[0,0].legend(ncol=2,fontsize=8);axes[0,1].legend(ncol=2,fontsize=8)
    for ax in axes[-1]:ax.set_xlabel('Raw chunk index (0 = previous action; 1 = first executed)');ax.set_xticks(range(16))
    fig.suptitle('Same 100 frozen transport observations (+6…+10 frames); shade = baseline executes indices 1,2',fontsize=12)
    save(fig,'chunk_profiles.png')
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    for ax,key,label in zip(axes,['sample_var_xyz_sum_mean','z_abs_fraction_xyz_mean','p_strong_targeted'],['Within-observation sample variance: XYZ trace','Mean |Z| / XYZ norm','P(XY > .25 and target cosine > .5)']):
        for seed in (1,2,3):
            rr=sorted([r for r in rs if r['model']=='diffusion' and r['training_seed']==seed and r['ddim_steps']==10 and r['group']=='transport_6_10'],key=lambda r:r['chunk_index'])
            if len(rr)==16:ax.plot(range(16),[r[key] for r in rr],label=f'seed {seed}')
        ax.set_xlabel('Raw chunk index');ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend();ax.axvspan(.6,2.4,color='gray',alpha=.12)
    save(fig,'chunk_variance_probability.png')

def sampleplots():
    paths=[OUT/f'diffusion_seed{s}_ddim10.npz' for s in (1,2,3)]
    if not all(p.exists() for p in paths):return
    # Lexicographically first validation demo fixed before inspecting predictions.
    demo=sorted({r['demo'] for r in META})[0];fig,axes=plt.subplots(3,3,figsize=(12,10),sharex=True,sharey=True)
    for row,seed in enumerate((1,2,3)):
        a=np.load(paths[row])['chunks']
        for col,offset in enumerate((-1,0,8)):
            i=next(i for i,r in enumerate(META) if r['demo']==demo and r['offset']==offset);g=GOAL[i]/np.linalg.norm(GOAL[i]);projection=a[i,:,1,:2]@g;z=a[i,:,1,2];xy=np.linalg.norm(a[i,:,1,:2],axis=1);cos=projection/np.maximum(xy,1e-9);strong=(xy>.25)&(cos>.5)
            ax=axes[row,col];ax.scatter(projection,z,c=np.where(strong,COL['direct'],COL['diffusion']),s=20,alpha=.7);ex=PANEL['expected'][i,1];ax.scatter([ex[:2]@g],[ex[2]],marker='*',c='black',s=130,label='expert');ax.scatter([projection.mean()],[z.mean()],marker='X',c='#a02cab',s=70,label='sample mean');ax.axvline(.25,color='gray',linestyle=':');ax.axhline(0,color='gray',linewidth=.5);ax.grid(alpha=.15);ax.set_title(f'seed {seed}, {demo}, offset {offset}\nP(strong and targeted)={strong.mean():.1%}');ax.set_xlim(-.7,1.5);ax.set_ylim(-1.05,1.05)
    for ax in axes[:,0]:ax.set_ylabel('Z command')
    for ax in axes[-1]:ax.set_xlabel('XY projection on EEF → goal unit vector')
    axes[0,0].legend(fontsize=8);fig.suptitle('64 samples of one identical observation per panel; blue = strong and targeted')
    save(fig,'conditional_sample_modes.png')
    fig,axes=plt.subplots(3,2,figsize=(12,10));names=sorted({r['demo'] for r in META})
    for row,seed in enumerate((1,2,3)):
        a=np.load(paths[row])['chunks'];x,_,c=fields(a);prob=((x[:,:,1]>.25)&(c[:,:,1]>.5)).mean(1);lift=(x[:,:,1]<.12)&(a[:,:,1,2]>.02)&(a[:,:,1,6]>0);tr=(x[:,:,1]>.25)&(c[:,:,1]>.5)&(a[:,:,1,2]<-.05)&(a[:,:,1,6]>0);both=(lift.mean(1)>=.15)&(tr.mean(1)>=.15)
        for col,values in enumerate((prob,both)):
            matrix=np.array([[values[next(i for i,r in enumerate(META) if r['demo']==name and r['offset']==o)] for o in range(-10,11)] for name in names]);im=axes[row,col].imshow(matrix,vmin=0,vmax=1,cmap='viridis',aspect='auto');axes[row,col].axvline(9.5,color='white',linewidth=.8);axes[row,col].set_title(f'seed {seed}: '+('P(strong and targeted)' if col==0 else 'Lift and transport each ≥15% of 64 draws'));axes[row,col].set_xticks([0,5,10,15,20],[-10,-5,0,5,10]);axes[row,col].set_yticks([0,9,19],[names[i] for i in (0,9,19)]);fig.colorbar(im,ax=axes[row,col],fraction=.045)
    for ax in axes[-1]:ax.set_xlabel('Frames relative to expert switch')
    save(fig,'conditional_probabilities.png')
    fig,axes=plt.subplots(1,3,figsize=(14,4),sharex=True,sharey=True)
    for ax,seed in zip(axes,(1,2,3)):
        for steps in (5,10,20,50):
            path=OUT/f'diffusion_seed{seed}_ddim{steps}.npz'
            if not path.exists():continue
            a=np.load(path)['chunks'];xy,_,cos=fields(a);mask=OFFSETS>=6
            ax.scatter(xy[mask,:,1].mean(),cos[mask,:,1].mean(),s=40+steps*2,label=f'DDIM {steps}')
        ax.set_title(f'seed {seed}');ax.set_xlabel('Mean sample XY norm');ax.set_ylabel('Mean sample target cosine');ax.legend();ax.grid(alpha=.2)
    fig.suptitle('DDIM comparison, same frozen transport states and 64 paired initial noises')
    save(fig,'ddim_offline.png')

def failureplots():
    rs=json.loads((OUT/'baseline_failures.json').read_text());from localise import ORDER
    fig,axes=plt.subplots(3,1,figsize=(14,9),sharex=True);labels=[f'{k} / {s}' for k in ('direct','diffusion') for s in (1,2,3)]
    matrices=[]
    for key in ('first_unfulfilled_task_indicator','max_cube_height_m','first_accidental_loss_seconds'):
        matrix=[]
        for kind in ('direct','diffusion'):
            for seed in (1,2,3):
                rows=sorted([r for r in rs if r['model']==kind and r['training_seed']==seed],key=lambda r:r['start_seed']);matrix.append([(ORDER.index(r[key])+1 if r[key] else 0) if key== 'first_unfulfilled_task_indicator' else (r[key] if r[key] is not None else np.nan) for r in rows])
        matrices.append(np.array(matrix))
    cmap=ListedColormap(['#2c9c69','#e0e0e0','#f9ce6b','#f0994e','#d95c47','#c13776','#97448c','#6a4c93','#333333'])
    im=axes[0].imshow(matrices[0],aspect='auto',cmap=cmap,norm=BoundaryNorm(np.arange(-.5,9.5),9));cb=fig.colorbar(im,ax=axes[0],ticks=range(9),fraction=.025,pad=.02);cb.ax.set_yticklabels(['success']+ORDER);axes[0].set_title('First unfulfilled task indicator; expert full height excluded (not required for success)')
    for ax,m,title,cmap in zip(axes[1:],matrices[1:],['Maximum cube B height (m)','First non-task-valid native grasp loss (s); gray = none'],['magma','cividis']):
        cm=plt.get_cmap(cmap).copy();cm.set_bad('#dadada');im=ax.imshow(m,aspect='auto',cmap=cm);fig.colorbar(im,ax=ax,fraction=.025,pad=.02);ax.set_title(title)
    for ax in axes:ax.set_yticks(range(6),labels)
    axes[-1].set_xticks(range(40),range(46000,46040),rotation=90);save(fig,'baseline_failure_map.png')

if __name__=='__main__':
    chunkplots();sampleplots();failureplots()
