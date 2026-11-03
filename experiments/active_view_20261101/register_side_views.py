"""Publish preserved diagnostic side-view artifacts; never run training."""
from pathlib import Path
import json,shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'experiments/visual_active_v3_20261101/run_001/presentation'
entries=[]
rows=[]
for direction,number,label in [('right','07_rechts_links','Kamera rechts → Blick links'),('left','08_links_rechts','Kamera links → Blick rechts')]:
    run=HERE/f'side_view_{direction}_001';r=json.loads((run/'report.json').read_text())
    stem=f'comparison-{number}'
    for source,suffix,kind in [('comparison.gif','.gif','comparison-gif'),('scene_comparison.json','.scene.json','comparison-scene'),('report.json','-report.json','document')]:
        name=stem+suffix;shutil.copy2(run/source,OUT/name)
        title=f"{label} · {r['camera_elevation_deg']:.1f}° über Zielhöhe · {r['camera_change']['baseline_m']*100:.1f} cm"
        entries.append(dict(name=name,file='presentation/'+name,kind=kind,label=title+(' · interaktive Geometrie' if kind=='comparison-scene' else '')))
    rows.append(f"| {label} | {r['camera_change']['baseline_m']*100:.1f} cm | {r['camera_elevation_deg']:.1f}° | {r['optical_axis_error_deg']:.2f}° | {r['initial_set_error_mm']:.2f} → {r['updated_set_error_mm']:.2f} |")

method='''# Gezielte Seitenansichten – technische Diagnose, 02.11.2026

Kamera nach Roboterrechts und zum Ziel nach links ausrichten; umgekehrt für Roboterlinks. Rechts/links beziehen sich auf die horizontale Richtung von Roboterbasis zum vorhergesagten Ziel. Die Kamera blickt entlang ihrer tatsächlichen MuJoCo-Achse −Z. Eine reine Kameradrehung oder ein großer Versatz allein genügen nicht.

Das Ziel ist die unsicherste vorhergesagte Objektgruppe (fehlende Ensemble-Unterstützung/Streuung), nicht die echte Objektposition. Kandidaten koppeln seitlichen Versatz und Ausrichtung auf dieses Ziel. Die Höhe wird auf eine flache Seitenansicht begrenzt. Start- und Zielblickstrahlen sowie der tatsächliche Kameraweg sind im interaktiven 3D-Abgleich einblendbar. Die Zwischenbewegung ist eine Gelenkbahn; ein dauerndes Nachführen der Blickachse während der Fahrt ist nicht nachgewiesen.

| Ansicht | Kameraversatz | Blickhöhe über Zielhorizontalen | Zielabweichung der optischen Achse | Satzfehler vor → nach (mm-äq.) |
| --- | --- | --- | --- | --- |
'''+ '\n'.join(rows)+'''

Der kombinierte Satzfehler berücksichtigt Position, Ecken und fehlende/zusätzliche Objekte. Beide Seitenbilder verschlechtern in dieser einen Diagnoseszene das eingefrorene Modell. Die aktualisierte Vorhersage wird deshalb nicht als Produktionskorrektur übernommen. Diese zwei Beispiele belegen keine Generalisierung. Drei unveränderte M2-Checkpoints mit geprüften Hashes werden ausgewertet; es gibt keine Optimizerupdates und kein neues Training.

## Basisansicht: blockiert

Die Kamera näher zur Basis und von dort zum Ziel ausgerichtet ist als eigener Kandidatenmodus implementiert. Die erste Suche fand keine gültige Haltung. Eine zweite diagnostische Suche mit sechs gültigen IK-Ausgangshaltungen und bis zu 40° Blickhöhe fand ebenfalls keine gültige Haltung (52 Kandidaten). Es wurde keine Basisfahrt ausgeführt und kein Basis-GIF erfunden. Dies beweist keine globale Unerreichbarkeit; der begrenzte Planer hat keine gültige Lösung gefunden.

## Bewegung und Sicherheitsgrenze

Beide ausgeführten Wege wurden einschließlich Arm, Greifer und Kameragehäuse gegen Gelenkgrenzen, Selbst- und Umweltkollisionen geprüft. Die Replay-Zustände wurden erneut geprüft; native Robot-Umwelt-Penetrationen: 0. Der rechte Weg enthält 920, der linke 898 vollständige Wegprüfungen. Dies nutzt ausdrücklich Simulatorreferenz und diskrete konservative Bahnprüfungen, keine formale Garantie für kontinuierliche Bewegung oder echte Hardware.

Die unabhängige rein visuelle Freigabe blockiert weiterhin mit `initial_arm_volume_unverified / unknown_space`. Nicht beobachteter Freiraum gilt nicht als frei. Die Demonstration umgeht diese Sperre nicht im visuellen Betrieb; Simulatorreferenz ist als eigener Diagnosemodus bezeichnet.

## Nächster fachlicher Schritt

Diese Blickfamilien mit tatsächlichen Kameraposen als Trainingsdaten abdecken und die Fusion/Übernahme zusätzlicher Bilder separat validieren. Verbesserung muss auf unabhängigen Szenen und einer Kalibrierungsmenge nachgewiesen werden. Bis dahin bleibt die gelernte aktive Produktionsentscheidung deaktiviert. Das ist Vorbereitung, kein gestarteter Trainingslauf.
'''
(HERE/'SIDE_VIEWS.md').write_text(method,encoding='utf-8')
shutil.copy2(HERE/'SIDE_VIEWS.md',OUT/'side-views-method.md')
for run in ['side_view_base_001','side_view_base_002']:
    shutil.copy2(HERE/run/'report.json',OUT/f'{run}-report.json')
    entries.append(dict(name=f'{run}-report.json',file=f'presentation/{run}-report.json',kind='document',label=f'Basisansicht blockiert · {run}'))
for source,name in [('praxis/src/active_view/side_views.py','planner_source.py'),('experiments/active_view_20261101/side_view_demo.py','demo_source.py')]:
    shutil.copy2(ROOT/source,HERE/'side_view_base_002'/name)
entries.append(dict(name='side-views-method.md',file='presentation/side-views-method.md',kind='document',label='Gezielte Seitenblicke · Methode, Ergebnisse und blockierte Basisansicht'))
registry=ROOT/'monitor/training-runs.json';data=json.loads(registry.read_text(encoding='utf-8'))
run=next(x for x in data['runs'] if x['id']=='vision-active-v3-run1')
names={x['name'] for x in entries};run['artifacts']=entries+[x for x in run['artifacts'] if x['name'] not in names]
run['description']='Abgeschlossen: M1/M2 mit je drei Seeds. Aktive Produktionsentscheidung bleibt gesperrt. Unter 3D-Abgleich: gezielte Seitenblicke rechts/links mit Gegenneigung (16–17° über Zielhöhe), Kameraweg und tatsächlicher Blickachse. Erkennung in diesen Diagnosen verschlechtert; Basisansicht blockiert. Nur Simulatorreferenz, rein visuelle Freigabe weiterhin blockiert.'
registry.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Registered two side views and two preserved blocked base searches; no training.')
