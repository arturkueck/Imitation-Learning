"""Read-only audit of the sole allowed training dataset."""
from pathlib import Path
import hashlib, json
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'

def main():
    h = hashlib.sha256()
    with DATA.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''): h.update(block)
    with h5py.File(DATA, 'r') as f:
        splits = {k: [x.decode() for x in f['mask'][k][:]] for k in ('train', 'valid')}
        assert not set(splits['train']) & set(splits['valid'])
        assert set(splits['train'] + splits['valid']) == set(f['data'])
        rows, starts = [], []
        amin, amax = np.full(7, np.inf), np.full(7, -np.inf)
        for name in sorted(f['data'], key=lambda x:int(x.split('_')[-1])):
            d = f['data'][name]; a = d['actions'][:]; n = len(a)
            assert a.shape == (n, 7) and np.isfinite(a).all()
            for k in ('object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos'):
                x = d['obs'][k][:]
                assert len(x) == n and np.isfinite(x).all(), (name,k)
            assert d['obs/object'].shape == (n,6)
            assert len(d['states']) == n
            images = d['obs/agentview_image'][:]
            black = np.all(images == 0, axis=(1,2,3))
            rows.append(dict(demo=name, split='train' if name in splits['train'] else 'valid',
                frames=n, black_frames=int(black.sum()), final_reward=float(d['rewards'][-1])))
            starts.append(d['obs/object'][0])
            amin = np.minimum(amin,a.min(0)); amax = np.maximum(amax,a.max(0))
        schema = {k:dict(shape=list(v.shape[1:]),dtype=str(v.dtype)) for k,v in f['data/demo_0/obs'].items()}
        report = dict(dataset=str(DATA), sha256=h.hexdigest(), bytes=DATA.stat().st_size,
            demos=len(rows), frames=sum(r['frames'] for r in rows), splits=splits,
            split_frames={s:sum(r['frames'] for r in rows if r['split']==s) for s in splits},
            lengths=dict(min=min(r['frames'] for r in rows),median=float(np.median([r['frames'] for r in rows])),max=max(r['frames'] for r in rows)),
            observation_schema=schema, action_min=amin.tolist(), action_max=amax.tolist(),
            black_image_demos=sum(r['black_frames']>0 for r in rows),black_frames=sum(r['black_frames'] for r in rows),
            environment=json.loads(f['data'].attrs['env_args']), rows=rows)
        (OUT/'dataset_audit.json').write_text(json.dumps(report,indent=2))
        fig, axes = plt.subplots(3,6,figsize=(15,8))
        for row, name in enumerate(['demo_0','demo_50','demo_100']):
            d=f['data'][name]; indices=np.linspace(0,len(d['actions'])-1,6,dtype=int)
            for ax,i in zip(axes[row],indices):
                ax.imshow(d['obs/agentview_image'][i]); ax.set_title(f'{name} | t={i/20:.2f}s'); ax.axis('off')
        fig.suptitle('Originaldaten: Zwei-Wuerfel-Demonstrationen (20 Hz; gespeicherte RGB-Frames)')
        fig.tight_layout(); fig.savefig(OUT/'dataset_examples.png',dpi=160); plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(11,4)); starts=np.asarray(starts)
        for k,label in [(0,'A: Ziel'),(3,'B: bewegter Wuerfel')]: axes[0].scatter(starts[:,k],starts[:,k+1],s=12,label=label)
        axes[0].legend(); axes[0].set(xlabel='x [m]',ylabel='y [m]',title='Startpositionen aller 200 Demos',aspect='equal')
        axes[1].hist([r['frames'] for r in rows],bins=20); axes[1].set(xlabel='Frames je Demo',ylabel='Anzahl',title='Trajektorienlaengen')
        fig.tight_layout();fig.savefig(OUT/'dataset_statistics.png',dpi=160);plt.close(fig)
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','splits','environment')},indent=2))

if __name__=='__main__': main()
