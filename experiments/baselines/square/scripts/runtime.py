"""Experiment-local Windows rendering bootstrap; upstream sources stay intact."""
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT / 'praxis/src'))
os.environ['MPLCONFIGDIR'] = str(ROOT / 'praxis/.cache/matplotlib')
os.environ['HF_HOME'] = str(ROOT / 'praxis/.cache/huggingface')
os.environ['MUJOCO_GL'] = 'glfw'
if sys.platform == 'win32':
    # EGL device enumeration is Linux-specific. GLFW chooses the Windows device.
    probe = types.ModuleType('egl_probe')
    probe.get_available_devices = lambda: []
    sys.modules['egl_probe'] = probe
    import robosuite.utils.binding_utils as binding
    binding._MUJOCO_GL = 'glfw'
    import robosuite.macros as macros
    macros.MUJOCO_GPU_RENDERING = False
import task_extensions  # register project-local tasks for dataset and checkpoint loading
