import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/stack_followup_20261001'; EXP.mkdir(exist_ok=True)
source=ROOT/'experiments/diffusion_20261001'
cfg=json.loads((source/'stack_two_diffusion_state/config.json').read_text())
cfg['experiment']['name']='stack_two_state_scheduler_fixed'
cfg['train']['output_dir']=str(EXP/'state_scheduler_fixed/runs')
folder=EXP/'state_scheduler_fixed'; folder.mkdir(exist_ok=True)
(folder/'config.json').write_text(json.dumps(cfg,indent=2))
baseline=json.loads((source/'evaluation/test/stack_two_diffusion_state/evaluation_results.json').read_text())['checkpoint']
manifest=dict(wait_for_status=str(source/'status.json'),baseline_checkpoint=baseline,
    config=str(folder/'config.json'),epochs=300,test_episodes=20,test_seed=46000,
    action_horizons=[8,2],deadline_hours=4,change='Scheduler advances only on training batches')
(EXP/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Exercise the corrected runner on CPU, separately from the active GPU job.
smoke=EXP/'smoke'; smoke.mkdir(exist_ok=True)
cfg['experiment']['name']='corrected_cpu_smoke'
cfg['experiment']['epoch_every_n_steps']=2
cfg['experiment']['validation_epoch_every_n_steps']=2
cfg['experiment']['save']['every_n_epochs']=1
cfg['train'].update(num_epochs=1,batch_size=1,cuda=False,output_dir=str(smoke/'runs'))
cfg['algo']['optim_params']['policy']['learning_rate']['warmup_steps']=1
(smoke/'config.json').write_text(json.dumps(cfg,indent=2))
print('FOLLOWUP_PREPARED')
