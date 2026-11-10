"""Final report generated only after both fixed-start evaluations are complete."""
import json
from dynamics_common import OUT
def read(name):return json.loads((OUT/name).read_text())
p=read('protocol.json');a=read('analysis.json');d=read('diagnostics.json');verify=read('verification.json');rr={v:read(v+'/rollouts/results.json') for v in ('baseline','dynamics')}
assert all(len(r)==20 for r in rr.values());assert all(len(s)==20 for s in verify['validated_rollout_seeds'].values())
b=a['baseline'];n=a['dynamics'];fmt=lambda x:f'{x:.2f}';pct=lambda x:f'{100*x:.1f} %'
def med(x):return fmt(x['q'][2]) if x.get('n') else 'nicht messbar'
def height(x):return f"{x['q'][2]:.3f}" if x.get('n') else 'nicht messbar'
def counts(key):return [sum(r[key] for r in rr[v]) for v in ('baseline','dynamics')]
stages=[('Greifen','grasp'),('Anheben, B > 0,88 m','lift'),('Expert-ähnliche Höhe erreicht','correct_lift'),('Transport begonnen, B > 0,98 m','transport_started'),('Vorzeitiger Transport, Bewegung','premature_transport'),('3-cm-Zielbereich','near'),('Positioniert, < 9 mm','position'),('Abgesenkt','lower'),('Release mit Würfelkontakt','release'),('Stack, auch vorübergehend','stack'),('Stabiler Stack, weitere 2 s','sustained_success')]
table='\n'.join('| '+label+' | '+' | '.join(f'{c}/20 ({5*c} %)' for c in counts(key))+' |' for label,key in stages)
ft=read('feature_distribution.json');norm=p['feature_normalization'];featuretable='\n'.join(f"| {name} | {norm['mean'][j]:.6f} | {norm['std'][j]:.6f} | {ft['lift'][name]['raw']['q'][2]:.6f} | {ft['transport'][name]['raw']['q'][2]:.6f} |" for j,name in enumerate(norm['names']))
def rowmetric(label,fn):return '| '+label+' | '+' | '.join(fn(a[v],v) for v in ('baseline','dynamics'))+' |'
offline='\n'.join([
rowmetric('Paar-Sensitivität / Expert-Sprung, Validierung, Median',lambda r,v:f"{100*r['paired']['model_over_expert_change']['q'][2]:.2f} %"),
rowmetric('Paar-Sensitivität / Expert-Sprung, Training, Median',lambda r,v:f"{100*d[v]['train_paired']['model_over_expert_change']['q'][2]:.2f} %"),
rowmetric('Expertgerichtete Paar-Reaktion, Validierung, Median',lambda r,v:f"{100*r['paired']['aligned_response_over_expert']['q'][2]:.2f} %"),
rowmetric('Klarer Lift → klarer Transport bei gepaartem Rauschen',lambda r,v:pct(r['paired']['strict_lift_to_transport_switch_fraction'])),
rowmetric('Vorzeitiger Start, früher als −0,1 s',lambda r,v:pct(r['sampling']['early_fraction'])),
rowmetric('Start innerhalb ±0,1 s',lambda r,v:pct(r['sampling']['on_time_fraction'])),
rowmetric('Start im Fenster gefunden',lambda r,v:pct(r['sampling']['onset_found_fraction'])),
rowmetric('Startzeit, Median unter gefundenen Starts',lambda r,v:f"{r['sampling']['onset_steps']['q'][2]*.05:.2f} s"),
rowmetric('Grenzbeobachtungen mit beiden Modi',lambda r,v:pct(r['sampling']['boundary_both_modes_fraction'])),
rowmetric('Klarer Lift-Modus direkt vor Grenze',lambda r,v:pct(r['pre']['lift_mode'])),
rowmetric('Klarer Transport-Modus direkt nach Grenze',lambda r,v:pct(r['post']['transport_mode'])),
rowmetric('XY-Aktionsbetrag vor / nach Grenze, Mittel',lambda r,v:fmt(r['pre']['xy']['mean'])+' / '+fmt(r['post']['xy']['mean'])),
rowmetric('Z-Aktion vor / nach Grenze, Mittel',lambda r,v:fmt(r['pre']['z']['mean'])+' / '+fmt(r['post']['z']['mean'])),
rowmetric('XY / Expert nach Grenze, Median',lambda r,v:pct(r['post']['xy_over_expert']['q'][2])),
rowmetric('XY / Expert im stabilen Transport, Median',lambda r,v:pct(r['transport']['xy_over_expert']['q'][2])),
rowmetric('Gripper öffnet direkt vor / nach Grenze',lambda r,v:pct(r['pre']['opening'])+' / '+pct(r['post']['opening'])),
rowmetric('Grenz-Streuung XY / Z, mittlere Standardabweichung',lambda r,v:fmt(r['sampling']['boundary_xy_std']['mean'])+' / '+fmt(r['sampling']['boundary_z_std']['mean']))])
distance='\n'.join('| '+s+' s | '+' | '.join((f"{100*a[v]['rollouts']['distance_after_full_lift'][s]['mean']:.2f} cm (n={a[v]['rollouts']['distance_after_full_lift'][s]['n']})" if a[v]['rollouts']['distance_after_full_lift'][s]['n'] else 'nicht messbar (n=0)') for v in ('baseline','dynamics'))+' |' for s in ('0.5','1.0','2.0'))
behavior=[]
for v in ('baseline','dynamics'):
    r=a[v]['rollouts'];early=sum(x['premature_command_start'] is not None and (x['full_lift_end'] is None or x['premature_command_start']<x['full_lift_end']) for x in rr[v]);ordered=sum(x['full_lift_end'] is not None and x['transport_start'] is not None and x['full_lift_end']<=x['transport_start'] for x in rr[v])
    maxall=max(x['max_cube_height_m'] for x in rr[v]);delay=r['transport_delay_steps'];dt=f"{delay['q'][2]*.05:.2f} s (n={delay['n']})" if delay['n'] else 'nicht messbar'
    behavior.append(f"- **{v}:** maximale gehaltene Würfelhöhe, Median {height(r['max_held_height'])} m; absolut höchste erreichte Würfelhöhe {maxall:.3f} m; Würfelhöhe beim Transportbeginn, Median {height(r['transport_start_height'])} m (n={r['transport_start_height']['n']}); Transportbeginn relativ zu vollem Lift-Ende, Median {dt}; vorzeitiger XY-Befehl {early}/20; volle Höhe vor erstem Transport {ordered}/20; XY-Richtungswechsel im Transport, Median {med(r['xy_reversals'])}.")
pairseeds=read('representative_seeds.json');links='\n'.join(f'- Seed {s}: [gepaarte Zustands-/Aktionsverläufe](rollout_pair_{s}.png), [Baseline-Video](baseline/rollouts/{s}.mp4), [Dynamik-Video](dynamics/rollouts/{s}.mp4).' for s in pairseeds)
matched=read('rollout_matched.json')['full_lift_in_both_seeds']
text=f'''# Kontrollierter Versuch: explizite Dynamik aus zwei Frames

**Einordnung: C – die kontinuierliche Dynamikdarstellung hilft messbar, löst aber die schwache Umschaltsensitivität nicht.** Die mediane Reaktion auf denselben gepaarten Expert-Grenzübergang wächst auf Validierungsdaten um den Faktor {n['paired']['model_over_expert_change']['q'][2]/b['paired']['model_over_expert_change']['q'][2]:.2f}, bleibt jedoch bei {pct(n['paired']['model_over_expert_change']['q'][2])} des Expert-Aktionssprungs. Keine der 640 gepaarten Vorhersagen vollzieht bei identischem Anfangsrauschen den klaren Lift→Transport-Wechsel. Der Effekt erscheint ähnlich auf Trainingsdaten. Die Rollout-Zahlen unten bestimmen zusätzlich, ob ein praktischer Trade-off vorliegt; die Klassifikation bedeutet keine generelle Widerlegung anderer Repräsentationen.

## Kontrolle des Vergleichs

- Ausgangspunkt: korrigierter Scheduler, zwei ausgeführte Aktionen, Epoch-300-Checkpoint; SHA256 `{p['source_sha256']}`.
- Beide Varianten starten aus demselben funktionsbewahrend erweiterten Checkpoint. Alte Netz-/EMA-Gewichte und AdamW-Momente werden übernommen, zusätzliche Projektionsspalten und deren Momente starten bei null. Initiale Vorhersagen zwischen Varianten bitgleich; maximaler Unterschied zur ursprünglichen Policy {p['initial_prediction_max_error_vs_original']:.8f} durch Rundung.
- Baseline: bisherige 15 Zustandsfeatures unverändert, vier zusätzliche Kapazitätskontroll-Kanäle konstant null. Dynamik: dieselben Rohfeatures plus vier kontinuierliche Merkmale. Deshalb in **beiden Armen exakt {p['parameters_both_variants']:,} Parameter**, gegenüber ursprünglich {p['parameters_original']:,}. Nur die FiLM-Eingangsbreite wächst in beiden von 286 auf 294; keine anderen Netzblöcke ändern sich. Die zusätzlichen Baseline-Gewichte bleiben tatsächlich exakt null; die Dynamikgewichte lernen, EMA-L2-Norm {verify['new_ema_weights']['dynamics']['l2_norm']:.3f}.
- Identischer unveränderter Datensatz: 200 Demos, 180 Training / 20 Validierung, identische vorbestehende Splits. Die 62 Demos mit schwarzen Bildern bleiben unverändert und separat dokumentiert; für diese State-Policy werden Bilder nicht verwendet.
- **5.000 Gradient Updates pro Arm**, Batch 8, Seed 1, uniformes Sampling; 40.000 Ziehungen und Lernratenfolgen bitgleich geprüft. Kein Oversampling. AdamW-/EMA-Step 30.000→35.000. Gemeinsamer Cosinus-Neustart bei 1e−4 mit 500 Warmup-Updates, weil die ursprüngliche LR bereits null war. Kein Zwischencheckpoint ausgewählt.
- History 2, Chunk 16, ausgeführte Aktionen 2, DDIM 10 / Diffusion-Training 100 Schritte und sonstige Hyperparameter identisch. Beide Arme FP32 mit deaktiviertem TF32 und cuDNN-Benchmark; diese numerische Kontrolle gilt für Training und Evaluation. Historische Ergebnisse außerhalb dieses Vergleichs sind dadurch keine bitgleichen Trainingskontrollen.
- Keine zusätzliche Sensorinformation, keine History-Verlängerung, kein binäres Phasenlabel, kein Controller und keine XY-Korrektur. Alle gespeicherten ursprünglichen und ausgeführten Aktionen sind bitgleich.

## Features und Skalierung

Bei 20 Hz: `Δz = z_t − z_(t−1)`, `v_z = Δz / 0,05 s`. EEF und Würfel B stammen ausschließlich aus den beiden bereits vorhandenen Frames. Die vier Features werden einmal aus dem Fenster berechnet und in beide History-Slots kopiert: **kein dritter Frame**. Δz und v_z sind kollinear, nach Standardisierung sogar redundant; vier Kanäle liefern nur zwei unabhängige dynamische Größen. Relative Transporthöhen wurden zur Isolierung nicht ergänzt.

Normalisierung: `(Feature − Trainingsmittel) / Trainingsstandardabweichung`, ohne Clipping, ausschließlich auf den 27.322 Trainings-Ankerframes fitten. Die bisherigen Rohbeobachtungen bleiben unnormalisiert; ihre Komponentenverteilungen stehen in [original_feature_scales.json](original_feature_scales.json). Positionen haben Größenordnung 1 m, die kritische Einzeländerung dagegen etwa 1 mm.

| Feature (m bzw. m/s) | Trainingsmittel | Trainings-Std | Lift-Median | Transport-Median |
|---|---:|---:|---:|---:|
{featuretable}

Die Höhenänderungs-Std betragen 6,083 mm (EEF) und 5,294 mm (B). Im Lift liegen die normalisierten Δz-Mediane bei 1,840 / 1,893, im Transport bei −0,153 / −0,400. Die Verteilungen umfassen 5.120 Lift- und 3.693 Transport-Ankerframes. Die vier Features werden in allen Phasen berechnet, ohne Griff- oder Phasengate. [Vollständige Verteilungen](feature_distribution.json), [Histogramme](feature_distributions.png).

## Offline: Reaktion auf die Expert-Grenze

Unverändertes vorheriges Validierungspanel: 20 Demos × 21 Offsets (−0,5 bis +0,5 s), acht Draws je Frame und 32 Draws je unmittelbarem Grenzframe. Vollständige Action-Chunks gespeichert. Die zentrale Sensitivitätsmessung verwendet **identisches initiales Diffusionsrauschen vor/nach der Grenze** und zwischen Modellen: 640 Paare auf Validierung, zusätzlich 1.440 Paare auf 180 Trainingsdemos mit acht Draws. Die ausgewertete erste ausgeführte Aktion ist Chunkindex 1. Native DDIM-Implementierung und Diagnose-Schleife stimmen exakt überein.

Sensitivität = `||a_post − a_pre|| / ||Expert_post − Expert_pre||`. Expertgerichtete Reaktion projiziert die Änderung auf den Expert-Sprung, damit größere Änderungen in falscher Richtung nicht als Erfolg zählen. Unterschiedliche Draws sind keine zusätzlichen unabhängigen Demos.

| Metrik | Baseline | Dynamik |
|---|---:|---:|
{offline}

„Vor“ = Offsets −2/−1, „nach“ = 0/1/2, stabiler Transport = +6…+10. Klarer Lift: XY < 0,12, Z > 0,02, geschlossen; klarer Transport: XY > 0,25, Zielcosinus > 0,5, Z < −0,05, geschlossen. Beide Modi pro Beobachtung: mindestens 15 % der Draws jeweils in beiden Modi. Offline-Start: drei aufeinanderfolgende signifikante XY-Befehle zum Ziel über das gespeicherte Fenster; n=160 Demo/Draw-Verläufe. Der Median der Startzeit enthält nur gefundene Starts, nicht fehlende Starts. Diese Offline-Startdiagnose ersetzt keinen geschlossenen Rollout.

Die Dynamikfeatures verbessern insbesondere den Verlauf der Z-Aktion über das breitere Fenster und reduzieren frühe XY-Befehle. **Unmittelbar am gepaarten Grenzframe bleibt die lokale Reaktion winzig**. Die größere Seed-Varianz gegenüber der kleinen Zustandsreaktion und die anhaltende Moduskoexistenz sind die zentrale Gegen-Evidenz zu „Skalierung reicht aus“. [Aktionsprofile](boundary_profiles.png), [Rohmetriken](analysis.json), [Trainingskontrollen und Trainings-Paare](diagnostics.json), [Trainingsloss](training_loss.png).

## Vollständige Rollouts

20 unveränderte feste Startzustände, Seeds 46000–46019, beide Arme mit identischen Startzustands-Hashes wie bisher. Maximal 500 Schritte plus 40 Policy-Schritte zur Stabilitätsprüfung; keine Aktionseingriffe.

| Stufe | Baseline | Dynamik |
|---|---:|---:|
{table}

Voller Lift: gehaltenes B ≥ 1,045 m und EEF ≥ 1,049 m für drei Schritte; **„Höhe erreicht“ heißt noch nicht, dass bis dahin keine frühe XY-Bewegung stattfand**. Transport: gehaltenes B > 0,98 m, horizontale Geschwindigkeit > 0,02 m/s und Zielcosinus > 0,5 für drei Schritte. Vorzeitige Bewegung: dasselbe Bewegungskriterium bei B > 0,88 m, bevor beide vollen Höhenschwellen erreicht sind. Kleine kontinuierliche Bewegungen können dieses Kriterium erfüllen; daher separat die Befehle XY > 0,25 angeben. Positionierung < 9 mm, Absenken auf 40 ± 8 mm über A, Release mit Würfelkontakt; nativer Stack und weitere 2 s durchgehend stabil separat.

{'\n'.join(behavior)}

XY-Distanz nach **erstem korrektem vollen Lift-Ende**, Mittel und gültiger Nenner:

| Zeit danach | Baseline | Dynamik |
|---|---:|---:|
{distance}

Diese bedingten Distanzen sind nur für Episoden mit vollem Lift definiert. Fehlende Lifts werden nicht als 0 cm oder als Transporterfolg behandelt. Verschiedene Nenner sind kein fairer alleiniger Transportvergleich. In beiden Varianten erreichen {len(matched)} gemeinsame Startzustände die volle Lift-Höhe: {matched}. [Gepaarte Stufendifferenzen](rollout_matched.json), [alle individuellen Baseline-Werte](baseline/rollouts/results.json) und [Dynamik-Werte](dynamics/rollouts/results.json) enthalten max. Höhe, Transporthöhe, Zeitpunkt, Verzögerung und Richtungswechsel pro Seed. [Stufenvergleich](rollout_stages.png).

## Schlussfolgerung und nächster Versuch

Die explizite kontinuierliche Darstellung vorhandener Dynamik verbessert die Konditionierung und einige Offline-Zeitmetriken. **Sie reicht in diesem kontrollierten 5.000-Update-Versuch nicht aus, um den abrupten Expert-Moduswechsel zuverlässig abzubilden.** Dass die Sensitivität bereits auf Trainings-Grenzframes klein bleibt, spricht gegen ein ausschließlich durch neue Rollout-Zustände verursachtes Problem. Rollout-Stabilität kann zusätzlich beitragen, wird aber hier nicht als alleinige Erklärung behauptet.

Die Evidenz stützt damit **C mit einem Rollout-Trade-off** stärker als A. B wäre zu stark formuliert: Ein sauberer lokaler Umschaltmechanismus wurde offline gerade nicht gelernt. Transportstarts steigen von 5/20 auf 10/20, aber Greifen sinkt von 15/20 auf 12/20, Anheben von 11/20 auf 10/20 und der 3-cm-Zielbereich von 2/20 auf 1/20. Volle Lift-Höhe bleibt bei 2/20, vorzeitige Bewegung steigt von 8/20 auf 9/20, alle späteren Stufen bleiben null. Das ist ein Trade-off im Sinne von D und keine Behebung der Umschaltung. Die kleine feste Stichprobe und ein Trainingsseed erlauben keine Behauptung einer statistisch gesicherten allgemeinen Rollout-Verschlechterung. Die Daten beweisen nicht, welches Teilproblem von Diffusion-Lernziel, Konditionierung oder Chunk-Modellierung dafür verantwortlich ist.

Als nächsten Forschungsversuch ist ein **kontrollierter Vergleich mit einer anderen Policy-Struktur bzw. einem direkten Action-Chunk-Lernziel** sinnvoll: gleiche Beobachtungen, gleiche Daten, gleicher Updatebudget und dieselben gepaarten Grenztests. Zuerst prüfen, ob dieses Modell den Expert-Sprung empfindlicher abbildet; nicht gleichzeitig History, Phasenlabels oder Controller ändern. Dieser Vergleich wurde hier noch nicht implementiert. Ein einzelner Trainingsseed, 20 feste Rollout-Starts, redundante Δz/v-Kanäle und die Fortsetzung ab einem bereits trainierten Modell begrenzen die Verallgemeinerung. Weitere Repräsentationen oder Training von Grund auf sind damit nicht ausgeschlossen.

## Nachvollziehbarkeit

Für alle 40 Rollouts sind Simulatorzustände, tatsächliche Zwei-Frame-Observations einschließlich Dynamikkanälen und ursprüngliche/ausgeführte Aktionen gespeichert. Für beide Modelle sind alle offline gesampelten 16×7-Chunks gespeichert. Repräsentative Videos sind Replays dieser Zustände; keine weiteren Policy-Runs:

{links}

Es gibt keine erfolgreichen Stack-Rollouts; die Replays zeigen Zwischenfortschritte und charakteristische Fehler. [Isolationsprüfung](verification.json), [eingefrorenes Protokoll](protocol.json).

Reproduktion aus dem Workspace mit `praxis/.venv/Scripts/python.exe` und Skripten in `experiments/stack_diagnostics/stack_followup_20261001/scripts`: `dynamics_common.py` (Protokoll einmalig), `train_dynamics.py baseline|dynamics`, `offline_dynamics.py baseline|dynamics` (optional `--train-boundary`), `evaluate_dynamics.py baseline|dynamics`, `analyze_dynamics.py`, `diagnostics_dynamics.py`, `verify_dynamics.py`, `plot_dynamics_rollouts.py`, `render_dynamics.py`, `report_dynamics.py`. Vorbereitung/Training verweigern ein Überschreiben vorhandener Endcheckpoints; vor einer Replikation einen neuen Ausgabeordner verwenden.
'''
(OUT/'ERGEBNISSE.md').write_text(text,encoding='utf-8');print(OUT/'ERGEBNISSE.md')
