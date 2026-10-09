import shutil
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'clearance_filter_001';N=O/'diagnosis_003';N.mkdir()
source=(O/'clearance_valid_arrays.py').read_text(encoding='utf-8')
needle="        assert result['copied_model_restored'] and result['original_model_unchanged'] and result['original_data_unchanged']"
assert source.count(needle)==1
diagnostic="""        from pathlib import Path
        current=array_hashes(original_data,omit_inactive_islands=islands_disabled)
        again=array_hashes(original_data,omit_inactive_islands=islands_disabled)
        report=dict(copied_model_restored=result['copied_model_restored'],original_model_unchanged=result['original_model_unchanged'],
                    original_data_unchanged=result['original_data_unchanged'],unmutated_repeated_data_hashes_equal=current==again,
                    changed_original_arrays={k:dict(dtype=str(getattr(original_data,k).dtype),shape=getattr(original_data,k).shape) for k in data_before if data_before[k]!=current[k]},
                    solver=int(model.opt.solver),jacobian=int(model.opt.jacobian),nisland=int(original_data.nisland),nefc=int(original_data.nefc),
                    explicit_query_forward_calls=1,physics_steps=0,policy_updates=0)
        with (Path(__file__).resolve().parent/'recorded_diagnosis.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
"""
# Diagnose only the failing recorded query, not the already successful synthetic cases.
source=source.replace(needle,diagnostic+needle)
with (N/'clearance_debug.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'preflight_002/run.py').read_text(encoding='utf-8').replace('import clearance_valid_arrays as clearance','import clearance_debug as clearance').replace('for excluded in [False,True]:','for excluded in []:')
with (N/'run.py').open('x',encoding='utf-8') as f:f.write(source)
shutil.copy2(O/'preflight_002/supervise.py',N/'supervise.py')
