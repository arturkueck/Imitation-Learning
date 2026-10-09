# Physischer Korrekturtest: Ergebnis und technische Reparatur

Der vorab festgelegte lokale Modellvergleich besteht: C3 (volle 7D-Antwort) reduziert den medianen absoluten Ratio-Vorhersagefehler nach tatsächlich ausgeführter Translationskorrektur gegenüber C2 (gleiche A-/Translationskalibrierung) um **88,90%**, von 0,0034693 auf 0,0003851; an **12/12** Ankern geringer. Die vorab bestimmten Grenzen waren mindestens 20% und 8/12. Das ist eine lokale Modellgüteverbesserung, keine trainierte BC-Verbesserung.

| Arm | Reale Ratio ≤0,99 | Median reale Ratio | Median Ratio-Vorhersagefehler | Median Korrekturnorm |
|---|---:|---:|---:|---:|
| C0 unveränderte BC-Aktion | 24/72 | 0,998815 | 0,00028446* | 0 |
| C1 Expert-OLS-K / I | 46/72 | 0,988816 | 0,00881562 | 0,006295 |
| C2 kalibriertes A / B_xyz | 72/72 | 0,978641 | 0,00346930 | 0,016646 |
| C3 kalibriertes A / B_7 | 72/72 | 0,979906 | 0,00038510 | 0,021438 |

*C0 hat keine Korrektur; sein Metadatenprädiktor verwendet A/B_7. Deshalb ist sein kleiner Fehler kein unabhängiger alternativer Modellnachweis. Der primäre Vergleich bleibt C3 gegen C2 nach Korrektur.

Alle drei Korrekturarme verbessern die reale Ratio gegenüber C0 in allen 72 Paaren. Kein Normlimit erreicht, kein Clipping, keine verworfenen Fälle. **C2 und C3 erreichen dieselben 72/72 Fälle**, C2 hat sogar die niedrigere aggregierte Medianratio; C3 benötigt etwa 28,8% mehr mediane Kommandonorm. Eine genauere Zielvorhersage bedeutet hier keine nachgewiesene überlegene tatsächliche Kontraktion oder günstigere Intervention. Ein möglicher BC-Nutzen müsste später separat gemessen werden.

## Daten, Kontrollen und Grenzen

[Vorab fixiertes Protokoll](PROTOCOL.md), Seed 4100404, neue Gegenprüfungsdemos demo_179/demo_188/demo_95/demo_12; je drei frühe Live-Präfixanker. Alle vier nur Gegenprüfung, kein neuer Matrixfit. Eingefrorener B0-Pilotcheckpoint, kalibriertes A/B_3/B_7 ausschließlich aus demo_59/demo_152 des früheren action7-Versuchs. Die 72 Störungen sind sechs Bedingungen je Anker auf vier Demos, keine 72 unabhängigen Trainingsseeds.

Identische physische Starts und BC-Basisaktionen; ausschließlich xyz-Zusatzkommandos, unveränderte Rotation/Gripper. Echte ±5-mm-EEF-Zustandsänderungen bei kontrollierter Orientierung/Geschwindigkeit, Objekt, Gripper und Controllerhistorie. Alle zwölf internen Gates bestanden; unabhängige [physische Prüfung](verification.json) bestätigt sämtliche **312 Zweige**, vollständige Zusatzfelder einschließlich Solver-Warmstart und beendete Prozesse. Das neue Rechenaudit reproduziert tatsächliche Aktionen und Modellvorhersagen mit maximaler Differenz **0**. Kontaktfreie frühe Zustände; keine Aussage über spätere Kontakt-/Greifphasen, mehrschrittige Recovery oder stabile Stacks.

Der Test nutzt die bekannte Störung und den ungestörten Referenzzweig: Oraclezugriff, kein einsatzfähiger Onlinecontroller. Er belegt weder gültige Expertlabels an diesen Zuständen noch die Reproduktion der ursprünglichen Datenaufnahme. Die modellbasierte Korrekturidee ist bestehende Forschung ([CCIL, Primärquelle](https://arxiv.org/html/2310.12972v2)); der eigene Projektbefund ist die kontrollierte Gegenprüfung einer konkreten Approximation. Kein Neuheits- oder Stabilitätsbeweis.

## Exakter technischer Status

Der Originalworker bleibt **FAILED, Exitcode 2**: Nach Abschluss aller Simulatorzweige verursachte die Ergebnisaggregation `dict(... predicted_ratio=..., **info)` einen doppelten Schlüssel. [Originalfehler und Rohdaten](result.json) sowie [Log](worker.log) und unveränderte gehashte Quellen bleiben erhalten. Supervisor und Worker sind beendet; Job geschlossen, keine eigene Wachhalteanforderung.

Nur Nachverarbeitung wurde repariert, in frischen Unterordnern: `analysis_repair_001` verwarf eine falsche float32-Annahme; Quellcode und Fehlernachweis erhalten. [analysis_repair_002](analysis_repair_002/analyze.py) nutzt die tatsächliche gespeicherte Präzision und prüft Korrekturlösung, Normbegrenzung, Clipping, Aktionen, Vorhersagen, Datenaufteilung und Kalibrierquellen aus den Rohdaten neu. Ergebnis **ANALYSIS_REPAIRED_VERIFIED** in [analysis_result.json](analysis_repair_002/analysis_result.json). **Null** wiederholte Simulatorzweige, null neue Fits, null Policyupdates. Kein technischer Neustart des fertigen BC-Piloten; `coordinator.py repair` würde einen Trainingsversuch anfordern und wird für diesen reinen Analysefehler daher nicht verwendet.

Kosten des ursprünglichen Workers: 167,609 s; Supervisor 170,145 s. 312 Reset-/Präfixrekonstruktionen, 1.326 Präfixaktionen, 312 Prüfaktionen, 40.950 Physiksteps, 576 IK-Iterationen, 300 Policyaufrufe. Gesamte Korrekturrechenzeit C1/C2/C3 jeweils etwa 5,5 ms für 72 Fälle; kein isolierter Performanzbenchmark. Reparierte Analyse 0,137 s plus unabhängige Prüfungen.

Rohdaten-SHA256 `9415a85808ecda188e7aa80aba41cc8f2436e3e387c18e7f1bca97664af6550b`. Dataset `2067777cb8b532e9263dd09fd6448c41cc31224bb27be4a3b734010ae13eb540`; B0-Checkpoint `27a38fc65415d419a060cd0fc529f8f30d82bc36cdf77d54cc79d7a3e52117fa`. Vollständige Quellen-/Inputhashes in source_hashes.json, calibration.json, verification.json und analysis_result.json.

Nächster fachlicher Schritt: [Verlust-/Gradientenskala ohne Optimizerupdates prüfen](../NEXT_GRADIENT_AUDIT.md). Domainabdeckung und Labelsemantik bleiben zusätzliche offene Gates. Hauptaussage zur fehlenden robusten BC-Verbesserung unverändert; Aufsicht bis 15:11:19 Berlin ACTIVE.
