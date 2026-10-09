import json,hashlib,py_compile,time
from pathlib import Path
O=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(O/'preflight_002/result.json')['state']=='PREFLIGHT_PASSED'
assert read(O/'preflight_002/result.json')['same_recorded_physical_state_error']==0
assert read(O/'preflight_002/result.json')['same_env_clock_error']==0
assert not (O/'launch.json').exists() and not (O/'result.json').exists()
for name in ['run.py','helpers.py','preparation.py','supervise.py']:py_compile.compile(str(O/name),doraise=True)
with (O/'PROTOCOL.md').open('a',encoding='utf-8') as f:
    f.write('\nVor Primärlaunch fixierte Umsetzung: Beide Geschichten erhalten dieselben aufgezeichneten qpos/qvel, Solver-Warmstart/act/ctrl/applied forces/userdata=0, keine Mocap-Arrays; Envzeit recorded sim time, timestep=t, done=False. H_prefix erhält alle numerisch erfassbaren Arm-/Gripper-Controller- und Grippermodellfelder außer ausdrücklich dokumentierten frisch zu berechnenden kinematischen/Jacobi-/Massen-/Updatecaches. Interpolatoren müssen None sein, sonst Abbruch. H_reset nutzt native update_initial_joints(recorded joints[t]) und reset_goal. Vollständige gehaltene Felder und Rollen in preparation.py und jedem Zweig. Vorprüfung hat geometrisch/physisch identische Präparationen bestätigt; ihre erste reine Difference-Zusammenfassung scheiterte am erwarteten Zahlenvektor-vs-None-Feld und wurde in frischem preflight_002 repariert. Kein Primärantwortschritt vor Quellenfreeze. Vorprüfungs-Physikzähler war nicht instrumentiert: dort protokollierte Null ist keine Aussage über tatsächlich ausgeführte Expertpräfixphysik; separate Kostenannotation verwenden.\n')
for name in ['preflight_001','preflight_002']:
    p=O/name;r=read(p/'result.json')
    annotation=dict(prefix_actions_performed=5,response_probe_steps=0,policy_training_updates=0,
                    original_physics_counter_instrumented=False,original_zero_physics_counter_not_a_total_cost_claim=True,
                    note='Five expert-prefix actions in each technical preflight. No primary response actions. Setup/forward calls and prefix physics not instrumented in preflight; primary worker instruments sim.step/step2.',
                    result_sha256=hashlib.sha256((p/'result.json').read_bytes()).hexdigest())
    with (p/'cost_annotation.json').open('x',encoding='utf-8') as f:json.dump(annotation,f,indent=2)
names=['run.py','helpers.py','preparation.py','supervise.py','freeze.py','repair_preflight.py','PROTOCOL.md','selection.json','calibration.json']
for d in ['preflight_001','preflight_002']:
    names += [d+'/'+n for n in ['run.py','supervise.py','result.json','cost_annotation.json']]
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:
    json.dump({name:hashlib.sha256((O/name).read_bytes()).hexdigest() for name in names},f,indent=2)
print('Two histories technically checked; fixed sources/selection/protocol frozen before primary response launch.')
