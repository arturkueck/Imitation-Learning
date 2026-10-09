# Wissenschaftliches Ziel und Vorgehen der Projektarbeit

## Verifizierter Abschluss der Sechs-Stunden-Session

Stand 2026-10-04T15:15:45.459954+02:00: Die unveränderte Deadline 04.10.2026, 15:11:19.697 Berlin ist abgelaufen. Finales Audit bestanden: alle Sessionworker/-Supervisoren sowie Coordinator und Launcher beendet, Wachhalteanforderung freigegeben; Automation anschließend über die App auf PAUSED gesetzt und gespeichert bestätigt. Pilot: exakt 2.000 Updates pro Arm, 104 vollständige Evaluationsepisoden; Hashes und Paarungen erneut verifiziert. Die neue Kontraktionsloss-Referenz ist implementiert und numerisch/auf eingefrorenen Parametern geprüft; sie wurde nicht als neue Policy trainiert. Keine robuste neue BC-Verbesserung oder schnellere Lernkonvergenz nachgewiesen. Nächste Empfehlung: lokal identifizierte Zustandsantwort A gegen eingefrorenes A bei gleicher lokaler Aktionsantwort B auf neuen Demos prüfen; Protokoll und Grenzen vorher fixieren. Dieser Anschlussversuch läuft nicht.

[Gesamtsynthese](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/SESSION_RESEARCH_REPORT.md), [Lossreferenz](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/method_reference_001/loss_reference.py), [Abschluss](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/automation_closeout.json).

**Arbeitsstand: 4. Oktober 2026.** Diese Datei präzisiert das vom Nutzer bestätigte Ziel und ersetzt ältere Empfehlungen für neue Versuche. Alte Ergebnisse bleiben erhalten. Die folgenden Möglichkeiten sind ein Forschungsplan; damit ist kein neuer Trainingslauf oder Simulatorversuch gestartet.

## 1. Ziel der Arbeit

**Eine begründete algorithmische Erweiterung von Behavioral Cloning in robomimic implementieren und kontrolliert untersuchen, ob sie Robustheit oder Lerneffizienz verbessert.** Die Netzwerkarchitektur darf unverändert bleiben. Training dient als Experiment zur Prüfung einer konkreten Änderung am Lernverfahren, an der Datennutzung oder an der Ausführung.

Ein neuer Satz Gewichte, ein weiterer zufälliger Seed oder die Anwendung einer veröffentlichten Architektur auf eigene Daten ist für sich genommen kein neuer BC-Algorithmus. Replikationen sind Kontrollen und messen Seedstreuung; sie ersetzen keine Methodenfragestellung.

Der Beitrag muss nicht eine neue Modellfamilie sein. Eine begründete Adaption, nachvollziehbare Implementation und kontrollierte Untersuchung ihrer Wirkung und Grenzen kann zur Projektarbeit passen. Weltweite Neuheit wird nicht vorausgesetzt, sondern durch Literatur- und Codevergleich geprüft.

**Arbeitspriorität:** Robustheit primär, Lerneffizienz sekundär, weil dafür bereits ein implementierter Ansatz und Fehlerdiagnosen existieren. Schnelleres Training kann später die Hauptfrage werden, benötigt aber eine eigene Intervention und Zeitmessung.

## 2. Was „Konvergenz“ bedeutet

| Begriff | Erforderliche Messung | Unzureichender Ersatz |
|---|---|---|
| Optimierung/Lernen | Aufgabenleistung über echte Optimizer-Updates; Updates bis zu einer vorab definierten Leistung | Nur fallender Trainingsloss |
| Recheneffizienz | Gleiche Aufgabenleistung nach weniger Trainingszeit, einschließlich Zusatzrechnung und Vorberechnung | Weniger Updates bei höherem Aufwand je Update |
| Recovery im Regelkreis | Erfolgreiche Fortsetzung nach einer echten Störung und Recovery-Zeit | Kleiner approximierter Kontraktionsloss |

Diese Größen werden getrennt berichtet. Weniger Updates können mehr Zeit kosten. Lokale Kontraktion garantiert keinen Taskerfolg. Eine hohe nominale Erfolgsrate ist kein Robustheitsnachweis.

## 3. Bereits vorhandene algorithmische und experimentelle Grundlage

### BC mit Kontraktionsverlust für Lift

In [contraction_bc.py](praxis/src/robomimic_ext/contraction_bc.py) ist bereits eine BC-Erweiterung implementiert:

```text
Δa = π_xyz(o_δ) − π_xyz(o)
e_next_hat = δ + Δa @ K
L_contr = mean(relu(||e_next_hat||² / ||δ||² − ρ²))
L_total = L_BC + λ * L_contr
```

K ist eine auf Trainingsdaten geschätzte lokale EEF-Aktionsantwort. Die EEF-Position wird perturbiert und das relative Objektmerkmal konsistent angepasst. Der Zusatzloss soll eine korrigierende Aktionsreaktion fördern. Diese Finite-Difference-Näherung ist von Stable-BC inspiriert, implementiert aber nicht dessen ursprüngliche Eigenwertbedingung und besitzt hier keine theoretische Kontakt-/Stack-Stabilitätsgarantie.

Vorhandene Lift-Berichte liefern einen positiven lokalen Anhalt: nach 100 Epochen nominal 44/60 Erfolge für BC gegenüber 56/60 für die Erweiterung, über drei Trainingsseeds; nach 20 Epochen 23/60 gegenüber 36/60. Mehrere geprüfte Störungen zeigen ebenfalls Vorteile. Das ist keine allgemeine Verbesserungsbehauptung. Wenige Lernkurvenpunkte und nicht isolierte Zusatzkosten reichen nicht für einen Nachweis schnellerer Konvergenz in Rechenzeit. Lift besitzt einen möglichen Deckeneffekt.

Quellen: [Lift-Ergebnisbericht samt Grenzen](latex/plan_a/RESULTS.md), [100-Epochen-Einzelwerte](praxis/reports/lift_ph_full_100ep_summary.json), [20-Epochen-Einzelwerte](praxis/reports/lift_ph_full_20ep_summary.json), [bestehende Tests](praxis/tests/test_contraction.py).

### Stack als anspruchsvollere Testumgebung

Direct erreicht in der ursprünglichen Replikation 28/40, 30/40 und 31/40 stabile Stacks. Unnormalisierte Diffusion erreicht 0/40 pro Seed; die observation-normalisierte C-Variante im vorhandenen Seed 2/40. Architektur und Lernziel unterscheiden sich gemeinsam. Die Ergebnisse liefern eine funktionierende Stack-Baseline und Fehlerdiagnosen, isolieren aber keinen allgemeinen Vorteil einer Modellfamilie.

Frühere Übergangsbalancierung verbesserte Transportindikatoren, verschlechterte Lift und löste die Gesamtaufgabe nicht. Zusätzliche Dynamikfeatures führten ebenfalls nicht zu stabilen Stacks. Das begründet keine erneute blinde Erhöhung von Samplinggewichten oder unverändertes Diffusionstraining.

Quellen: [Gesamtsynthese](experiments/stack_replication_20261001/FINAL_EXPERIMENT_SYNTHESIS.md), [Balancierung](experiments/stack_balance_20261001/ERGEBNISSE.md), [Dynamikfeatures](experiments/stack_dynamics_20261001/ERGEBNISSE.md), [geprüfte Forschungsübersicht](experiments/stack_overnight_C_diffusion_20261004/RESEARCH_REVIEW.md).

## 4. Priorisierte Möglichkeiten

| Priorität | Algorithmischer Ansatz | Mechanismushypothese | Anhalt und Grenze | Entscheidender Vergleich |
|---|---|---|---|---|
| 1 | Datenbasierte Gültigkeitsgewichtung des vorhandenen Kontraktionslosses | Korrektur dort fördern, wo die Dynamiknäherung tragfähig ist; schädlichen Druck in unpassenden Bereichen vermindern | Vorhandener Lift-Vorteil, aber begrenzte Modellgüte und keine Kontaktgarantie; neue Gewichtung ungetestet | Konstante gegen gewichtete Kontraktion, plus BC und Rauschkontrolle |
| 2 | Strukturierte, zeitlich konsistente Observation-Augmentation | Unempfindlichkeit gegen kleine Messfehler lernen | Einfacher plausibler Mechanismus; kann präzise Phasenunterschiede verwischen; keine Recovery-Garantie | Sensorbias getrennt von echten Aktions-/Objektstörungen |
| 3 | Begrenztes adaptives Sampling kritischer Fenster | Updates auf schwer gelernte Entscheidungen konzentrieren, ohne übrige Phasen zu verdrängen | Frühere 50%-Balancierung zeigt schädlichen Trade-off; adaptiver Mechanismus ungetestet | Uniform, feste und adaptive Gewichtung bei gleichem Budget |
| 4 | Recovery-Daten mit DAgger-/DART-artiger Erhebung | Learner-besuchte Zustände mit gültigen Expert-Korrekturen abdecken | Literatur passt zu Distribution Shift; neue Daten und korrekt verwalteter stateful Expert erforderlich | Gleiche Zahl zusätzlicher Standarddemos gegen Recovery-Demos; Erhebungskosten separat |
| 5 | Zeitliches Ensembling oder kohärente Chunk-Ausführung | Sprünge zwischen aufeinanderfolgenden Plänen reduzieren | ACT liefert Motivation; alte Horizon-Sweeps retten Diffusion nicht; Gripper-Mittelung problematisch | Gleiche Checkpoints, isolierter Ausführungsvergleich und Inferenzzeit |

**Empfehlung:** Den vorhandenen Kontraktionsansatz und seine Gültigkeitsgrenzen als Ausgangspunkt verwenden. Priorität 1 ist danach ein konkreter Kandidat für eine begrenzte Weiterentwicklung. Für Stack ist die erfolgreiche deterministische Direct-Baseline sinnvoller als das Ziel, um jeden Preis Diffusion zu retten. Die Übertragung von Lift nach Stack bleibt ein eigener, bedingter Schritt.

Rauschaugmentation ist eine wichtige Kontrolle. Wenn sie denselben Vorteil billiger erreicht, rechtfertigt das den zusätzlichen Kontraktionsmechanismus nicht. Auch das wäre ein nützliches Ergebnis.

## 5. Konkreter Vorschlag: gültigkeitsgewichtete Kontraktionsregularisierung

**Status: Konzept, noch nicht implementiert oder trainiert. Weltweite Neuheit ungeprüft.**

Die bisherige Methode verwendet dieselbe näherungsweise Aktionsantwort K in vielen Situationen. Ein guter mittlerer Experten-Trajektorienfit beweist nicht, dass K in einer bestimmten Kontaktgeometrie oder für gegenfaktuelle Actions stimmt. Der Vorschlag verändert zunächst nur die Gewichtung des Zusatzterms; Netzwerk, BC-Loss, K und Perturbationsverteilung bleiben gleich.

```text
r(o) = auf inneren Prüf-Demos geschätzter lokaler Fehler der festen Dynamiknäherung
w(o) = I(Gültigkeitsbereich(o)) * clip(1 − r(o) / r_max, 0, 1)
L_neu = L_BC + λ * mean(w(o) * relu(||δ + Δa @ K||² / ||δ||² − ρ²))
```

K, Fehlerabschätzung, Gültigkeitsbereiche und r_max werden ausschließlich innerhalb der Trainingsdemos festgelegt. Eine demoweise innere Fit-/Prüftrennung verhindert die Bewertung auf denselben Frames wie der Fit. Die äußeren Validierungsdemos und finalen Teststarts bleiben dafür ungenutzt. Ein globaler Fit wird nicht stillschweigend zusätzlich gegen einen lokalen Fit ausgetauscht.

w wird vor dem Policy-Training eingefroren und erhält keine Policy-Gradienten. Die Policy darf das Gewicht nicht selbst verringern. Gewichte und aktive Regularisierungsabdeckung werden protokolliert; ein fast überall null gesetztes w prüft keine wirksame Erweiterung.

Der Gültigkeitsbereich muss auf tatsächlich verfügbaren Daten beruhen. Kontaktflags dürfen nicht als vorhandene Observationen angenommen werden; ein Geometrieproxy braucht eine Prüfung. Vor einem neuen Haupttraining ist außerdem die Reaktionsrichtung der Näherung zu prüfen, möglichst an rekonstruierten Simulatorzuständen mit kleinen kontrollierten Eingriffen. Solche Machbarkeitstests liefern keine neuen Expert-Labels und sind kein Haupttraining. Gute Fehlerwerte auf Demonstrationen allein validieren keine Gegenfaktualdynamik.

**Haupt-Hypothese:** Die Gewichtung verbessert Robustheit gegenüber der konstanten Regularisierung bei erhaltener nominaler Leistung. Vorteile gegenüber reinem BC und schnellere Lernkonvergenz sind zusätzliche, getrennte Fragen.

Wenn Reaktionsrichtung oder sinnvolle Abdeckung fehlen, wird der Kandidat verworfen oder auf einen begründeten Gültigkeitsbereich begrenzt. Dann ist strukturierte Augmentation der einfachere Kandidat. Es folgt keine automatische Parametersuche bis zu einem positiven Ergebnis.

## 6. Vorgehensweise

### Schritt 1: Evidenz und Machbarkeit, zunächst ohne Training

Vorhandenen Lift-Loss, Datenfit und Rohresultate prüfen; fehlende Mechanismus-/Zeitmessungen und mögliche Pilotkontamination dokumentieren. Bereits zur Auswahl benutzte Fälle werden nicht nachträglich als unberührte Testfälle beschrieben.

Für Stack gelten zusätzliche Voraussetzungen: Lift besitzt ein 10-dimensionales Objektmerkmal, Stack hier sechs absolute Positionswerte. Lift-K ist keine Stack-Dynamikmatrix. Stack führt zwei Chunkaktionen aus; eine Ein-Schritt-Näherung darf nicht ungeprüft als Stabilität beider Schritte gelten. Konsistente Perturbation, Stack-spezifische Aktionsantwort und Horizonprüfung sind vor einer Übertragung notwendig.

Die vorgeschlagene Gripper-Sperre kann eine begrenzte Ursachenprobe sein. Sie ist kein neuer BC-Trainingsalgorithmus und nicht automatisch der Kern der Arbeit. Weitere Diffusionsdiagnosen sollen nur eine konkrete Methodenentscheidung klären.

### Schritt 2: Hypothese und Protokoll vor neuen Trainings vergleichen

Schriftlich festlegen: Mechanismus, genaue algorithmische Änderung, Kontrollarme, Daten/splits, Budget, Seeds, Messpunkte, Störungen, primäre Metrik, Abbruchbedingungen und Interpretation negativer Ergebnisse. „Vorgeschlagen“, „implementiert“ und „empirisch bestätigt“ bleiben getrennte Zustände.

Ein Protokoll ist keine zusätzliche Bestätigungsrunde für ausdrücklich beauftragte Experimente, sondern macht sie prüfbar. **Am 04.10.2026 hat der Nutzer den Start dieses Forschungsplans und anschließend einen 30-Minuten-Trigger autorisiert.** Die Machbarkeitsprüfung läuft unter [eingefrorenen Diagnosekriterien](experiments/lift_contraction_validity_20261004/PROTOCOL.md). Ein begrenzter Methodenpilot folgt nur für eine fachlich begründete Hypothese; der abgebrochene Diffusionslauf bleibt beendet.

### Schritt 3: Kleiner, kontrollierter Methodenvergleich

| Arm | Verfahren | Zweck |
|---|---|---|
| B0 | Unverändertes BC | Faire lokale Referenz |
| B1 | BC mit strukturierter Observation-Augmentation | Einfachere Alternative für Sensorrobustheit |
| B2 | BC mit bestehendem konstantem Kontraktionsloss | Kontrolle des vorhandenen Zusatzes |
| B3 | BC mit gültigkeitsgewichteter Kontraktion | Isoliert neue Gewichtung gegenüber B2 |

Zuerst λ=0-Parität, Geometrie, sinnvolle/endliche Gradienten, unabhängige Perturbations-RNG und Logging prüfen. Danach höchstens ein kleiner, vorab begrenzter Entwicklungsvergleich auf separaten Pilotfällen. Erst bei bestandener Machbarkeit folgt ein eingefrorener Vergleich mit mindestens drei gepaarten unabhängigen Trainingsseeds je benötigtem Arm. Seeds messen Unsicherheit; sie sind keine Suche nach einem guten Einzellauf.

Architektur, Trainingsdemos, Normalisierung, Optimizer, EMA, Fenstersampling, Chunkkonvention und Evaluator bleiben im Vergleich gleich. B1/B2/B3 besitzen zusätzliche Rechenkosten, die mitgemessen werden. Daten-/Darstellungsänderungen brauchen eigene Kontrollen. Den konkreten Budgetumfang erst nach kurzer Aufwandsschätzung festlegen, statt pauschal viele 30.000-Update-Jobs zu starten.

### Schritt 4: Wirkung und Aufwand getrennt messen

**Robustheit:** vollständiger nominaler und gestörter Taskerfolg. Bei Stack bleibt der native stabile Stack mit zusätzlichem 40-Schritte-Tail primär. Sensorbias, echte Aktionsimpulse und physische Objektstörungen getrennt auswerten. Dosis und Richtung vorab festlegen; tatsächliche Verschiebungen messen. Nicht ausgelöste phasenabhängige Störungen ausweisen und alle Episoden im Gesamterfolgsnenner behalten.

Neue Teststarts vorab reservieren. Die bekannten 40 Stackstarts sind ein Entwicklungs-/Replikationssatz, nach umfangreicher Methodenauswahl kein unberührter Test. Mindestens eine Richtung oder Stärke wird bei der Auswahl nicht verwendet. Robustheitsbehauptungen gelten nur für die getesteten Störungstypen und -stärken.

**Lerneffizienz:** Aufgabenleistung an denselben vorab festgelegten Update-Messpunkten. Auf einem separaten Evaluationssatz eine Leistungsschwelle und Regel für nachhaltiges Erreichen festlegen, beispielsweise zwei aufeinanderfolgende Messpunkte. Nicht erreichte Schwellen zensiert berichten. Updates und Trainingszeit bis zur Schwelle, Datenfit-/Vorberechnungskosten und Evaluationszeit separat angeben. Ein gleiches Updatebudget und ein separat begrenzter Zeitvergleich beantworten unterschiedliche Fragen. Epochzahlen ohne echte Updates genügen nicht. Messpunkte dienen der Lernkurve; sie erlauben keine nachträgliche Auswahl eines besseren Hauptcheckpoints.

**Mechanismus:** Recovery-Verlauf nach bekannter echter Störung, lokale Modellgüte, Kontraktionsverhältnis und Gewichtsabdeckung ergänzend messen. Ein Demo-Nachbarschaftsabstand braucht festgelegte Merkmale/Skalierung und Kontrolle von Phasenunterschieden. Erfolgsgewinn beweist nicht automatisch den angenommenen Mechanismus.

**Replikation:** pro Trainingsseed berichten; Starts sind innerhalb jedes Seeds gepaart. Rollouts, Frames und Perturbationen sind keine zusätzlichen Trainingsreplikate. Bei wenigen Seeds deskriptive Streuung statt weitreichender Signifikanzbehauptungen. Ein positiver Pilot ist keine robuste Verbesserung.

### Schritt 5: Aussage und Grenzen formulieren

- B3 besser als B0/B2 unter Störung bei erhaltener Nominalleistung: Unterstützung für die getestete Gültigkeitsgewichtung.
- Nur B1 hilft bei Sensorbias: Sensorrobustheit, kein Nachweis physischer Recovery.
- B3 gleich gut wie B2, aber teurer: keine praktische Verbesserung durch die neue Komponente.
- Weniger Updates, längere Zeit: bessere Updateeffizienz, keine schnellere Berechnung.
- Bessere Offlinewerte ohne mehr Taskerfolg: Haupt-Hypothese nicht bestätigt.
- Vorteil nur auf Lift: begrenzter Lift-Befund, Stack-Transfer offen.
- Nominalverlust trotz Störungsvorteil: Trade-off, keine uneingeschränkte Überlegenheit.
- Kein Vorteil: dokumentierter negativer Vergleich; keine nachträgliche Anpassung von Testfällen, Erfolgskriterium oder Checkpointwahl.

## 7. Literatur und mögliche Eigenleistung

Stable-BC motiviert lokale Fehlerdynamik, setzt aber Annahmen an Zustände und Dynamikmodelle voraus. Eine mögliche Eigenleistung wäre die Gültigkeitsprüfung/gewichtete Approximation für robomimic-BC und ihre kontrollierte Evaluation, kein neuer Beweis der Originalgarantie. [Inspektierter Originalvolltext, Abschnitte III–IV](https://arxiv.org/html/2408.06246v1).

DART erhebt Korrekturen durch gestörte Expert-Ausführung; DAgger durch Expert-Labels auf learner-besuchten Zuständen. Beide unterscheiden sich von offline Input-Augmentation. [DART](https://proceedings.mlr.press/v78/laskey17a.html), [DAgger](https://proceedings.mlr.press/v15/ross11a.html).

ACT verbindet Chunking, Ensembling und eine eigene Modell-/Lernformulierung. Da die lokalen Stack-Baselines bereits Chunks verwenden, ist „Chunking hinzufügen“ hier kein eigenständiger neuer Beitrag. [ACT](https://www.roboticsproceedings.org/rss19/p016.html).

Vor Implementierung von B3 folgt ein gezielter Vergleich mit Arbeiten über modellfehler-/unsicherheitsgewichtete Regularisierung und Robustheitsverluste. Bis dahin lautet die Beschreibung **„konkreter Projektvorschlag zur Untersuchung“**, nicht „neu erfundener Stand der Technik“.

## 8. Aktueller Status und nächste fachliche Arbeit

**Elfter Check, Trigger14:39Berlin:** [Lossreferenz und Cacheaudit](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/method_reference_001/RESULT.md) abgeschlossen: konkrete reine7D-/A-/B_local-/w-/epsilon-Tensorfunktion implementiert, keine produktive Registrierung/Trainingsupdates. Numerische Vorprüfung und vier Float64-Parameterableitungen bestanden, NumPygegenprüfung12Frames×4Varianten. Features12/12 passend, B_cache8/12 nach privilegierter Physik; Aktionsregion70/72, Cachefälle48/48 darin. M0gewichtete48/72 versus M2 42/72, Marge aktiviert zusätzliche Lossfälle und ändert Stärke. Parameter/Checkpoint/Dataset unverändert; wissenschaftlich gescheiterte Fehlerhülle bleibt gescheitert. Worker/-Jobs beendet, Coordinator/Heartbeat ACTIVE bis Originaldeadline15:11:19. Letzter konkrete Auftrag [SESSION_CLOSEOUT.md](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/SESSION_CLOSEOUT.md): Gesamtevidenz und Prozess-/Wachhalteende verifizieren, erst nach Deadline pausieren. Kein weiterer Trainingslauf.

**Zehnter Check, Trigger14:09 Berlin:** [Fixierte Fehlermarge](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/error_margin_001/RESULT.md), 336 Zweige, Herstellung12/12, Domain8/12, 8 lokale Fits und null Policyupdates. Marge0.0021163913 aus alten48Trainfällen unverändert; auf 48/72 geplanten Gegenprüfungen 10 Fehlerhüllenverletzungen, falsche Freigaben roh2 / mit Marge0, richtig frei mit Marge4, unnötig verworfen6. Wissenschaftlicher StatusEMPIRICAL_MARGIN_DEVELOPMENT_GATE_FAILED; kein Vergrößern der Marge, kein weiterer Seed-/Schwellensweep oder Training. Lokale Fits/Entscheidungen direkt nachgerechnet, native Queries12/12 reproduziert, Worker/-Jobs beendet. [NEXT_METHOD_REFERENCE.md](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_METHOD_REFERENCE.md) implementiert als nächste begrenzte Arbeit eine isolierte Lossreferenz plus Cache-/Aktionsregion-/Gradientenaudit ohne Updates, kein validierter produktiver Algorithmus. Monitoring/Originaldeadline15:11:19 unverändert; ältere Aufträge unten erledigte Historie.

**Neunter Check, Trigger 13:37 Berlin:** [Frische externe Nähegegenprüfung](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/external_proxy_001/RESULT.md), 336 Zweige, Herstellung12/12, Domain8/12. M2 erfüllt kleines vorab fixiertes Entwicklungsgate (7 richtig akzeptiert, null falsch akzeptiert), verwirft aber einen gültigen Fall zusätzlich; M0 ist auf diesem neuen Satz8/8 richtig akzeptiert und ebenfalls ohne Fehlannahme. Damit kein zusätzlicher Filtervorteil belegt; alte M0-Gegenbeispiele bleiben bestehen. Keine Threshold-/Scopeanpassung und kein Training. Alle nativen Masken/Zustände unabhängig12/12 reproduziert, alle Diagnoseworker/-jobs beendet. [NEXT_ERROR_MARGIN.md](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_ERROR_MARGIN.md) fixiert einen neuen Entscheidungsfehlermargenvergleich auf vier weiteren Demos; empirische Marge ausschließlich aus alten Trainproben, kein allgemeiner Sicherheitsbeweis. Sessioncoordinator/Heartbeat ACTIVE bis unveränderte Deadline15:11:19 Berlin. Ältere konkrete Aufträge unten sind erledigte Historie.

**Neuester Stand, achter Check ab 13:07 Berlin:** [Konservativer Nähefilter](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/clearance_filter_001/RESULT.md) vor Antwortaktionen geprüft, 336 Zweige auf vier neuen Demos. Physische Herstellung 12/12, Domain 8/12; All-Paar-Filter lehnt12/12 ab und ist wegen Nullabdeckung verworfen. Nominale Kontaktfreiheit lässt einen ungültigen Fall durch. Native Querystati und volle nominale Zustände in unabhängiger Neuherstellung exakt reproduziert. Permanente roboterinterne Nähe legt als nächste einmalige Diskrimination [externe versus alle Nähepaare](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_EXTERNAL_PROXY.md) nahe: frische Demos, gleiche 15-mm-Werte, dynamisches Label enthält weiterhin alle tatsächlichen Selbstkontakte. Explorative Aufteilung bestehender Daten dient nur der Hypothesenbildung. Kein methodisches Training aus einem nachträglich passend gemachten Filter; keine robuste BC-Verbesserung etabliert. Gesamtdeadline/Heartbeat unverändert.

**Neuester Stand, siebter Check ab 12:37 Berlin:** [Zustandslokale Antwort](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/local_response_001/RESULT.md) auf vier neuen Demos geprüft: 336 Zweige, Herstellung 12/12, Domain 8/12. Acht lokale Simulatoridentifikationen, keine neuen Policyupdates. Mit unverändertem A: 56,12% weniger medianer Ratiofehler gegenüber festem B7, an 8/8 gültigen Ankern besser; falsche Kontraktionsfreigaben 6→1. Das begründet die Untersuchung einer zustandsabhängigen Dynamikapproximation, beweist aber keine trainierte BC-Verbesserung. Die eine verbliebene Fehlentscheidung zeigt die Bedeutung einer Fehlermarge. Nächster minimaler Gateversuch [vor Loss verfügbarer Nähefilter](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_CLEARANCE_FILTER.md); daneben Unsicherheitsmarge und Gradientenskala offen. Die eigentliche algorithmische Forschungsfrage bleibt eine nachvollziehbar gültigkeits-/fehlergewichtete volle BC-Kontraktionsregularisierung, nicht eine neue Modellarchitektur. Simulatoridentifikation verursacht zusätzlich zu bilanzierende Kosten, bevor ein replizierter Methodenvergleich sinnvoll wird.

**Neuester Stand, 04.10.2026, sechster geplanter Check ab 12:07 Berlin:** [Recorded-Antworttest](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/recorded_response_001/RESULT.md): 672 Simulatorzweige, technische Herstellung 24/24, kontaktfreie Domain 16/24, kein Policytraining. Bei identischen Recorded-Zuständen wirken die zwei kontrollierten Ersatzgeschichten ähnlich; trotzdem sechs falsche B7-Kontraktionsfreigaben je Geschichte auf gültigen Frames. Das beantwortet eine wissenschaftliche Frage zur Übertragbarkeit des Antwortmodells, liefert keinen Trainingsgewinn. Priorität nun [zustandslokale versus feste 7D-Antwort](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_LOCAL_RESPONSE.md), danach praktisch verfügbarer konservativer Gültigkeits-/Fehlerfilter und kontrollierte Gradientenskala. Keine Freigabe eines neuen Kontraktionstrainings. Hauptziel bleibt eine belastbar geprüfte BC-Algorithmusverbesserung; unveränderte Modelle erneut zu trainieren erfüllt es nicht. Die unten beschriebenen älteren Pausierungen/Fehlstarts sind historische Stände; aktuelle Sessionaufsicht ACTIVE bis 15:11:19 Berlin.

Der unveränderte C-Diffusionslauf wurde auf Nutzerwunsch bei **16.800 Updates** beendet. Checkpoint, Konfiguration, Losses und Hashes bleiben erhalten; keine finale Evaluation. Er ist weder eine Methodenverbesserung noch ein vergleichbares 30.000-Update-Replikat. [Abbruchnachweis](experiments/stack_overnight_C_diffusion_20261004/cancellation_verified.json).

**Arbeit seit 04.10.2026:** vorhandene Lift-Kontraktionsmethode samt Kontrollbefunden prüfen, die Dynamiknäherung mit Demo-getrennter Cross-Validation und Aktionsinterventionen untersuchen, die Gewichtung mit Primärliteratur vergleichen. Status und Entscheidungen stehen im [neuen Forschungsordner](experiments/lift_contraction_validity_20261004/PROTOCOL.md). Der 30-Minuten-Trigger verfolgt Fortschritt, Fehler und die nächsten autorisierten Protokollschritte; er startet fehlgeschlagene Trainings nicht automatisch neu.

**Ergebnis der ersten Arbeitsetappe:** [Forschungsbefunde](experiments/lift_contraction_validity_20261004/RESEARCH_STATUS.md). Expert-OLS-K besteht die geprüften Aktionsantworten nicht; kleine Demo-Vorhersagefehler liefern hier kein gesichertes Gültigkeitssignal. Eine explorative partielle Aktionsidentifikation reduziert den Fehler auf vom Fit getrennten Demos, ohne eine Policyverbesserung zu etablieren. Die vollständige Zustandsantwort bleibt ungeprüft; der [nächste diskriminierende Versuch](experiments/lift_contraction_validity_20261004/NEXT_EXPERIMENT.md) trennt A und B vor Policy-Training. Der separate Sensor-Pilot scheiterte beim Runtimeimport vor Update 1; Vorbereitung ohne Training repariert, kein Ersatzlauf. Aktuell kein Training aktiv.

Der eingerichtete 30-Minuten-Trigger ist nach Ende dieser begrenzten Arbeitsetappe pausiert. Der nächste Methodenlauf muss ein frisches Verzeichnis verwenden; kein automatischer Retry des fehlgeschlagenen Piloten.

### Neue Autorisierung am 04.10.2026, morgens

Der Nutzer hat anschließend ausdrücklich die Fortsetzung für sechs Stunden mit aktivem 30-Minuten-Trigger und technischer Fehlerbehebung samt erneutem Start nach Fehlstart beauftragt. **Diese neuere Anweisung ersetzt die bisherigen No-Retry-/Pausierungsregeln für technische Fehler dieser Session.** Wissenschaftlich negative Ergebnisse sind kein Retrygrund; Hypothese, Split, Seed, Updatebudget und Machbarkeitsgates bleiben verbindlich.

Aktive Session: [SESSION_PROTOCOL.md](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/SESSION_PROTOCOL.md). Gesamtdeadline: 04.10.2026, 15:11 Uhr Berlin. Kontrollierter BC/Sensor-Augmentation-Pilot, je 2.000 Updates, neue Versuchsverzeichnisse; vollständige GPU-/Simulator-Vorprüfung. Der lokale Coordinator kontrolliert Worker alle fünf Sekunden; der App-Agent alle 30 Minuten mit getrennten Checkprotokollen. Beide bleiben auch nach Fehlstart aktiv. Nach Pilotende folgen Auswertung und fachlich begründete Diagnose, kein bloßes Füllen der Zeit mit weiteren Trainings. Alle Fehler und früheren Ergebnisse bleiben erhalten.

**Neue Session, verifizierter Pilotabschluss um 09:26 Uhr:** Beide Arme haben exakt 2.000 Updates und die festen 104 Evaluationsepisoden abgeschlossen. BC/Augmentation: nominal 4/10 gegen 3/10; Sensorbias insgesamt 6/20 gegen 8/20; echter Aktionsimpuls jeweils 3/10. Ein Seed und ein kleiner Trade-off: kein robuster Verbesserungsnachweis, keine nachgewiesene schnellere Konvergenz. [Auswertung und nächster Agentauftrag](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/PILOT_INTERPRETATION.md). Die aktive Überwachung bleibt bis zur ursprünglichen Deadline eingeschaltet; die A/B-Mechanismusdiagnose ist der nächste Schritt, kein weiteres unverändertes Training.

**Erster geplanter Agentcheck ab 09:38 Uhr:** [Physische A/B-Diagnose abgeschlossen und unabhängig verifiziert](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/mechanism_AB_002/RESULT.md), einschließlich konkret repariertem Solver-Warmstart-Fehler in einem frischen Versuchsordner. Keine neuen Trainingsupdates. A≈I ist an den geprüften frühen freien Ankern kompatibel; Expert-OLS-K passt weiterhin nicht zur partiellen Aktionsantwort. Die 3D-Näherung lässt Rotations-/Gripperreaktionen der vollen Policy aus. Nächster Schritt: [vollständige 7D-Aktionsantwort auf neuen Demos](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_ACTION_RESPONSE.md), vor weiterem Methoden-Training. Die Aufsicht bleibt bis zur ursprünglichen Deadline aktiv.

**Zweiter geplanter Agentcheck ab 10:08 Uhr:** [7D-Diagnose abgeschlossen und unabhängig verifiziert](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/mechanism_action7_001/RESULT.md), 408 Zweige auf neuen Demos ohne Training. Die bisher ausgelassene Rotationsantwort verbessert die lokale Ein-Schritt-Ratio-Vorhersage bei gleicher A-/Translationskalibrierung; medianer Fehler um 91,9% geringer, 6/6 Gegenprüfungsanker besser. Das ist keine Trainingsverbesserung. Der konkret begründete BC-Losskandidat berücksichtigt volle Aktionsdifferenzen und ein kausal kalibriertes B_7; Domain/Verlustskala bleiben zu prüfen. [Nächste Diskrimination](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_CORRECTION_PROBE.md): aus Modellen berechnete Korrekturen auf neuen Demos physisch ausführen, bevor neue Policies trainiert werden. Die Aufsicht bleibt ACTIVE bis 15:11:19 Berlin.

**Dritter geplanter Agentcheck ab 10:39 Uhr:** [Korrekturtest auf vier neuen Demos](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/mechanism_correction_001/RESULT.md), 312 physisch verifizierte Zweige. Reiner Aggregationsfehler gezielt aus gespeicherten Rohdaten repariert; Originalworker FAILED bleibt dokumentiert, keine neue Simulation/kein Training. Die volle Aktionsantwort verringert den Fehler der realisierten Ratio-Vorhersage um 88,9%, an 12/12 Ankern. Beide kalibrierten Korrektoren erreichen 72/72 Ein-Schritt-Schwellen; die volle Variante braucht mehr Kommandonorm. Deshalb keine überlegene Recovery oder BC-Methode daraus ableiten. Als nächstes [Gradientenskalen prüfen](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_GRADIENT_AUDIT.md), damit ein späterer Methodenvergleich keine bloße Regularisierungsstärkenänderung verschleiert. Domainabdeckung, Labelsemantik und replizierte Trainingsgewinne bleiben offen. Monitoring weiter ACTIVE bis zur Originaldeadline.

**Vierter geplanter Check, Trigger 11:07 Uhr:** [Gradientenaudit abgeschlossen und unabhängig verifiziert](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/gradient_audit_001/RESULT.md), 60 aufgezeichnete Frames, keine Optimizerkonstruktion und unveränderte Parameter. B_7 verändert Gradientennorm/Richtung abschnittsabhängig; gegenüber OLS etwa 1,06/1,09-fach früh und 4,07/2,77-fach später (Train/Valid). Deshalb ist eine Kontrolle der effektiven Regularisierungsstärke Bestandteil eines späteren BC-Methodenvergleichs, kein aus diesen Daten gewähltes Training. Als nächstes [physische Domainabdeckung prüfen](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_DOMAIN_PROBE.md). Replay-/Labelsemantik und eine im BC-Batch verfügbare Gültigkeitsregel bleiben offen. Hauptaussage zur fehlenden robusten BC-Verbesserung unverändert; Aufsicht bis 15:11:19 Berlin ACTIVE.

**Fünfter geplanter Check, Trigger 11:37 Uhr:** Zwei notwendige Diagnosen direkt nacheinander, keine neuen Trainings. [Live-Domainprobe](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/mechanism_domain_001/RESULT.md): technische Zustandskontrollen 12/12 bestanden, Kontakt-Domain nur 8/12; vier späte Kontaktfälle bleiben im Nenner und sind kein Retrygrund. Volle kalibrierte Antwort besteht an gültigen frühen/mittleren Ankern, damit keine globale Kontaktaussage. Eine statische Startkontaktregel lässt einen erst im nächsten Schritt entstehenden Kontakt durch. [Recorded-Frame-Zuordnung](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/recorded_domain_001/RESULT.md): Geometrie an 60/60 bekannten Auditframes passend, 49/60 statisch kontaktfrei; ein Teil des ungewichteten Lossgradienten betrifft nicht geprüfte Kontaktdynamik. Annotation ist technisch verfügbar, dynamische Gültigkeit und Expertgeschichte bleiben offen. [Nächste Gegenprüfung](experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_RECORDED_RESPONSE.md): Antwortübertragung auf aufgezeichnete Zustände unter zwei bekannten Ersatzgeschichten. Kein automatisch gestartetes Training, Hauptaussage unverändert; Monitoring bis Originaldeadline ACTIVE.
