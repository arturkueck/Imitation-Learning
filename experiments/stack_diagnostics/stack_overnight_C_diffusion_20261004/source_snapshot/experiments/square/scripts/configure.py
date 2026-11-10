import runtime
import copy
import json
from pathlib import Path
from robomimic.config import config_factory

EXP = runtime.ROOT / 'experiments/square'
DATA = runtime.ROOT / 'praxis/data/square/ph/image_64_v15.hdf5'
for method in ('bc', 'bc_rnn', 'bc_transformer'):
    folder = EXP / method
    folder.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(config_factory('bc').dump())
    cfg['experiment'].update(name=method, validate=True, render_video=False,
        epoch_every_n_steps=100, validation_epoch_every_n_steps=20)
    cfg['experiment']['rollout']['enabled'] = False
    cfg['experiment']['save'].update(every_n_epochs=10, on_best_validation=True,
        on_best_rollout_success_rate=False)
    cfg['train'].update(data=[{'path':str(DATA)}], output_dir=str(folder / 'runs'),
        num_epochs=50, batch_size=16, seed=1, num_data_workers=0,
        hdf5_cache_mode='all', hdf5_filter_key='train', hdf5_validation_filter_key='valid')
    cfg['observation']['modalities']['obs']['low_dim'] = [
        'robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos']
    cfg['observation']['modalities']['obs']['rgb'] = ['agentview_image']
    cfg['observation']['encoder']['rgb']['core_kwargs'] = {
        'backbone_class':'ResNet18Conv', 'backbone_kwargs':{'pretrained':False},
        'pool_class':'SpatialSoftmax', 'pool_kwargs':{'num_kp':32}, 'feature_dimension':64}
    cfg['algo']['actor_layer_dims'] = [256,256]
    cfg['algo']['gmm']['enabled'] = False
    cfg['algo']['loss'].update(l2_weight=1.0,l1_weight=0.0,cos_weight=0.0)
    if method == 'bc_rnn':
        cfg['train']['seq_length'] = 5
        cfg['algo']['rnn'].update(enabled=True,horizon=5,hidden_dim=256,num_layers=1)
    if method == 'bc_transformer':
        cfg['train']['seq_length'] = 1
        cfg['train']['frame_stack'] = 5
        cfg['algo']['transformer'].update(enabled=True,context_length=5,embed_dim=128,
            num_layers=2,num_heads=4,supervise_all_steps=True)
    (folder / 'config.json').write_text(json.dumps(cfg,indent=2))
    print(method, flush=True)
