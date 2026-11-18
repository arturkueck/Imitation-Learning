"""Freeze the completion FUNCTION, including the shared hidden layers."""
import copy
import torch


class FixedCompletion(torch.nn.Module):
    def __init__(self, actor, reference):
        super().__init__()
        self.actor = actor
        self.reference = copy.deepcopy(reference).eval().requires_grad_(False)

    def train(self, mode=True):
        super().train(mode)
        self.reference.eval()
        return self

    def forward(self, x, phase):
        action, _ = self.actor(x, phase)
        with torch.no_grad():
            _, completion = self.reference(x, phase)
        return action, completion
