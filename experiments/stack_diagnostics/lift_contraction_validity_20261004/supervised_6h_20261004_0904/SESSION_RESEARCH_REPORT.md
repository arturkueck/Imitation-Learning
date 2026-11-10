# Ergebnis der beaufsichtigten BC-Forschung

Fachlicher Stand 2026-10-04T14:59:48.085497+02:00. Sessionfenster **04.10.2026,09:11:19–15:11:19 Berlin**, unverändert sechs Stunden. Forschungsarbeit ausgewertet; organisatorischer Abschluss mit tatsächlichem Prozess-/Wachhalteende wird nach Deadline separat unten ergänzt. [Sessionprotokoll](SESSION_PROTOCOL.md), [operative Endprüfung](SESSION_CLOSEOUT.md). Der alte [Pilotbericht](RESULT.md) bleibt erhalten.

**Hauptaussage:** Das Projekt besitzt begrenzte historische Lift-Taskgewinne einer Kontraktionsregularisierung. Die jetzige Arbeit identifiziert konkrete Fehler ihrer lokalen Dynamikapproximation und implementiert einen korrigierten Lossentwurf. **Eine robuste neue BC-Algorithmusverbesserung, schnellere Trainingskonvergenz und eine Erklärung des Direct-vs-Diffusion-Gaps sind weiterhin nicht etabliert.** Der neue Sensorvergleich ist genau ein Trainingsseed; alle nachfolgenden Simulatorzweige benutzen eingefrorene Checkpoints und sind keine zusätzlichen Trainingsreplikate.

## 1. Primärliteratur, getrennt von Projektbefunden

Die Originalarbeiten wurden vor Implementationsentscheidungen geprüft und für diese Synthese erneut am 04.10.2026 gelesen. Externe Resultate übertragen sich nicht automatisch auf diesen Lift-/Stack-Aufbau.

| Originalarbeit | Allgemeiner Beitrag | Konsequenz für dieses Projekt |
|---|---|---|
| [Stable-BC, Mehta et al.2024, Abschnitte III–IV](https://arxiv.org/html/2408.06246v1) | Modelliert gekoppelte lokale Fehlerdynamik und formuliert modellbasierte bzw. eingeschränkte modellfreie Stabilitätsbedingungen; nimmt bekannte Roboterdynamik voraus. | Unser diskreter finite-Differenz-Loss auf EEF-Position mit empirischem A/B prüft nicht sämtliche Eigenwert-/Kopplungsbedingungen des Papers. Keine Übernahme seiner Garantie. Die dortige Konvergenz der Zustandsfehler ist außerdem kein Nachweis weniger Optimizerupdates. |
| [CCIL, Ke et al., Abschnitte 4.2–4.3 und Appendix B](https://arxiv.org/html/2310.12972v2) | Lernt lokal kontinuierliche Dynamik, erzeugt korrigierende Labels und begrenzt deren Fehler unter lokalen Annahmen; behandelt ungeeignete Bereiche gesondert. | Fehler-/Gültigkeitsgewichtung ist eine bestehende Idee. Expert-OLS-Gain und Kontaktfreiheit ersetzen die erforderliche lokale Genauigkeitsprüfung nicht. |
| [Deshpande et al.2024, Abschnitte IV-C/IV-D](https://arxiv.org/html/2405.19307v1) | Untersucht CCIL in feiner Manipulation; im dortigen Versuch können schlechte generierte Labels Leistung verschlechtern. Labelqualität und zusätzliche Datenabdeckung bilden einen Trade-off. | Begründet die Messung von Fehlannahmen **und** Abdeckung; belegt weder Schaden noch Nutzen unseres noch untrainierten Losskandidaten. Kontakt ist auch kein universeller Ausschluss aller möglichen lernbaren Dynamikmodelle. |
| [DART, Laskey et al.2017](https://proceedings.mlr.press/v78/laskey17a.html) | Stört Expert-Ausführung bei der Demonstrationsaufnahme und passt den Störungsumfang an Lernerfehler an. | Unsere bestehende Offline-Sensoraugmentation erhebt keine echten Experten-Recoveryaktionen; anderes Label-/Datenregime. |
| [DAgger, Ross et al.2011](https://proceedings.mlr.press/v15/ross11a.html) | Aggregiert Expertlabels auf von der lernenden Policy besuchten Zuständen. | Benötigt zusätzliche Expertabfragen; kein solcher Zugang in den jetzigen Offlineproben. |
| [ACT, Zhao et al.2023](https://www.roboticsproceedings.org/rss19/p016.html) | Verbindet Actionchunking mit temporalem Ensembling für feine Manipulation. | Bestehende Stack-Baselines nutzen bereits Chunks. ACT-Erfolg erklärt den lokalen Direct-/Diffusion-Vergleich nicht kausal. |

Mögliche Eigenleistung: überprüfbare, kostenbilanzierte volle und zustandsabhängige Dynamikregularisierung unter expliziten Gültigkeits-/Fehlerannahmen. Neuheit ist **nicht** durch einen B7-Fit oder die allgemeine Regularisierungs-/Recoveryidee nachgewiesen. Erst saubere Abgrenzung zu Literatur und replizierter Nutzen tragen einen wissenschaftlichen Verbesserungsanspruch.

## 2. Verifizierte historische Projektergebnisse

[Separater Rohdaten-/Hashaudit](../legacy_verification.json): drei alte Lift-Trainingsseeds. Bei 10000 Updates nominal BC 44/60 versus bestehende Kontraktion 56/60; unter +2 cm Offset 47/60 versus 55/60, unter −2 cm 37/60 versus 57/60; +Impuls 41/60 versus 59/60, −Impuls 48/60 versus 55/60. Bei 2000 Updates nominal 23/60 versus 36/60. Die älteren 2000 Update-Auswertungen haben 180 fehlende Initialzustands-Paarmetadaten; spätere Auswertungen prüfen gepaarte Starts. Das sind lokale Taskbefunde der bestehenden Methode, keine etablierte Erklärung ihres Mechanismus, keine ausaggregierten 60 unabhängigen Trainingsreplikate und kein Zeitkonvergenznachweis.

Expert-OLS-K sagt Demonstrationsübergänge vergleichsweise gut voraus, besteht aber die geprüfte partielle Aktionsantwort nicht. Die Schlussfolgerung „Zustands-/Aktionskorrelation ersetzt keine kontrollierte kausale Aktionsintervention“ ist durch Projektinterventionen gestützt. Welche verborgenen Zustands-/Controllergrößen die gesamte Abweichung erklären, bleibt offen. [Vorherige Forschungsetappe](../RESEARCH_STATUS.md).

Der frühere unveränderte Stack Two-C-Diffusionslauf wurde auf Nutzerwunsch bei **16800 Updates** abgebrochen, Checkpoint/Logs/Hashes erhalten, keine finale Evaluation. [Abbruchnachweis](../../stack_overnight_C_diffusion_20261004/cancellation_verified.json). Er bleibt beendet. Lift-Nativerfolge sind keine stabilen Stacks; weder dieser Abbruch noch die folgenden Lift-Diagnosen beantworten den Direct-vs-Diffusion-Gap.

## 3. Ein neuer Trainingsseed: BC versus Sensoraugmentation

`attempt_002`, Seed 41004,180/20 Lift-PH-Demos, gleiche 256×256 Policy/Adam 1e-4/Batch 100; identische Anfangsgewichte und gesamte Trainingsbatchreihenfolge. Jeder Arm **genau 2000 Optimizerupdates**, alle 104 Evaluationsepisoden komplett. Keine anhand von Evaluation gewählte Zwischencheckpointauswahl. Verifiziert 302 Source-/Konfigurationsdateien und 916 Runtimeassets bei Pilotabschluss; [Nachweis](verification_1791098800.json), [effektive Konfigurationen/Checkpoints](attempts/attempt_002), [Rohzusammenfassung](pilot_summary.json).

Sensorarm:50%sauberer BC-Loss und 50%gleicher Expertenaktion unter zufälliger 5 mm EEF-Messstörung, abgeleitetes Objekt-minus-EEF-Feature passend geändert; keine physisch verschobene Expertaufnahme. Separate Noise-RNG schützt Batchpaarung. Keine neue Policyarchitektur.

| Finale Bedingung, feste Starts | BC | Augmentation |
|---|---:|---:|
| Nominal |4/10|3/10|
| Sensorbias+5 mm |3/10|4/10|
| Sensorbias−5 mm |3/10|4/10|
| Tatsächlicher Aktionsimpuls |3/10|3/10|

Sensor 6/20→8/20 bei nominalem Verlust; die 20 Fälle sind zwei Bedingungen auf denselben 10 Starts, nicht 20 unabhängige Trainingsreplikate. Kleine vorab fixierte Entwicklungsregel genau erfüllt, keine robuste Überlegenheit. Nominale Lernkurve der ersten 6 Starts für beide 0/6 bei 500,0/6 bei 1000,1/6 bei 2000; nachhaltige 4/6 Schwelle von keinem erreicht, beide zensiert. **Kein schnellere-Konvergenz-Nachweis.** Trainingszeit 8.859s BC/11.391s Augmentation, Evaluation 182.095s. Letzter Loss 0.04073427/0.04005975; unterschiedliche Ziele, deshalb kein eigenständiger Verbesserungsnachweis aus diesen Losswerten.

Dataset-SHA 256 `2067777cb8b532e9263dd09fd6448c41cc31224bb27be4a3b734010ae13eb540`; B0-Endcheckpoint `27a38fc65415d419a060cd0fc529f8f30d82bc36cdf77d54cc79d7a3e52117fa`, B1 `0850c472342f79bada30dde6b7e2f9cbf0d106b0fd76144f41eb0177f404d6e9`. Losskurven, effektive Configs und vollständige Checkpointmanifeste in den Armen. Technischer attempt_001 scheiterte vor Training an abgeleiteten Configschlüsseln; korrigiert mit frischem Preflight und Versuch, ursprüngliche Artefakte erhalten.

## 4. Mechanismusbefunde, keine weiteren Trainingseeds

| Frage | Verifizierter eigener Befund | Tragweite |
|---|---|---|
| Passt Expert-OLS als Aktionsgain? | [A/B-Diagnose](mechanism_AB_002/RESULT.md): OLS 0/18, frühere partielle Kalibrierung 18/18, neuer Fit 18/18 auf getrennten Prüfdemos. | Partielle kausale Aktionsantwort, keine Policyverbesserung. Technisch reparierte Wiederholung mit bereits gesehenen Ankern kein neuer unberührter Bestätigungssatz. |
| Fehlt Rotation? | [Volle 7D-Antwort](mechanism_action7_001/RESULT.md): bei gleichem A/Translationsfit 91.9%weniger medianer Ratiofehler,6/6 Prüfanker besser; Gripper früh degeneriert. | Unterstützt Einbeziehung der Rotation, keine 91.9%Taskverbesserung. |
| Verbessert genauere Vorhersage die tatsächliche Korrektur? | [Korrekturtest](mechanism_correction_001/RESULT.md):88.9%weniger Ratiofehler, aber beide kalibrierten Korrektoren 72/72 Ein-Schritt-Schwellen; volle Variante braucht mehr Kommandonorm. | Kein besseres Recoveryverhalten gegenüber Translationskontrolle etabliert. |
| Ist gleicherlambda ein fairer Vergleich? | [Gradientenaudit](gradient_audit_001/RESULT.md): B7/OLSNormquotient spät 4.07 Train/2.77 Valid, früh 1.06/1.09. | Stärke/Richtung verändern sich abschnittsabhängig; zusätzlich kontrollieren. |
| Gilt Kalibrierung für alle Phasen? | [Live-Domain](mechanism_domain_001/RESULT.md): Herstellung 12/12, Domain 8/12; alle 4 späten Kontakte. [Statische Zuordnung](recorded_domain_001/RESULT.md):60/60 geometrisch passend,49/60 statisch frei. | Gültigkeit nur konditional; statische Annotation kein dynamischer Beweis. |
| Erklärt kontrollierte Controllergeschichte die Übertragungsfehler? | [Zwei Ersatzgeschichten](recorded_response_001/RESULT.md):672 Zweige,24/24 hergestellt,16/24 frei; ähnliche Antworten, trotzdem sechs falsche B7-Freigaben je Geschichte. | Diese beiden Historien erklären den Fehler nicht hinreichend; Originalexpertgeschichte nicht rekonstruiert. |
| Hilft lokale statt feste B7? | [Neue lokale Identifikation](local_response_001/RESULT.md):56.12%weniger Fehler,8/8 Anker besser, falsche Freigaben 6→1. | Zustandslokalität gestützt, lokale Simulator-/Cachekosten nötig, Restfehler bleibt. |
| Liefert ein vorab verfügbarer Filter ausreichend Coverage? | [Alle Nähepaare](clearance_filter_001/RESULT.md):0/12 akzeptiert. [Externer Proxy](external_proxy_001/RESULT.md):7 gültigakzeptiert,0 falsch,1 gültigverworfen; einfacher Kontaktflag hier besser. Spätere [neue Probe](error_margin_001/RESULT.md) hat M0 eine Fehlannahme, M2 keine bei gleicher 7/12 Abdeckung. | All-Paar-Regel verworfen, externer Filter begrenzter Trade-off statt universeller Garantie. Tatsächliche Selbstkontakte im Label unverändert. |
| Überträgt sich eine empirische Fehlerhülle? | [Neue Demos](error_margin_001/RESULT.md): alteepsilon 0.0021163913,10/48 gültige Antworten überschreiten Grenze; falsche Freigaben 2→0, richtige Freigaben 10→4. | Vorab fixiertes Entwicklungsgate **verfehlt**; kein Vergrößern/Retuning aus Prüfoutcomes. |
| Ist der konkrete Lossentwurf berechenbar? | [Referenz](method_reference_001/RESULT.md):7D/A/B_local/w/epsilon implementiert, Num Pyprüfung und 4/4 Parameterableitungen bestanden; Policyfeatures 12/12 passend, privilegierter B_cache 8/12, effektive Coverage M0 48/72/M2 42/72. | Rechenbarkeit bestätigt; produktiver Algo unverändert, gescheiterte Fehlerhülle und Trainingsgates bleiben offen. |

Echte körperliche 5 mm EEF-Perturbationen, feste Orientierung/Geschwindigkeit/Objekt/Gripper/Controller-/Auxiliarzustände und Kontakt/Wiederholungsgates geprüft. Fehler-/Kontaktfälle bleiben in geplanten Nennern; keine wissenschaftlich negativen Frames ersetzt. Gegenprüfungsdemos jeweils vorab disjunkt von bis dahin verwendeten Daten; posthoc Exploration und reparierte technische Wiederholung gesondert markiert. Ein gefrorener BC-Checkpoint, keine breit replizierte Policyfamilie.

## 5. Geranktes Hypothesenledger und Forschungsentscheidung

| Rang | Hypothese | Status / nächstes diskriminierendes Ergebnis |
|---:|---|---|
|1|Die verbleibende feste offene Zustandsantwort A begrenzt die enge Fehlerentscheidung.|Lokales B verbessert; Restfehler/gescheiterte Hülle bleiben. Frühes A≈I widerspricht großem grobem Fehler, schließt entscheidungsrelevante kleine lokale Fehler nicht aus. Lokal identifiziertes A gegen gleichesfestes A bei gleichem B_local auf neuen Demos testen. **Noch Hypothese.**|
|2|Volle und zustandslokale Aktionsantwort verhindert falsche Lossbewertung.|Rotation und B-Lokalität in mehreren kleinen Interventionstests gestützt. Preiswerte breite Cacheversorgung/Aktionsdomain bei weitertrainierter Policy ungeprüft.|
|3|Verfügbares Domaingewicht und übertragbare Fehlergrenze erlauben nützliche Regularisierung.|All-Paar Filter verworfen, extern begrenzte Coverage/Trade-off. Endliche globale Fehlerhülle scheitert; keine Trainingsfreigabe.|
|4|Ein Nutzen des Losswechsels kann bloß geänderte Gradientenstärke sein.|Stärkeunterschiede gemessen; passende Kontrollbedingung erforderlich. Noch kein neuer Trainingseffekt zur Erklärung.|
|5|Sensoraugmentation liefert robuste Recovery oder schnellere Konvergenz.|Ein Sensorpilot zeigt kleinen Biasvorteil/nominalen Verlust, echter Impuls gleich, Kurven zensiert. Keine Unterstützung für diese stärkeren Aussagen.|
|6|Mehr unverändertes Diffusionstraining erklärt/verbessert BC.|Kein Algorithmenvergleich, auf Nutzerwunsch abgebrochen. Wird nicht verfolgt.|

Minimaler **nächster Versuch außerhalb dieser Session**, noch nicht gestartet: vier neue Train-Demos vorab aus dem 180/20 Split fixieren, je 10/50/85%Frame, eingefrorenes B0; gleiche 336 Zweige. B_local aus 14 nominalen Aktionsinterventionen, A_local aussechsnominalenphysischen Zustandsinterventionen, getrennte Pfull-Zweige prüfen. Primär einzig A_frozen/B_local gegen A_local/B_local, gleiche alte Fehlerhülle/Schwelle, vollständige Coverage/Kontakt-/Klassifikations-/Vektorfehler-/Kostenangaben. Gegenprüfung ist von A/B-Identifikationszweigen getrennt. Kein nachträgliches Erhöhenepsilon; Rang-/Gatefehler erhalten. Das isoliert die Zustandsapproximation, statt ein unverändertes Modell erneut zu trainieren. Vor Launch konkretes Protokoll/Seed/Quelle/Entscheidungsregel einfrieren; dieser Bericht ist eine Empfehlung, keine automatisch eingeplante neue Session.

Erst bei tragfähigen Domain-/Fehler-/Kosten-/Cache-/Aktionsregiongates: vorab budgetierter gepaarter Methodenvergleich mit mehreren Trainingsseeds, gleichem Demosplit/Initialgewichten/Batches/Starts/Updatebudget. Neue Regularisierung gegen BC und bestehende Kontraktion sowie eine Kontrolle der effektiven Gradientenstärke. Sensorbias und tatsächliche Aktionsstörung separat, Taskerfolg/Teilphasen sowie Update-/Gesamtzeitkurven getrennt; gesamte Simulatoridentifikation mitzählen. Kein Best Checkpoint nach Evaluation. Auf Stack separat stabile Stackmetriken/feste 40 Starts prüfen, Lift Erfolg nicht als Stackerfolg ausgeben.

## 6. Zusatzkosten, Fehler und Nachvollziehbarkeit

| Diagnose | Primärworker s | Primärsupervisor s | Unveränderter Rohstatus |
|---|---:|---:|---|
| [mechanism_AB_001](mechanism_AB_001/RESULT.md) | 165.453 | 168.143 | COMPLETE |
| [mechanism_AB_002](mechanism_AB_002/RESULT.md) | 165.485 | 168.144 | COMPLETE |
| [mechanism_action 7_001](mechanism_action7_001/RESULT.md) | 235.531 | 238.208 | COMPLETE |
| [mechanism_correction_001](mechanism_correction_001/RESULT.md) | 167.609 | 170.145 | FAILED |
| [gradient_audit_001](gradient_audit_001/RESULT.md) | 2.828 | 6.012 | COMPLETE |
| [mechanism_domain_001](mechanism_domain_001/RESULT.md) | 208.672 | 210.187 | DOMAIN_GATE_FAILED |
| [recorded_domain_001](recorded_domain_001/RESULT.md) | 24.140 | 26.030 | COMPLETE_STATIC_AUDIT |
| [recorded_response_001](recorded_response_001/RESULT.md) | 567.516 | 570.483 | DOMAIN_GATE_FAILED |
| [local_response_001](local_response_001/RESULT.md) | 191.406 | 194.187 | DOMAIN_GATE_FAILED |
| [clearance_filter_001](clearance_filter_001/RESULT.md) | 195.578 | 198.170 | DOMAIN_GATE_FAILED |
| [external_proxy_001](external_proxy_001/RESULT.md) | 195.718 | 198.169 | DOMAIN_GATE_FAILED |
| [error_margin_001](error_margin_001/RESULT.md) | 197.344 | 200.175 | DOMAIN_GATE_FAILED |
| [method_reference_001](method_reference_001/RESULT.md) | 2.640 | 6.013 | REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE |

Diese Tabelle zählt Primärworker/aufsicht; nicht addieren, weil Supervisorzeit Workerzeit einschließt. Alle **27** gespeicherten Diagnose-Supervisorjobs einschließlich Vorprüfungen, technischer Fehlversuche und unabhängiger Verifikation zusammen **2452.249s**; [vollständiges Kosteninventar](research_cost_inventory.json). Nicht vollständig instrumentierte Foreground Vorbereitung/Analyse und alle Setupforwards sind darin nicht erschöpfend enthalten; daher kein vollständiger End-to-End-Laufzeitbenchmark. Pilottraining/Evaluation separat. Viel höherer Kalibrieraufwand als 20.25s Pilottraining verhindert schon jetzt eine Behauptung allgemeiner Beschleunigung aus Trainingssekunden allein.

Technische Negativeerhalten: attempt_001 Configvorstart; mechanism_AB_001 verändertes Solverwarmstart undfrische Reparatur; mechanism_correction_001 Aggregation erst nach 312 Zweigen, reine Analyse-Reparaturenohne Physikwiederholung; recorded_response Vorprüfungsmetadaten; clearance Vorprüfungen mit nichtberechneten nativen Insel-/Dual Arbeitsarrays und dokumentierterkonditionaler Hashkorrektur; error_margin Phase Nenner 72→24 ausschließlich Metadaten in frischem Ordner. Keinefachliche Gate-/Marginlockerung. [Agentchecks](agent_checks.jsonl) protokollieren nur tatsächliche Agentaufrufe; [lokale Checks](monitor_checks.jsonl) sind getrennt. Immediate 09:26 Prüfung ist scheduled:false. Keinebehaupteten Agentchecks aus lokalen Watchdogticks.

Aktuell alle Forschungsworker/-jobs beendet, organisatorische Sessionaufsicht bleibt bis 15:11:19 Berlin ACTIVE. Der tatsächlicheoperative Schlussnachweis wird nach Deadline ergänzt. Quellen/Configs/Dataset/Seeds/Updatecounts/Losses/Startpaarungen/Checkpointhashes sind in denverlinkten Immutable Artefakten dokumentiert. Ein späterer final_verification_-Nachweis prüft Ende und Provenienz, ohne alte Berichte oder Checkpoints zu überschreiben.


## Tatsächlicher operativer Abschluss

Geprüft 2026-10-04T15:13:50.446909+02:00: WINDOW_FINISHED nach unveränderter Deadline, Coordinator und Launcher beendet, alle 27 gespeicherten Diagnoseworker/-Supervisoren beendet und Jobs geschlossen; Pilotworker nicht aktiv. Wachhalteanforderung durch Coordinatorfinally freigegeben und Prozessende verifiziert. Quellen 302 Pilotdateien/916 Runtimeassets/145 Diagnose-Sourceeinträge, Dataset/Endcheckpoints/Updates/Losszeilen/Batch-/Startpaarungen und104Episoden erneut geprüft. [Abschlussnachweis](final_verification_1791119630.json). Automation wird erst nach dieser Prüfung pausiert; Bestätigung separat in automation_closeout.json. Keine weitere Training-/Simulatorrunde.


### Überwachung nach Abschluss pausiert

App-Rückmeldung und gespeicherter PAUSED-Status nach dem finalen Prozess-/Provenienzaudit geprüft; andere Automationsfelder unverändert. Dokumentiert 2026-10-04T15:15:45.459954+02:00. [Automationsabschluss](automation_closeout.json). Keine laufenden Sessionworker, Supervisoren, Coordinator oder Launcher; Wachhalteanforderung freigegeben. Der Abschluss bestätigt den technischen Ablauf, keine robuste neue BC-Verbesserung. Kein weiterer Lauf gestartet.
