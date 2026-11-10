"""Q1: learned quality of a fixed geometric proposal, not a robot policy."""
import torch
from torch import nn
from torch.nn import functional as F

class QualityModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.network=nn.Sequential(nn.Linear(48,128),nn.GELU(),nn.Dropout(.1),nn.Linear(128,64),nn.GELU(),nn.Dropout(.1),nn.Linear(64,4))
    def forward(self,x):
        if x.ndim!=2 or x.shape[1]!=48:raise ValueError('Expected B×48 observed features')
        out=self.network(x)
        return dict(logits=out[:,:3],gain=out[:,3]*10.)

def loss(model,x,labels,gains,weights):
    out=model(x);classification=F.cross_entropy(out['logits'],labels,weight=x.new_tensor([3.,1.,1.]),reduction='none')
    regression=F.huber_loss(out['gain']/10.,gains.clamp(-25,25)/10.,delta=.5,reduction='none')
    return ((classification+.5*regression)*weights).sum()/weights.sum().clamp_min(1e-9)
