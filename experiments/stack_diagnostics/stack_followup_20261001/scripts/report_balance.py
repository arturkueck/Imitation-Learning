"""Assemble complete reproducible matched comparison from saved results."""
import json
from balance_common import EXP,ROOT
p=json.loads((EXP/'protocol.json').read_text());verify=json.loads((EXP/'verification.json').read_text());roll=json.loads((EXP/'rollout_summary.json').read_text());extra=json.loads((EXP/'offline_extra.json').read_text())
vs=['source','uniform','balanced'];labels={'source':'Ausgangsmodell','uniform':'Uniform +5.000','balanced':'Balanciert +5.000'}
offline={v:json.loads((EXP/v/'offline_results.json').read_text()) for v in vs}
expert_roll=json.loads((EXP/'expert_lift_summary.json').read_text())
lines=['# Kontrollierter Vergleich: Gewichtung Lift-Ende → Transportbeginn','',
'## Antwort und nächste Konsequenz','',
'**Phasenimbalance ist eine belegte Mitursache der zu schwachen Transportaktionen. Sie erklärt den fehlerhaften Lift→Transport-Wechsel und das Scheitern der Gesamtaufgabe nicht ausreichend.** Größere Samplingmasse verstärkt XY-Aktionen auf allen Trainings- und Validierungsdemos. Der Effekt ist auch in echten Policy-Fortsetzungen ab identischen Expert-Lift-Enden vorhanden: 3-cm-Zielbereich 11→19/20, Positionierung 3→7/20, XY-Restabstand nach 2 s 4,91→2,95 cm. Es handelt sich also nicht nur um einen Teacher-Forcing-Gewinn.','',
'Die 50%-Balancierung verschiebt jedoch eine bereits vorgezogene, geglättete Umschaltreaktion weiter nach vorne: auf Validierung steigt der Anteil deutlich zu früher Transportbefehle von 45 % auf 80 %. Vor dem Wechsel wird mehr XY-Bewegung und stärker negative Z-Bewegung vorhergesagt, obwohl der Expert noch anhebt. Die Gesamt-Liftrate sinkt gegenüber der uniformen Fortsetzung von 10/20 auf 2/20; beide Varianten erreichen keinen vollständigen Stack aus den festen ursprünglichen Startzuständen. Aus Expert-Lift-Enden schafft balanciert mehr laterale Positionierungen, aber 0/20 korrektes Absenken oder Release.','',
'**Wahrscheinlichste Interpretation:** Geringe Gewichtung schwächt die gewünschte Transportkomponente; zugleich bildet die Policy die scharfe Zustands-/Aktions-Umschaltung unzureichend ab. Mehr Gewicht verstärkt die Komponente über beide Seiten der Grenze, statt die Phase zuverlässig zu unterscheiden. Diese Interpretation ist durch Aktionsverläufe gestützt. Ob die Ursache in lokaler Mehrdeutigkeit der kurzen State-History, im trainierten Diffusionsfeld oder in der DDIM-Rekonstruktion liegt, ist mit diesem Vergleich nicht entschieden.','',
'**Nächster sinnvoller Schritt:** zuerst die Umschalt-/Modenzuordnung und Diffusion/DDIM getrennt diagnostizieren, bevor weitere Samplingstärken oder eine endgültige Trainingsänderung gewählt werden. Die hier getestete 50%-Balancierung eignet sich wegen der Lift-Regression nicht als Ersatzpolicy. Ein zukünftiger Trainingsansatz müsste den Übergang präziser abbilden und die übrigen Phasen nachweislich erhalten; stärkeres Oversampling ist aus diesem Befund keine begründete nächste Maßnahme. In dieser Runde wurden keine zusätzlichen Methoden trainiert und keine XY-Heuristik eingesetzt.','',
'## Fragestellung und Isolation','',
'Zwei Fortsetzungen desselben korrigierten Scheduler-Checkpoints, jeweils genau 5.000 Gradient-Updates, Batchgröße 8, Seed 1. Architektur, State-Observations, Diffusion-Training, DDIM (10 Schritte), Beobachtungshistorie (2 Frames), Vorhersagehorizont (16), AdamW und EMA bleiben zwischen den Armen identisch. Inferenz führt wie bisher 2 Aktionen aus. Keine XY-Heuristik; ausschließlich Samplinggewichte unterscheiden die Trainingsarme. Nur der letzte Checkpoint wird evaluiert, keine Auswahl anhand der Ergebnisse.','',
'Der Ausgangscheckpoint beendet den bisherigen Cosine-Zyklus bei Lernrate 0. Deshalb erhalten beide Arme identisch einen neuen 5.000-Update-Cosine-Zyklus mit Ausgangs-LR 1e-4 und 500 Warmup-Schritten. AdamW-Momente und rohe/EMA-Gewichte werden restauriert. Der im Checkpoint nicht gespeicherte EMA-Schritt wird in beiden Armen auf den aus AdamW abgeleiteten Schritt 30.000 gesetzt; beide enden bei 35.000. Damit testet der Unterschied balanciert minus uniform den Samplingeffekt, nicht zusätzliche Trainingszeit.','',
'[Vorab gespeichertes Protokoll](protocol.json), [Isolation und Dataset-Abgleich](verification.json). Identische LR-Arrays und Checkpoint-Konfigurationen; 60 History-/Action-Fenster mit dem ursprünglichen SequenceDataset abgeglichen. Beide Anfangsgewichte sind exakt gleich dem Ausgangscheckpoint.','',
'## Automatische Übergangsdefinition','',
'Der erste Frame k erfüllt: B-Höhe >0,98 m; geschlossener Gripper-Befehl; XY-Aktionsnorm >0,25; Cosinus zwischen XY-Aktion und EEF→A-Zielvektor >0,85; EEF–B-Abstand <12 mm; vorherige drei XY-Normen <0,12 und die drei ab k >0,25. Das Kriterium findet genau einen Umschaltpunkt je Demo und stimmt in allen 200 Demos mit dem rekonstruierten Expert-Transportbeginn überein. Keine manuellen Phasenlabels bestimmen das Sampling.','',
'Die inklusiven Ankerfenster [k−6,k+8] enthalten 15 Frames (−0,30 bis +0,40 s). Auf 180 Trainingsdemos: 2.700/27.322 Ankerframes = 9,88 %. Balanciert bekommen diese Frames zusammen 50 % Samplingmasse, die übrigen 24.622 Frames 50 %. Ein Übergangsframe erhält somit 9,12-mal das Gewicht eines anderen Frames. Alle übrigen Phasen bleiben enthalten; 20 Validierungsdemos werden nicht gesampelt.','',
'Jeder Trainingsanker enthält History t−1,t und 16 überwachte Aktionen t−1…t+14. Die Prozentzahlen beziehen sich auf Ankerframes, nicht auf exklusive Verlustmasse einer Phase.','',
'| Tatsächliche Stichproben | Uniform | Balanciert |','|---|---:|---:|']
audits={v:json.loads((EXP/v/'training_audit.json').read_text()) for v in vs[1:]}
lines += [f"| Übergangsanker von 40.000 | {audits['uniform']['critical_samples']} ({audits['uniform']['effective_critical_mass']:.2%}) | {audits['balanced']['critical_samples']} ({audits['balanced']['effective_critical_mass']:.2%}) |",'| Phase | Uniform | Balanciert |','|---|---:|---:|']
names=['Annähern','Absenken zum Greifen','Greifen','Lift','Transport','Absenken zum Platzieren','Release']
for i,name in enumerate(names):lines.append(f"| {i}: {name} | {verify['actual_phase_sample_counts']['uniform'][str(i)]} | {verify['actual_phase_sample_counts']['balanced'][str(i)]} |")
lines += ['', '## Offline: Expert-Zustände', '',
'Alle 180 Train-/20 Validierungsdemos, sämtliche Transportframes (3.693/399), drei gemeinsame Diffusions-Zufallsziehungen. Teacher Forcing verwendet echte histories; beide ausgeführten Aktionen je Replanning werden ausgewertet. Verhältnis = mediane Policy-/Expert-XY-Norm bei Expert-Norm >0,1. Falsche Richtung = Cosinus <0. Diese Auswertung ersetzt keine Rollouts.','',
'| Split / Modell | XY-Verhältnis | Richtungscosinus, Median | Falsche Richtung | Transport-Öffnen | Lift-Öffnen | Lift Z-MAE |','|---|---:|---:|---:|---:|---:|---:|']
for s in ('train','valid'):
    for v in vs:
        t=offline[v]['scores'][s+'_phase4'];l=offline[v]['scores'][s+'_phase3'];lines.append(f"| {s} / {labels[v]} | {t['xy_ratio']['q'][2]:.1%} | {t['direction_cosine']['q'][2]:.3f} | {t['wrong_direction']:.1%} | {t['opening']:.1%} | {l['opening']:.1%} | {l['z_mae']:.3f} |")
lines += ['', '### Unmittelbarer Umschaltbereich', '',
'Früher Transport = k…k+8. Vorbereich = k−6…k−1. Signifikanter Beginn erfordert drei aufeinanderfolgende Aktionen mit XY-Norm >0,25 und Zielcosinus >0,5 im Fenster k−10…k+30. Ein Beginn bei −10 ist links zensiert; er kann noch früher liegen. Timingwerte behandeln diesen Fall als mindestens 0,5 s zu früh.','',
'| Split / Modell | XY-Verhältnis früh | XY-Norm vor Wechsel | Z-Aktion vor Wechsel | Beginn ±0,1 s | Zu früh >0,1 s | Kein Beginn im Fenster | XY-Richtungswechsel im gesamten Transport |','|---|---:|---:|---:|---:|---:|---:|---:|']
for s in ('train','valid'):
    for v in vs:
        x=extra[v][s];b=offline[v]['boundary'][s];lines.append(f"| {s} / {labels[v]} | {x['early_transport']['ratio']['q'][2]:.1%} | {x['pre_transition']['policy_xy']['mean']:.3f} | {x['pre_transition']['z_mean']:+.3f} | {x['onset']['within_2_steps_fraction']:.1%} | {x['onset']['premature_fraction']:.1%} | {1-b['onset_found_fraction']:.1%} | {b['full_transport_reversal_fraction']:.1%} |")
lines += ['', 'Das Expert-XY-Kommando springt am Wechsel von nahezu null auf etwa 1,17. Die Modelle bilden diesen Sprung als breite, vorgezogene Bewegung ab. Balancierung erhöht sowohl die gewünschte Bewegung danach als auch die unerwünschte Bewegung davor. Das Verhalten ist auf Train und Validierung ähnlich. Die Z-Aktion vor dem Wechsel sollte positiv sein; in der Policy liegt der Mittelwert bereits im negativen Bereich.','',
'Der gepaarte Vergleich zeigt größere mittlere frühe XY-Aktionen bei allen 180 Trainings- und allen 20 Validierungsdemos. Auf Validierung steigt die frühe XY-Norm im Mittel um 0,123. Vor dem Wechsel: Expert-XY-Norm 0,020, uniforme Policy 0,422, balancierte Policy 0,575; Expert-Z-Aktion +0,116, uniform −0,084, balanciert −0,167. Der Gewinn an Aktionsstärke generalisiert, die korrekte Umschaltgrenze wird dadurch aber nicht gelernt.','',
'![Aktionsverläufe um den Expert-Wechsel](boundary_profiles.png)','',
'## Rollouts: 20 feste Startzustände','',
'Seeds 46000–46019; alle initialen Simulatorzustands-Hashes stimmen mit dem bisherigen Vergleich überein. 500 Schritte Hauptauswertung; anschließend 40 Schritte Policy-Fortsetzung. Stabiler Stack = bisheriges Environment-Kriterium (0,5 s gültiger Stack); zusätzlich wird Fortbestand in der 2-s-Fortsetzung gemessen.','',
'Lift entspricht dem bisherigen Kriterium B>0,88 m. Vollständiges Lift-Ende wird getrennt als gehaltenes B≥1,045 m und EEF≥1,049 m während drei Frames definiert. Transportbeginn: gehalten, B>0,98 m, XY-Geschwindigkeit >2 cm/s und Zielcosinus >0,5 während drei Frames. Das ist Beginn zielgerichteter Bewegung, keine Garantie anhaltender Annäherung. Positioniert: XY<9 mm und Höhendifferenz >32 mm; abgesenkt zusätzlich 40±8 mm; Release zusätzlich Würfelkontakt und kein B-Grasp.','',
'| Stufe | Ausgangsmodell | Uniform +5.000 | Balanciert +5.000 |','|---|---:|---:|---:|']
for k,label in [('grasp','Greifen'),('lift','Anheben (bisheriges Kriterium)'),('transport_started','Transportbeginn'),('near','3-cm-Zielbereich'),('position','Positioniert'),('lower','Abgesenkt'),('release','Release'),('stack','Stabiler Stack')]:lines.append('| '+label+' | '+' | '.join(f"{roll[v]['counts'][k]}/20 ({roll[v]['counts'][k]*5} %)" for v in vs)+' |')
lines += ['| Vollständiges Lift-Ende | '+' | '.join(f"{roll[v]['full_lift_count']}/20" for v in vs)+' |','| Stack über weitere 2 s erhalten | '+' | '.join(f"{roll[v]['sustained_stack']}/20" for v in vs)+' |','',
'Die Ausgangsspalte ist aus den bereits gespeicherten instrumentierten Rollouts des unveränderten Bestmodells berechnet (17 Grasp, 13 Lift); der historische Evaluationslauf hatte 14 Lift. Diese kleine Wiederholungsabweichung ist dokumentiert; uniforme und balancierte Fortsetzung werden hier direkt und mit gleichem Ablauf verglichen. Der diagnostische XY-Regler mit 45 % Stack-Erfolg wird in keinem neuen Lauf eingesetzt.','',
'Zusätzlicher Blick auf die frühe Lift-Steuerung im Rollout: innerhalb der ersten 40 Schritte ab erstem Grasp, solange B≤0,88 m und weiter gehalten wird, erzeugt uniform in 16,0 % der ausgewerteten Schritte Z>0,1, balanciert nur in 11,0 %. Öffnungsbefehle treten in 19,0 % bzw. 26,7 % dieser Schritte auf (343/273 Schritte; unterschiedliche erreichte Zustände, deshalb beschreibend und kein kontrollierter Teacher-Forcing-Vergleich).','',
'![Erfolgsstufen](rollout_stages.png)','',
'### Distanz nach vollständigem Lift-Ende','',
'Mittelwert mit Anzahl verfügbarer Fälle; fehlende volle Lifts werden nicht als Nullabstand behandelt. Werte sind auf das erste vollständige Lift-Ende bezogen, nicht auf das frühere 8-cm-Anhebekriterium. Unterschiedliche Erfolgsselektion kann die bedingten Mittelwerte verzerren.','',
'| Zeit | Ausgangsmodell | Uniform | Balanciert |','|---|---:|---:|---:|']
for s in ('0.5','1.0','2.0'):
    cells=[]
    for v in vs:
        d=roll[v]['distance'][s];cells.append(f"{d['mean']*100:.2f} cm (n={d['n']})" if d['n'] else '— (n=0)')
    lines.append('| '+s+' s | '+' | '.join(cells)+' |')
lines += ['',f"Gemeinsame vollständige Lifts beider Fortsetzungen: {roll['matched_full_lift_seeds']}.",'',
'| Zeit / gemeinsame Fälle | Uniform | Balanciert |','|---|---:|---:|']
for s in ('0.5','1.0','2.0'):
    cells=[]
    for v in ('uniform','balanced'):
        d=roll['matched_distance'][v][s];cells.append(f"{d['mean']*100:.2f} cm (n={d['n']})" if d['n'] else '— (n=0)')
    lines.append('| '+s+' s | '+' | '.join(cells)+' |')
lines += ['', '| XY-Aktionswechsel während Transport | Ausgangsmodell | Uniform | Balanciert |','|---|---:|---:|---:|','| Richtungswechsel / benachbarte aktive Replans | '+' | '.join(f"{roll[v]['reversal_fraction']:.1%}" for v in vs)+' |','| Anzahl je geliftetem Rollout, Median | '+' | '.join(f"{roll[v]['reversals']['q'][2]:.0f}" if roll[v]['reversals']['n'] else '—' for v in vs)+' |','',
'Transportbeginn relativ zum vollständigen Lift-Ende (negative Werte = Bewegung bereits davor): '+ '; '.join(labels[v]+': '+(f"{roll[v]['transport_delay_seconds']['mean']:+.2f} s (n={roll[v]['transport_delay_seconds']['n']})" if roll[v]['transport_delay_seconds']['n'] else 'kein auswertbarer Fall') for v in vs)+'.','',
'Gezählt werden aufeinanderfolgende aktive Replanning-Kommandos (alle zwei Schritte), gehaltenes B und Zielabstand >2 cm, XY-Norm >0,01; Richtungswechsel = negativer Dot-Product. Beginn ab vollem Lift, falls erreicht, sonst ab erstem bisherigen Lift. Offline verwendet einzelne ausgeführte Aktionen; die Nenner sind daher unterschiedlich.','',
'![Repräsentative gespeicherte Zustandsverläufe](representative_rollouts.png)','',
'## Dateien und Reproduzierbarkeit','',
'Finale Checkpoints: `uniform/model_final.pth`, `balanced/model_final.pth`. Trainingslogs, tatsächliche Samplinghäufigkeiten und LR-Arrays liegen in den jeweiligen Unterordnern. `offline_predictions.npz` enthält dreifache Predictions, Expert-Aktionen und exakte Beobachtungshistorien; `offline_samples.json` ordnet sie Demos und Umschaltpunkten zu. `rollouts/<seed>.npz` speichert alle tatsächlichen Beobachtungen, Simulatorzustände und Zustands-/Aktionsverläufe einschließlich Fortsetzung; `results.json` enthält alle Ereigniszeiten.','',
'Repräsentative Videos: `uniform/rollouts/46004.mp4` (voller Lift, danach kein Stack), `balanced/rollouts/46002.mp4` (Lift scheitert), `uniform/expert_lift_rollouts/demo_47.mp4` und `balanced/expert_lift_rollouts/demo_47.mp4` (derselbe Expert-Lift-Start; balanciert positioniert, uniform erreicht den 3-cm-Bereich nicht). `uniform/expert_lift_rollouts/demo_22.mp4` zeigt den einzigen temporären Stack der Zusatzdiagnose; er hält die folgende 2-s-Policy-Fortsetzung nicht durch. Alle Videos sind aus gespeicherten Simulatorzuständen gerendert.','',
'62 Demonstrationen mit schwarzen Transportbildern (1.266/4.092 Transportframes) bleiben separat dokumentiert und unverändert. Dieser Versuch liest ausschließlich 15 State-Merkmale pro Frame und keine RGB-Observation; schwarze Bilder bestimmen weder Sampling noch Ausschluss. Der vollständige HDF5-Hash bestätigt unveränderte Daten.','',
f"Ausgangscheckpoint SHA256: `{p['source_sha256']}`. HDF5 SHA256: `{p['dataset_sha256']}`.",'',
'Ein Trainingsseed, 20 feste Rollouts und drei Offline-Diffusionsziehungen: ein kontrollierter Richtungsvergleich, keine präzise Schätzung einer allgemeinen Erfolgswahrscheinlichkeit. Es wurden keine weiteren Methoden oder Hyperparameterkombinationen getestet.']
section=['## Zusatzdiagnose: identische Expert-Lift-Enden als Startzustände','',
'Diese zusätzliche Auswertung wurde nach den frühen vollständigen Rollouts ergänzt, weil die balancierte Policy häufig keinen Lift erreichte. Sie ist eine Evaluation derselben drei eingefrorenen Modelle, kein dritter Trainingsarm und keine neue Methode. Alle 20 Validierungsdemos werden ab ihrem automatisch erkannten Expert-Transportbeginn fortgesetzt: identische gespeicherte Simulatorzustände, bereits gegriffener/angehobener Würfel und genaue Expert-History k−1,k für den ersten Policy-Aufruf. Anschließend kommen alle Beobachtungen und Bewegungen aus der unveränderten Policy/Simulation. Haupt-Horizont 120 Schritte (6 s), Fortsetzung 40 Schritte.','',
'Alle Startzustands-Hashes stimmen zwischen den Modellen überein; alle 20 initialen Grasps sind vorhanden. Wiederhergestellte Würfelpositionen stimmen auf <1 mm mit der Demo überein. Controller-interne Erinnerung wird beim Restore in allen Varianten gleich neu initialisiert; deshalb sind diese Starts eine kontrollierte Zustandsfortsetzung, kein exakt unterbrechungsfreier Expert→Policy-Wechsel. Die Zahlen werden getrennt vom bisherigen vollständigen Startvergleich berichtet. [Zusatzprotokoll](expert_lift_protocol.json).','',
'| Ergebnis ab Expert-Lift-Ende | Ausgangsmodell | Uniform | Balanciert |','|---|---:|---:|---:|']
for k,label in [('transport_started','Transportbeginn'),('near','3-cm-Zielbereich'),('position','Positioniert'),('lower','Abgesenkt'),('release','Release'),('stack','Stabiler Stack')]:section.append('| '+label+' | '+' | '.join(f"{expert_roll[v]['counts'][k]}/20" for v in vs)+' |')
section += ['| Stack über weitere 2 s erhalten | '+' | '.join(f"{expert_roll[v]['sustained_stack']}/20" for v in vs)+' |','',
'Die folgenden Abstände sind ab dem vorgegebenen Expert-Lift-Ende gemessen; alle Varianten haben denselben Nenner n=20.','',
'| Zeitpunkt | Ausgangsmodell | Uniform | Balanciert |','|---|---:|---:|---:|']
for s in ('0.5','1.0','2.0'):section.append('| '+s+' s | '+' | '.join(f"{expert_roll[v]['distance'][s]['mean']*100:.2f} cm" for v in vs)+' |')
section += ['| XY-Richtungswechsel / aktive Replan-Paare | '+' | '.join(f"{expert_roll[v]['reversal_fraction']:.1%}" for v in vs)+' |','',
'![Vergleich ab vorgegebenem Expert-Lift-Ende](expert_lift_comparison.png)','']
idx=lines.index('## Dateien und Reproduzierbarkeit');lines[idx:idx]=section
# Absolute local artifact links also render when opened outside this folder.
import re
lines=[re.sub(r'\]\(([^()]+)\)',lambda m:'](<'+str(EXP/m.group(1)).replace('\\','/')+'>)' if not m.group(1).startswith(('http','/')) else m.group(0),line) for line in lines]
(EXP/'ERGEBNISSE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(EXP/'ERGEBNISSE.md')
