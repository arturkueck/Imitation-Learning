# Gültigkeitsbereich der eingefrorenen Aktionsantwort

**Alle 336 geplanten Zweige wurden ausgeführt und geprüft. Die globale Domainprüfung ist nicht bestanden: DOMAIN_GATE_FAILED, unabhängig AUDIT_VERIFIED_DOMAIN_GATE_FAILED.** Das ist ein wissenschaftlicher Abdeckungsbefund, kein technischer Startfehler und kein Neustartgrund. Kein Fit und kein Policytraining.

| Vorab bestimmter Demoabschnitt | Gültige Anker / vorgesehen | Herstellungs-/Paarungsfehler | Kontaktfälle | Bestandene B_7-Antworten / vorgesehen |
|---|---:|---:|---:|---:|
| 10% | 4/4 | 0/4 | 0/4 | 24/28; vier Gripperantworten degeneriert |
| 50% | 4/4 | 0/4 | 0/4 | 24/28; vier Gripperantworten degeneriert |
| 85% | 0/4 | 0/4 | 4/4 | 0/28 bewertet; alle 28 wegen Domain ausgeschlossen |
| Gesamt | 8/12 | 0/12 | 4/12 | 48/84; acht degeneriert, 28 nicht gültig prüfbar |

Alle Nenner bleiben erhalten. Die 28 späteren Antworten sind **nicht als numerische Modellfehler oder Erfolge bewertet**. Der Test belegt keine grundsätzliche Unmodellierbarkeit von Kontaktdynamik; unsere vorbestimmte kontaktfreie Näherung deckt diese Zustände nicht ab. Demozeit ist ein Stratum, kein unabhängig gemessener Phasenname.

## Konditionale Modellgüte an gültigen Ankern

Das an frühen anderen Demos identifizierte B_7 wird unverändert geprüft, ohne Nachfit. Bei 10% und 50% bestehen jeweils sämtliche 24 nicht degenerierten Aktionsantworten. Gripper ist jeweils viermal degeneriert; beide vorab ausgewiesenen Degenerationskonventionen (1 µm und historische 10 µm) liefern hier dieselben Zählungen. Medianer relativer Vektorfehler der nicht degenerierten B_7-Antworten: 0,01770 früh, 0,06684 bei 50%.

Auf den jeweils zwölf xyz-Antworten besteht B_xyz 12/12, Expert-OLS 0/12. Dessen medianer relativer Fehler 1,162 früh bzw. 1,121 bei 50%. A=I ist in diesen gültigen Strata weiter kompatibel, medianer relativer Fehler 0,142% bzw. 0,071%; keine große Identitätsfehlerquelle hier bestätigt.

| Gültiges Stratum | Vollständige Policyreaktionen | Median Ratiofehler OLS | B_xyz | B_7 | OLS falsche Freigaben | B_xyz falsche Strafen | B_7 Fehlentscheidungen |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10% | 24/24 | 0,002082 | 0,004112 | 0,000241 | 0 | 8 | 0 |
| 50% | 24/24 | 0,002622 | 0,003932 | 0,000614 | 8 | 6 | 0 |
| 85% | 0/24 gültig bewertet | — | — | — | — | — | — |

Entscheidungsschwelle ist Ratio<0,99 wie fixiert. Die Teilwerte stützen die volle Antwortmodellierung auch an diesen vier mittleren kontaktfreien Ankern. Sie liefern keine globale Robustheits-/Trainingsgarantie und keine Aufgabenleistung.

## Warum ein Kontaktfilter am Start nicht genügt

In demo_165 bei 85% ist die ungestörte Referenz **zu Beginn kontaktfrei**, während im anschließenden BC-Prüfschritt Kontakt entsteht. Die anderen drei 85%-Referenzen enthalten bereits vor dem Schritt Kontakt. Ein nachträglich rein deskriptiver Filter „Referenz startet ohne Roboterkontakt“ würde damit 9/12 Anker freigeben, obwohl nur 8/12 die vollständige Domainprüfung bestehen: eine falsche Freigabe unter den neun akzeptierten Fällen. Das ist ein Gegenbeispiel auf bereits gesehenen Daten, keine neue unberührte Klassifikatorprüfung.

Das gewünschte Trainingsgewicht w braucht eine vor der Lossberechnung verfügbare und nachvollziehbare Regel. Die erst nach Simulatorzweigen bekannte Domainmarkierung ist dafür allein nicht ausreichend. Aufgezeichnete BC-Daten können außerdem andere Livezustände/Controllergeschichten repräsentieren; die zuvor dokumentierte Replayabweichung bleibt offen. Deshalb keine automatische Kontraktions-Trainingsfreigabe.

## Durchführung und unabhängige Prüfung

[Protokoll](PROTOCOL.md) und [Auswahl](selection.json) vor neuen Antworten fixiert. Seed 4100406, vier neue Train-Demos demo_118/demo_165/demo_174/demo_117, alle nur Gegenprüfung, alle bisherigen 36 Diagnose-/Auditdemos ausgeschlossen. Je zwölf Anker, 28 Zweige: Referenz/Wiederholung, 14 Aktionsinterventionen, sechs physische A-Zweige, sechs vollständige BC-Antworten. B0-Endcheckpoint, A/B_xyz/B_7 von demo_59/demo_152 unverändert. Keine intermediate Checkpointwahl, kein Lambda-Tuning.

Numerische Start-/History-/Auxfelder, Referenzwiederholungen, echte EEF-Herstellung, Orientierung, Geschwindigkeit, Objekt/Gripper und Solver-Warmstart geprüft. Die vorab bestimmte Domainprobe ergänzt den unveränderten 50-µm-IK-Helfer um eine strengere 1-µm-Positionsprüfung; keine nachträgliche Gateänderung. Alle zwölf technischen Gates bestehen. Kontaktfreiheit wird vor, während und nach dem Prüfschritt verlangt; 85%-Fälle bleiben im Abdeckungsnenner.

[Unabhängiges Rechen-/Zustandsaudit](analysis_verification.json) rekonstruiert Aufteilung, Paarung, die numerischen geometrischen/History-/Auxgates sowie die Modellvorhersagen aus Rohdaten. Die Gelenkgrenzprüfung nutzt das unveränderte gehashte Worker-Gate; Modell-Gelenkbereiche wurden im reinen Rohzustandsaudit nicht nochmals im Simulator erzeugt. Diese Prüfgrenze wird ausdrücklich ausgewiesen. Es wurde kein Zweig zur Verifikation wiederholt.

Kosten: 208,672 s Worker, 210,187 s Supervisor; 336 Reset-/Präfixrekonstruktionen, 7.644 Präfixaktionen, 336 Prüfaktionen, 199.500 Physiksteps, 288 IK-Iterationen, 84 Policyaufrufe. Analyse 0,371 s. Worker und Watchdog beendet, Job geschlossen, keine eigene Wachhalteanforderung. null Fits/Policyupdates; kein Retry dieses fachlichen Ergebnisses.

Rohdaten-SHA256 `5580d7b1f5a917b75057d6be389d889cb0831e5115d027d618804b711621e8b8`. Dataset und B0-Checkpoint unverändert; alle Source-/Inputhashes in source_hashes.json, selection.json, calibration.json und analysis_verification.json. [Originaldaten](result.json) und [Log](worker.log) bleiben erhalten.

Nächster minimaler Schritt: [prüfen, ob statische Domaininformationen an den tatsächlichen aufgezeichneten BC-Frames verfügbar sind](../NEXT_RECORDED_DOMAIN_MASK.md), getrennt von deren dynamischer Gültigkeit. Die Hauptaussage bleibt: konkrete lokale Modellkorrektur unterstützt, robuste neue BC-Verbesserung nicht etabliert. Bekannte lokale Dynamik-/Gültigkeitsideen siehe [Stable-BC](https://arxiv.org/html/2408.06246v1), [CCIL](https://arxiv.org/html/2310.12972v2); diese Literatur behauptet unsere Projektergebnisse nicht.
