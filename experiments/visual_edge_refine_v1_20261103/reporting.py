"""Actual RGB/track animations and truth/initial/adopted 3D diagnostic overlays."""
import numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from geometry import corners,EDGES,project

FACES=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]

def render(folder,images,cameras,tracks,initial,adopted,truth):
    folder=Path(folder);frames=[]
    for i,rgb in enumerate(images):
        im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
        for boxes,color in [(initial,'orange'),(adopted,'lime')]:
            for box in boxes:
                uv,z=project(corners(box),cameras[i])
                for a,b in EDGES:
                    if z[a]>.02 and z[b]>.02 and np.max(np.abs(uv[[a,b]]))<2000:draw.line([tuple(uv[a]),tuple(uv[b])],fill=color,width=1)
        n=0
        for t in tracks:
            obs=[p for frame,p in t['observations'] if frame==i]
            if obs:
                x,y=obs[0];draw.ellipse((x-2,y-2,x+2,y+2),fill='cyan');n+=1
        draw.rectangle((0,0,im.width,35),fill='black')
        draw.text((5,3),f'Frame {i:02d} | fitting tracks: {n}',fill='white')
        draw.text((5,18),'Orange initial | Green adopted | Cyan tracks',fill='white')
        frames.append(im)
    frames[0].save(folder/'tracking.gif',save_all=True,append_images=frames[1:],duration=110,loop=0,optimize=False)
    indices=np.linspace(0,len(frames)-1,4,dtype=int);strip=Image.new('RGB',(frames[0].width*4,frames[0].height))
    for j,i in enumerate(indices):strip.paste(frames[i],(j*frames[0].width,0))
    strip.save(folder/'sequence.png')
    fig=plt.figure(figsize=(11,4));ax=fig.add_subplot(121,projection='3d');top=fig.add_subplot(122);points=[]
    from scipy.spatial import ConvexHull
    for boxes,color,label in [(truth,'#16bdd0','Simulation'),(initial,'#e78c22','Initial'),(adopted,'#20a857','Adopted geometry')]:
        for j,box in enumerate(boxes):
            c=corners(box);points.extend(c.tolist());ax.add_collection3d(Poly3DCollection([c[f] for f in FACES],facecolors=color,edgecolors=color,alpha=.12))
            hull=ConvexHull(c[:,:2]);xy=c[hull.vertices,:2];top.plot(*np.vstack([xy,xy[0]]).T,color=color,label=label if j==0 else None)
    if points:
        p=np.array(points);lo=p.min(0)-.02;hi=p.max(0)+.02
        ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]))
    ax.set(xlabel='X [m]',ylabel='Y [m]',zlabel='Z [m]');top.set(xlabel='X [m]',ylabel='Y [m]',aspect='equal');top.grid(alpha=.2)
    if top.get_legend_handles_labels()[0]:top.legend(fontsize=8)
    fig.suptitle('Geometric diagnostic; GT used only for this comparison');fig.tight_layout();fig.savefig(folder/'comparison.png',dpi=130);plt.close(fig)

def summary_plot(run,results):
    labels=['initial','neural_extra','geometry_raw','geometry_adopted'];valid=[r for r in results if 'metrics' in r]
    if not valid:return
    fig,ax=plt.subplots(figsize=(9,4));x=np.arange(len(valid));width=.19
    for j,label in enumerate(labels):ax.bar(x+(j-1.5)*width,[r['metrics'][label]['error_mm'] for r in valid],width,label=label)
    ax.set(xticks=x,xticklabels=[str(r['index']) for r in valid],xlabel='Development family index',ylabel='Set error [mm-equivalent]',title='Small development diagnostic, not an end test');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(Path(run)/'comparison.png',dpi=140);plt.close(fig)
