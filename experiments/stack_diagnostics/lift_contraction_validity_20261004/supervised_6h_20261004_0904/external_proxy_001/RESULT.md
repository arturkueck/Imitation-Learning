# Externe Nähe: frische Gegenprüfung ohne Policytraining

Stand 2026-10-04T13:51:50.228334+02:00. Seed **4100411**, vier neue Train-Demos demo_108, demo_136, demo_166, demo_102; zwölf vorab festgelegte H_reset-Anker bei 10/50/85%, **336/336** Simulatorzweige. Ein eingefrorener B0-Endcheckpoint, null Policyupdates, null neue Fits. [Vorabprotokoll](PROTOCOL.md), [Auswahl/Dataset-/Checkpointhashes](selection.json), [Originaldaten](result.json), [physischer Audit](analysis_verification.json), [Maskenaudit](filter_analysis.json).

## Ergebnis der Masken

| Vor Antwortaktion verfügbare Regel | Akzeptiert / 12 | Richtig akzeptiert | Falsch akzeptiert | Falsch verworfen | Richtig verworfen |
|---|---:|---:|---:|---:|---:|
| M0: nominal kein Robotkontakt | 8 | 8 | 0 | 0 | 4 |
| M1: zusätzlich keine Robotnähe, alle Paare | 0 | 0 | 0 | 8 | 4 |
| M2: zusätzlich keine externe Robotnähe | 7 | 7 | 0 | 1 | 4 |

Technische Herstellung **12/12** korrekt; dynamische kontaktfreie Domain **8/12**. Alle vier späten Anker liegen wegen tatsächlicher Kontakte außerhalb der fixierten Domain. Alle tatsächlichen Robot-/Selbstkontakte vor/während/nach jedem Zweig bleiben im Label. Wissenschaftlicher Rohstatus **DOMAIN_GATE_FAILED**, unabhängig bestätigt; kein Retrygrund.

M2 erfüllt die vorab fixierte kleine Entwicklungsregel (null Fehlannahmen, mindestens vier richtig angenommene Anker). **Kein inkrementeller Vorteil gegenüber M0 auf diesem neuen Satz**: M0 klassifiziert hier alle zwölf richtig, M2 verwirft zusätzlich demo_102 bei Frame 28 (50%), obwohl alle geprüften Antwortzweige kontaktfrei sind. Frühe M2-Abdeckung 4/4, mittlere 3/4, späte 0/4. M1 bleibt wegen interner Nähe ohne Abdeckung. Frühere M0-Gegenbeispiele bleiben gültig; der neue kleine Satz beweist auch für M0 keine allgemeine Gültigkeit. Keine nachträgliche Änderung von 15-mm-Query, Scope oder Label.

Die unterstützte Aussage ist technische Verfügbarkeit einer vor Loss berechenbaren externen Nähemaskierung unter kontrollierter Ersatzgeschichte. Die Daten etablieren weder eine bessere Domainvorhersage gegenüber M0 noch universelle kontaktfreie Folgezustände, Stabilität oder bessere trainierte BC-Robustheit. Native Näheliste ist keine bewiesene exakte Clearancegrenze. Margin-/Kontaktsemantik folgt dem tatsächlich verwendeten [MuJoCo 3.2.3](https://mujoco.readthedocs.io/en/3.2.3/XMLreference.html#body-geom-margin); das begründet die Implementierung, keine Garantie für diesen Projektfilter.

## Verifikation und Kosten

Die sieben nominalen Aktionsachsen, physischen Zustandsperturbationen und vollen Policyantworten werden weiterhin kontrolliert. Query auf separater Modellkopie/MjData mit je 0,015 m Margin/Gap, ohne Integration oder Änderung des Originalzustands; sämtliche physikalisch definierten Model-/Datafelder und vollständige Controller-/Hilfszustände geprüft. Die bereits dokumentierten konditional nicht berechneten nativen Insel-/Dual-Arbeitsarrays werden weiterhin separat ausgewiesen. Keine neue technische Reparatur in diesem Versuch.

Vorprüfung: sechs bekannte synthetische Boxcases plus ein alter Kontrollframe, 4.484 s Worker / 6.011 s Supervisor; sechs originale synthetische Forwards, sieben Queryforwards und eine Recorded-Rekonstruktion, keine Integrations-/Antwortaktionen. Neue Primärdemos werden erst danach verwendet. Unabhängige frische Neuherstellung reproduziert alle zwölf nominalen Zustände, Kontaktlisten und M0/M1/M2 exakt; [separater Nachweis](query_verification_001/result.json), 10.234 s Worker / 12.017 s Supervisor, zwölf Rekonstruktionen/Queryforwards, keine Policy-/Antwortaktionen oder Integration. Weitere Setupforwards sind nicht vollständig instrumentiert.

Primärworker **195.718 s**, Supervisor **198.169 s**. Zähler: 336 Resets, 336 Antwortaktionen, 8.400 Physiksteps, null Expertprefixaktionen, 288 IK-Iterationen, 84 Policycalls, zwölf explizite Queryforwards; weitere Setupforwards nicht vollständig instrumentiert. Kalibrier-/Filteraufwand zählt zu späteren Methodenkosten und darf nicht hinter Trainingszeit verschwinden. Sämtliche drei Worker und Supervisoren sind anhand PID plus Erzeugungszeit beendet, Windows-Jobs geschlossen. Sessioncoordinator und 30-Minuten-Heartbeat bleiben bis **15:11:19 Berlin** aktiv.

## Unveränderte Forschungsentscheidung

Kein Kontraktionstraining aus diesem Ergebnis. Priorität: Entscheidungsfehlermarge auf neuen Demos statt weiterer Kontaktfilterparameter. [Nächstes fixiertes Protokoll](../NEXT_ERROR_MARGIN.md). Der frühere Sensorpilot bleibt ein einzelner Seed mit kleinem Trade-off, ohne Robustheits-/Konvergenznachweis. Literatur, alte Taskgewinne und neue lokale Diagnosen bleiben getrennte Evidenz.

SHA-256: Rohdaten `2832be6e74008da0305c31ebb0ffa9fdc41191608266bed1e66a07a194f033b1`; physischer Audit `ce3e6c84a0d5ac70dda69f997aed5ef57b47c321ab44bed7ba0e46925095c597`; Filteraudit `b1afa20f98d07d83ec69745bc420f2700f54d30ee069cac75e3b7307db017cda`; Querygegenprüfung `6519ad2ec755800ede4c80fd5f59652bc80872d93f8717aa7d24b854a9ab623a`. Alle effektiven Quellen vor Primärlaunch eingefroren in [source_hashes.json](source_hashes.json); Dataset und unveränderter Endcheckpoint separat in selection.json.
