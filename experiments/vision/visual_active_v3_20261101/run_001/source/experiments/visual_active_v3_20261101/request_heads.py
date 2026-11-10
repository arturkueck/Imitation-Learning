"""Untrained request/candidate heads for a design review. No training entrypoint."""
import torch
from torch import nn

OBSERVATION_FEATURES=[
    'focus_x','focus_y','focus_z','size_x','size_y','size_z',
    'rotation6d_0','rotation6d_1','rotation6d_2','rotation6d_3','rotation6d_4','rotation6d_5',
    'existence_score','seed_support_fraction','position_std_x','position_std_y','position_std_z',
    'fixed0_visibility','fixed1_visibility','wrist_any_visibility','history_length',
    'rgb_inconsistency_or_minus_one','predicted_object_focus_present']
CANDIDATE_FEATURES=[
    'camera_x','camera_y','camera_z','camera_rotation6d_0','camera_rotation6d_1','camera_rotation6d_2',
    'camera_rotation6d_3','camera_rotation6d_4','camera_rotation6d_5',
    'focus_direction_x','focus_direction_y','focus_direction_z','focus_distance',
    'joint_motion_norm','fixed0_expected_robot_occlusion','fixed1_expected_robot_occlusion',
    'calibration_valid','capture_cost','candidate_valid']


class RequestHeads(nn.Module):
    """23 observed features -> need logit; 23+19 -> gain and helpful logit.

    Needs refer to image evidence. Candidates are supplied by an independent
    geometric planner. Outputs from this untrained class must not drive a robot.
    """
    def __init__(self):
        super().__init__()
        self.need=nn.Sequential(nn.Linear(23,64),nn.GELU(),nn.Linear(64,32),nn.GELU(),nn.Linear(32,1))
        self.candidate=nn.Sequential(nn.Linear(42,128),nn.GELU(),nn.Linear(128,64),nn.GELU(),nn.Linear(64,2))

    def forward(self,observed,candidates):
        if observed.ndim!=2 or observed.shape[-1]!=23:raise ValueError('B x 23 observed features required')
        if candidates.ndim!=3 or candidates.shape[0]!=observed.shape[0] or candidates.shape[-1]!=19:raise ValueError('B x K x 19 candidates required')
        context=observed[:,None].expand(-1,candidates.shape[1],-1)
        scores=self.candidate(torch.cat([context,candidates],dim=-1))
        return dict(need_image_logit=self.need(observed).squeeze(-1),gain=scores[...,0],helpful_logit=scores[...,1])


if __name__=='__main__':
    import json
    torch.manual_seed(1101);model=RequestHeads().eval()
    with torch.inference_mode():output=model(torch.zeros(2,23),torch.zeros(2,6,19))
    print(json.dumps(dict(trained=False,optimizer_updates=0,
                         need_parameters=sum(p.numel() for p in model.need.parameters()),
                         candidate_parameters=sum(p.numel() for p in model.candidate.parameters()),
                         total_parameters=sum(p.numel() for p in model.parameters()),
                         output_shapes={k:list(v.shape) for k,v in output.items()}),indent=2))
