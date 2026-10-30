from pathlib import Path
import json,math
OUT=Path(__file__).resolve().parent
def wilson(k,n):
    z=1.96;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-r,c+r
lines=['# Nachtlauf: beobachtete Ergebnisse','', 'Automatische Auswertung; fehlende oder unvollstaendige Tests sind keine Erfolge.','', '| Arm | Seed | Update | Datenpass-Aequivalent | Dev 2 | Dev 3 |','|---|---:|---:|---:|---:|---:|']
for arm in ['raw','relative']:
    for seed in [1,2,3]:
        folder=OUT/f'{arm}_seed{seed}';curve=folder/'learning_curve.json'
        if not curve.exists():continue
        for r in json.loads(curve.read_text()):
            three='nicht gemessen' if r['dev3'] is None else f"{100*r['dev3']:.1f}%"
            lines.append(f"| {arm} | {seed} | {r['update']} | {r['effective_epochs']:.3f} | {100*r['dev2']:.1f}% | {three} |")
lines+=['','## Separater Test: 100 neue Starts pro Trainingsseed','']
passed={a:[] for a in ['raw','relative']}
for path in sorted(OUT.glob('*_seed*/test3.json')):
    r=json.loads(path.read_text());lo,hi=wilson(r['successes'],r['n'])
    lines.append(f"- {path.parent.name}: {r['successes']}/{r['n']}; Wilson 95% [{lo:.1%}, {hi:.1%}]; vollstaendig: {r['complete']}.")
    passed[r['arm']].append(bool(r['complete'] and r['n']==100 and r['successes']>=90))
lines+=['',f"90%-Punktziel auf allen drei Trainingsseeds erreicht: { {a:len(v)==3 and all(v) for a,v in passed.items()} }.",
    '', '90/100 ist eine Punktschaetzung, kein Beleg, dass die wahre Erfolgswahrscheinlichkeit mindestens 90% betraegt. Entwicklungsrollouts duerfen dafuer nicht als Test verwendet werden.']
lines+=['','## Uebergangsdiagnose (Entwicklungsrollouts)','', '| Lauf / Checkpoint | Erste Paarplatzierung | Zweite Fertigkeit gestartet | Voller Turm |','|---|---:|---:|---:|']
for path in sorted(OUT.glob('*_seed*/dev3_*.json')):
    r=json.loads(path.read_text());rows=r['rows'];n=len(rows)
    lines.append(f"| {path.parent.name}/{path.stem} | {sum(x['first_stack_step'] is not None for x in rows)}/{n} | {sum(x['second_skill_started'] for x in rows)}/{n} | {r['successes']}/{n} |")
(OUT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
