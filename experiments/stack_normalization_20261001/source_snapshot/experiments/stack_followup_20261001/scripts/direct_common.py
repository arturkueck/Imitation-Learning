"""Direct chunk regression baseline; original raw two-frame observations only."""
import json,copy
from collections import deque
import numpy as np,torch
from torch import nn
from transport_data import ROOT,KEYS,DATA
from balance_common import SOURCE
OUT=ROOT/'experiments/stack_direct_20261001';OUT.mkdir(exist_ok=True)
ORDER=['object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']
class Block(nn.Module):
    def __init__(self,width):
        super().__init__();self.net=nn.Sequential(nn.LayerNorm(width),nn.Linear(width,width),nn.SiLU(),nn.Linear(width,width))
    def forward(self,x):return (x+self.net(x))/2**.5
class DirectChunk(nn.Module):
    def __init__(self):
        super().__init__();self.input=nn.Linear(30,2048);self.blocks=nn.Sequential(*[Block(2048) for _ in range(8)]);self.output=nn.Linear(2048,112)
    def forward(self,x):return self.output(self.blocks(torch.nn.functional.silu(self.input(x)))).tanh().reshape(-1,16,7)
def flatten(ob):return np.concatenate([np.asarray(ob[k]) for k in ORDER],axis=-1).reshape(-1,30).astype(np.float32)
class DirectPolicy:
    def __init__(self,path):
        ck=torch.load(path,map_location='cpu',weights_only=False);self.model=DirectChunk().cuda().eval();self.model.load_state_dict(ck['ema']);self.queue=deque()
    def start_episode(self):self.queue.clear()
    def __call__(self,ob):
        if not self.queue:
            x=torch.tensor(flatten(ob),device='cuda');chunk=self.model(x)[0].detach().cpu().numpy();self.queue.extend(chunk[1:3])
        return self.queue.popleft()
