# Feste versus zustandslokale Aktionsantwort

Siebter geplanter Agentcheck, Trigger **04.10.2026, 12:37:45 Berlin**. Alle **336/336** Zweige ausgeführt. Technische Recorded-/History-/Störungs-/Wiederholungsgates **12/12** bestanden; kontaktfreie Domain **8/12**. Alle vier 85%-Anker wegen Kontakt ausgeschlossen und im Nenner erhalten: wissenschaftlicher **DOMAIN_GATE_FAILED**, unabhängig **AUDIT_VERIFIED_DOMAIN_GATE_FAILED**, kein Retrygrund. Kein neues Policytraining und keine Checkpointauswahl.

Neue Train-Demos demo_69, demo_16, demo_157, demo_23, Seed 4100409; zwölf Recorded-Frames bei 10/50/85%, ausschließlich bekannte H_reset-Präparation. Die ursprüngliche Expert-Controllergeschichte wird nicht rekonstruiert. B0-Endcheckpoint, bestehende Kalibrierung und Dataset unverändert. Quellen, Auswahl, physische Rohzustände und die daraus berechneten Modelle geprüft.

## Was der Versuch unterscheidet

Pro gültigem Anker eine lokale B-Matrix aus **14 nominalen ±0,1 Aktionszweigen** bestimmt: D enthält tatsächlich ausgeführte 7D-Aktionsdifferenzen, Y die zugehörigen EEF-Nachfolgedifferenzen; B_local=lstsq(D,Y). **Acht lokale Identifikationen mit je 21 Koeffizienten**, null Optimizerupdates. Rank(D)=7, Condition 1,00–1,99; sechs Anker mit je einem geclippten Aktionszweig. Die tatsächlichen Differenzen berücksichtigen das Clipping. Gripperwirkung kann trotz vollen Eingaberangs degenerieren. Identifikationsresiduen sind keine unabhängigen Modellprüfungen.

Davon getrennte Prüfzweige: echte ±5-mm-EEF-Störungen und volle deterministische BC-Reaktionen. Der primäre Vergleich ändert ausschließlich B: gleiches eingefrorenes A, feste B7-Matrix gegen lokale B7. Eine dritte, vorab festgelegte Kontrolle ersetzt sekundär A durch I. Keine Identifikation aus den Policyprüfreaktionen.

| Modell, 48 gültige Policyprüfungen | Medianer absoluter Ratiofehler | P90 | Falsche <0,99-Freigaben | Falsche Strafen |
|---|---:|---:|---:|---:|
| A / festes B7 | 0,00106262 | 0,00263929 | 6 | 0 |
| Gleiches A / lokales B7 | 0,00046629 | 0,00097291 | 1 | 0 |
| I / lokales B7, sekundär | 0,00026885 | 0,00075592 | 0 | 2 |

Primär **56,12%** weniger medianer Ratiofehler; lokale Variante an **8/8** gültigen Ankern besser, 0 gleich/schlechter. 10%-Abschnitt 4/4 besser: Fehler 0,00075362→0,00019256, Freigabefehler 6→1. 50%-Abschnitt 4/4 besser: 0,00109536→0,00073769, beide ohne Klassifikationsfehler. 85%: 0/4 gültig, keine numerische Modellbewertung. 48 geprüfte Reaktionen von acht Zuständen sind keine 48 unabhängigen Trainingsseeds; kein nachträglicher Signifikanz-/Trainingsfreigabegrenzwert.

Das verbleibende Gegenbeispiel ist konkret: demo_157, t=4, +z-Störung, beobachtete Ratio **0,99008031**, lokale Vorhersage **0,98989165**. Eine kleine Modellabweichung kippt die enge 0,99-Entscheidung. Die sekundäre I-Kontrolle behebt diesen Fall, erzeugt aber zwei falsche Strafen; daraus kein nachträglicher Wechsel des primären A oder automatische Trainingsfreigabe.

Die tatsächliche gemeinsame Zustands-/Aktionsantwort minus separat beobachteter Zustandsantwort und lokaler Aktionsantwort hat median **0,130 µm** Restfehler; mit festem B7 **4,526 µm**. Die eingefrorene A-Zustandsvorhersage hat median **5,568 µm** Fehler. Das spricht in diesen Fällen für eine wichtige Zustandslokalität von B und begrenzt die Präzision des festen A; die kleinen Restfehler bleiben bei engen Entscheidungsmargen relevant. Kein universeller Linearitätsbeweis und keine Stabilitätsgarantie.

## Kosten und technische Verifikation

Worker **191,406 s**, Supervisor **194,187 s**; **336 Resets, 336 Antwortaktionen, 8.400 instrumentierte Physiksteps, 288 IK-Iterationen, 84 Policyaufrufe**, null Expertpräfixaktionen. Vorprüfung zusätzlich zwei identische H_reset-Rekonstruktionen, 4,578 s Worker/6,011 s Supervisor, keine Antwortaktion oder Zeitintegration; Setup-/Forwardaufrufe dort nicht instrumentiert. Der gespeicherte Null-Resetcounter ist keine Aussage, dass keine Rekonstruktionen stattfanden. Physischer Audit 0,425 s, lokale Nachverarbeitung 0,152 s, unabhängige lokale Verifikation 0,163 s, ohne erneute Simulation.

Während der Codeprüfung vor Analyseausführung wurde ein falscher Metadatenfeldname erkannt (`passed` statt `eligible`). Die eingefrorene Originalanalyse blieb erhalten; allein dieser Feldzugriff und der Pfad wurden in [analysis_repair_001](analysis_repair_001/REPAIR.json) korrigiert. Keine geänderte Auswahl/Gate/Formel, kein neuer Simulatorlauf. Direkte lineare Lösung statt lstsq prüft alle acht Matrizen unabhängig; 48 gehaltene Prüfvorhersagen und Klassifikationen aus tatsächlichen Rohzuständen nachgerechnet, maximale Differenz **6,78e−21**. Physischer Audit verwendet gespeicherte Worker-Gelenkgrenzenprüfungen; andere ausgewiesene Gültigkeitsgates werden unabhängig rekonstruiert.

Worker, Vorprüfungsworker und eigene Supervisoren beendet, Jobs geschlossen. Sessioncoordinator/30-Minuten-Heartbeat bleiben ACTIVE bis **15:11:19 Berlin**.

- [Fixiertes Protokoll](PROTOCOL.md), [Auswahl und Dataset-/Checkpoint-SHA256](selection.json), [eingefrorene Quellen](source_hashes.json)
- [Rohdaten](result.json), [physischer Audit](analysis_verification.json), [lokale Identifikationen und Prüfmetriken](local_identification.json), [unabhängige Rechenprüfung](local_verification.json)
- Rohdaten-SHA256 `dc534493affadcae038990d630a5bf11a6e9da2dd27e41427d0911293bd3c2e3`
- Physischer Audit-SHA256 `43e56daf85362b5ea532ef185daf61c0ab8edbf16ede9bfc6c7035320e0c9470`
- Lokale Analyse-SHA256 `c65222271e11d45f90b746da76fdbb05047f56e665368a4047347d65e8291716`

## Forschungsentscheidung

Die Hypothese einer unzureichend übertragenen festen B7-Matrix wird für diese geprüften kontaktfreien Recorded-Zustände unterstützt. Lokale Identifikation verbessert den Mechanismusvergleich, nicht eine trainierte Policy. Sie verlangt privilegierten Simulatorzugriff und zusätzliche Kosten; das ist noch kein im BC-Batch verfügbares günstiges Verfahren.

Nächste getrennte Gates: **vor der Lossberechnung verfügbarer konservativer Kontakt-/Nähefilter** und **empirische Fehlermarge der engen Ratioentscheidung**, danach explizite Gradientenskalenkontrolle. Ein Anfangskontaktflag genügte bereits im Live-Gegenbeispiel nicht. Keine Freigabe eines neuen Kontraktionstrainings. Hauptaussage unverändert: frühere begrenzte Taskgewinne, Mechanismus eingeschränkt, robuste neue BC-Algorithmusverbesserung und schnellere Konvergenz nicht etabliert. Allgemeine Fehlerdynamik-/Gültigkeitsideen stammen unter anderem aus [Stable-BC](https://arxiv.org/html/2408.06246v1) und [CCIL](https://arxiv.org/html/2310.12972v2), nicht aus diesem Einzelversuch als allgemeiner Neuheitsnachweis.
