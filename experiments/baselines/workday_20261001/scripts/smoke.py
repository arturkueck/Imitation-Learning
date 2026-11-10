"""Exercise each actual architecture, dataset, checkpoint and collage renderer."""
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
EXP=ROOT/'experiments/baselines/workday_20261001'
SHARED=ROOT/'experiments/baselines/square/scripts'
SMOKE=EXP/'smoke'; SMOKE.mkdir(exist_ok=True)
manifest=json.loads((EXP/'manifest.json').read_text())
completed=[]
for job in manifest['jobs']:
    name=job['name']; cfg=json.loads(Path(job['config']).read_text())
    cfg['experiment']['name']=name+'_smoke'
    cfg['experiment']['epoch_every_n_steps']=2
    cfg['experiment']['validation_epoch_every_n_steps']=2
    cfg['experiment']['save']['every_n_epochs']=1
    cfg['train'].update(num_epochs=1,output_dir=str(SMOKE/name/'runs'))
    folder=SMOKE/name
    if name=='square_rnn_gmm': folder=folder/'gmm_validation_fixed'
    folder.mkdir(parents=True,exist_ok=True)
    cfg['train']['output_dir']=str(folder/'runs')
    path=folder/'config.json'; path.write_text(json.dumps(cfg,indent=2))
    checkpoints=list(folder.glob('runs/**/models/model_epoch_1*.pth'))
    if not checkpoints:
        with (folder/'training.log').open('w') as log:
            subprocess.run([sys.executable,'-u',str(SHARED/'train_model.py'),str(path)],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        checkpoints=list(folder.glob('runs/**/models/model_epoch_1*.pth'))
    assert len(checkpoints)==1
    result_path=SMOKE/'evaluation'/name/'evaluation_results.json'
    if name=='square_rnn_gmm' or not result_path.exists():
        with (folder/'evaluation.log').open('w') as log:
            subprocess.run([sys.executable,'-u',str(SHARED/'evaluate.py'),str(checkpoints[0]),
                name,'--output-root',str(SMOKE),'--episodes','1','--horizon','10',
                '--video-episodes','1'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    if name=='square_rnn_gmm':
        import re
        text=(folder/'training.log').read_text(errors='replace')
        assert 'GMM_VALIDATION_USES_LEARNED_VARIANCE' in text
        validation=json.loads(re.search(r'Validation Epoch 1\s*(\{.*?\})',text,re.S)[1])
        assert abs(validation['Loss']) < 100, validation
    result=json.loads((SMOKE/'evaluation'/name/'evaluation_results.json').read_text())
    assert result['video_layout']=='collage' and result['video_tail_seconds']==2
    assert Path(result['rollouts'][0]['video']).stat().st_size>0
    if job['kind']=='StackTwo': assert 'stack_progress' in result['rollouts'][0]
    completed.append(name)
    (SMOKE/'validation.json').write_text(json.dumps(dict(completed=completed,
        note='Technical one-epoch smoke test; not a performance result'),indent=2))
    print('SMOKE_OK',name,flush=True)
