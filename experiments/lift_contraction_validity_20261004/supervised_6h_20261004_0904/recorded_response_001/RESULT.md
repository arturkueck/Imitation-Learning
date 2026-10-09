# Recorded-Zustandsantwort: Ergebnis des sechsten geplanten Checks

Trigger 04.10.2026, 12:07 Berlin. **DOMAIN_GATE_FAILED**, unabhängig **AUDIT_VERIFIED_DOMAIN_GATE_FAILED**. Wissenschaftliches Gültigkeitsergebnis, kein technischer Neustartgrund. Alle 672/672 geplanten Zweige an 24 Geschichte-Ankern (=12 eindeutige Frames aus vier neuen Train-Demos) ausgeführt. Kein Policytraining, kein neuer Modellfit und keine Checkpointauswahl. Seed 4100408; demo_61, demo_182, demo_4, demo_128, jeweils 10/50/85%.

Identische aufgezeichnete qpos/qvel, kanonische Zusatzfelder, nominale Beobachtungen, Referenzaktion und Simulations-/Umgebungszeit zwischen H_prefix und H_reset unabhängig geprüft. Die unterschiedlichen Ziele, Nullraumreferenzen und Grippergedächtnisse sind explizit gespeichert; innerhalb einer Geschichte alle Zweigstarts kontrolliert. Recorded-Geometrie und technische Herstellung **24/24 bestanden**, einschließlich Referenzwiederholung und echter ±5-mm-EEF-Störungen. Das rekonstruiert ausdrücklich nicht die ursprüngliche Experten-Controllergeschichte.

| Geschichte / Frameabschnitt | Gültige Anker / geplant | B7 bestanden / nicht degeneriert / geplant | B7 medianer relativer Antwortfehler | Full-Policy medianer Ratiofehler B7 / B3 / OLS | B7 falsche Freigaben / Strafen |
|---|---:|---:|---:|---|---|
| H_prefix 10% | 4/4 | 24/24/28 | 0,15291 | 0,001044 / 0,002462 / 0,003948 | 5 / 0 |
| H_prefix 50% | 4/4 | 22/24/28 | 0,18813 | 0,001326 / 0,003085 / 0,009344 | 1 / 0 |
| H_prefix 85% | 0/4 | nicht bewertet / 28 | – | – | – |
| H_reset 10% | 4/4 | 24/24/28 | 0,15291 | 0,001050 / 0,002462 / 0,003948 | 5 / 0 |
| H_reset 50% | 4/4 | 22/24/28 | 0,19103 | 0,001323 / 0,003085 / 0,009342 | 1 / 0 |
| H_reset 85% | 0/4 | nicht bewertet / 28 | – | – | – |

Kontaktprüfung vor/während/nach sämtlichen Zweigen: 16/24 Geschichte-Anker gültig, acht späte ausgeschlossen. Global B7 **92/168 geplante Antworten bestanden**, 16 Gripperantworten degeneriert, vier nicht degenerierte Antworten verfehlen das Gate, 56 wegen Kontakt nicht bewertet. Beide Geschichten verwenden dieselben Frames: weder 24 unabhängige Zustände noch zwei Trainingsreplikate. Konditionale volle Policyreaktionen: 48 je Geschichte; sechs falsche <0,99-Freigaben je Geschichte, keine falsche Strafe. Antwortgate (Kosinus≥0,8, relativer Fehler≤0,5) und enge Ratioentscheidung sind verschiedene Anforderungen. Ein bestandenes Antwortgate genügt hier nicht als Loss-Freigabe.

An acht beidseitig gültigen Framepaaren unterscheiden sich Referenz-Nachfolgepositionen median um **0,185 µm**, maximal **3,574 µm**. Mediane absolute gepaarte Differenz des B7-relativen Antwortfehlers 0,00001785; des Policy-Ratiofehlers 0,000003402. Für diese beiden kontrollierten Ersatzgeschichten ist der Historyeffekt klein gegenüber den beobachteten Antwortfehlern. Keine allgemeine Historyunabhängigkeit daraus. A≈I bleibt konditional kompatibel (Identitätsfehler median etwa 0,04–0,10%). OLS besteht keine der 48 xyz-Antworten über beide Geschichten. B7 ist lokal genauer als xyz/OLS, aber die vorherigen sehr guten Livezustandswerte übertragen sich nicht uneingeschränkt auf diese Recorded-Zustände. Die Daten identifizieren die genaue Ursache dieses Unterschieds noch nicht.

## Technik, Kosten und Nachweise

Technische Vorprüfung preflight_001: nominale Herstellung beider Geschichten erfolgreich; anschließend FAILED bei reinem Vergleich eines numerischen Controllerfeldes mit None. Fehlerquelle und Originaloutputs erhalten. Vergleich in frischem preflight_002 um explizite Feldpräsenz-/Form-/Typprüfung ergänzt, PASSED. Keine Änderung der physikalischen Gates und kein Wiederholen primärer Antwortdaten. [Reparaturprotokoll](../repairs.jsonl), [Vorprüfung](preflight_002/result.json).

Primärworker **567,516 s**, Supervisor **570,483 s**; 672 Resets, 8.456 Expertpräfixaktionen, 672 Antwortaktionen, **228.200 instrumentierte Physiksteps**, 576 IK-Iterationen, 168 Policyaufrufe. Beide Vorprüfungen zusätzlich jeweils fünf Expertpräfixaktionen und etwa 4,72 s Worker/6,01 s Supervisor; ihr Physikcounter war nicht instrumentiert. Die dort gespeicherte Null darf nicht als gesamte Physikkosten ausgegeben werden; [Kostenannotation](preflight_002/cost_annotation.json). Numerischer Audit 0,822 s ohne Simulatorwiederholung; gepaarte Nachverarbeitung ebenfalls ohne Simulator/Fit/Updates.

Primärworker und eigener Supervisor beendet; Job geschlossen. Dataset und B0-Endcheckpoint unverändert, Kalibrierung und vor Start eingefrorene Quellen verifiziert. Gelenkgrenzenprüfung verwendet gespeicherte Workerprüfungen; die unabhängige Zustandsauswertung rekonstruiert die Gelenkgrenzen nicht selbst. Andere ausgewiesene Geometrie-, History- und Zusatzfeldgates aus Rohdaten nachgerechnet.

- [Protokoll](PROTOCOL.md), [Auswahl und Dataset-/Checkpoint-SHA256](selection.json), [Quellenmanifest](source_hashes.json)
- [Rohdaten](result.json), [unabhängiger Audit](analysis_verification.json), [gepaarter Historyvergleich](history_comparison.json)
- Rohdaten-SHA256: `37eecaa10e8f6eb8f86a6ebec7a9f87eeacaaa68e5a0c48962e49cc0dbbf73ad`
- Audit-SHA256: `cc669eb2bea021b2e0a82d83f1bf413e748b18201f6db247c48e6363eb214491`

## Wissenschaftliche Entscheidung

Kein Kontraktionstraining freigegeben. Nächster minimaler Versuch: an neuen Recorded-Frames die nominale lokale 7D-Aktionsantwort aus separaten ±Aktionsproben identifizieren und gegen bisher eingefrorenes B7 auf echten Zustands-/Policyreaktionen prüfen. Damit wird geprüft, ob zustandslokale Identifikation die Fehlentscheidungen verringert oder ob Restfehler der gemeinsamen Zustands-/Aktionslinearisierung entscheidend bleiben. Eigene Projektbefunde oben, keine allgemeine Verbesserungsthese.

[Stable-BC](https://arxiv.org/html/2408.06246v1) und [CCIL](https://arxiv.org/html/2310.12972v2) motivieren die allgemeine Prüfung von Fehlerdynamik beziehungsweise Gültigkeit modellbasierter Korrekturen. Sie belegen weder diese Projektzahlen noch die Gültigkeit unseres B7-Losses. Hauptaussage unverändert: begrenzte frühere Taskgewinne, unbestätigter Stabilitätsmechanismus; robuste neue BC-Algorithmusverbesserung und schnellere Konvergenz weiterhin nicht etabliert. Sessionaufsicht bleibt bis 15:11:19 Berlin aktiv.
