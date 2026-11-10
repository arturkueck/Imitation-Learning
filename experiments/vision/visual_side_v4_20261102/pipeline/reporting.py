"""Loss plots, fixed validation reconstructions and monitor-compatible artifacts."""
import sys
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image
from .common import ROOT,EXPERIMENT,save,read,check_stop
from .samples import batch_pairs,pair
from .engine import forward,tensors
sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
from learning import decode,boxes

def plots(run,curves):
    run=Path(run);fig,axes=plt.subplots(2,3,figsize=(13,7),squeeze=False)
    for ax,key in zip(axes.flat,sorted({f"{r['arm']}{r['seed']}" for r in curves})):
        rows=[r for r in curves if f"{r['arm']}{r['seed']}"==key]
        for field,label,color in [('train_loss','Train','#36a7bc'),('validation_loss','Validation','#d68e37'),('probe_loss','Fixed train probe','#947ec9')]:
            values=[(r['updates'],r[field]) for r in rows if r.get(field) is not None]
            if values:ax.plot(*zip(*values),label=label,color=color)
        ax.set(title=key,xlabel='Optimizer updates',ylabel='Loss');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('V4 paired A/B: losses per seed, identical validation contexts');fig.tight_layout();fig.savefig(run/'loss.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for arm in ['A','B']:
        rows=[r for r in curves if r['arm']==arm];epochs=sorted({r['epoch'] for r in rows})
        for field,label in [('side_set_error_mm','Side'),('old_set_error_mm','Old')]:
            values=[np.mean([r[field] for r in rows if r['epoch']==e]) for e in epochs]
            ax.plot(epochs,values,label=f'{arm} {label}')
    ax.set(xlabel='Epoch',ylabel='Common-target set error [mm-equivalent]',title='Mean of three seeds; not robot placement accuracy');ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(run/'view_metrics.png',dpi=140);plt.close(fig)

SIGNS=np.array([[a,b,c] for a in [-1,1] for b in [-1,1] for c in [-1,1]])
FACES=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]
def corners(b):return (SIGNS*np.array(b['size'])/2)@np.array(b['rotation']).T+np.array(b['center'])
def geometry(run,model,store,epoch,seed,arm,tag='epoch',device='cuda'):
    run=Path(run);folder=run/'geometry';folder.mkdir(exist_ok=True);index_path=folder/'index.json';index=read(index_path) if index_path.exists() else []
    model.eval()
    for i in range(min(16,len(store.records))):
        check_stop(run,15);row=store[i];arrays=batch_pairs([row],'B',kind='side');history=pair(row,'B',kind='side')[2];pred=[]
        with torch.inference_mode():
            for a in arrays:
                raw,_=forward(model,tensors(a,device));pred.append(boxes(decode(raw),0))
        gt=[dict(center=row['positions'][j].tolist(),size=row['sizes'][j].tolist(),rotation=row['rotations'][j].tolist()) for j in np.flatnonzero(row['active'])]
        stem=f'{tag}_epoch_{epoch:05.2f}_{arm}_seed{seed}_scene{i:04d}'
        scene=dict(ground_truth=gt,initial_prediction=pred[0],updated_predictions=[pred[1]],family=list(map(int,row['family'])),
            history=history,source_split=store.split,update_adopted=False,note='Same model weights, initial vs acquired additional views; no fitted alignment')
        save(folder/(stem+'_scene.json'),scene)
        fig=plt.figure(figsize=(11,4));ax=fig.add_subplot(121,projection='3d');top=fig.add_subplot(122)
        all_points=[]
        for objects,color,label in [(gt,'#22cfe0','Ground truth'),(pred[0],'#e89b39','Initial'),(pred[1],'#35b966','After extra view')]:
            for j,b in enumerate(objects):
                p=corners(b);all_points.extend(p.tolist());ax.add_collection3d(Poly3DCollection([p[f] for f in FACES],facecolors=color,edgecolors=color,alpha=.15))
                xy=p[:,:2];from scipy.spatial import ConvexHull
                hull=ConvexHull(xy);q=xy[hull.vertices];top.plot(*np.vstack([q,q[0]]).T,color=color,label=label if j==0 else None)
        pts=np.array(all_points) if all_points else np.array([[-.1,-.1,.8],[.1,.1,1.]])
        low=pts.min(0)-.02;high=np.maximum(pts.max(0)+.02,low+.05)
        ax.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),zlim=(low[2],high[2]),xlabel='X [m]',ylabel='Y [m]',zlabel='Z [m]');top.set(xlabel='X [m]',ylabel='Y [m]',aspect='equal');top.grid(alpha=.3)
        handles,labels=top.get_legend_handles_labels()
        if handles:fig.legend(handles,labels,loc='lower center',ncol=3)
        fig.suptitle(f'V4 {arm} seed {seed}, epoch {epoch:g}, validation family {i}');fig.tight_layout(rect=(0,.08,1,.92));fig.savefig(folder/(stem+'_overlay.png'),dpi=120);plt.close(fig)
        current=history[-1];images=[*row['images'][current,:2],*[row['images'][h,2] for h in history]]
        Image.fromarray(np.concatenate(images,axis=1)).save(folder/(stem+'_inputs.png'))
        for suffix,kind,label in [('_overlay.png','geometry','3D comparison'),('_scene.json','geometry-scene','Interactive scene'),('_inputs.png','input','Acquired RGB context')]:
            name=stem+suffix;index=[v for v in index if v['name']!=name];index.append(dict(name=name,file='geometry/'+name,kind=kind,epoch=epoch,seed=seed,variant=arm,label=f'{label} {arm} seed {seed}, epoch {epoch:g}, scene {i}'))
    save(index_path,index)
