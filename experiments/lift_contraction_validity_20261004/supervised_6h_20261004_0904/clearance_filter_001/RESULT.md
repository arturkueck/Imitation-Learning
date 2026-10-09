# Nähefilter: Nullabdeckung trotz technisch gültiger Abfrage

Achter geplanter Agentcheck, Trigger **04.10.2026, 13:07:45 Berlin**. Zwölf neue Recorded-Anker aus demo_106, demo_139, demo_39, demo_41, Seed 4100410, je10/50/85%. Alle **336/336** geplanten Antwortzweige ausgeführt; technische Gates **12/12** bestanden, dynamisch kontaktfreie Domain **8/12**. Wissenschaftlicher Workerstatus **DOMAIN_GATE_FAILED**, unabhängiger physischer Audit **AUDIT_VERIFIED_DOMAIN_GATE_FAILED**. Der neue Filter über alle Roboterpaarungen ist wissenschaftlich **unbrauchbar wegen Nullabdeckung**, kein technischer Retrygrund. Keine Policyupdates, Fits oder Checkpointauswahl.

Der native Nähequery wurde jeweils auf dem nominalen H_reset-Recorded-Zustand **vor dem ersten Antwortzweig** gespeichert: kopiertes MuJoCo-Modell, separate MjData, geom_margin/gap und vorhandene pair_margin/gap jeweils **0,015 m**, ein Forward ohne Integration. Originalmodell, wohldefinierte Datenarrays und vollständiger Controller-/Physicalsnapshot unverändert. M0=keine ursprünglichen nominalen Robot-/Gripperkontakte, M1=M0 und keine Robot-/Grippernähekontakte im Query. Der Query ist ein fest definierter Simulatorproxy; keine exakte universelle Signed-Distance-Regel oder zusätzliche vorhandene Policyobservation.

| Maske | Angenommen / geplant | Richtig angenommen | Falsch angenommen | Falsch verworfen | Richtig verworfen |
|---|---:|---:|---:|---:|---:|
| M0: nominal kontaktfrei | 9/12 | 8 | 1 | 0 | 3 |
| M1: zusätzlich alle Nähepaare frei | **0/12** | 0 | 0 | **8** | 4 |

10%- und50%-Abschnitte jeweils vier dynamisch gültige Anker: M0 akzeptiert4/4, M1 verwirft4/4. 85% vier ungültige: M0 lässt einen durch, M1 verwirft alle. Die Null falsch angenommener Fälle von M1 ist hier **kein brauchbarer Erfolg**, weil kein gültiger Fall angenommen wird. Parameter/Schwelle wurden nach diesen Ergebnissen nicht geändert.

Konkretes M0-Gegenbeispiel **demo_139,t=39**: Referenz und alle Zweigstarts ohne Robotkontakt. Kontakte treten bei mehreren Aktions-/Zustands-/Policyzweigen während oder nach dem Schritt auf, etwa B_1_plus und A_0_minus. Die Referenz selbst hat keine Stepkontakte. Nominale Startkontaktfreiheit genügt deshalb erneut nicht als dynamisches Gültigkeitsgewicht.

## Warum M1 alles verwirft: getrennte explorative Evidenz

In allen zwölf Nähequeries erscheint **robot0_link0_collision / robot0_link1_collision**, mit nativ gemeldetem Abstand etwa0,9974–0,9977 mm. Das ist eine in diesen Zuständen beständige roboterinterne Nähe am Basis-/ersten Armglied. Dieser Proxy blockiert deshalb auch frühe gültige Zustände, obwohl in deren tatsächlichen Antwortzweigen keine Robot-/Selbstkontakte auftreten. Genannte Distanzen sind Queryausgaben für Meshgeometrien, keine unabhängige genaue Abstandsmessung.

[Nachträgliche Scopeauswertung](pair_scope_exploration.json) trennt Kontakte anhand der vorher gespeicherten Robot-/Grippergeomnamen in intern versus extern. Eine rein externe Nähemaske würde auf **diesen bereits gesehenen Daten**8/12 akzeptieren, alle acht gültig, keine Fehlentscheidung. **EXPLORATORY_POSTHOC_PAIR_SCOPE_ONLY**, kein neuer Bestätigungssatz, kein Ersatz für das negative M1-Ergebnis und keine Trainingsfreigabe. Sie begründet genau eine neue mechanistische Gegenprüfung auf frischen Demos. Deren dynamischer Gültigkeitsnenner muss weiterhin **alle** tatsächlichen Robot-/Selbstkontakte enthalten.

## Technische Fehler, Reparaturen und unabhängige Prüfung

preflight_001 FAILED beim Hashvergleich sämtlicher nativer Arrays. Die separate Diagnose zeigt: deaktivierte Constraint-Island-Arbeitsarrays ändern gelesene Werte sogar ohne Query. preflight_002 prüft diese nur bei aktivierter nativer Inselberechnung; alle sechs primitiven Box-/Ausschlusskontrollen bestanden, aber der bekannte Recorded-Frame scheiterte an einem ebenfalls nicht berechneten Dualsolver-Arbeitsarray. Wiederholte Lesung von efc_AR_colind wechselt bei Newton ohne Operation. Die [MuJoCo3.2.3-Typdefinition](https://mujoco.readthedocs.io/en/3.2.3/APIreference/APItypes.html#mjdata) sowie lokalen Header ordnen diese Gruppen den nur bedingt ausgeführten Routinen mj_island beziehungsweise mj_projectConstraint für Dualsolver zu.

preflight_003 PASSED: Hashvergleich aller Modelarrays und wohldefinierter Dataarrays; Inselgruppe nur bei deaktiviertem mjENBL_ISLAND **und nisland=0**, Dualarbeitsgruppe nur bei nativem mj_isDual=false ausgenommen. Physical-, Auxiliary-, Controller- und Modellgates bleiben exakt. Originalquellen, Diagnosen, beide FAILED-Prüfungen und Reparaturen erhalten; keine primären Antwortzweige vor bestandener Vorprüfung, keine Primärdaten wiederholt. [Reparaturen](../repairs.jsonl), [bestandene Vorprüfung](preflight_003/result.json).

Physischer/Rohzustandsaudit verifiziert bisherige Herstellungsgates und Quellen. [Unabhängige nominale Neuherstellung](query_verification_001/result.json) führt alle zwölf Queries erneut ohne Antwortaktion aus: volle nominale Controller-/Zustandssnapshots identisch, ursprüngliche und Nähekontaktlisten sowie beide Masken **12/12 exakt reproduziert**. Gelenkgrenzen im physikalischen Audit beruhen auf gespeicherten Workerprüfungen; andere ausgewiesene Gates unabhängig nachgerechnet.

Die [versionsbezogene XML-Dokumentation](https://mujoco.readthedocs.io/en/3.2.3/XMLreference.html#body-geom-margin) erläutert margin/gap; die [native Kollisionsauswahl](https://mujoco.readthedocs.io/en/3.2.3/computation/index.html#collision) die Body-/Parent-/Bitmasken-/Exclusionfilter. Primärquellen beschreiben Simulatorfunktionen, **nicht** die Projektzahlen oben. Der verwendete native Python-/Bibliotheksstand3.2.3 ist in den Outputs verifiziert.

## Kosten und Status

Primärworker **195,578 s**, Supervisor **198,170 s**, 336 Resets, 336 Antwortaktionen, **8.400 instrumentierte Physiksteps**, 288 IK-Iterationen, 84 Policyaufrufe, null Expertpräfixaktionen. Zusätzlich **12 explizite Queryforwardcalls**, ohne Integration; Setup-/Resetforwards nicht vollständig instrumentiert. Audit0,416 s, Filterklassifikation0,157 s.

Vorprüfungsworker:3,641 s FAILED,4,406 s FAILED,4,516 s PASSED; je Supervisor etwa6,01 s. Vorprüfung1: erster synthetischer Originalforward und Queryforward vor Assertion; Vorprüfungen2/3: je sechs synthetische Originalforwards und sieben Queries einschließlich bekanntem Frame. Zusätzliche reine Arraydiagnosen ohne Integration, bekannte Recorded-Diagnose4,531 s Worker/6,012 s Supervisor. Unabhängige Queryneuherstellung **10,282 s Worker /12,018 s Supervisor**, zwölf Rekonstruktionen und zwölf Queryforwards, keine Zeitintegration/Policyaktion. Fehlgeschlagene Arraysummaries sind keine Nullkostenbehauptung.

Alle Primär-/Vorprüfungs-/Verifikationsworker und eigenen Supervisoren beendet, Jobs geschlossen. Keine technische oder wissenschaftliche automatische Wiederholung. Sessioncoordinator und30-Minuten-Agenttrigger weiterhin ACTIVE bis **15:11:19 Berlin**.

- [Fixiertes Protokoll](PROTOCOL.md), [Auswahl und Dataset-/Checkpoint-SHA256](selection.json), [Quellenmanifest](source_hashes.json)
- [Rohdaten](result.json), [physischer Audit](analysis_verification.json), [Filtermetriken](filter_analysis.json), [Queryreproduktion](query_verification_001/result.json)
- Rohdaten-SHA256 `f42b1ec73f80bb38959e111b2c0355fe7d3752ec78fb3ab434b2e3c88e18f1e8`
- Physischer Audit-SHA256 `965bc13e1d60d4eac9b124091994083b23b47ce70fcfc3c8b77864f4a2bedea9`
- Filteranalyse-SHA256 `1aafca167d47838eb5abc8f5a5ff66952bb87534794aac32e3458d3a6a40e36e`
- Queryreproduktions-SHA256 `652cbf552cc4e0e3ed534fe33166983b994c8778a4a378077da9382c31a17430`

**Forschungsentscheidung:** All-Paar-Nähefilter verwerfen; keine automatische Parametertuningrunde. Ein einzelner fachlich begründeter Scopevergleich auf neuen Demos ist der nächste diskriminierende Test, bei unverändertem dynamischem Kontaktgate. Unsicherheits-/Ratiofehlermarge, praktisch verfügbare Approximation und Gradientenskalenkontrolle bleiben offen. Keine robuste neue BC-Algorithmusverbesserung oder schnellere Konvergenz durch diese Diagnose etabliert; Hauptschluss unverändert.
