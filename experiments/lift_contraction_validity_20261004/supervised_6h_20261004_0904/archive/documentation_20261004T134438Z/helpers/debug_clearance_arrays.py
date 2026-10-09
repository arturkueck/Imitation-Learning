import importlib.util,json,copy,sys
from pathlib import Path
import numpy as np
S=Path(__file__).resolve().parent;D=S/'clearance_filter_001';O=D/'diagnosis_001';O.mkdir()
P=S/'attempts/attempt_002';spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
sys.path.insert(0,str(D));import clearance,mujoco
model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body name="one"><freejoint/><geom type="box" size=".02 .02 .02"/></body><body name="two" pos=".04 0 0"><freejoint/><geom type="box" size=".02 .02 .02"/></body></worldbody></mujoco>')
data=mujoco.MjData(model);mujoco.mj_forward(model,data)
before=clearance.array_hashes(model);again=clearance.array_hashes(model);clone=copy.copy(model);cb=clearance.array_hashes(clone)
saved={k:getattr(clone,k).copy() for k in clearance.FIELDS}
for k in clearance.FIELDS:getattr(clone,k)[:]=.015
cd=mujoco.MjData(clone);cd.qpos[:]=data.qpos;cd.qvel[:]=data.qvel;mujoco.mj_forward(clone,cd)
for k,v in saved.items():getattr(clone,k)[:]=v
ca=clearance.array_hashes(clone);after=clearance.array_hashes(model)
changed={k:dict(dtype=str(getattr(clone,k).dtype),shape=getattr(clone,k).shape,values=getattr(clone,k).tolist()) for k in cb if cb[k]!=ca[k]}
result=dict(repeated_unmutated_original_hashes_equal=before==again,copied_before_matches=cb==before,original_after_matches=after==before,
            copied_changed_fields=changed,original_changed_fields=[k for k in before if before[k]!=after[k]],native_version=mujoco.__version__,
            physics_integration_steps=0,policy_training_updates=0)
with (O/'array_diagnosis.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
