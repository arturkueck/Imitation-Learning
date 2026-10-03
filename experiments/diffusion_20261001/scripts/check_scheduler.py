"""Exercise actual upstream epoch runner without GPU or optimizer work."""
import json, sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
from robomimic.algo.algo import Algo
from robomimic.utils.train_utils import run_epoch
from scheduler_fix import install

class FakePolicy:
    def __init__(self):
        self.nets=SimpleNamespace(training=True)
        self.optimizer_updates=0; self.scheduler_updates=0
        self.step_lr_schedulers_every_batch={'policy':True}
        self.lr_schedulers={'policy':SimpleNamespace(step=self.scheduler_step)}
    def scheduler_step(self): self.scheduler_updates+=1
    def set_train(self): self.nets.training=True
    def set_eval(self): self.nets.training=False
    def process_batch_for_training(self,batch): return batch
    def postprocess_batch_for_training(self,batch,obs_normalization_stats=None): return batch
    def train_on_batch(self,batch,epoch,validate=False):
        self.optimizer_updates+=not validate
        return {}
    def log_info(self,info): return {'Loss':0.}
    def on_gradient_step(self): return Algo.on_gradient_step(self)

def count():
    model=FakePolicy()
    run_epoch(model,[{},{}],epoch=1,validate=False,num_steps=2)
    run_epoch(model,[{},{}],epoch=1,validate=True,num_steps=2)
    return dict(optimizer_updates=model.optimizer_updates,scheduler_updates=model.scheduler_updates)
before=count(); install(); after=count()
assert before==dict(optimizer_updates=2,scheduler_updates=4)
assert after==dict(optimizer_updates=2,scheduler_updates=2)
result=dict(before=before,after=after,expected_300_epoch_schedule=dict(
    optimizer_updates=30000,old_scheduler_updates=36000,corrected_scheduler_updates=30000,
    old_lr_minimum_epoch=250),active_process_modified=False)
(ROOT/'experiments/diffusion_20261001/diagnostics/scheduler_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
