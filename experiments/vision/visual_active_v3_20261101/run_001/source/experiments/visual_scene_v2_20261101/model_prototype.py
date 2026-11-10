"""Untrained architecture prototype. No training loop or deployment claim."""
import torch
from torch import nn


class ScenePerception(nn.Module):
    """RGB + calibrated world rays -> up to five unordered cuboid detections.

    rays[..., :3] = unit world ray; rays[..., 3:] = camera origin in metres.
    These encode camera calibration/robot kinematics, never object ground truth.
    Poses are relative to a configured workspace origin and scale; postprocessing
    and symmetry-aware losses must be implemented before training.
    """
    def __init__(self):
        super().__init__()
        modules=[]
        prev=3
        for width in (32,64,128):
            modules += [nn.Conv2d(prev,width,3,stride=2,padding=1),nn.ReLU(),
                        nn.Conv2d(width,width,3,padding=1),nn.ReLU()]
            prev=width
        self.backbone=nn.Sequential(*modules)
        self.ray_projection=nn.Linear(6,128)
        self.view_embedding=nn.Embedding(3,128)
        self.queries=nn.Parameter(torch.empty(5,128))
        nn.init.normal_(self.queries,std=.02)
        layer=nn.TransformerDecoderLayer(d_model=128,nhead=4,dim_feedforward=256,
            dropout=.1,activation='gelu',batch_first=True,norm_first=True)
        self.decoder=nn.TransformerDecoder(layer,num_layers=3,norm=nn.LayerNorm(128))
        self.head=nn.Sequential(nn.Linear(128,128),nn.GELU(),nn.Linear(128,16))

    def forward(self,images,rays,view_available):
        b,v,c,h,w=images.shape
        if (v,c,h,w)!=(3,3,160,160):raise ValueError('Expected B x 3 x 3 x 160 x 160')
        if rays.shape!=(b,3,20,20,6):raise ValueError('Expected calibrated ray grid B x 3 x 20 x 20 x 6')
        if view_available.shape!=(b,3) or not view_available.any(dim=1).all():
            raise ValueError('At least one available view is required per sample')
        # Mask image before feature extraction AND tokens in cross attention.
        images=images*view_available[:,:,None,None,None]
        features=self.backbone(images.reshape(b*v,c,h,w)).reshape(b,v,128,20,20)
        tokens=features.permute(0,1,3,4,2)+self.ray_projection(rays)
        tokens=tokens+self.view_embedding.weight[None,:,None,None,:]
        tokens=tokens.reshape(b,1200,128)
        padding=(~view_available.bool())[:,:,None].expand(b,3,400).reshape(b,1200)
        slots=self.decoder(self.queries[None].expand(b,-1,-1),tokens,memory_key_padding_mask=padding)
        out=self.head(slots)
        return dict(detection_logits=out[...,0],position=out[...,1:4],
                    dimensions_raw=out[...,4:7],rotation_6d=out[...,7:13],visibility_logits=out[...,13:16])


if __name__=='__main__':
    import json
    torch.manual_seed(1);model=ScenePerception().eval()
    images=torch.rand(2,3,3,160,160)
    rays=torch.rand(2,3,20,20,6)
    available=torch.tensor([[True,True,False],[True,True,True]])
    with torch.no_grad():
        out=model(images,rays,available)
        changed=images.clone();changed[0,2]=torch.rand_like(changed[0,2])*100
        changed_rays=rays.clone();changed_rays[0,2]=torch.rand_like(changed_rays[0,2])*100
        masked=model(changed,changed_rays,available)
        assert all(torch.isfinite(v).all() for v in out.values())
        assert all(torch.allclose(out[k][0],masked[k][0],atol=1e-6,rtol=1e-6) for k in out), 'Unavailable camera leaked into output'
    result=dict(parameters=sum(p.numel() for p in model.parameters()),
        backbone_parameters=sum(p.numel() for p in model.backbone.parameters()),
        output_shapes={k:list(v.shape) for k,v in out.items()},masked_camera_test='passed',trained=False)
    print(json.dumps(result,indent=2))
