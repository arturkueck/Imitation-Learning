import json
import numpy as np
from transport_data import OUT
data=json.loads((OUT/'data_behavior.json').read_text());pred=json.loads((OUT/'baseline_prediction_analysis.json').read_text());bound=json.loads((OUT/'boundary_visibility.json').read_text());aligned=json.loads((OUT/'aligned_trajectories.json').read_text());check=json.loads((OUT/'verification.json').read_text())
tf=pred['teacher_forcing'];probe=pred['rollout_observation_probe'];goal=pred['goal_shift_probe']
def pct(x):return f'{100*x:.1f}%'
def ratio(v):return pct(v['xy_magnitude_ratio']['q'][2])
table=['| Beobachtungen / Vergleich | XY-Stärke¹ | Falsche Richtung² | Öffnungsbefehle |','|---|---:|---:|---:|']
for label,v in [('Expert-Transport, 20 Trainingsdemos',tf['train_phase4']),('Expert-Transport, 20 Validierungsdemos',tf['valid_phase4']),('Aufgezeichnete Rollout-Zustände',probe['original']),('Dieselben Zustände, nur Transporthöhe',probe['raised_to_expert_height'])]:
    table.append(f"| {label} | {ratio(v)} | {pct(v['wrong_direction_fraction'])} | {pct(v['opening_fraction'])} |")
report=f'''# Warum die State-Policy horizontal nicht zuverlässig zum Ziel fährt

Die Zielposition fehlt nicht. Die Policy erhält sie und reagiert überwiegend in der richtigen Richtung auf ihre Änderung. Der stärkste Befund ist eine **zu schwache gelernte Transportaktion, verstärkt durch eine unzuverlässige, höhenabhängige Lift→Transport-Umschaltung**. Im freien Rollout gerät die Policy in niedrigere und anders gegriffene Zustände als die erfolgreichen Expert-Transporte. Dort produziert sie fast keine zielgerichtete XY-Bewegung und häufiger Öffnungsbefehle. Selbst bei exakten Expert-Eingaben ist ihre XY-Stärke deutlich zu klein; der Fehler ist deshalb nicht ausschließlich ein Folgefehler der vorausgehenden Rollout-Abweichung.

Diese Analyse verändert weder Gewichte noch Daten. Die XY-Korrektur aus der vorherigen Runde bleibt lediglich ein diagnostischer Referenzwert (9/20 Stacks), kein Bestandteil einer neuen Policy. Es wurden genau **zwei Eingabe-Gegenproben** mit unveränderten Gewichten und jeweils drei gepaarten Diffusion-Samples durchgeführt: Zielverschiebung und Höhenverschiebung. Kein neues Trainingsmodell, keine Architektur- oder Hyperparameterkombination.

## 1. Was die Policy tatsächlich sieht

Der eingesetzte Scheduler-korrigierte Epoch-300-Checkpoint ist eine **State-Diffusion-Policy**. Pro Frame erhält sie 15 Zahlen: `robot0_eef_pos` (3), `robot0_eef_quat` (4), `robot0_gripper_qpos` (2), `object` (6 = Weltposition A, Weltposition B). Zwei Frames, t−1 und t, ergeben 30 Eingabewerte und 50 ms beobachtete Bewegung. Eine neue Aktionsequenz wird nach zwei ausgeführten Aktionen, also 100 ms, erzeugt. Vorhersagehorizont: 16 Aktionen.

A ist immer der Ziel-/Basiswürfel, B immer der zu bewegende Würfel. Beide Rollen und die Koordinatenreihenfolge stimmen zwischen Dataset und Umgebung überein. Aktionen sind im Weltkoordinatensystem; die XY-Regel des Experts und die Richtung A−B sind deshalb direkt vergleichbar. Es gibt weder RGB- noch Tiefeninput, keine separate Goal-Observation und keine Beobachtungsnormalisierung. Aktionsnormalisierung ist Identität.

Die Vektoren `A_xy − EEF_xy` und `A_xy − B_xy` sind nicht explizit gespeichert, lassen sich aber eindeutig aus den Eingaben berechnen. Geschwindigkeit ist nicht explizit vorhanden, jedoch näherungsweise aus den zwei Frames ableitbar. Es fehlen als direkte Eingaben: Kontakt-/Grasp-Flag, Expert-Phase, Phasenalter und gespeichertes Zwischenziel. Objektorientierung ist ebenfalls kein State-Eingabefeld; EEF-Orientierung ist vorhanden.

**Kein zeitlicher Interface-Fehler gefunden:** An 30 echten `SequenceDataset`-Fenstern wurde geprüft, dass die ersten zwei Beobachtungen t−1,t sind und die bei Inferenz zuerst ausgeführte Vorhersage (Index 1) zur Expert-Aktion a[t] gehört. Die Teacher-Forced-Auswertung nutzt genau diesen Index und dieselben beiden Frames.

## 2. Expert-Verhalten und systematische Rollout-Abweichung

Die interne Expert-Phase wurde mit den gespeicherten Positionen und dem originalen `StackExpert` rekonstruiert. Auf allen {data['phase_frames'][4]:,} Transportframes passen rekonstruierte und gespeicherte Aktionen: maximaler Fehler etwa {data['transport_label_error']['q'][-1]:.2g}. Die Transportlabels sind also in dieser Phase numerisch konsistent.

Der Expert beendet zunächst einen hohen vertikalen Lift. Am Transportbeginn beträgt das B-Zentrum median {bound['B_z_at_transport_start']['q'][2]:.3f} m (etwa 25 cm über dem 0,8-m-Tisch), die EEF-Höhe {bound['eef_z_at_transport_start']['q'][2]:.3f} m. Die bisherige Anhebemetrik zählt dagegen bereits ab B >0,88 m. **„Angehoben“ war deshalb nicht gleichbedeutend mit „Expert-Lift vollständig beendet“.**

Im Expert-Transport sind XY-Aktionen fast perfekt zum Ziel gerichtet: mittlerer Richtungs-Cosinus {data['expert_transport']['goal_cosine']['mean']:.3f}, keine vom Ziel weg gerichteten Aktionen bei Abstand >20 mm, keine gemessenen >90°-Umkehrungen der Transportgeschwindigkeit. Die mittlere XY-Aktionsnorm ist {data['expert_transport']['action_magnitude']['mean']:.3f}, die mittlere Cube-XY-Geschwindigkeit {data['expert_transport']['velocity_m_s']['mean']:.3f} m/s.

Nach demselben +80-mm-Anhebeereignis sinkt die Expert-Zieldistanz nach zwei Sekunden median auf {pct(aligned['expert_distance_ratio_after_2s'][1])} der anfänglichen Distanz; bei der Policy bleiben {pct(aligned['policy_distance_ratio_after_2s'][1])}. Nach vier Sekunden: Expert {pct(aligned['expert_distance_ratio_after_4s'][1])}, Policy {pct(aligned['policy_distance_ratio_after_4s'][1])}. Diese Kurven vergleichen die 200 Demonstrationen mit 13 angehobenen festen Rollouts; Startverteilungen sind dabei nicht paarweise identisch. Die nachfolgende Teacher-Forced-Prüfung beseitigt diesen Vergleichsunterschied.

Im viersekündigen Fenster nach gehaltenem Anheben tritt Folgendes auf:

- {pct(data['policy_fraction_below_expert_transport_min_z'])} der noch gegriffenen Policy-Zustände liegen unter der niedrigsten B-Höhe, die in einer Expert-Transportphase vorkommt. Das heißt außerhalb der **Transportphase**, nicht außerhalb des gesamten Datensatzes: niedrige Lift-/Close-Zustände gibt es dort durchaus.
- Der EEF–B-Abstand beträgt median {1000*data['policy_EEF_cube_offset_m']['q'][2]:.1f} mm statt {1000*data['expert_EEF_cube_offset_m']['q'][2]:.1f} mm beim Expert. Auch die Griffgeometrie ist verschoben.
- Über die 13 Episoden beträgt die mittlere XY-Aktionsnorm im Mittel rund 0,068 statt 0,838 im Expert-Transport. Rund 77% der Aktionen bleiben unter 0,05; etwa 46% der nichttrivialen Aktionen zeigen vom Ziel weg (Mittel über Episoden).
- Zwischen 333 aufeinanderfolgenden auswertbaren Neuplanungen gibt es 88 XY-Aktionsumkehrungen >90° (26,4%). Der Expert hält seine Transportrichtung kohärent.

Die Policy weicht also schon vor bzw. beim erwarteten Beginn der horizontalen Fahrt ab. Sie verharrt häufig in einer vertikalen/greifnahen Verhaltensweise, senkt wieder ab oder öffnet, statt den großen XY-Zielvektor in eine anhaltende horizontale Fahrt umzusetzen.

## 3. Vorhersagen auf echten Expert-Beobachtungen

Teacher Forcing bedeutet hier: der unveränderten Policy die echten zwei gespeicherten Expert-Frames geben, ohne vorherigen Policy-Rollout. Es werden 20 Trainingsdemos und alle 20 Validierungsdemos, jede zweite Frameposition der Close-/Lift-/Transport-/Lower-Phasen und drei Diffusion-Samples ausgewertet. Die Transportphase enthält dabei 220 eindeutige Trainings- und 205 Validierungsfenster.

'''+ '\n'.join(table)+f'''

¹ Median der Aktionsnorm relativ zur Expert-/zielgerichteten Referenzaktion, nur bei Expert-Aktionsnorm >0,1 und Zielabstand >20 mm. ² XY-Skalarprodukt zur Referenzaktion <0. Nahezu-null Aktionen werden über die separate Stärke-/Stall-Metrik sichtbar. Öffnungsanteil über alle jeweils ausgewerteten Frames.

Auf Expert-Transportzuständen liegt der XY-RMSE bei {tf['train_phase4']['xy_rmse']:.3f} auf Training und {tf['valid_phase4']['xy_rmse']:.3f} auf Validierung. Schon im ersten Viertel des Expert-Transports erreicht die Validierungs-Policy nur {ratio(tf['valid_transport_0_0.25'])} der Expert-Stärke. Das Defizit entsteht somit nicht erst durch schlechte eigene Rollout-Zustände und ist kein reiner Train-/Validierungs-Generalisationseffekt.

Gleichzeitig sagt sie auf echten Expert-Transportzuständen fast immer „geschlossen“ voraus ({100*(1-tf['valid_phase4']['opening_fraction']):.1f}%). Die vielen verfrühten Öffnungen im freien Rollout sind daher stärker an die abweichenden Rollout-Zustände gekoppelt als an inkonsistente Transport-Gripperlabels.

Diese Aktionsabweichung bezeichnet das Verhalten des **deployed EMA-Modells samt unverändertem 10-Schritt-DDIM-Sampling**. Ein Entrauschungsverlust von etwa 0,013 ist kein unmittelbarer Nachweis guter Aktionsrekonstruktion. Gewichtsunteranpassung, Loss-Gewichtung und Samplingbeitrag wurden in dieser Runde nicht voneinander isoliert; insbesondere wurde kein anderer DDIM-Horizont als dritter Test ausprobiert.

## 4. Die verdeckte Phase und die beiden Isolationsexperimente

Die verdeckte Phase ist keine unsichtbare Zielposition. Gemeint sind der Expert-interne Automat mit festen Zwischenzielen und Verweilzeiten. Am Übergang Lift→Transport ändern sich Positions-/Fingermerkmale median nur um {1000*bound['feature_distance_m']['q'][2]:.2f} mm gemeinsamer euklidischer Distanz; die XY-Aktion springt gleichzeitig median um {bound['xy_action_jump']['q'][2]:.2f} in Aktionsnorm. Erst vorher fast vertikal, dann energisch zum anderen Würfel. Die Policy muss diesen scharfen Wechsel aus kurzem Kontext und der erreichten Geometrie erschließen. Ähnliche Beobachtungen sind **kein Beweis identischer vollständiger Inputs oder prinzipieller Unbeobachtbarkeit**; Höhe, Bewegung und Finger liefern durchaus Signale.

**Experiment 1 – Zielinformation:** Auf {goal['n_observations']} frühen Validierungs-Transportbeobachtungen wird nur A_x um ±4 cm verschoben. Alle anderen Eingaben bleiben gleich; beide verschobenen A-Positionen bleiben innerhalb der empirischen Start-X-Grenzen des Datensatzes. Je Paar wird derselbe Diffusionsnoise verwendet, dreimal wiederholt. Bei {pct(goal['correct_response_fraction'])} der {goal['x_response']['n']} Paare verschiebt sich die vorhergesagte X-Aktion in die richtige Richtung. Der mediane Unterschied ist {goal['x_response']['q'][2]:.3f}. Das Ziel wird also aus dem absoluten Positionsinput verwendet; „Ziel fehlt/ist unsichtbar“ ist keine tragfähige Hauptursache.

**Experiment 2 – Phasen-/Höhenabhängigkeit:** 107 rekonstruierte Beobachtungspaare aus den ersten vier Sekunden nach gehaltenem Anheben in den aufgezeichneten Policy-Rollouts; B und EEF werden in beiden Frames gemeinsam vertikal auf die Expert-Transporthöhe B=1,05 m verschoben. Relative Griffposition und Zwei-Frame-Geschwindigkeit bleiben erhalten; XY-Zielvektor, Finger und Orientierung bleiben gleich. Drei gepaarte Diffusion-Samples: Medianstärke {ratio(probe['original'])}→{ratio(probe['raised_to_expert_height'])}, falsche Richtungen {pct(probe['original']['wrong_direction_fraction'])}→{pct(probe['raised_to_expert_height']['wrong_direction_fraction'])}, Öffnungsbefehle {pct(probe['original']['opening_fraction'])}→{pct(probe['raised_to_expert_height']['opening_fraction'])}.

Das stützt eine stark höhenabhängige Wahl des Verhaltensmodus. Der verbleibende Stärkeverlust auf Expert-Höhe zeigt aber, dass die fehlende Endhöhe nicht die ganze Erklärung ist. Das sind **Vorhersage-Gegenproben, keine physikalischen Rollouts und keine neuen Stack-Erfolgsraten**. Objektpositionen und die nicht mitgespeicherte EEF-Quaternion wurden aus dem Simulationszustand rekonstruiert; EEF-Position und Finger stammen aus dem tatsächlichen Trace. Rekonstruierte Objektpositionen wurden gegen den Trace mit <1 mm Toleranz geprüft. Die Expert-Teacher-Forcing-Eingaben stammen dagegen vollständig aus den Originalbeobachtungen.

## 5. Datensatzverteilung und Bilder

200 erfolgreiche Demos, 180 Training/20 Validierung, insgesamt {sum(data['phase_frames']):,} Frames. Die Startkoordinaten beider Würfel liegen je X/Y ungefähr zwischen −13,2 und +13,2 cm; Z ist initial 0,83 m. Initiale Transportdistanz: {100*data['distances_m']['q'][0]:.1f}–{100*data['distances_m']['q'][-1]:.1f} cm, Median {100*data['distances_m']['q'][2]:.1f} cm. 46 Demos unter 10 cm, 107 zwischen 10 und 20 cm, 47 zwischen 20 und 30 cm. Keine Demo über 30 cm.

In acht 45°-Richtungssektoren, beginnend bei −180°: 33, 24, 22, 20, 24, 22, 25, 30 Demos; im Training jeweils 18–31. Es fehlt keine ganze Richtung. Sehr lange Transporte am oberen Rand sind naturgemäß dünner besetzt; die verbreiteten Fehler treten aber auch bei mittleren Distanzen auf.

Reine Transportphase: {data['phase_frames'][4]:,} Frames (3.693 Training), {pct(data['transport_fraction'])} der gesamten Frame-/Fensterstartverteilung. Pro Demo 14–55 Frames, Median 19, also median 0,95 s. Von +80-mm-Anheben bis zur 9-mm-Zielnähe: median 38 Frames =1,9 s, Bereich 30–75 Frames. Wegen überlappender 16-Aktions-Chunks ist 13,5% **nicht** der exakte Transportanteil am Diffusionsloss.

Für Vision sind die Daten gesondert problematisch: {bound['visibility']['all_black_frames']:,} von 4.092 Transportbildern sind vollständig schwarz, verteilt auf {bound['visibility']['all_black_demo_count']} Demos. Das ist fehlende Bildinformation, keine Objektverdeckung. In den übrigen Transportframes liefern beide Würfel mindestens drei farbspezifische Pixel; die Montage wurde visuell geprüft. Ein Farb-Pixel-Test beweist keine genaue Lokalisierung und schließt partielle Verdeckung nicht aus. Für den aktuellen State-Checkpoint hat dieser Bildfehler jedoch keinen Einfluss. Ein Image-only-Vergleich wäre vor Reparatur/Prüfung dieser Daten nicht sauber interpretierbar.

## 6. Wahrscheinlichste Ursache und nächste Trainingsänderung

Am besten gestützt ist folgende Kette: Die Demonstrationen enthalten einen kurzen, abrupt einsetzenden Transportmodus nach einem vollständigen hohen Lift. Das Modell rekonstruiert diesen Modus bereits auf Expert-Inputs zu schwach. Kleine Abweichungen in Lift-Endhöhe und Griffzentrierung bringen den freien Rollout dann in Zustände, in denen es wieder vertikale, absenkende oder öffnende Aktionen auswählt. Die fehlende zielgerichtete Bewegung verhindert ihrerseits, dass die Policy in die gut demonstrierten Transport-/Placement-Zustände gelangt. Das erklärt den großen zusätzlichen Verlust vom Teacher-Forced-Transport (~27% Stärke) zum freien Rollout (~3%).

Die **praktische Beobachtbarkeit des Ziels** ist nachgewiesen; eine ausschließlich fehlende XY-Information, reine Bildverdeckung oder eine fehlende Transportrichtung im Datensatz erklären den State-Befund nicht. Die kurze Historie und verborgene Phase sind plausible Verstärker, nicht allein nachgewiesene Ursachen. Datenanteil und großer Aktionssprung machen eine unzureichende Gewichtung des Lift→Transport-Übergangs plausibel, aber noch nicht kausal bewiesen.

**Sinnvollste nächste isolierte Trainingsänderung:** phasenbalanciertes Sampling von Sequenzfenstern um das Ende des Lifts und den Anfang des Transports. Diese Fenster häufiger ziehen, andere Phasen weiterhin erhalten; Beobachtungen, Architektur, Loss, Vorhersagehorizont und Aktionshorizont unverändert lassen. Gleiche Anzahl Updates gegen eine uniform gesampelte Kontrollfortsetzung vergleichen. Zuerst die Teacher-Forced-XY-Stärke im frühen Transport sowie das Erreichen der Expert-Lift-Endhöhe prüfen, danach dieselben 20 Startzustände wie bisher. Das testet gezielt den schwach gelernten Umschalt-/Transportmodus und benötigt keine dauerhafte XY-Heuristik.

Relative Zielvektoren wären eine sinnvolle spätere Repräsentations-Gegenprobe, liefern aber keine neue Information und lösen allein nicht die Wahl zwischen „weiter anheben“ und „horizontal fahren“. Deshalb sind sie hier nicht die erste Empfehlung. Rückzug und Recovery-Abdeckung bleiben getrennte Baustellen; die erfolgreichen Demos decken die beobachteten Fehlzustände nur schwach ab.

## Gespeicherte Evidenz

`data_behavior.json`: Positionen, Richtungen, Transportzeiten, XY-Aktionen/-Geschwindigkeiten und Neuplanungsumkehrungen je Demo/Start. `boundary_visibility.json`: Übergangsgrößen und schwarze Bildframes. `baseline_teacher_predictions.npz` und `baseline_teacher_samples.json`: Expert-Inputs und Policy-Predictions. `rollout_observation_probes.npz` und `rollout_probe_samples.json`: beide Höhenbedingungen samt ursprünglichen Beobachtungen und Samples. `baseline_prediction_analysis.json`: alle Vorhersagemetriken. `verification.json`: echte Dataset-Fensterprüfung, Eingabeformen, unveränderte Checkpoint-/Dataset-Hashes und Gegenprobenscope.

Grafiken: `lift_to_transport_comparison.png`, `relative_xy_paths.png`, `transport_distribution.png`, `action_prediction_comparison.png`, `demo_transport_visibility.png`. Die relativen Pfade zeigen für drei feste Starts die jeweils nächstliegende Demonstration nach initialem XY-Zielvektor; die Zuordnung steht in `relative_path_matches.json`. Skripte liegen getrennt von Training/Produktcode unter `experiments/stack_followup_20261001/scripts/`: `analyze_transport.py`, `probe_transport.py`, `analyze_transport_boundary.py`, `plot_transport.py`, `verify_transport.py`, `report_transport.py`; gemeinsamer Zugriff in `transport_data.py`. Ausführen mit der vorhandenen `praxis/.venv/Scripts/python.exe`.
'''
(OUT/'DIAGNOSE.md').write_text(report,encoding='utf-8')
(OUT/'status.json').write_text(json.dumps(dict(state='COMPLETED',counterfactual_experiments=2,training_changes=0,xy_correction_used=False),indent=2))
print(str(OUT/'DIAGNOSE.md'))
