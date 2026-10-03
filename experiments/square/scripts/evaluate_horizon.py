"""Explicit inference-only DP horizon override, without changing checkpoint files."""
import runtime
import argparse, json, runpy, sys
from pathlib import Path
import torch
from robomimic.utils import file_utils
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--action-horizon',type=int,required=True)
parser.add_argument('--cpu',action='store_true')
args,remaining=parser.parse_known_args()
assert 1<=args.action_horizon<=15
original=file_utils.policy_from_checkpoint
def load_override(*positional,**kwargs):
    checkpoint=file_utils.load_dict_from_checkpoint(kwargs.pop('ckpt_path'))
    cfg=json.loads(checkpoint['config'])
    assert cfg['algo_name']=='diffusion_policy'
    assert args.action_horizon<=cfg['algo']['horizon']['prediction_horizon']-cfg['algo']['horizon']['observation_horizon']+1
    cfg['algo']['horizon']['action_horizon']=args.action_horizon
    checkpoint['config']=json.dumps(cfg)
    kwargs['ckpt_dict']=checkpoint
    if args.cpu: kwargs['device']=torch.device('cpu')
    return original(*positional,**kwargs)
file_utils.policy_from_checkpoint=load_override
if args.cpu: torch.set_num_threads(2)
script=Path(__file__).with_name('evaluate.py')
sys.argv=[str(script),*remaining]
runpy.run_path(str(script),run_name='__main__')
# Make the override visible alongside measurements, including the unchanged
# source checkpoint path. All camera and scoring logic comes from evaluate.py.
output_root=Path(remaining[remaining.index('--output-root')+1])
result_path=output_root/'evaluation'/remaining[1]/'evaluation_results.json'
result=json.loads(result_path.read_text())
result['inference_action_horizon']=args.action_horizon
result['inference_device']='cpu' if args.cpu else 'configured'
result_path.write_text(json.dumps(result,indent=2))
