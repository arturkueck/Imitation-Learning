"""Correct phase denominator metadata only; preserve original sources/results."""
import json,hashlib,py_compile
from pathlib import Path
S=Path(__file__).resolve().parent; O=S/'error_margin_001'; D=O/'analysis_repair_001'; D.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=(O/'analyze_margin.py').read_text(encoding='utf-8')
assert source.count('O=Path(__file__).resolve().parent; S=O.parent')==1
source=source.replace('O=Path(__file__).resolve().parent; S=O.parent','O=Path(__file__).resolve().parent.parent; S=O.parent')
source=source.replace('def summary(cases):','def summary(cases,planned=72):').replace('conditional_cases=len(cases),planned_cases=72,','conditional_cases=len(cases),planned_cases=planned,')
source=source.replace("summary([c for c in cases if c['fraction']==fr])","summary([c for c in cases if c['fraction']==fr],planned=24)")
source=source.replace("(O/'margin_analysis.json').open", "(Path(__file__).resolve().parent/'margin_analysis.json').open")
with (D/'analyze_margin.py').open('x',encoding='utf-8') as f:f.write(source)
source=(O/'verify_margin.py').read_text(encoding='utf-8')
source=source.replace('O=Path(__file__).resolve().parent; S=O.parent','O=Path(__file__).resolve().parent.parent; S=O.parent')
source=source.replace("read(O/'margin_analysis.json')","read(Path(__file__).resolve().parent/'margin_analysis.json')")
source=source.replace("sha(O/'margin_analysis.json')","sha(Path(__file__).resolve().parent/'margin_analysis.json')")
source=source.replace("(O/'margin_verification.json').open","(Path(__file__).resolve().parent/'margin_verification.json').open")
with (D/'verify_margin.py').open('x',encoding='utf-8') as f:f.write(source)
for name in ['analyze_margin.py','verify_margin.py']:py_compile.compile(str(D/name),doraise=True)
record=dict(reason='Per-phase planned_cases metadata incorrectly repeated global72; corrected to24 in each of three phases only. Primary/secondary global72, formulas, threshold, epsilon, decisions, selection and all simulator data unchanged.',
            original_hashes={n:sha(O/n) for n in ['analyze_margin.py','margin_analysis.json','verify_margin.py','margin_verification.json']},
            replacement_source_hashes={n:sha(D/n) for n in ['analyze_margin.py','verify_margin.py']},new_physics_steps=0,new_policy_updates=0)
with (D/'REPAIR.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps(record,indent=2))
