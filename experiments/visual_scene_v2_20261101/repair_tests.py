"""Re-render invalid black test images in a fresh process; frozen models only."""
from pathlib import Path
import os,site
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import json,time,hashlib
import numpy as np,torch
from scene_data import Generator
from model_prototype import ScenePerception
from preflight import settings
from train import Session,evaluate
from night import save


def main():
    settings();source=HERE/'run_001';out=source/'test_repair_001';out.mkdir(exist_ok=False)
    cfg=json.loads((source/'config.json').read_text());cfg.update(training_enabled=False,repair_only=True,
        started_unix=time.time(),deadline_unix=time.time()+900)
    save(out/'config.json',cfg);session=Session(out)
    selection=json.loads((source/'selection.json').read_text())['models'];models={}
    for row in selection:
        path=source/'checkpoints'/f"{row['arm']}_seed{row['seed']}_best.pth"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],'Frozen checkpoint changed'
        m=ScenePerception().cuda();m.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model'])
        models[(row['seed'],row['arm'])]=m.eval()
    generator=Generator();tests={};reports={}
    try:
        for split,seed in [('reserved_test',cfg['reserved_seeds'][0]),('reserved_ood',cfg['reserved_seeds'][1])]:
            old={p.stem:np.load(p,mmap_mode='r') for p in (source/'data'/split).glob('*.npy')}
            count=len(old['images']);folder=out/split;folder.mkdir();data={}
            for i in range(count):
                row=generator.scene(seed,i,ood=split.endswith('_ood'))
                for key in ('positions','sizes','rotations','rays','active','count','kind','family'):
                    if not np.array_equal(old[key][i],row[key]):raise RuntimeError(f'Physical source mismatch: {split}/{i}/{key}')
                if float(row['images'].mean())<1 or int(row['images'].max())<20:raise RuntimeError('Invalid repaired RGB')
                if row['active'].any() and not ((row['visibility'].max(-1)>=.05)&row['active']).any():raise RuntimeError('No observable object in nonempty repaired scene')
                if not data:
                    for key,value in row.items():data[key]=np.lib.format.open_memmap(folder/f'{key}.npy',mode='w+',dtype=value.dtype,shape=(count,)+value.shape)
                for key,value in row.items():data[key][i]=value
                if i%64==0:session.status(stage='render',split=split,rendered=i,render_total=count)
            for a in data.values():a.flush()
            reports[split]=dict(samples=count,original_black_images=True,physical_arrays_exactly_equal=True,
                original_observed_objects=int((old['active']&(old['visibility'].max(-1)>=.05)).sum()),
                repaired_observed_objects=int((data['active']&(data['visibility'].max(-1)>=.05)).sum()))
            prefix='ood/' if split.endswith('_ood') else ''
            for (model_seed,arm),model in models.items():
                tests[f'{prefix}{model_seed}/{arm}']=evaluate(session,model,data,arm)
            save(out/'progress_results.json',dict(reports=reports,tests=tests))
    finally:generator.close()
    for row in selection:
        path=source/'checkpoints'/f"{row['arm']}_seed{row['seed']}_best.pth"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    save(out/'results.json',dict(status='repaired_test_evaluation_complete',training_updates=0,
         selection_unchanged=True,selection=selection,reports=reports,tests=tests,
         original_results_preserved=True,elapsed_seconds=time.time()-cfg['started_unix']))
    session.status(stage='complete');print(json.dumps(dict(status='complete',tests=tests)),flush=True)


if __name__=='__main__':main()
