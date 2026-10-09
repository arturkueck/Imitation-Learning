import importlib.util,json,copy,sys
from pathlib import Path
import numpy as np
S=Path(__file__).resolve().parent;D=S/'clearance_filter_001';O=D/'diagnosis_002';O.mkdir()
P=S/'attempts/attempt_002';spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
sys.path.insert(0,str(D));import clearance,mujoco
model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body name="one"><freejoint/><geom name="box_one" type="box" size=".02 .02 .02"/></body><body name="two" pos=".04 0 0"><freejoint/><geom name="box_two" type="box" size=".02 .02 .02"/></body></worldbody></mujoco>')
data=mujoco.MjData(model);mujoco.mj_forward(model,data)
before=clearance.array_hashes(data);again=clearance.array_hashes(data)
initial={k:getattr(data,k).copy() for k in before}
try:clearance.query(model,data,{'box_one','box_two'},.015);error=None
except BaseException as e:error=repr(e)
after=clearance.array_hashes(data)
changed={k:dict(dtype=str(getattr(data,k).dtype),shape=getattr(data,k).shape,exact_value_equal=bool(np.array_equal(initial[k],getattr(data,k),equal_nan=True)),
                old_values=initial[k].tolist(),new_values=getattr(data,k).tolist()) for k in before if before[k]!=after[k]}
result=dict(repeated_unmutated_data_hashes_equal=before==again,error=error,data_changed_fields=changed,native_version=mujoco.__version__,physics_integration_steps=0,policy_training_updates=0)
with (O/'data_diagnosis.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
