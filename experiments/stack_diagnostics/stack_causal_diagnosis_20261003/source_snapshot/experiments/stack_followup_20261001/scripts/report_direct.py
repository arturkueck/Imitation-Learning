"""Write the final comparison after all 40 paired starts and checks finish."""
import json,argparse
from direct_common import OUT
p=argparse.ArgumentParser();p.add_argument('--classification',required=True);p.add_argument('--interpretation',required=True);args=p.parse_args()
read=lambda path:json.loads((OUT/path).read_text());a=read('analysis.json');c=read('config.json');verify=read('verification.json');loss=read('offline_loss.json');assert verify['fixed_start_hash_pairs_verified']==40
pct=lambda x:f'{100*x:.1f} %';num=lambda x:f'{x:.3f}'
def metric(label,fn):return '| '+label+' | '+' | '.join(fn(a[v]) for v in ('diffusion','direct'))+' |'
offline='\n'.join([
metric('Grenzreaktion / Expert-Sprung, Median',lambda r:f"{100*r['paired']['ratio']['q'][2]:.2f} %"),
metric('Expertgerichtete Grenzreaktion, Median',lambda r:f"{100*r['paired']['aligned']['q'][2]:.2f} %"),
metric('Vorzeitiger Offline-Start (< −0,1 s)',lambda r:pct(r['onset']['early_fraction'])),
metric('Start innerhalb ±0,1 s',lambda r:pct(r['onset']['on_time_fraction'])),
metric('Verspäteter Start (> +0,1 s)',lambda r:pct(r['onset']['late_fraction'])),
metric('Kein Start im Fenster',lambda r:pct(r['onset']['missing_fraction'])),
metric('Startzeit, Median der gefundenen Starts',lambda r:f"{r['onset']['steps']['q'][2]*.05:.2f} s" if r['onset']['steps']['n'] else 'nicht messbar')])
phases=[]
for phase,label in [('lift','Stabiler Lift'),('pre','Unmittelbar davor'),('post','Unmittelbar danach'),('transport','Stabiler Transport')]:
    for v in ('diffusion','direct'):
        r=a[v][phase];direction=num(r['expert_direction_cosine']['mean']) if r['expert_direction_cosine']['n'] else 'nicht definiert';ratio=pct(r['xy_over_expert']['q'][2]) if r['xy_over_expert']['n'] else 'nicht definiert';phases.append(f"| {label} | {v} | {num(r['xy']['mean'])} | {num(r['z']['mean'])} | {ratio} | {direction} | {pct(r['lift_mode'])} | {pct(r['transport_mode'])} |")
keys=[('Greifen','grasp'),('Anheben','lift'),('Expert-ähnliche volle Lift-Höhe','correct_lift'),('Transport begonnen','transport_started'),('Vorzeitiger Transport','premature_transport'),('3-cm-Zielbereich','near'),('Positioniert','position'),('Abgesenkt','lower'),('Release','release'),('Stack, auch vorübergehend','stack'),('Stabiler Stack, weitere 2 s','sustained_success')]
tables={}
for group in ('first20','extra20','all'):
    tables[group]='\n'.join('| '+label+' | '+' | '.join(f"{a[v]['rollouts'][group]['counts'][key]}/{a[v]['rollouts'][group]['n']}" for v in ('diffusion','direct'))+' |' for label,key in keys)
    tables[group]+='\n| Volle Lift-Höhe vor Transportbeginn | '+' | '.join(f"{a[v]['rollouts'][group]['full_lift_before_transport']}/{a[v]['rollouts'][group]['n']}" for v in ('diffusion','direct'))+' |'
behavior=[]
for v in ('diffusion','direct'):
    r=a[v]['rollouts']['all'];h=r['transport_height'];dist=r['xy_distance_at_transport_start'];height=f"{h['q'][2]:.3f} m" if h['n'] else 'nicht messbar';distance=f"{100*dist['q'][2]:.2f} cm" if dist['n'] else 'nicht messbar';behavior.append(f"- **{v}:** volle Lift-Höhe vor Transport {r['full_lift_before_transport']}/40; maximale Würfelhöhe pro Episode, Median {r['max_cube_height']['q'][2]:.3f} m, Maximum {r['max_cube_height']['q'][-1]:.3f} m; Höhe beim Transportstart, Median {height}; XY-Abstand beim Transportstart, Median {distance} (n={dist['n']}).")
seeds=read('representative_seeds.json');videos='\n'.join(f'- Seed {s}: [Zustands-/Aktionsvergleich](rollout_pair_{s}.png), [Diffusion-Video](diffusion/rollouts/{s}.mp4), [Direkt-Video](direct/rollouts/{s}.mp4).' for s in seeds)
text=f'''# Diffusion versus direkter Action-Chunk-Regressor

**Einordnung: {args.classification}.** {args.interpretation}

## Fragestellung und Kontrolle

Kann ein einfacher deterministischer Chunk-Predictor aus denselben zwei Rohframes den abrupten Lift→Transport-Wechsel besser abbilden? Kein Phasenclassifier, keine State Machine, kein separater Controller, keine Hierarchie, keine Dynamikfeatures, keine zusätzliche History, keine Phasenbalancierung und keine XY-Heuristik.

Die Diffusionsreferenz ist der ursprüngliche Scheduler-korrigierte Epoch-300-Checkpoint mit **30.000 Gradient Updates ab zufälliger Initialisierung**. Das Direktmodell trainiert ebenfalls von zufälliger Initialisierung für genau 30.000 Updates. Die 5.000-Update-Fortsetzungen der letzten Runde sind hierfür keine passenden Vergleichsbudgets und werden nicht verwendet. Vorhandene Diffusionsgewichte werden nicht neu trainiert.

Datensatz unverändert: 200 Demos, 180 Training / 20 Validierung, vorbestehende Splits. Beide trainieren nur auf den 180 Trainingsdemos, uniform mit Zurücklegen, Batch 8, insgesamt 240.000 Sample-Ziehungen. Seed 1 soweit zwischen Architekturen sinnvoll. Die exakte historische Diffusions-Ziehfolge wurde nicht gespeichert und lässt sich nicht als bitgleich nachweisen; Samplingverteilung und maximale Trainingsmenge stimmen überein. Die 62 Demos mit schwarzen Bildern bleiben unverändert, State-Inputs enthalten keine Bilder. Datensatz-SHA256 `{c['dataset_sha256']}`.

## Direktmodell

| Eigenschaft | Wert |
|---|---|
| Observation | object(6), EEF-Position(3), EEF-Quaternion(4), Fingerpositionen(2) |
| Dimension | 15 pro Frame; 2 Frames; flach 30 |
| Encoder | gleiche Rohfeature-Konkatenation; keine zusätzliche Observation-Normalisierung |
| Netzwerk | Input 30→2048; 8 Residualblöcke, je LayerNorm→Linear→SiLU→Linear, Residuum / √2; Output 2048→112, tanh |
| Parameter Direkt / Diffusion | {c['parameter_count']:,} / {c['diffusion_parameter_count']:,} (+{100*(c['parameter_count']/c['diffusion_parameter_count']-1):.2f} %) |
| Output | 112 = 16 × 7; vollständiger Action Chunk |
| Replanning | zwei ausgeführte Aktionen, Chunkindex 1 und 2 |
| Loss | ungewichteter MSE über Batch × 16 Zeitpositionen × 7 Komponenten |
| Action-Normalisierung | Identität, exakt wie Diffusion; Expert-Aktionen in [−1,1]; tanh begrenzt direkte Ausgabe |
| Optimizer | AdamW, LR 1e−4, Betas 0,9/0,999, eps 1e−8, Weight Decay 1e−6 |
| LR | 500 Warmup-Updates, danach Cosinus bis Update 30.000 |
| EMA | Power 0,75, gleiche Methode wie Diffusion; finale EMA für Evaluation |
| Auswahl | ausschließlich finaler Checkpoint, kein Tuning anhand der Rollouts |

Das Aktionsfenster eines Ankerframes i beginnt wie im tatsächlichen Robomimic-Loader bei i−1. Beide geben die Aktionen an Index 1/2 aus, also i/i+1. Randpadding ist identisch und gegen 40 reale SequenceDataset-Fenster überprüft. Observationen werden FP32 übergeben, keine Mischpräzision. Unterschiedliche Modelle und Losses verhindern gemeinsame Initialgewichte und einen numerisch identischen Optimierungspfad; identischer Seed ist keine Gleichheit dieser Pfade.

Direkter Expert-Chunk-MSE nach Training: Training {loss['train']['chunk_mse']:.6f}, Validierung {loss['valid']['chunk_mse']:.6f}. Der MSE auf Actions ist nicht numerisch mit dem Diffusions-Epsilon-MSE vergleichbar. [Vollständige Direkt-Konfiguration](config.json), [ursprüngliche Diffusions-Konfiguration](diffusion_config.json), [Direkt-Checkpoint](model_final.pth). Diffusionscheckpoint: `{c['diffusion_checkpoint']}`, SHA256 `{c['diffusion_checkpoint_sha256']}`.

## Offline: identische Expert-Grenzbeobachtungen

Unverändertes gespeichertes Panel: 20 Validierungsdemos × 21 Frames, −0,5…+0,5 s um Expert-Transportbeginn. Diffusion DDIM10, zwei ausgeführte Aktionen, acht gespeicherte Draws je Panel-Frame und 32 Draws je unmittelbarem Grenzframe. Direktmodell deterministisch, je Zustand genau eine Ausgabe. Für die Grenzreaktion wird bei Diffusion das **identische Rauschen vor/nach** verwendet; so wird der Observation-Effekt von Zufallsstreuung getrennt. Direkt: 20 Paare, Diffusion: 20 × 32 Draw-Paare. Draws sind keine unabhängigen Demos.

Grenzreaktion = `||a_post − a_pre|| / ||Expert_post − Expert_pre||`, erste ausgeführte XYZ-Aktion. Zusätzlich Projektion der Reaktion auf den Expert-Sprung, damit falsche Änderungsrichtungen nicht als Verbesserung zählen. [Paarvergleiche](paired_boundary_comparisons.json), [Bootstrap über Demos](paired_demo_bootstrap.json), [Offline-Predictions](offline_predictions.npz). Für das Direktmodell wurden außerdem alle Frames der 200 Demos vorhergesagt und gespeichert, ohne Validierungsdaten für Updates zu verwenden.

| Offline-Metrik | Diffusion | Direkt |
|---|---:|---:|
{offline}

Startkriterium: XY > 0,25 und Zielcosinus > 0,5 für drei aufeinanderfolgende Frames. Früher als −2 Frames = vorzeitig, ±2 Frames = pünktlich, später als +2 = verspätet; kein Start im ±0,5-s-Fenster separat. Startzeit-Median nur unter gefundenen Starts. Die deterministische direkte Policy wird für diese Prozentwerte über 20 Demos bewertet, Diffusion über 160 Demo/Draw-Verläufe. Der Bootstrap aggregiert zuvor die Diffusionsdraws pro Demo; seine Unsicherheit beschreibt Validierungsdemos, nicht unbekannte Trainingsseed-Variation.

## Vier Phasenbereiche

Stabiler Lift: Offsets −10…−6; unmittelbar davor −2/−1; unmittelbar danach 0/1/2; stabiler Transport +6…+10. XY/Z in der Tabelle sind Mittelwerte. Der Richtungs-Cosinus und das XY/Expert-Verhältnis werden nur bei Expert-XY > 0,1 gemessen; bei Lift-Aktionen ist die Richtung kleiner XY-Komponenten kein sinnvoller Fehlerindikator. Klarer Lift: XY < 0,12, Z > 0,02, Gripper geschlossen. Klarer Transport: XY > 0,25, zum Ziel, Z < −0,05, geschlossen.

| Bereich | Modell | XY-Betrag | Z-Aktion | XY/Expert, Median | Richtungs-Cosinus | Lift-Modus | Transport-Modus |
|---|---|---:|---:|---:|---:|---:|---:|
{'\n'.join(phases)}

[Aktionsprofile um den Umschaltpunkt](boundary_profiles.png) zeigen, ob die Ausgabe einen Sprung oder eine geglättete Übergangszone bildet. Ein größerer XY-Betrag oder ein guter durchschnittlicher Transportmodus allein ist noch kein korrekter Umschaltmechanismus. [Vollständige Zahlen einschließlich Richtungsfehler und Gripper-Öffnungen](analysis.json).

## Rollouts: 40 gemeinsame Startzustände

Seeds 46000–46019 bleiben erhalten; hinzu kommen 46020–46039. Alle 40 initialen Zustands-Hashes sind zwischen Modellen identisch. Die ersten 20 unveränderten Diffusions-Rollouts wurden bitgleich aus der bisherigen Diagnose übernommen, inklusive 500-Schritt-Horizont. Dort gibt es keinen nativen Stack-Erfolg, daher benötigt ein stabiler Stack keine zusätzliche Verifizierung. Neue Rollouts: höchstens 500 Schritte, bei Erfolg früher beendet, jeweils weitere 40 Policy-Schritte für zwei Sekunden Stabilitätsprüfung. Keine Aktionen korrigiert.

**Alle 40 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
{tables['all']}

**Bisherige 20 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
{tables['first20']}

**Zusätzliche 20 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
{tables['extra20']}

{'\n'.join(behavior)}

Anheben: B > 0,88 m. Volle Expert-ähnliche Höhe: gehaltenes B ≥ 1,045 m und EEF ≥ 1,049 m für drei Schritte. Transport: gehaltenes B > 0,98 m, XY-Geschwindigkeit > 0,02 m/s, Zielcosinus > 0,5 für drei Schritte. **Volle Höhe irgendwann erreicht ist kein korrekt getimter Lift**; zusätzlich oben „volle Höhe vor Transport“ und vorzeitige Bewegungen. Vorzeitige Bewegung prüft das Bewegungskriterium vor Erreichen beider Höhenschwellen bei B > 0,88 m. Positionierung <9 mm XY, Absenken 40±8 mm über Ziel, Release mit Würfelkontakt, nativer Stack und weitere zwei Sekunden Stabilität getrennt. [Individuelle Diffusions-Metriken](diffusion/rollouts/results.json), [Direkt-Metriken](direct/rollouts/results.json).

## Interpretation und Grenzen

{args.interpretation}

**Expert-Timing ist hier nicht identisch mit Aufgabenlösbarkeit:** 19 der 28 stabilen Direkt-Stacks erreichen die volle Expert-ähnliche Höhenschwelle nicht und werden als vorzeitiger Transport gezählt. Diese Diagnosemarkierung darf bei einem anschließend stabilen Stack nicht automatisch als Fehler der Gesamtaufgabe interpretiert werden. Das Direktmodell nutzt einen kontinuierlicheren Übergang bei geringerer maximaler Höhe als der Expert. Es reproduziert also nicht exakt dessen Phasenwechsel, kann aber dennoch sicher genug platzieren und loslassen. Native Erfolge werden zusätzlich auf allen 40 Folgeschritten geprüft: keine gehaltenen Würfel, fortbestehender Würfelkontakt; [physische Erfolgskontrolle](success_tail_audit.json).

Als nächster Schritt erscheint eine Bestätigung dieser direkten Baseline mit mehreren **Trainingsseeds** sinnvoll, bevor neue Controller oder Hierarchien eingeführt werden. Die 70-%-Stackrate stammt von einem Trainingsseed; 85 % auf den bisherigen und 55 % auf den zusätzlichen Starts zeigen bereits eine relevante Abhängigkeit von der Startverteilung. Für die spezielle Umschaltfrage bleiben ein kontinuierlicherer Expert-Zielverlauf oder die präzise Abbildung des abrupten Action-Ziels Gegenstände weiterer isolierter Vergleiche; beides wurde hier nicht geändert. Der Befund rechtfertigt nicht, allein wegen der geglätteten Expert-Grenze ein komplexeres stochastisches Modell vorauszusetzen.

Dieser Versuch vergleicht **Modellstruktur und Lernziel gemeinsam**, nicht nur einen Loss bei identischer Architektur: Residual-MLP mit direktem Action-MSE versus bedingtes zeitliches UNet mit Epsilon-MSE und DDIM. Vergleichbare Kapazität, Inputs, Daten, Budget und Ausführung reduzieren andere Unterschiede, erlauben aber keine eindeutige kausale Zuordnung zu Diffusion allein. Ein Trainingsseed je Modell; zusätzliche Startzustände sind keine zusätzlichen Trainingsseeds. Auch EMA, tanh-Ausgabebegrenzung versus Diffusions-Clipping und die unbekannte historische Ziehfolge begrenzen die Isolation. Kein weiteres Modell und keine zusätzliche Methode wurde in diesem Versuch getunt.

## Gespeicherte Artefakte

Finaler Direkt-Checkpoint enthält Rohnetz, EMA, AdamW-Momente, LR-Scheduler, EMA-Step und vollständige Konfiguration. Diffusionsreferenz und deren Konfiguration bleiben unverändert verlinkt. Direkte Panel- und Gesamt-Datensatz-Predictions, gepaarte Grenzreaktionen, alle Rollout-Metriken und Simulatorzustände sind gespeichert. Neue Rollouts speichern zusätzlich die tatsächlich verwendeten Zwei-Frame-Observations. Videos sind Replays gespeicherter Zustände:

{videos}

[Isolationsprüfung](verification.json). Reproduktion mit `praxis/.venv/Scripts/python.exe` und Skripten in `experiments/stack_followup_20261001/scripts`: `train_direct.py`, `offline_direct.py`, `evaluate_direct_comparison.py diffusion|direct`, `analyze_direct.py`, `verify_direct.py`, `artifacts_direct.py`, `report_direct.py`. Training verweigert das Überschreiben eines Endcheckpoints; für eine Replikation den Ausgabeordner wechseln.
'''
(OUT/'ERGEBNISSE.md').write_text(text,encoding='utf-8');print(OUT/'ERGEBNISSE.md')
