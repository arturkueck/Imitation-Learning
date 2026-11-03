# V4 Daten- und Laufzeitpilot

**Pilot abgeschlossen; Haupttraining nicht gestartet; keine Modellgewichte übernommen.**

## Tatsächlich ausgeführt

200 neue Familien angefragt, 200 gültige Datensätze. Neue Familien-ID-Basis 94140202; ausschließlich Pilotdaten, nicht als späterer Blindtest verwenden. Die drei ursprünglichen M2-Checkpoint-Hashes wurden vor und nach dem Pilot geprüft. Ansichten nutzen deren eingefrorenes Ensemble als Fokusquelle, keine GT-Zielposition.

Je Familie werden Ausgangsansicht, kleiner Kontrollversatz und ein zugeordneter Blickwunsch untersucht. Dies ist **kein vollständiger sechs-Kandidaten-Datensatz pro Familie**. Kamerabank mit 10 zertifizierten Wegen. Statische Geometrie, Robotervertrag und Startzustand werden per Fingerprint kontrolliert; analytische Swept-AABBs prüfen separat die Objektfreiheit jeder neuen Szene. Der Fokus muss vollständig im Kamerabild liegen; die Kamera zielt bei diesem Bankpilot nicht zwingend bis auf drei Grad ins Zentrum. Die tatsächliche Winkelabweichung wird gespeichert. Bankvorbereitung: 71.9 s. Nicht gefundene Lösungen beweisen keine globale Unerreichbarkeit.

| Blickfamilie | Angefragt | Aufgenommen |
| --- | ---: | ---: |
| right | 40 | 12 |
| left | 40 | 5 |
| base | 40 | 0 |
| elevated | 40 | 13 |
| difficult | 40 | 17 |

Alle abgelehnten Wünsche sind erhalten. Paddings für nicht aufgenommene Bilder sind als nicht verfügbar maskiert. Keine Ablehnung wird als erfundene Aufnahme gezählt. Lange/dünne Quader wurden in 18 Familien untersucht, zunächst nur verstreut. Objektanzahlen: `{'5': 37, '4': 39, '3': 44, '2': 37, '1': 32, '0': 11}`. Anordnungen: `{'tower': 58, 'wall': 24, 'mixed': 54, 'scattered': 64}`.

## Geometrie und Sicherheit

Rückprojektion tatsächlicher Kamerastrahlen: maximal 0.000067 Pixel Abweichung. Für erfolgreiche Wünsche ganze Armwege einschließlich Greifer/Kameraproxy erneut geprüft und native Kontakte an Replay-Zuständen geprüft. Kein aufgezeichneter Robot-Umwelt-Penetrationsfehler im erfolgreich abgeschlossenen Pilot. Referenzquelle bleibt Simulatorgeometrie; keine rein visuelle Freigabe und keine Realroboterfahrt. Diskrete Prüfungen sind keine formale kontinuierliche Sicherheitsgarantie.

Geprüft sind tatsächliche Kameraposen und Verfügbarkeitsmasken, nicht die Qualität eines trainierten V4-Modells. Bildfehlerfälle enthalten einen ausdrücklich protokollierten Weichzeichner, keine manipulierte Pose.

## Numerischer Test

* Wahrnehmung: 904,112 Parameter; vorgeschlagener Übernahmekopf separat auf 4.291 Parameter nachgezählt.
* Drei echte Diagnose-Optimizerupdates, dazu ein wiederholtes Resume-Suffix; FP32, effektive Szenenbatch 32, Microbatch 4, zwei Präfixkontexte.
* Parameteränderung nachgewiesen: maximal 0.00020051003.
* Wiederaufnahme mitten in Epoche und Gradient Accumulation: Gewicht-/Optimizermomentabweichung 0.0/0.0, Scheduler/RNG/Sampleroffset wiederhergestellt.
* Median Updatezeit 0.661 s. Drei Messwerte: `[1.1446537000010721, 0.6611324000114109, 0.5991996999946423]`.
* GPU: NVIDIA GeForce RTX 5070; Peak allocated 0.342 GiB, reserved 0.514 GiB; RSS am Datengenerations-Messpunkt maximal 1.775 GiB (kein kontinuierlicher Gesamtprozess-Peak).

Die Diagnosekopie wird nicht produktiv gespeichert oder ausgewählt. Maßgebliche Numerikartefakte: `numerical_002/numerical.json`, `numerical_002/diagnostic_partial_resume.pth`, `numerical_002/diagnostic_loss.png`. Die erste Messung bleibt separat erhalten. Nach Vereinheitlichung der geometrischen und Sichtbarkeits-Zuordnung wurde der Benchmark unabhängig wiederholt: zweimal drei Updates plus je ein wiederholtes Resume-Suffix, insgesamt acht Diagnose-Optimizeraufrufe. Keine dieser Kopien wird übernommen. Die drei Losswerte je Messung sind **keine belastbare Trainings-/Validation-Lernkurve**. Der separate feste Probe-Loss ist eine Laufzeitkontrolle; keine Aussage über Overfitting oder Generalisierung.

## Zeit-/Speicherabschätzung

Gemessene Datenerzeugung 1.81 min, im Mittel 0.183 s/Familie. Komprimierte Arrays im Mittel 0.212 MiB/Familie für drei Poseslots. Insgesamt Pilotdauer 1.93 min.

Für 18.000 neue Trainingsfamilien + 6.000 Replayziehungen pro effektiver Epoche, Batch 32, zwei Varianten und drei Seeds:

| Epochen je Variante/Seed | Updates insgesamt | Nur Optimizerzeit, hochgerechnet |
| --- | ---: | ---: |
| 10 | 45,000 | 8.26 h |
| 20 | 90,000 | 16.53 h |
| 40 | 180,000 | 33.06 h |

30.000 neue Familien bei genau dieser begrenzten Drei-Pose-Pilotsuche: 1.53 h. Der vollständige Bankgenerator muss mehr Blickfamilien prüfen; diese Zahl ist keine Zusage für dessen Laufzeit. Sieben Poseslots ergeben rechnerisch etwa 50.8 GiB rohe Arrays; naive Kompressionshochrechnung 14.5 GiB ist wegen der gepaddeten blockierten Ansichten unsicher. Speicher für Replay, Optimizer, Kopfdatensätze, Rohjournale, Plots und Sicherheitsreserve kommt hinzu.

Diese Hochrechnung enthält **keine** vollständigen Validation-/Request-/Kalibrierungs-/Blindtest- oder Renderkosten. Drei Updates sind eine kleine Laufzeitstichprobe. Erst der fertig implementierte Trainer und vollständige Kandidatenbank-Pilot erlauben ein verbindlicheres End-to-End-Budget; keine pauschale 10-Stunden-Zusage.

## Nächste Freigabe und verbleibende Arbeiten

Der technische Pilot prüft Daten-/Numerikmachbarkeit. **Noch keine Startfreigabe für einen unveränderten Hauptlauf:** Nur 47/200 zusätzliche Wünsche wurden erfasst, darunter 5/40 linke und 0/40 Basisansichten. Die geringe Abdeckung darf nicht als ausreichender Trainingsdatensatz ausgegeben werden. Basis hatte keine Bankkandidaten; das ist kein globaler Unerreichbarkeitsnachweis. Zuerst Bank verbreitern und Kosten/Abdeckung erneut prüfen, ohne Sicherheitskriterien zu lockern. Benötigt werden mindestens 20 gültige Ansichten pro rechter/linker/erhöhter Blickfamilie in einem festgelegten Pilot von 200 Familien; fehlende Basisansichten bleiben separat blockiert. Für Datenvolumenplanung zusätzlich die tatsächlichen Positivquoten ausweisen.

Vor einem Hauptlauf außerdem erforderlich: definierte Kamera-/Geometrie-Holdouts mit Hashmanifest; A/B-Trainer mit festem gemeinsamem Updatebudget; Beobachtungs-/Übernahmemerkmale und Kopftrainer; Kalibrierungsgates und automatische Berichte. Die V4-Dateien sind noch kein freigegebener Haupttrainer. Als erste Wahrnehmungsstudie empfehlen sich zehn gepaarte Epochen mit allen drei Seeds statt sofort vierzig. Die Tabelle zeigt ausschließlich Optimizerzeit; ein späteres Budget muss Datenerzeugung, Bankvorbereitung, Validation und Auswertung zusätzlich enthalten. Kopftraining erst nach bestandenem Wahrnehmungsgate und als eigener gemessener Abschnitt.

Bei Freigabe zuerst den festen Update-/Zeitumfang wählen. Die gemessene Machbarkeit sagt nichts darüber aus, ob Seitenbilder die Erkennung verbessern; genau das muss der geplante A/B-Versuch zeigen. Eine nicht erreichbare Basisansicht oder unbekannter visueller Freiraum bleiben blockiert.

Artefakte: `manifest.json`, `checkpoint_hashes.json`, `families.jsonl`, `samples/`, `examples/`, `numerical.json`, `budget_estimate.json`, `coverage_and_runtime.png`, `diagnostic_loss.png`, `source/`.
