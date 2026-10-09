"""Build the fixed two-history worker before response measurements."""
import hashlib,json,py_compile,shutil
from pathlib import Path
S=Path(__file__).resolve().parent;O=S/'recorded_response_001'
source=(S/'mechanism_domain_001/run.py').read_text(encoding='utf-8')
source=source.replace('import helpers as h','import helpers as h\nimport preparation')
start=source.index('                    row = dict(')
end=source.index("        assert len(result['rows']) == 12")
body=source[start:end]
body=body.replace("split='heldout', fraction=fraction, stratum=str(fraction), branches={}","split='heldout', fraction=fraction, stratum=str(fraction), history=history, branches={}")
prep_start=body.index("                            ctrl.update_initial_joints(d['obs/robot0_joint_pos'][0])")
prep_end=body.index('                            anchor, anchor_measure',prep_start)
body=body[:prep_start]+"                            preparation_info = preparation.prepare(env, ctrl, d, t, actions, history, selection)\n"+body[prep_end:]
body=body.replace('branch = dict(anchor=anchor, anchor_measure=anchor_measure,','branch = dict(preparation=preparation_info, anchor=anchor, anchor_measure=anchor_measure,')
body=body.replace("auxiliary_fields_passed=all(v['auxiliary_gate']['passed'] for v in b.values()),","auxiliary_fields_passed=all(v['auxiliary_gate']['passed'] for v in b.values()),\n                                        recorded_geometry_passed=all(v['preparation']['geometry_passed'] for v in b.values()),")
body=body.replace("and g['auxiliary_fields_passed'] and g['interventions_passed'])","and g['auxiliary_fields_passed'] and g['interventions_passed'] and g['recorded_geometry_passed'])")
body=body.replace("print(f'{demo} t={t}: {g}'","print(f'{history} {demo} t={t}: {g}'")
indented=''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))
source=source[:start]+"                    for history in selection['histories']:\n"+indented+source[end:]
source=source.replace("== 12 and sum(len(r['branches']) for r in result['rows']) == 336","== 24 and sum(len(r['branches']) for r in result['rows']) == 672")
source=source.replace('planned_branches=336','planned_branches=672')
assert 'for history' in source and 'preparation_info' in source and '== 672' in source
with (O/'run.py').open('x',encoding='utf-8') as f:f.write(source)
py_compile.compile(str(O/'run.py'),doraise=True);py_compile.compile(str(O/'preparation.py'),doraise=True)
pref=O/'preflight_001';pref.mkdir();shutil.copy2(O/'supervise.py',pref/'supervise.py')
# Supervisor locates session/job by parent; preflight is nested one extra level.
p=pref/'supervise.py';text=p.read_text();text=text.replace('SESSION = OUT.parent','SESSION = OUT.parent.parent');p.write_text(text,encoding='utf-8')
print('Fixed two-history 672-branch worker syntax checked; prepare technical-only preflight next.')
