import json,hashlib,shutil,py_compile,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
S=Path(__file__).resolve().parent;O=S/'clearance_filter_001';N=O/'preflight_002';N.mkdir()
source=(O/'clearance.py').read_text(encoding='utf-8')
source=source.replace("def array_hashes(obj):","INACTIVE_ISLAND_FIELDS={'dof_island','island_dofnum','island_dofadr','island_dofind','dof_islandind','efc_island','island_efcnum','island_efcadr','island_efcind'}\n\ndef array_hashes(obj, omit_inactive_islands=False):")
source=source.replace("    hashes={}\n", "    hashes={}\n    if omit_inactive_islands:assert obj.nisland==0\n")
source=source.replace("        if name.startswith('_'):continue", "        if name.startswith('_') or (omit_inactive_islands and name in INACTIVE_ISLAND_FIELDS):continue")
source=source.replace("model_before=array_hashes(model);data_before=array_hashes(original_data);time_before=float(original_data.time)",
                      "model_before=array_hashes(model)\n    islands_disabled=not bool(model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ISLAND))\n    data_before=array_hashes(original_data,omit_inactive_islands=islands_disabled);time_before=float(original_data.time)")
source=source.replace("original_model_numeric_arrays=len(model_before),original_data_numeric_arrays=len(data_before),",
                      "original_model_numeric_arrays=len(model_before),original_data_numeric_arrays=len(data_before),\n                island_discovery_enabled=not islands_disabled,excluded_inactive_data_arrays=sorted(INACTIVE_ISLAND_FIELDS) if islands_disabled else [],\n                island_array_role='Only computed by mj_island; exclude these arrays only when native island feature disabled and nisland=0.',")
source=source.replace("array_hashes(original_data)==data_before", "array_hashes(original_data,omit_inactive_islands=islands_disabled)==data_before")
with (O/'clearance_valid_arrays.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'preflight_001/run.py').read_text(encoding='utf-8').replace('import preparation,clearance','import preparation\nimport clearance_valid_arrays as clearance')
with (N/'run.py').open('x',encoding='utf-8') as f:f.write(source)
shutil.copy2(O/'preflight_001/supervise.py',N/'supervise.py')
source=(O/'run.py').read_text(encoding='utf-8').replace('import clearance','import clearance_valid_arrays as clearance')
with (O/'run_valid_arrays.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'supervise.py').read_text(encoding='utf-8').replace("OUT / 'run.py'","OUT / 'run_valid_arrays.py'")
with (O/'supervise_primary.py').open('x',encoding='utf-8') as f:f.write(source)
for p in [O/'clearance_valid_arrays.py',O/'run_valid_arrays.py',O/'supervise_primary.py',N/'run.py']:py_compile.compile(str(p),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
record=dict(actor='agent',event='clearance_preflight_repair',unix=now,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
            reason='Synthetic preflight exact-state hash failed because disabled native constraint-island arrays expose uninitialized arena storage. Fresh diagnosis shows hashes change even without a query; model arrays remain exact. Version 3.2.3 headers identify these as computed by mj_island. Exclude only inactive island arrays when island discovery disabled AND nisland=0; all physical/auxiliary/defined array and model checks retained.',
            primary_response_started=False,prior_preflight='clearance_filter_001/preflight_001',fresh_preflight='clearance_filter_001/preflight_002',
            repair_source=str(O/'clearance_valid_arrays.py'),repair_source_sha256=hashlib.sha256((O/'clearance_valid_arrays.py').read_bytes()).hexdigest(),
            source_original_retained=True,new_policy_updates=0,response_probes_repeated=0,coordinator_training_repair_not_requested=True,
            primary_reference='https://mujoco.readthedocs.io/en/3.2.3/APIreference/APItypes.html#mjdata')
with (N/'REPAIR.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
with (S/'repairs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record,indent=2))
