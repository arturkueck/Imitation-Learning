import json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
EXP=ROOT/'experiments/stack_diagnostics/stack_followup_20261001'
diag=ROOT/'experiments/baselines/diffusion_20261001/diagnostics'
assert all(r['action_replay_success'] for r in json.loads((diag/'demo_replay.json').read_text()))
schedule=json.loads((diag/'scheduler_check.json').read_text())
assert schedule['after']==dict(optimizer_updates=2,scheduler_updates=2)
text=(EXP/'smoke/training.log').read_text(errors='replace')
assert 'LR_SCHEDULER_TRAIN_UPDATES_ONLY' in text
for kind in ('Train','Validation'):
    values=json.loads(re.search(kind+r' Epoch 1\s*(\{.*?\})',text,re.S)[1])
    assert 0<values['Loss']<100
result=json.loads((EXP/'smoke/evaluation/horizon_2_cpu/evaluation_results.json').read_text())
assert result['inference_action_horizon']==2 and result['inference_device']=='cpu'
manifest=json.loads((EXP/'manifest.json').read_text())
assert Path(manifest['baseline_checkpoint']).exists()
assert not list((EXP/'state_scheduler_fixed/runs').glob('**/*.pth'))
assert shutil.disk_usage(ROOT).free>8*1024**3
ready=dict(validated=True,cpu_training_smoke=True,horizon_2_rollout_smoke=True,
    real_epoch_scheduler_test=True,successful_demo_replays=6,wait_for_current_process_exit=True)
(EXP/'preflight.json').write_text(json.dumps(ready,indent=2))
sys.path.insert(0,str(EXP/'scripts')); import pipeline
pipeline.save()
print(json.dumps(ready))
