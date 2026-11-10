# Isolierter Algorithmusentwurf: Rechenbarkeit und praktische Voraussetzungen

Stand 2026-10-04T14:54:24.448496+02:00. [Reine Tensorreferenz](loss_reference.py), [fixiertes Protokoll](PROTOCOL.md), [Eingangs-/Sourcehashes](selection.json), [exploratives Audit](result.json). **Kein Policytraining, keine neue Simulatoraktion und keine produktive Algo-Registrierung.** Bestehender Kontraktions- und Sensor-BC-Code sind gegen die ursprünglichen Pilotquellen unverändert. Wiederverwendung der bereits gesehenen error_margin_001-Daten ist ein Implementationsaudit, keine frische wissenschaftliche Bestätigung oder neuer Seed der Policy.

## Konkrete Änderung im Forschungsentwurf

L=L_BC+lambda/N * sum_i w_i relu((||delta_i A_i+DeltaAction_i B_i||/||delta_i||+epsilon_i)^2-rho^2), rho0.99. Volle7D-Aktionsdifferenz, lokale3D-Positionsantwortmatrix B_i7×3, getrennte offene Zustandsantwort A_i3×3, konstante Gültigkeitsannotation/Fehlerhülle. Alle Annotationen detached, Gradienten nur über Policyaktionen. Fehlende/nullgewichtete Cacheeinträge werden vor Norm/Matrixmultiplikation ausgeschlossen; NaN*0 wird vermieden. Ganzer geplanter Batchnenner, kein Hochskalieren durch Teilen nur durch gültige Fälle. Controllerseitiges Aktionsclipping und komponentenweise Identifikationsregion werden explizit berücksichtigt. BC bleibt das offizielle unclipped Expertenziel; lambda1 dient ausschließlich der Skalenmessung, kein hier gewählter Trainingswert.

Das ist eine implementierte Referenz eines vorgeschlagenen BC-Zusatzlosses. Sie liefert keine allgemeine Stabilität und setzt keine fachliche Trainingsfreigabe voraus. Die verwendete endliche empirische Fehlermarge **scheiterte zuvor** auf zehn von48 neuen gültigen Antworten; Formelkorrektheit macht sie nicht gültig. Im alten produktiven Loss ist diese Referenz nicht aktiv.

## Numerische und Gradientenkontrollen

Zehn reine Checks: undefined Cache bei Nullgewicht, konstante Annotationen ohne Gradient, unabhängige NumPyformel/voller Batchnenner,7D-Aktionsableitung, Rotations-/Gripperspalten, komplett maskierter Batch mit endlichen Nullgradienten, Ablehnung von Nullperturbation/nichtfinitem aktivem B/negativem epsilon, alle7Achsen der Aktionsregion. [Vorprüfung](preflight_001/result.json) bestanden; zufällige Aktionsrichtungsableitung Fehler5.83e-12. Die synthetische Gripperableitung prüft nur Implementationsfähigkeit, nicht physische Gripperwirksamkeit.

Richtungsableitung des eingefrorenen B0 auf vorab festem demo_38,t4: vier Varianten **4/4 VERIFIED**, Float64-Klon, eps1e-5, maximaler relativer Fehler 4.21e-11, kein Kink zwischen den Prüfpunkten; Klon exakt restauriert, Hauptmodell unverändert. Unabhängig frisch geladene Policy plus NumPyformel rekonstruiert12Frames×4Varianten/72geplante Perturbationen, Masken/Featurezuordnung/Aktionsregion; maximaler Verlustunterschied 8.5e-08, Ratiounterschied 1.26e-07 durch Float32- versus NumPyrechnung, [Nachweis](verification_001/result.json).

## Cache, Featuresemantik und Abdeckung

Tatsächlich verwendete Policykeys: object, robot0_eef_pos, robot0_eef_quat, robot0_gripper_qpos. Vollständige Zuordnung der nominalen Features zum HDF5 an **12/12** Frames innerhalb vorab1e-6; maximale absolute Abweichungen {"object": 2.9579874327723132e-08, "robot0_eef_pos": 5.304723371679643e-08, "robot0_eef_quat": 2.583000469069674e-08, "robot0_gripper_qpos": 1.5480563914094247e-09}. Andere Simulatorobservables wie Jointvelocity sind hier keine Policyinputs. Lokale B-Matrix nur an **8/12** Frames vorhanden, nach privilegierter vollständiger physischer Validierung; vier späte Kontaktframes haben fehlenden Cache. Dies ist zusätzliche Simulatorkalibrierung und kein vorher verfügbarer unabhängiger Sensorfilter.

Die getrennten nominalen M0/M2-Masken werden vor dem Loss berechnet. **Gewichte im Audit kombinieren diese Masken ausdrücklich mit Cacheverfügbarkeit aus dem früheren physikalischen Gate.** Dadurch wird die M0-Fehlannahme nicht zum brauchbaren M0-Filter umgedeutet: an diesem angenommenen ungültigen Frame fehlt B und die effektive Cachemaske ist null. Kosten, vollständiger Coverage-Nenner und Herkunft dieses privilegierten Labels bleiben offen ausgewiesen.

Komponentenweise Region um tatsächliche ±0.1nominalen Identifikationsaktionen: **70/72** Sensorperturbationen innerhalb; alle48Cachefälle innerhalb, zwei späte Fälle außerhalb. Die Prüfung gilt für den eingefrorenen B0, nicht für während Training veränderte Aktionen. Sensor- versus echte physische Perturbation der vier verwendeten Eingangsfeatures: maximale absolute Abweichungen {"object": 1.4901161193847656e-08, "robot0_eef_pos": 5.960464477539063e-08, "robot0_eef_quat": 3.725290298461914e-09, "robot0_gripper_qpos": 0.0}, maximale Aktionsdifferenz 2.38e-07; unabhängig reproduzierte gespeicherte physische Aktionen maximal 1.79e-07 abweichend. Kleine Differenzen unter dieser kontrollierten Ersatzgeschichte sind kein Nachweis korrekter Recoverylabels oder Originalexpertgeschichte. Sensoraugmentation behält dieselbe Aktion bei; physische Recovery verlangt eine andere Label-/Dynamikbegründung.

## Wirksame Gradienten, lambda1 nur Diagnostik

| Variante | Gewichtete / geplante Fälle | Aktiver Loss / geplant | Batchloss | Gradientennorm / BC | Kosinus zu BC |
|---|---:|---:|---:|---:|---:|
| M0_raw | 48/72 | 36/72 | 0.00849049 | 0.4799 | 0.2412 |
| M0_margin | 48/72 | 44/72 | 0.01083601 | 0.5218 | 0.2044 |
| M2_raw | 42/72 | 32/72 | 0.007462339 | 0.4231 | 0.2486 |
| M2_margin | 42/72 | 40/72 | 0.009572619 | 0.4757 | 0.2019 |

Die feste Marge aktiviert zusätzliche Regularisierungsfälle, Maske und Cacheabdeckung verändern die Stärke. Die globalen Gradienten sind Mittelwerte über alle12Frames, nicht Normmittelwerte über nur gültige Beispiele. Kein daraus gewähltes lambda, keine Task-/Robustheits-/Konvergenzaussage. Späte ausgeschlossene Fälle behalten ihren BC-Loss; nur dieser Zusatzloss fehlt dort.

## Kosten und Status

Vorprüfungsworker 0.031s / Supervisor 2.009s; Primärworker 2.640s / Supervisor 6.013s; unabhängiger Worker 2.594s / Supervisor 6.012s. Hauptauditcounts {"main_forward_batches": 48, "main_policy_input_samples": 168, "clone_forward_batches": 24, "clone_policy_input_samples": 84, "physics_steps": 0, "optimizer_constructions": 0, "optimizer_updates": 0}; unabhängige NumPygegenprüfung zusätzlich24Policyforwardbatches/84Inputs. Keine Optimizerkonstruktionen, Updates, Physiksteps oder neuen Antwortfits. Bestehende Kalibrierkosten gehören weiterhin zum Gesamtmethodenaufwand.

Alle Worker/-Supervisoren per PID plus Erzeugungszeit beendet, Jobs geschlossen. Parameter-SHA256 **6073d5be417959e6f544985fa2565044895ca8ec0c04a95a8583446d7610408b**, Endcheckpoint **27a38fc65415d419a060cd0fc529f8f30d82bc36cdf77d54cc79d7a3e52117fa**, Dataset **2067777cb8b532e9263dd09fd6448c41cc31224bb27be4a3b734010ae13eb540**, jeweils unverändert. Code-SHA256 `6f2cf13b09da62a2e646b7a5107b49c53fe5bbf9630cd74516818c4a66091d33`; Audit `b09df728b7b1b2aceeb0caaba681f46dbc572a34dedbbf7cfb9c6937b28c2e07`; Gegenprüfung `a2bc5c000aa6dafb9b0c04c5e2d278f2f4bc4607dc7a117b6063e6bb8db65df9`.

Fachliche Entscheidung: konkreter Lossentwurf jetzt implementiert und rechnerisch geprüft; preiswerte breite Cacheversorgung, dynamische Gültigkeit, übertragbare Fehlermarge, Skalenkontrolle und replizierter Trainingsnutzen weiterhin nicht etabliert. Kein ungeplanter neuer Trainingslauf. Sessioncoordinator/Heartbeat bleiben ACTIVE bis exakt15:11:19 Berlin. Nächster letzter Agentauftrag: [SESSION_CLOSEOUT.md](../SESSION_CLOSEOUT.md), Gesamtevidenz getrennt synthetisieren und erst nach tatsächlichem Deadlineende alle Prozesse/Wachhaltemodus prüfen und Automation pausieren.
