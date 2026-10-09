from pathlib import Path
import py_compile
S=Path(__file__).resolve().parent;O=S/'recorded_response_001'
source=(S/'mechanism_domain_001/analyze_audit.py').read_text(encoding='utf-8')
source=source.replace('import h5py,numpy as np,psutil','import h5py,numpy as np,psutil\nimport history_audit')
source=source.replace("assert len(r['rows'])==12 and sum(len(x['branches']) for x in r['rows'])==336", "assert len(r['rows'])==24 and sum(len(x['branches']) for x in r['rows'])==672\nprepared_history_audit=history_audit.verify(O,r,sel)")
source=source.replace("and all(x['aux_passed'] and x['physical_passed'] for x in checks))", "and all(x['aux_passed'] and x['physical_passed'] for x in checks) and row['gates']['recorded_geometry_passed'])")
source=source.replace("audits.append(dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],", "audits.append(dict(demo=row['demo'],t=row['t'],fraction=row['fraction'],history=row['history'],")
start=source.index('for fraction in sel[\'anchor_fractions\']:');end=source.index('assert len(eligible)==sum',start)
body=source[start:end]
body=body.replace("x['fraction']==fraction]","x['fraction']==fraction and x['history']==history]")
body=body.replace("strata[str(fraction)]", "strata[history+'_'+str(fraction)]")
source=source[:start]+"for history in sel['histories']:\n"+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))+source[end:]
source=source.replace('len(eligible)==12','len(eligible)==24')
source=source.replace('planned_anchors=12,executed_anchors=12,planned_branches=336,executed_branches=336','planned_anchors=24,executed_anchors=24,planned_branches=672,executed_branches=672')
source=source.replace("physical_audits=audits,worker_counts=", "prepared_history_audit=prepared_history_audit,physical_audits=audits,worker_counts=")
source=source.replace("if k not in ['physical_audits','strata']", "if k not in ['physical_audits','strata','prepared_history_audit']")
with (O/'analyze_audit.py').open('x',encoding='utf-8') as f:f.write(source)
py_compile.compile(str(O/'analyze_audit.py'),doraise=True);py_compile.compile(str(O/'history_audit.py'),doraise=True)
print('Independent physical, recorded-state/history and no-fit prediction audit built.')
