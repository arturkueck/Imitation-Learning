import json,hashlib,shutil,py_compile,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
S=Path(__file__).resolve().parent;O=S/'clearance_filter_001';N=O/'preflight_003';N.mkdir()
source=(O/'clearance_valid_arrays.py').read_text(encoding='utf-8')
source=source.replace('def array_hashes(obj, omit_inactive_islands=False):',"INACTIVE_DUAL_FIELDS={'efc_AR','efc_AR_rownnz','efc_AR_rowadr','efc_AR_colind'}\n\ndef array_hashes(obj, omit_inactive_islands=False, omit_inactive_dual=False):")
source=source.replace("if name.startswith('_') or (omit_inactive_islands and name in INACTIVE_ISLAND_FIELDS):continue", "if name.startswith('_') or (omit_inactive_islands and name in INACTIVE_ISLAND_FIELDS) or (omit_inactive_dual and name in INACTIVE_DUAL_FIELDS):continue")
source=source.replace("    data_before=array_hashes(original_data,omit_inactive_islands=islands_disabled);", "    dual_solver_active=bool(mujoco.mj_isDual(model))\n    data_before=array_hashes(original_data,omit_inactive_islands=islands_disabled,omit_inactive_dual=not dual_solver_active);")
source=source.replace("array_hashes(original_data,omit_inactive_islands=islands_disabled)==data_before", "array_hashes(original_data,omit_inactive_islands=islands_disabled,omit_inactive_dual=not dual_solver_active)==data_before")
source=source.replace("island_discovery_enabled=not islands_disabled,", "dual_solver_active=dual_solver_active,excluded_inactive_dual_arrays=sorted(INACTIVE_DUAL_FIELDS) if not dual_solver_active else [],\n                dual_array_role='Only computed by mj_projectConstraint for dual solvers; excluded only when native mj_isDual(model) is false.',\n                island_discovery_enabled=not islands_disabled,")
with (O/'clearance_defined_arrays.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'preflight_002/run.py').read_text(encoding='utf-8').replace('import clearance_valid_arrays as clearance','import clearance_defined_arrays as clearance')
with (N/'run.py').open('x',encoding='utf-8') as f:f.write(source)
shutil.copy2(O/'preflight_002/supervise.py',N/'supervise.py')
source=(O/'run.py').read_text(encoding='utf-8').replace('import clearance','import clearance_defined_arrays as clearance')
with (O/'run_defined_arrays.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'supervise.py').read_text(encoding='utf-8').replace("OUT / 'run.py'","OUT / 'run_defined_arrays.py'")
with (O/'supervise_defined.py').open('x',encoding='utf-8') as f:f.write(source)
for p in [O/'clearance_defined_arrays.py',N/'run.py',O/'run_defined_arrays.py',O/'supervise_defined.py']:py_compile.compile(str(p),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
record=dict(actor='agent',event='clearance_dual_array_preflight_repair',unix=now,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
            reason='All six synthetic query/filter cases passed after inactive-island repair. Recorded preflight still hashes uninitialized efc_AR_colind, shown to change under repeated reads with no operation. Native model uses Newton, and 3.2.3 mjData defines efc_AR arrays as computed by mj_projectConstraint for dual solvers. New utility excludes only that inactive group when native mj_isDual is false, preserving all model, physical/core/auxiliary and defined array checks.',
            prior_preflight='clearance_filter_001/preflight_002',fresh_preflight='clearance_filter_001/preflight_003',primary_response_started=False,
            repair_source_sha256=hashlib.sha256((O/'clearance_defined_arrays.py').read_bytes()).hexdigest(),original_sources_and_failures_retained=True,
            new_policy_updates=0,response_probes_repeated=0,coordinator_training_repair_not_requested=True)
with (N/'REPAIR.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
with (S/'repairs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record,indent=2))
