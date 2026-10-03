"""Final preflight; does not launch or train the production runs."""
import json, sys
from pathlib import Path
import h5py
import imageio.v2 as imageio
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/workday_20261001'
manifest=json.loads((EXP/'manifest.json').read_text())
assert len(json.loads((EXP/'smoke/validation.json').read_text())['completed'])==4
assert not (EXP/'launch.json').exists()
for job in manifest['jobs']:
    path=Path(job['config']); cfg=json.loads(path.read_text())
    cfg['experiment']['save']['on_best_validation']=False
    assert cfg['train']['num_epochs']==400 and cfg['train']['cuda']
    assert cfg['train']['seq_length']==cfg['algo']['rnn']['horizon']
    assert cfg['train']['seq_length']*cfg['train']['batch_size']==80
    path.write_text(json.dumps(cfg,indent=2))
    video=EXP/'smoke/videos'/job['name']/'rollout_00.mp4'
    reader=imageio.get_reader(str(video))
    assert reader.get_data(0).shape==(768,768,3)
    assert reader.count_frames()==42  # 2 measurement frames + 40 tail frames
    reader.close()
task=ROOT/'experiments/additional_tasks/stack_two'
info=json.loads((task/'task_info.json').read_text())
collection=json.loads((task/'collection_report.json').read_text())
assert collection['ready_for_baseline'] and collection['accepted']==200
with h5py.File(info['dataset'],'r') as f:
    train=set(f['mask/train'][:]); valid=set(f['mask/valid'][:])
    assert len(train)==180 and len(valid)==20 and not train&valid
    assert len(train|valid)==200
    lengths=[]
    for demo in f['data'].values():
        assert demo['actions'].shape[1]==7 and np.isfinite(demo['actions'][:]).all()
        assert demo['obs/object'].shape[1]==6
        assert demo['obs/agentview_image'].shape[1:]==(64,64,3)
        assert demo['rewards'][-1]>0
        lengths.append(len(demo['actions']))
info['status']='READY_FOR_BASELINE'; (task/'task_info.json').write_text(json.dumps(info,indent=2))
preflight=dict(state='VALIDATED',demos=200,attempts=len(collection['attempts']),
    train_demos=180,valid_demos=20,length_min_median_max=[min(lengths),float(np.median(lengths)),max(lengths)],
    architectures_smoke_tested=4,video_layout='4-view 768x768',tail_seconds=2,
    checkpoint_interval_epochs=50,deadline_hours=6.5)
(EXP/'preflight.json').write_text(json.dumps(preflight,indent=2))
sys.path.insert(0,str(EXP/'scripts'))
import pipeline
pipeline.status['state']='PREPARED'
pipeline.report()
print(json.dumps(preflight),flush=True)
