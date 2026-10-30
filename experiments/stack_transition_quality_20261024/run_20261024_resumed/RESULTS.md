# Abschluss: Qualitätsgewichtetes Übergangslernen B0/B

Alle sechs Modelle absolvierten insgesamt10.000 Updates. Nach technischer Unterbrechung wurde aus gemeinsamem Update3000 mit Optimizer- und Samplerzuständen fortgesetzt. Der Lauf und sämtliche12 Modell-/Splitgruppen sind regulär abgeschlossen. Der Supervisor endete mit Exitcode0, die Wachhaltesperre wurde freigegeben. Die ursprüngliche Deadline wurde eingehalten.

## Ergebnis und Interpretation

Die Qualitätsgewichtung lieferte in diesem Pilot keinen nachgewiesenen Vorteil. Die gemeinsame Entwicklung wählte für alle sechs Modellpositionen den unveränderten Parent mit0 Zusatzupdates. Daher prüfen die reservierten Endtests diese Parents, nicht die10000er Kandidaten. Gleiche B0/B-Endtestquoten sind hier keine unabhängige Replikation eines trainierten Effekts: Es sind pro Seed identische ausgewählte Ausgangsmodelle. Auch eine Nullwirkung in anderen Datensätzen oder Architekturen ist damit nicht bewiesen.

| Seed (B0 und B identisch ausgewählt) | Vollständige Zweiertürme | Dreiertürme | Vierertürme | P2-Erhaltübergang | P3-Erhaltübergang |
|---|---:|---:|---:|---:|---:|
| 1 | 50/50 | 57/100 | 28/100 | 17/50 | 7/50 |
| 2 | 50/50 | 50/100 | 22/100 | 14/50 | 7/50 |
| 3 | 48/50 | 40/100 | 16/100 | 10/50 | 9/50 |

90 % stabile Dreier auf jedem Seed sind klar nicht erreicht. Fünfertürme wurden nicht trainiert oder endgetestet. Zweierquoten beruhen auf50 Starts je Seed und werden nicht als90/100 ausgegeben. Diese neue Datengrundlage enthält Drei-/Viererrollouts; kein reiner Zweier-Zero-shot-Nachweis.

## Warum wurden Ausgangsmodelle ausgewählt?

Auswahl ausschließlich auf Entwicklung: schlechtere der beiden Präfixquoten, dann vollständiger Vierererfolg, dann geringere Unterstufenregression, dann früherer Checkpoint. Die technisch unterbrochene3000er Runde blieb symmetrisch für alle sechs ausgeschlossen. Gemeinsame Kandidaten waren0 und10000; die reservierten Starts waren noch ungesehen.

| Seed | Update | P2 | P3 | Voll2 | Voll3 | Voll4 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 9/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| 1 | 10000 | 9/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| 2 | 0 | 10/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| 2 | 10000 | 9/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| 3 | 0 | 7/20 | 4/20 | 8/10 | 3/10 | 2/10 |
| 3 | 10000 | 7/20 | 4/20 | 8/10 | 3/10 | 1/10 |

Die10000er Kandidaten beider Arme haben in diesen fünf aggregierten Entwicklungsmetriken je Seed identische Quoten. Bei Seeds1/2 bleibt der entscheidende schlechtere Präfixwert und der Vierererfolg gleich; der vorab festgelegte Tie-Break bevorzugt Update0. Bei Seed3 fällt der Vierererfolg von2/10 auf1/10. Damit kein Anlass, mehr Updates oder eine Verbesserung zu behaupten. Seed2 verliert zudem einen P2-Erfolg, was die Minimumquote in diesem Fall nicht verändert. Die kleinen20er/10er Panels begrenzen die Empfindlichkeit; keine Signifikanzbehauptung.

## Bestätigung und Coverage

| Seed (beide Arme) | Bestätigung P2 | Bestätigung P3 |
|---|---:|---:|
| 1 | 4/20 | 4/20 |
| 2 | 3/20 | 3/20 |
| 3 | 1/20 | 3/20 |

Bestätigung bewertete ausschließlich die bereits eingefrorenen Parents und wurde nicht zur neuen Auswahl genutzt. Unterschiedliche Quoten auf anderen Startfamilien zeigen die Sensitivität gegenüber Ausgangslagen.

| Modell | Präfix | Erfolg / geplant | Erfolg / vorbereitet | Vorbereitung fehlt | Fehlschläge mit Turmkontakt |
|---|---:|---:|---:|---:|---:|
| B0_seed1 | 2 | 17/50 | 17/48 | 2 | 26 |
| B0_seed1 | 3 | 7/50 | 7/30 | 20 | 20 |
| B0_seed2 | 2 | 14/50 | 14/48 | 2 | 30 |
| B0_seed2 | 3 | 7/50 | 7/30 | 20 | 19 |
| B0_seed3 | 2 | 10/50 | 10/48 | 2 | 31 |
| B0_seed3 | 3 | 9/50 | 9/30 | 20 | 19 |
| B_seed1 | 2 | 17/50 | 17/48 | 2 | 26 |
| B_seed1 | 3 | 7/50 | 7/30 | 20 | 20 |
| B_seed2 | 2 | 14/50 | 14/48 | 2 | 30 |
| B_seed2 | 3 | 7/50 | 7/30 | 20 | 19 |
| B_seed3 | 2 | 10/50 | 10/48 | 2 | 31 |
| B_seed3 | 3 | 9/50 | 9/30 | 20 | 19 |

Vorbereitungsfehler bleiben im gemeinsamen Nenner. Die bedingte Quote auf tatsächlich vorbereiteten Zuständen ist zusätzlich ausgewiesen; sie ersetzt keine Vollturmquote. Kontakte sind Ereigniszählungen, kein vollständiger Kausalbeweis. P2/P3 messen bestätigte nächste Aufnahme und50 Folgeschritte bei kontinuierlich erhaltenem unterem Turm; sie messen nicht die nächste abgeschlossene Platzierung.

## Fehlerbild und Grenzen

Schon die vorherigen Entwicklungsepisoden zeigten Turmkontakt wenige Schritte nach einem Paarwechsel. Viele vollständige Viererfehlschläge verbrannten den Großteil des Horizonts in Phase6. Die Endauswertung enthält Phasenbelegungen und Kontakt-/Erhaltflags, aber keine vollständigen Objekttrajektorien aller Fehlschläge. Eine präzise Platzierungsgenauigkeit in Millimetern oder eine eindeutige Ursache jedes Einsturzes ist daraus nicht belastbar ableitbar.

Nur49 akzeptierte Trainingsabschnitte aus46 Familien, davon acht mit bereits drei geschützten Würfeln. Strenge Akzeptanz macht den Erhaltterm konstant; effektive gewichtete Abschnittszahl48,89 von49. Der B0/B-Kontrast ist daher moderat. Eigene Erfolgsdaten reproduzieren Teacherbias und liefern keine korrigierende Expertenaktion für fehlgeschlagene Zustände. Der Actor erhielt keine zusätzlichen expliziten Turm-/Freiraumfeatures. Originalcompletion-BCE erhält kein garantiert unverändertes Phasenverhalten, weil Hiddenlayer gemeinsam trainiert werden.

Architektur, sieben Phasen, Sequencer, Controller, Original-/Replay-/Neu-Mischung50/25/25, Samplereihenfolge, Seeds und Lernrate3e-5 waren in beiden Armen identisch. Nur neue Übergangsframes wurden in B qualitativ gewichtet. Keine neuen Skriptexpertenaktionen und kein RL. Die ursprüngliche Fingerkontaktmessung war fehlerhaft und wurde für diesen Versuch korrigiert; historische Quoten sind deshalb keine uneingeschränkt vergleichbaren Baselines.

## Integrität, Arbeit und Kosten

Alle gespeicherten Loss-/Gradientwerte endlich, gespeicherte Samplehashes pro Seed undUpdate zwischen B0/B gleich. Gehashte Originaldaten, Originalarrays, Replayepisoden, Teacher und Code einschließlich separater Wiederaufnahmequelle unverändert. Sechs Modelle vor Bestätigung und reservierten Endtests gemeinsam eingefroren. Keine erneute Optimierung nach Endtests. Technische3001-Smokes nicht produktiv eingesetzt.

60000 reale Optimizerupdates insgesamt: ursprüngliche18000 bis3000 plus42000 der Fortsetzung. Pro Modell10000×64/27322 = 23.424 Originalpass-Äquivalente aller Mischbeispiele; tatsächlich gezogene Originalframes entsprechen 11.712 Originalpässen. Keine klassischen Epochen des gemischten Datensatzes. Vortraining und Sammlung zusätzlich.

Wandzeit ab ursprünglichem Start bis Ende: 5.182h einschließlich Unterbrechung. Fortsetzungswandzeit: 2.329h. Abstand zur ursprünglichen Deadline: 2.818h. Keine Verlängerung; GPU-Aktivzeit nicht separat instrumentiert.
Gespeicherte reservierte Vollrolloutframes über alle sechs Modellpositionen: 1228304; vorbereitete Übergangsaktionen: 18648. Identische Parentpaare werden hierbei als tatsächlich ausgeführte Kosten gezählt, nicht als unabhängige wissenschaftliche Evidenz. Weitere Kosten für Entwicklung, Bestätigung und Panelaufbau kommen hinzu.

## Nächste wissenschaftliche Entscheidung

Unveränderte Parents als aktuelle Referenz behalten; kein neues Training aus den reservierten Testergebnissen. Ein weiterer Lauf braucht einen separat eingefrorenen Entwicklungsplan und neue Endteststarts. Sinnvoll zu untersuchen: mehr unabhängige sichere Übergänge mitPräfix3, beobachtbare untere Turmgeometrie und eigene Diagnose der Phasen6-/Freigabebedingungen. Zuerst Dateninformation und Ablauf beobachten, statt denselben kleinen Erfolgsdatensatz nur länger zu trainieren. Gewichtung bleibt eine unbestätigte Hypothese.

Datensatzdetails: ../DATASET_REPORT.md. Technische Reparatur: ../RESUME_REPAIR.md. Historischer Teilabschluss: ../run_20261024_approved/RESULTS.md.
