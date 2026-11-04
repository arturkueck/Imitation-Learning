"""Read-only motion annotation from saved RGB and actual camera/joint logs."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from geometry import project

def annotate(run,indices=None):
    run=Path(run)
    for folder in sorted((run/'development').glob('scene_*')):
        if indices is not None and int(folder.name.split('_')[-1]) not in indices:continue
        if not (folder/'sequence.npz').exists():continue
        result=json.loads((folder/'result.json').read_text());motion=json.loads((folder/'motion.json').read_text());frames=motion['frames'];focus=np.asarray(result['focus']['center'])
        with np.load(folder/'sequence.npz',allow_pickle=False) as z:rgb=z['images']
        images=[]
        for i,(array,frame) in enumerate(zip(rgb,frames)):
            im=Image.fromarray(array);draw=ImageDraw.Draw(im);cam={k:np.asarray(v) if k in ['position','rotation'] else v for k,v in frame['camera'].items()};uv,depth=project(focus,cam)
            if depth>0:
                x,y=uv;draw.line((x-7,y,x+7,y),fill='red',width=2);draw.line((x,y-7,x,y+7),fill='red',width=2)
            draw.rectangle((0,0,im.width,43),fill='black');draw.text((5,3),f'{i:03d} {frame["phase"]}',fill='white')
            aim=frame['aim'];draw.text((5,18),f'Axis error: {aim["axis_error_deg"]:.2f} deg | fixed group focus',fill='white')
            draw.text((5,30),'Red cross: projected fixed 3D target',fill='white');images.append(im)
        images[0].save(folder/'active_motion.gif',save_all=True,append_images=images[1:],duration=100,loop=0,optimize=False)
        fig=plt.figure(figsize=(10,4));ax=fig.add_subplot(121,projection='3d');top=fig.add_subplot(122);colors={'right':'#4477bb','left':'#a154a5','initial':'#888888','restore':'#aaaaaa'}
        for prefix,color in colors.items():
            for kind in sorted({f['phase'] for f in frames if f['phase'].startswith(prefix)}):
                pts=np.asarray([f['camera']['position'] for f in frames if f['phase']==kind]);ax.plot(*pts.T,color=color,label=kind);top.plot(*pts[:,:2].T,color=color,label=kind)
        ax.scatter(*focus,color='red',marker='x',s=80);top.scatter(*focus[:2],color='red',marker='x',s=80)
        ax.set(xlabel='X [m]',ylabel='Y [m]',zlabel='Z [m]');top.set(xlabel='X [m]',ylabel='Y [m]',aspect='equal');top.grid(alpha=.2);top.legend(fontsize=6)
        fig.suptitle('Actual camera positions; red = fixed group focus');fig.tight_layout();fig.savefig(folder/'camera_path.png',dpi=130);plt.close(fig)
    (run/'active_visualization.json').write_text(json.dumps(dict(source='saved actual RGB/poses; no rerender or changed decisions',outputs=['development/scene_*/active_motion.gif','development/scene_*/camera_path.png']),indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);annotate(p.parse_args().run)
