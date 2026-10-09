"""Report only after all six training replicates have passed the frozen audit."""
import json
import numpy as np
from replication_common import OUT,OLD,folder
from replication_common import rollouts

a=json.loads((OUT/'analysis.json').read_text())
v=json.loads((OUT/'verification.json').read_text())
assert v['fixed_start_hashes_verified']==240
assert all(a['aggregate'][k]['n_training_replicates']==3 for k in ('diffusion','direct'))
lines=['# Trainingsseed-Replikation: direkter Chunk-Regressor vs. Diffusion','',
'Drei unabhängige Trainingsinitialisierungen je Modellklasse, jeweils 30.000 Gradient Updates. Seed 1 ist der bereits abgeschlossene, exakt passende Ausgangsversuch; Seeds 2 und 3 wurden frisch initialisiert und vollständig neu trainiert. Keine Auswahl des besten Zwischencheckpoints.','',
'## Ergebnis je Trainingsseed','',
'| Modell | Seed | Stabile Stacks / 40 | Erfolgsrate |',
'|---|---:|---:|---:|']
for kind in ('diffusion','direct'):
    for seed in (1,2,3):
        r=a['per_seed'][kind][str(seed)]['rollout']
        lines.append(f"| {kind} | {seed} | {r['counts']['sustained_success']}/40 | {100*r['stack_rate']:.1f}% |")
lines+=['','| Modell | Mittelwert | Stichproben-SD | Minimum–Maximum |','|---|---:|---:|---:|']
for kind in ('diffusion','direct'):
    r=a['aggregate'][kind]
    lines.append(f"| {kind} | {100*r['mean']:.1f}% | {100*r['sample_std']:.1f} Prozentpunkte | {100*r['min']:.1f}–{100*r['max']:.1f}% |")
lines+=['','Die drei Trainingsseeds sind die Replikate. Die 40 identischen Startzustände innerhalb eines Modells sind gepaarte Aufgabenfälle; sie erhöhen nicht die Anzahl unabhängiger Trainingsreplikate. Bei n=3 werden keine Signifikanzbehauptungen oder scheingenauen Konfidenzintervalle angegeben.','',
'![Erfolg je Trainingsseed](seed_success.png)','',
'## Rollout-Phasen','',
'Alle Werte sind Anzahlen unter denselben 40 Starts. Phasenindikatoren sind separat gezählte Diagnosen, kein zwingend verschachtelter Funnel.','',
'| Modell/Seed | Greifen | Anheben | Expert-Höhe | Transport | Vollhöhe vor Transport | Vorzeitig | 3 cm | Position | Absenken | Release | Stabil |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for kind in ('diffusion','direct'):
    for seed in (1,2,3):
        c=a['per_seed'][kind][str(seed)]['rollout']['counts']
        vals=[c[k] for k in ('grasp','lift','correct_lift','transport_started','full_height_before_transport','premature_transport','near','position','lower','release','sustained_success')]
        lines.append(f"| {kind}/{seed} | "+' | '.join(map(str,vals))+' |')
lines+=['','Kriterien unverändert gegenüber dem Einzelversuch: Expert-ähnliche Vollhöhe verlangt gehaltenen Würfel z≥1,045 m und EEF z≥1,049 m für drei Frames. Vorzeitiger Transport ist eine zielgerichtete horizontale Bewegung vor diesem Kriterium. Das ist eine Abweichung vom Expert, kein automatischer Aufgabenfehler. Der stabile Stack verlangt die ursprüngliche Success-Bedingung durchgehend in 40 zusätzlichen Frames (2 s), Würfelkontakt und keinen gehaltenen Würfel.','',
'Greifen verwendet das native Grasp-Prädikat; Anheben verlangt B-z>0,88 m. Der bestehende Transportindikator verlangt gehaltenen Würfel B-z>0,98 m, XY-Geschwindigkeit >0,02 m/s und Zielrichtungs-Cosinus >0,5 für drei Frames. „Vollhöhe vor Transport“ bezieht sich auf diesen Indikator. Die zusätzliche Früherkennung prüft schon bei B-z>0,88 m dieselbe horizontale Bewegung, solange mindestens eine Vollhöhengrenze noch unterschritten ist, und zählt nur Ereignisse vor der ersten vollständigen Lift-Erkennung. Die Indikatoren verwenden daher bewusst verschiedene Höhengates; Transport bedeutet hier nicht jegliche erste horizontale Bewegung.','',
'Der 3-cm-Bereich verlangt XY-Abstand <3 cm und B−A-Höhe >3,2 cm. Positionierung verlangt XY-Abstand <9 mm bei derselben Höhe; Absenken zusätzlich B−A-Höhe 4 cm ±8 mm. Release verlangt dabei Würfelkontakt und keinen Grasp.','',
'## Variation der Startzustände','',
'![Gleiche 40 Startzustände, drei Trainingsseeds](start_state_success.png)','']
for kind in ('diffusion','direct'):
    r=a['aggregate'][kind]
    for key,label in [('all_seeds_success_starts','Von allen drei Seeds gelöst'),('mixed_starts','Seedabhängig'),('all_seeds_failure_starts','Von keinem Seed gelöst')]:
        values=r[key]
        lines.append(f"- **{kind}: {label}: {len(values)}/40**. Starts: "+(', '.join(map(str,values)) if values else 'keine')+'.')
lines+=['','Bei systematischen Direkt-Fehlschlägen zeigt die folgende Tabelle den ersten nicht erfüllten Phasenindikator. Dies ist eine Beschreibung der Messwerte, keine kausale Fehlerklassifikation.','',
'| Start | Direkt Seed 1 | Direkt Seed 2 | Direkt Seed 3 |','|---|---|---|---|']
rowmaps={s:{r['seed']:r for r in json.loads((rollouts('direct',s)/'results.json').read_text())} for s in (1,2,3)}
for start in a['aggregate']['direct']['all_seeds_failure_starts']:
    labels=[]
    for s in (1,2,3):
        r=rowmaps[s][start]
        labels.append(next(label for key,label in [('grasp','Greifen'),('lift','Anheben'),('transport_started','Transport'),('near','3 cm'),('position','Positionierung'),('lower','Absenken'),('release','Release'),('sustained_success','Stabiler Stack')] if not r[key]))
    lines.append(f'| {start} | '+' | '.join(labels)+' |')
lines+=['','Vollständige Erfolgsanteile je Start sind in `analysis.json` unter `start_states` gespeichert. Diese Startzustandsvariation ist von der Streuung der drei modellweiten Erfolgsraten zu unterscheiden.','',
'Die gespeicherten Direkt-Rollouts enthalten drei nachvollziehbare Beispiele: Start 46000 ist seedabhängig, 46003 wird von allen drei Seeds gelöst, 46005 von keinem. Die Zustands-/Aktionsplots und vier Videos liegen unter `representative`; die Videos spielen gespeicherte Simulatorzustände ab und sind keine zusätzlichen Evaluationen. Das Seed-3-Modellpaar auf Start 46003 zeigt zusätzlich beide Modellklassen bei identischen Anfangsbedingungen.','',
'![Seedabhängiger Start 46000](representative/direct_start_46000.png)','',
'![Modellvergleich: Trainingsseed 3, Start 46003](representative/model_pair_seed_3_start_46003.png)','',
'Im gezeigten Diffusion-Rollout wird der Würfel wiederholt nur teilweise angehoben und später verloren; schwache XY-Aktionen und wechselnde Gripperbefehle erreichen das Ziel nicht. Das Direktmodell erreicht hier keine Expert-Vollhöhe, steuert aber gezielt zum Ziel und gibt den Würfel stabil frei. Dieses Beispiel veranschaulicht die Trajektorien und ersetzt keine Auswertung über die Trainingsseeds.','',
'## Offline auf identischen Validierungsbeobachtungen','',
'20 eingefrorene Validierungsdemos, jeweils −10 bis +10 Frames um den Expert-Umschaltpunkt. Verwendet wird Chunk-Aktion 1, also die zuerst ausgeführte Aktion. Diffusion: dieselben acht gespeicherten Initialrausch-Samples je Beobachtung; Grenzreaktion: 32 gepaarte Rausch-Samples je Demo für Frame −1 und 0. Direkt: eine deterministische Vorhersage. Diese Inferenzsamples sind keine Trainingsreplikate.','',
'| Modell/Seed | Grenzreaktion / Expert (Median) | Früh | Pünktlich | Spät | Kein Start | XY/Expert (Median) | Falsche XY-Richtung | Transport-Cosinus (Mittel) |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for kind in ('diffusion','direct'):
    for seed in (1,2,3):
        o=a['per_seed'][kind][str(seed)]['offline']
        vals=[100*o['boundary_response']['q'][2],100*o['early_fraction'],100*o['on_time_fraction'],100*o['late_fraction'],100*o['missing_fraction'],100*o['xy_over_expert']['q'][2],100*o['wrong_direction_fraction']]
        lines.append(f"| {kind}/{seed} | "+' | '.join(f'{x:.2f}%' for x in vals)+f" | {o['direction_cosine']['mean']:.4f} |")
lines+=['','Grenzreaktion = ‖ΔXYZ-Vorhersage‖ / ‖ΔXYZ-Expert‖ zwischen den gepaarten Grenzframes; zusätzlich ist die Projektion auf den Expert-Sprung gespeichert. Beginn verlangt XY-Aktionsnorm >0,25 und Zielrichtungs-Cosinus >0,5 für drei Frames. Früh: früher als −2 Frames; pünktlich: ±2 Frames; spät: >2 Frames. Das begrenzte Fenster kann früheren Beginn nur linkszensiert erfassen. Stabiler Transport: +6 bis +10 Frames.','',
'![Lift–Transport-Profile je Trainingsseed](boundary_profiles.png)','',
'## Offline ↔ Closed Loop','',
'![Explorative Zusammenhänge auf Trainingsseed-Ebene](offline_rollout.png)','',
'| Metrik | Gepoolt (n=6) | Direkt (n=3) | Diffusion (n=3) |',
'|---|---:|---:|---:|']
for key,label in [('boundary_response','Grenzreaktion'),('early_fraction','Früher Offline-Beginn'),('on_time_fraction','Pünktlicher Offline-Beginn'),('xy_strength','XY-Stärke'),('direction_cosine','Transport-Cosinus'),('wrong_direction_fraction','Falsche Richtung'),('grasp_rate','Rollout-Greifrate'),('lift_height','Rollout-Maximalhöhe (Median)')]:
    values=[a['correlations'][group][key]['pearson'] for group in ('pooled','direct','diffusion')]
    lines.append('| '+label+' | '+' | '.join('nicht definiert' if x is None else f'{x:+.3f}' for x in values)+' |')
lines+=['','Pearson-Korrelationen dienen ausschließlich der Beschreibung. Gepoolte Werte können vollständig durch den Modellklassenunterschied entstehen. Innerhalb einer Klasse reichen drei Punkte nicht zur belastbaren Wahl einer Prognosemetrik; konstante Erfolgsraten oder Merkmale liefern keine definierte Korrelation. Greifrate und erreichte Höhe sind Rollout-Diagnosen, keine rein offline verfügbaren Prädiktoren.','',
'## Drei Forschungsfragen','']
dc=a['correlations']['direct']
lines.insert(lines.index('## Drei Forschungsfragen'),f"Innerhalb der Direktklasse ist die Rangfolge nicht eindeutig: r(XY-Stärke, Stackrate)={dc['xy_strength']['pearson']:+.3f}, r(Grenzreaktion, Stackrate)={dc['boundary_response']['pearson']:+.3f}, r(Richtungs-Cosinus, Stackrate)={dc['direction_cosine']['pearson']:+.3f}. Alle drei Direktmodelle beginnen offline in sämtlichen Validierungsdemos früh; die dennoch unterschiedlichen Stackraten können durch diesen konstanten Timing-Indikator nicht erklärt werden. Diese drei-Punkte-Werte werden nicht als validierte Vorhersagegüte interpretiert.")
lines.insert(lines.index('## Drei Forschungsfragen'),'')
d=a['aggregate']['direct'];f=a['aggregate']['diffusion']
lines.append(f"1. **Reproduzierbarkeit:** Direkt {100*d['mean']:.1f}% ± {100*d['sample_std']:.1f} Prozentpunkte gegenüber Diffusion {100*f['mean']:.1f}% ± {100*f['sample_std']:.1f}. "+('Der Abstand bleibt in jedem der drei Trainingsseeds bestehen.' if d['min']>f['max'] else 'Die Einzelwerte müssen berücksichtigt werden; die Bereiche überlappen.'))
successful_early=sum(a['per_seed']['direct'][str(s)]['rollout']['successful_premature'] for s in (1,2,3));successful_low=sum(a['per_seed']['direct'][str(s)]['rollout']['successful_without_full_height'] for s in (1,2,3));total=sum(a['per_seed']['direct'][str(s)]['rollout']['counts']['sustained_success'] for s in (1,2,3))
lines.append(f"2. **Exaktes Expert-Timing:** {successful_early}/{total} erfolgreiche Direkt-Rollouts transportieren vorzeitig; {successful_low}/{total} erreichen keine Expert-Vollhöhe. Diese Fälle zeigen, dass die scharfe Expert-Umschaltung und ihre maximale Lift-Höhe nicht notwendig für einen stabilen Stack in diesen Starts sind. Das ist keine Aussage, dass jedes frühe Transportieren sicher oder erfolgreich ist.")
gap=json.loads((OUT/'early_success_clearance.json').read_text())['gap_summary']
lines.append(f"   Bei diesen erfolgreichen frühen Starts beträgt der vertikale Abstand der orientierungsabhängigen Würfel-Bounding-Boxes beim ersten gemessenen horizontalen Transport mindestens {100*gap['q'][0]:.1f} cm und im Median {100*gap['q'][2]:.1f} cm. Das hilft zu erklären, warum die zusätzliche Expert-Lift-Höhe in der vorliegenden Zwei-Würfel-Aufgabe nicht erforderlich ist; es ist keine allgemeine Sicherheitsgarantie für andere Aufgaben.")
lines.append('   Im programmierten StackExpert liegt das Lift-EEF-Ziel 24 cm über der anfänglichen Würfelhöhe, das anschließende Transportziel 19 cm über dem Basiswürfel. Der Expert wechselt damit abrupt sein Zwischenziel und senkt dessen Höhe wieder ab. Die native Aufgabenbedingung fordert stattdessen Ausrichtung, Kontakt, Freigabe und Stabilität des fertigen Stacks; diese zusätzliche Zwischenhöhe ist kein Erfolgskriterium.')
lines.append('3. **Nützlichere Offline-Diagnosen:** XY-Stärke und Richtungs-Cosinus im stabilen Transport beschreiben die Fähigkeit zur Zielsteuerung direkter als die Grenzreaktion. Die Einzelwerte und Profile müssen zusammen mit Greifen, Lift und Release betrachtet werden. Dieser Versuch kann ihren Nutzen als Diagnose stützen, aber bei drei Seeds je Klasse keine allgemein gültige Prognoserangfolge etablieren. Eine schwache Grenzreaktion allein ist kein hinreichender Grund, ein Closed-Loop-fähiges Modell zu verwerfen.')
lines+=['','Der kontrollierte Vergleich repliziert die bestehenden Modellklassen einschließlich ihrer jeweiligen Architektur und ihres Lernziels. Er isoliert keine einzelne mathematische Eigenschaft von Diffusion unabhängig von der Architektur. Das Direktmodell hat 67.467.376, Diffusion 65.648.903 Parameter. Keine neue Methode wurde eingeführt.','',
'## Trainingskontrolle und Aufwand','',
'Identische 180/20 Demos und State-Observationen (15 Merkmale × 2 Frames), 16×7 Aktionen, Replanning nach zwei ausgeführten Aktionen; uniforme Verteilung, Batch 8, 30.000 Updates = 240.000 Trainingsfenster. Keine Normalisierung der Rohbeobachtungen oder Actions. AdamW 1e−4, Gewichtszerfall 1e−6, 500 Warmup-Updates mit Cosine-Scheduler, EMA Power 0,75. Innerhalb jeder Modellklasse variiert ausschließlich der Trainingsseed sowie der Ablagepfad. Direkter MSE über alle 16×7 Ausgaben, Diffusion ursprüngliches Epsilon-Ziel und DDIM mit zehn Inferenzschritten. Der korrigierte Scheduler zählt ausschließlich Trainingsupdates.','',
'| Neues Training | Updates | Trainingslaufzeit | Offline + 40 Rollouts |','|---|---:|---:|---:|']
for kind in ('diffusion','direct'):
    for seed in (2,3):
        t=json.loads((folder(kind,seed)/'training_complete.json').read_text());e=json.loads((folder(kind,seed)/'evaluation_complete.json').read_text())
        lines.append(f"| {kind}/{seed} | {t['updates']} | {t['elapsed_seconds']/60:.1f} min | {e['elapsed_seconds']/60:.1f} min |")
lines+=['','Drei statt fünf Seeds: eine gemeinsame CUDA-GPU mit 12 GB VRAM und anfangs ungefähr 26 GB freiem Datenträgerspeicher. Laufzeiten umfassen zeitweise konkurrierende GPU-Prozesse und sind keine isolierten Leistungsbenchmarks. Die vorhandenen Seed-1-Läufe und Artefakte wurden wiederverwendet.','',
'Alle 240 Startzustands-Hashes, 30.000 Optimizer-/Scheduler-Schritte pro Modell, Konfigurationsgleichheit, unveränderte Daten und stabile Erfolgs-Tails sind in `verification.json` geprüft. Frische Gewichtsinitialisierungen für Seeds 2/3 wurden gehasht. Die 62 Demonstrationen mit schwarzen Bildern bleiben unverändert; dieser Versuch verwendet ausschließlich State-Daten.','',
'## Artefakte','',
'- `protocol.json`: eingefrorene Seeds, Datenhash, Starts und Kontrollen.','- `analysis.json`: alle Einzelwerte, Startzustandsanteile und deskriptive Korrelationen.','- `verification.json`: vollständiger Audit und Checkpoint-Hashes.','- `direct/seed_2`, `direct/seed_3`, `diffusion/seed_2`, `diffusion/seed_3`: Konfiguration, Initialisierungsaudit, Checkpoints, Offline-Chunks, Logs und Rollout-Zustands-/Aktionsverläufe.','- Seed 1: unveränderte Referenzartefakte in `../stack_direct_20261001` sowie `../stack_switch_20261001/source`; Checkpointpfade in `protocol.json`.','']
body='\n'.join(lines)
for relative in ('seed_success.png','start_state_success.png','boundary_profiles.png','offline_rollout.png','representative/direct_start_46000.png','representative/model_pair_seed_3_start_46003.png'):
    body=body.replace(f']({relative})',f'](<{(OUT/relative).as_posix()}>)')
(OUT/'ERGEBNISSE.md').write_text(body,encoding='utf-8')
print(OUT/'ERGEBNISSE.md')
