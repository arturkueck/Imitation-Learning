# Kontrollierter Vergleich: Gewichtung Lift-Ende → Transportbeginn

## Antwort und nächste Konsequenz

**Phasenimbalance ist eine belegte Mitursache der zu schwachen Transportaktionen. Sie erklärt den fehlerhaften Lift→Transport-Wechsel und das Scheitern der Gesamtaufgabe nicht ausreichend.** Größere Samplingmasse verstärkt XY-Aktionen auf allen Trainings- und Validierungsdemos. Der Effekt ist auch in echten Policy-Fortsetzungen ab identischen Expert-Lift-Enden vorhanden: 3-cm-Zielbereich 11→19/20, Positionierung 3→7/20, XY-Restabstand nach 2 s 4,91→2,95 cm. Es handelt sich also nicht nur um einen Teacher-Forcing-Gewinn.

Die 50%-Balancierung verschiebt jedoch eine bereits vorgezogene, geglättete Umschaltreaktion weiter nach vorne: auf Validierung steigt der Anteil deutlich zu früher Transportbefehle von 45 % auf 80 %. Vor dem Wechsel wird mehr XY-Bewegung und stärker negative Z-Bewegung vorhergesagt, obwohl der Expert noch anhebt. Die Gesamt-Liftrate sinkt gegenüber der uniformen Fortsetzung von 10/20 auf 2/20; beide Varianten erreichen keinen vollständigen Stack aus den festen ursprünglichen Startzuständen. Aus Expert-Lift-Enden schafft balanciert mehr laterale Positionierungen, aber 0/20 korrektes Absenken oder Release.

**Wahrscheinlichste Interpretation:** Geringe Gewichtung schwächt die gewünschte Transportkomponente; zugleich bildet die Policy die scharfe Zustands-/Aktions-Umschaltung unzureichend ab. Mehr Gewicht verstärkt die Komponente über beide Seiten der Grenze, statt die Phase zuverlässig zu unterscheiden. Diese Interpretation ist durch Aktionsverläufe gestützt. Ob die Ursache in lokaler Mehrdeutigkeit der kurzen State-History, im trainierten Diffusionsfeld oder in der DDIM-Rekonstruktion liegt, ist mit diesem Vergleich nicht entschieden.

**Nächster sinnvoller Schritt:** zuerst die Umschalt-/Modenzuordnung und Diffusion/DDIM getrennt diagnostizieren, bevor weitere Samplingstärken oder eine endgültige Trainingsänderung gewählt werden. Die hier getestete 50%-Balancierung eignet sich wegen der Lift-Regression nicht als Ersatzpolicy. Ein zukünftiger Trainingsansatz müsste den Übergang präziser abbilden und die übrigen Phasen nachweislich erhalten; stärkeres Oversampling ist aus diesem Befund keine begründete nächste Maßnahme. In dieser Runde wurden keine zusätzlichen Methoden trainiert und keine XY-Heuristik eingesetzt.

## Fragestellung und Isolation

Zwei Fortsetzungen desselben korrigierten Scheduler-Checkpoints, jeweils genau 5.000 Gradient-Updates, Batchgröße 8, Seed 1. Architektur, State-Observations, Diffusion-Training, DDIM (10 Schritte), Beobachtungshistorie (2 Frames), Vorhersagehorizont (16), AdamW und EMA bleiben zwischen den Armen identisch. Inferenz führt wie bisher 2 Aktionen aus. Keine XY-Heuristik; ausschließlich Samplinggewichte unterscheiden die Trainingsarme. Nur der letzte Checkpoint wird evaluiert, keine Auswahl anhand der Ergebnisse.

Der Ausgangscheckpoint beendet den bisherigen Cosine-Zyklus bei Lernrate 0. Deshalb erhalten beide Arme identisch einen neuen 5.000-Update-Cosine-Zyklus mit Ausgangs-LR 1e-4 und 500 Warmup-Schritten. AdamW-Momente und rohe/EMA-Gewichte werden restauriert. Der im Checkpoint nicht gespeicherte EMA-Schritt wird in beiden Armen auf den aus AdamW abgeleiteten Schritt 30.000 gesetzt; beide enden bei 35.000. Damit testet der Unterschied balanciert minus uniform den Samplingeffekt, nicht zusätzliche Trainingszeit.

[Vorab gespeichertes Protokoll](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/protocol.json>), [Isolation und Dataset-Abgleich](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/verification.json>). Identische LR-Arrays und Checkpoint-Konfigurationen; 60 History-/Action-Fenster mit dem ursprünglichen SequenceDataset abgeglichen. Beide Anfangsgewichte sind exakt gleich dem Ausgangscheckpoint.

## Automatische Übergangsdefinition

Der erste Frame k erfüllt: B-Höhe >0,98 m; geschlossener Gripper-Befehl; XY-Aktionsnorm >0,25; Cosinus zwischen XY-Aktion und EEF→A-Zielvektor >0,85; EEF–B-Abstand <12 mm; vorherige drei XY-Normen <0,12 und die drei ab k >0,25. Das Kriterium findet genau einen Umschaltpunkt je Demo und stimmt in allen 200 Demos mit dem rekonstruierten Expert-Transportbeginn überein. Keine manuellen Phasenlabels bestimmen das Sampling.

Die inklusiven Ankerfenster [k−6,k+8] enthalten 15 Frames (−0,30 bis +0,40 s). Auf 180 Trainingsdemos: 2.700/27.322 Ankerframes = 9,88 %. Balanciert bekommen diese Frames zusammen 50 % Samplingmasse, die übrigen 24.622 Frames 50 %. Ein Übergangsframe erhält somit 9,12-mal das Gewicht eines anderen Frames. Alle übrigen Phasen bleiben enthalten; 20 Validierungsdemos werden nicht gesampelt.

Jeder Trainingsanker enthält History t−1,t und 16 überwachte Aktionen t−1…t+14. Die Prozentzahlen beziehen sich auf Ankerframes, nicht auf exklusive Verlustmasse einer Phase.

| Tatsächliche Stichproben | Uniform | Balanciert |
|---|---:|---:|
| Übergangsanker von 40.000 | 3898 (9.74%) | 19955 (49.89%) |
| Phase | Uniform | Balanciert |
|---|---:|---:|
| 0: Annähern | 5208 | 2820 |
| 1: Absenken zum Greifen | 6354 | 3580 |
| 2: Greifen | 5226 | 3034 |
| 3: Lift | 7471 | 11170 |
| 4: Transport | 5352 | 13731 |
| 5: Absenken zum Platzieren | 6184 | 3409 |
| 6: Release | 4205 | 2256 |

## Offline: Expert-Zustände

Alle 180 Train-/20 Validierungsdemos, sämtliche Transportframes (3.693/399), drei gemeinsame Diffusions-Zufallsziehungen. Teacher Forcing verwendet echte histories; beide ausgeführten Aktionen je Replanning werden ausgewertet. Verhältnis = mediane Policy-/Expert-XY-Norm bei Expert-Norm >0,1. Falsche Richtung = Cosinus <0. Diese Auswertung ersetzt keine Rollouts.

| Split / Modell | XY-Verhältnis | Richtungscosinus, Median | Falsche Richtung | Transport-Öffnen | Lift-Öffnen | Lift Z-MAE |
|---|---:|---:|---:|---:|---:|---:|
| train / Ausgangsmodell | 37.0% | 0.798 | 18.0% | 0.4% | 8.2% | 0.648 |
| train / Uniform +5.000 | 35.1% | 0.773 | 19.5% | 1.3% | 10.9% | 0.657 |
| train / Balanciert +5.000 | 54.6% | 0.872 | 14.7% | 0.7% | 11.3% | 0.685 |
| valid / Ausgangsmodell | 36.5% | 0.824 | 20.5% | 0.8% | 7.1% | 0.630 |
| valid / Uniform +5.000 | 34.4% | 0.808 | 20.0% | 1.8% | 10.1% | 0.640 |
| valid / Balanciert +5.000 | 56.1% | 0.898 | 15.6% | 1.1% | 10.9% | 0.659 |

### Unmittelbarer Umschaltbereich

Früher Transport = k…k+8. Vorbereich = k−6…k−1. Signifikanter Beginn erfordert drei aufeinanderfolgende Aktionen mit XY-Norm >0,25 und Zielcosinus >0,5 im Fenster k−10…k+30. Ein Beginn bei −10 ist links zensiert; er kann noch früher liegen. Timingwerte behandeln diesen Fall als mindestens 0,5 s zu früh.

| Split / Modell | XY-Verhältnis früh | XY-Norm vor Wechsel | Z-Aktion vor Wechsel | Beginn ±0,1 s | Zu früh >0,1 s | Kein Beginn im Fenster | XY-Richtungswechsel im gesamten Transport |
|---|---:|---:|---:|---:|---:|---:|---:|
| train / Ausgangsmodell | 32.8% | 0.439 | -0.088 | 19.8% | 50.2% | 24.1% | 11.6% |
| train / Uniform +5.000 | 28.4% | 0.416 | -0.075 | 17.8% | 49.3% | 26.9% | 12.7% |
| train / Balanciert +5.000 | 52.1% | 0.560 | -0.150 | 14.8% | 74.4% | 8.0% | 11.4% |
| valid / Ausgangsmodell | 37.1% | 0.438 | -0.094 | 28.3% | 46.7% | 16.7% | 14.5% |
| valid / Uniform +5.000 | 33.4% | 0.422 | -0.084 | 21.7% | 45.0% | 25.0% | 15.3% |
| valid / Balanciert +5.000 | 60.0% | 0.575 | -0.167 | 10.0% | 80.0% | 5.0% | 13.2% |

Das Expert-XY-Kommando springt am Wechsel von nahezu null auf etwa 1,17. Die Modelle bilden diesen Sprung als breite, vorgezogene Bewegung ab. Balancierung erhöht sowohl die gewünschte Bewegung danach als auch die unerwünschte Bewegung davor. Das Verhalten ist auf Train und Validierung ähnlich. Die Z-Aktion vor dem Wechsel sollte positiv sein; in der Policy liegt der Mittelwert bereits im negativen Bereich.

Der gepaarte Vergleich zeigt größere mittlere frühe XY-Aktionen bei allen 180 Trainings- und allen 20 Validierungsdemos. Auf Validierung steigt die frühe XY-Norm im Mittel um 0,123. Vor dem Wechsel: Expert-XY-Norm 0,020, uniforme Policy 0,422, balancierte Policy 0,575; Expert-Z-Aktion +0,116, uniform −0,084, balanciert −0,167. Der Gewinn an Aktionsstärke generalisiert, die korrekte Umschaltgrenze wird dadurch aber nicht gelernt.

![Aktionsverläufe um den Expert-Wechsel](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/boundary_profiles.png>)

## Rollouts: 20 feste Startzustände

Seeds 46000–46019; alle initialen Simulatorzustands-Hashes stimmen mit dem bisherigen Vergleich überein. 500 Schritte Hauptauswertung; anschließend 40 Schritte Policy-Fortsetzung. Stabiler Stack = bisheriges Environment-Kriterium (0,5 s gültiger Stack); zusätzlich wird Fortbestand in der 2-s-Fortsetzung gemessen.

Lift entspricht dem bisherigen Kriterium B>0,88 m. Vollständiges Lift-Ende wird getrennt als gehaltenes B≥1,045 m und EEF≥1,049 m während drei Frames definiert. Transportbeginn: gehalten, B>0,98 m, XY-Geschwindigkeit >2 cm/s und Zielcosinus >0,5 während drei Frames. Das ist Beginn zielgerichteter Bewegung, keine Garantie anhaltender Annäherung. Positioniert: XY<9 mm und Höhendifferenz >32 mm; abgesenkt zusätzlich 40±8 mm; Release zusätzlich Würfelkontakt und kein B-Grasp.

| Stufe | Ausgangsmodell | Uniform +5.000 | Balanciert +5.000 |
|---|---:|---:|---:|
| Greifen | 17/20 (85 %) | 14/20 (70 %) | 12/20 (60 %) |
| Anheben (bisheriges Kriterium) | 13/20 (65 %) | 10/20 (50 %) | 2/20 (10 %) |
| Transportbeginn | 9/20 (45 %) | 4/20 (20 %) | 1/20 (5 %) |
| 3-cm-Zielbereich | 4/20 (20 %) | 1/20 (5 %) | 0/20 (0 %) |
| Positioniert | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Abgesenkt | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Release | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Stabiler Stack | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Vollständiges Lift-Ende | 3/20 | 1/20 | 0/20 |
| Stack über weitere 2 s erhalten | 0/20 | 0/20 | 0/20 |

Die Ausgangsspalte ist aus den bereits gespeicherten instrumentierten Rollouts des unveränderten Bestmodells berechnet (17 Grasp, 13 Lift); der historische Evaluationslauf hatte 14 Lift. Diese kleine Wiederholungsabweichung ist dokumentiert; uniforme und balancierte Fortsetzung werden hier direkt und mit gleichem Ablauf verglichen. Der diagnostische XY-Regler mit 45 % Stack-Erfolg wird in keinem neuen Lauf eingesetzt.

Zusätzlicher Blick auf die frühe Lift-Steuerung im Rollout: innerhalb der ersten 40 Schritte ab erstem Grasp, solange B≤0,88 m und weiter gehalten wird, erzeugt uniform in 16,0 % der ausgewerteten Schritte Z>0,1, balanciert nur in 11,0 %. Öffnungsbefehle treten in 19,0 % bzw. 26,7 % dieser Schritte auf (343/273 Schritte; unterschiedliche erreichte Zustände, deshalb beschreibend und kein kontrollierter Teacher-Forcing-Vergleich).

![Erfolgsstufen](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/rollout_stages.png>)

### Distanz nach vollständigem Lift-Ende

Mittelwert mit Anzahl verfügbarer Fälle; fehlende volle Lifts werden nicht als Nullabstand behandelt. Werte sind auf das erste vollständige Lift-Ende bezogen, nicht auf das frühere 8-cm-Anhebekriterium. Unterschiedliche Erfolgsselektion kann die bedingten Mittelwerte verzerren.

| Zeit | Ausgangsmodell | Uniform | Balanciert |
|---|---:|---:|---:|
| 0.5 s | 5.69 cm (n=3) | 7.68 cm (n=1) | — (n=0) |
| 1.0 s | 6.33 cm (n=3) | 8.19 cm (n=1) | — (n=0) |
| 2.0 s | 3.15 cm (n=2) | 3.63 cm (n=1) | — (n=0) |

Gemeinsame vollständige Lifts beider Fortsetzungen: [].

| Zeit / gemeinsame Fälle | Uniform | Balanciert |
|---|---:|---:|
| 0.5 s | — (n=0) | — (n=0) |
| 1.0 s | — (n=0) | — (n=0) |
| 2.0 s | — (n=0) | — (n=0) |

| XY-Aktionswechsel während Transport | Ausgangsmodell | Uniform | Balanciert |
|---|---:|---:|---:|
| Richtungswechsel / benachbarte aktive Replans | 29.1% | 31.0% | 32.9% |
| Anzahl je geliftetem Rollout, Median | 23 | 16 | 14 |

Transportbeginn relativ zum vollständigen Lift-Ende (negative Werte = Bewegung bereits davor): Ausgangsmodell: -0.95 s (n=3); Uniform +5.000: -2.00 s (n=1); Balanciert +5.000: kein auswertbarer Fall.

Gezählt werden aufeinanderfolgende aktive Replanning-Kommandos (alle zwei Schritte), gehaltenes B und Zielabstand >2 cm, XY-Norm >0,01; Richtungswechsel = negativer Dot-Product. Beginn ab vollem Lift, falls erreicht, sonst ab erstem bisherigen Lift. Offline verwendet einzelne ausgeführte Aktionen; die Nenner sind daher unterschiedlich.

![Repräsentative gespeicherte Zustandsverläufe](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/representative_rollouts.png>)

## Zusatzdiagnose: identische Expert-Lift-Enden als Startzustände

Diese zusätzliche Auswertung wurde nach den frühen vollständigen Rollouts ergänzt, weil die balancierte Policy häufig keinen Lift erreichte. Sie ist eine Evaluation derselben drei eingefrorenen Modelle, kein dritter Trainingsarm und keine neue Methode. Alle 20 Validierungsdemos werden ab ihrem automatisch erkannten Expert-Transportbeginn fortgesetzt: identische gespeicherte Simulatorzustände, bereits gegriffener/angehobener Würfel und genaue Expert-History k−1,k für den ersten Policy-Aufruf. Anschließend kommen alle Beobachtungen und Bewegungen aus der unveränderten Policy/Simulation. Haupt-Horizont 120 Schritte (6 s), Fortsetzung 40 Schritte.

Alle Startzustands-Hashes stimmen zwischen den Modellen überein; alle 20 initialen Grasps sind vorhanden. Wiederhergestellte Würfelpositionen stimmen auf <1 mm mit der Demo überein. Controller-interne Erinnerung wird beim Restore in allen Varianten gleich neu initialisiert; deshalb sind diese Starts eine kontrollierte Zustandsfortsetzung, kein exakt unterbrechungsfreier Expert→Policy-Wechsel. Die Zahlen werden getrennt vom bisherigen vollständigen Startvergleich berichtet. [Zusatzprotokoll](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/expert_lift_protocol.json>).

| Ergebnis ab Expert-Lift-Ende | Ausgangsmodell | Uniform | Balanciert |
|---|---:|---:|---:|
| Transportbeginn | 20/20 | 20/20 | 20/20 |
| 3-cm-Zielbereich | 14/20 | 11/20 | 19/20 |
| Positioniert | 3/20 | 3/20 | 7/20 |
| Abgesenkt | 1/20 | 1/20 | 0/20 |
| Release | 1/20 | 1/20 | 0/20 |
| Stabiler Stack | 0/20 | 1/20 | 0/20 |
| Stack über weitere 2 s erhalten | 0/20 | 0/20 | 0/20 |

Die folgenden Abstände sind ab dem vorgegebenen Expert-Lift-Ende gemessen; alle Varianten haben denselben Nenner n=20.

| Zeitpunkt | Ausgangsmodell | Uniform | Balanciert |
|---|---:|---:|---:|
| 0.5 s | 9.84 cm | 10.08 cm | 8.62 cm |
| 1.0 s | 7.26 cm | 7.62 cm | 5.34 cm |
| 2.0 s | 4.41 cm | 4.91 cm | 2.95 cm |
| XY-Richtungswechsel / aktive Replan-Paare | 30.1% | 32.7% | 32.1% |

![Vergleich ab vorgegebenem Expert-Lift-Ende](<C:/Users/artur/Desktop/Programmieren/IT/Imitation Learning/experiments/stack_balance_20261001/expert_lift_comparison.png>)

## Dateien und Reproduzierbarkeit

Finale Checkpoints: `uniform/model_final.pth`, `balanced/model_final.pth`. Trainingslogs, tatsächliche Samplinghäufigkeiten und LR-Arrays liegen in den jeweiligen Unterordnern. `offline_predictions.npz` enthält dreifache Predictions, Expert-Aktionen und exakte Beobachtungshistorien; `offline_samples.json` ordnet sie Demos und Umschaltpunkten zu. `rollouts/<seed>.npz` speichert alle tatsächlichen Beobachtungen, Simulatorzustände und Zustands-/Aktionsverläufe einschließlich Fortsetzung; `results.json` enthält alle Ereigniszeiten.

Repräsentative Videos: `uniform/rollouts/46004.mp4` (voller Lift, danach kein Stack), `balanced/rollouts/46002.mp4` (Lift scheitert), `uniform/expert_lift_rollouts/demo_47.mp4` und `balanced/expert_lift_rollouts/demo_47.mp4` (derselbe Expert-Lift-Start; balanciert positioniert, uniform erreicht den 3-cm-Bereich nicht). `uniform/expert_lift_rollouts/demo_22.mp4` zeigt den einzigen temporären Stack der Zusatzdiagnose; er hält die folgende 2-s-Policy-Fortsetzung nicht durch. Alle Videos sind aus gespeicherten Simulatorzuständen gerendert.

62 Demonstrationen mit schwarzen Transportbildern (1.266/4.092 Transportframes) bleiben separat dokumentiert und unverändert. Dieser Versuch liest ausschließlich 15 State-Merkmale pro Frame und keine RGB-Observation; schwarze Bilder bestimmen weder Sampling noch Ausschluss. Der vollständige HDF5-Hash bestätigt unveränderte Daten.

Ausgangscheckpoint SHA256: `a2c2cca1cd087409261402f3b95f7b6592961e6aac92c276c72657dd436343f4`. HDF5 SHA256: `5222cbf96dc6218389d491fe7b99449295dcfc9bceb3bab8f8776ffff19fe6f8`.

Ein Trainingsseed, 20 feste Rollouts und drei Offline-Diffusionsziehungen: ein kontrollierter Richtungsvergleich, keine präzise Schätzung einer allgemeinen Erfolgswahrscheinlichkeit. Es wurden keine weiteren Methoden oder Hyperparameterkombinationen getestet.
