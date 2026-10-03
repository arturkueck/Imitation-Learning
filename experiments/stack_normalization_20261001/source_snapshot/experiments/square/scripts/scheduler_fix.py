"""Future runs only: scheduler ticks correspond to optimizer updates."""
from robomimic.algo.algo import Algo


def install():
    original=Algo.on_gradient_step
    def training_only(self):
        if self.nets.training:
            return original(self)
    Algo.on_gradient_step=training_only
