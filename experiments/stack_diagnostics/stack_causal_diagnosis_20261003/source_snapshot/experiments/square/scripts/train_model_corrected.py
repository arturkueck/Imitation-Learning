"""Opt-in correction; an already running Python process is unaffected."""
import runtime
import runpy
from pathlib import Path
from scheduler_fix import install
install()
print('LR_SCHEDULER_TRAIN_UPDATES_ONLY',flush=True)
runpy.run_path(str(Path(__file__).with_name('train_model.py')),run_name='__main__')
