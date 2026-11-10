> **Abschluss der Vorbereitung:** Alle Startgates bestanden; aktuelle Abnahme in [EXECUTION_READINESS.md](EXECUTION_READINESS.md), Daten in [DATASET_REPORT.md](DATASET_REPORT.md). Frühere offene Punkte unten sind historische Zwischenstände. Freigabe zum Langlauf steht aus.

# Implementierung und technische Validierung

Stand 24.10.2026. **Kein Produktionslauf gestartet; Konzept noch nicht produktionsbereit.** Implementiert ist ein bewusst gesperrter B0/B-Vorbereitungskern, kein vorgetäuschter vollständiger Trainingsevaluator. Historische Rohdaten, Checkpoints und Produktionsskripte wurden nicht verändert. Der Hauptagent hat historische Berichte separat um die dokumentierte Messkorrektur ergänzt.

## Implementierte Dateien

- `transition_pilot.py`: explizite N3/N4-Sammlungsallowlist, zeitlich kausale Extraktion, Quellen-/Teacherhashes, Familien-/Splitprüfung, Qualitätsmetadaten, Übergangssampler und gepaarter Optimizer-Smoke. Default dry-run. `--train` bricht vor jedem Update ab.
- `native_collector.py`: neuer technischer Collector mit nativen Grasp-Signalen, korrekt aufgelösten Grippergeometrien, synchronisierten Pre-/Postzuständen und Restorationsprüfung. Default dry-run; `--smoke` maximal400Frames, technische Seeds498001/498002 ausschließlich, keine Trainingsdaten.
- `test_transition_pilot.py`:17 zielgerichtete Invariantentests.

## Wesentliche gefundene und behobene Fehler

**Historische Fingerkontaktmessung ist unzuverlässig.** Die reale Umgebung liefert `robots[0].gripper` als dict. Die alte Übergabe des dict an `env.check_contact` fragt damit nicht die tatsächlichen Fingergeometrien ab. Neue Messung aggregiert ausdrücklich `gripper.values()` und ihre `contact_geoms`. Native Grasp-Prüfung benutzt die dafür geeignete `_check_grasp`-API. Der neue untere Präfix verlangt zusätzlich explizite Fingerkontaktfreiheit. Alte Fingerbools und alte Präfixwerte beweisen daher keine vollständige Fingerfreiheit; historische Dateien bleiben erhalten.

**Zustands-/Beobachtungssynchronisierung:** Nach Reset und Step werden im neuen Collector `sim.forward()` und aktualisierte Beobachtungen verwendet. Dies ist eine dokumentierte neue Messsemantik für beide künftigen Arme; keine Behauptung, historische Derived-State-Werte seien identisch. Gespeicherte Postzustände werden wiederhergestellt und Positionen sowie native Kontakte/Grasp gegen die gespeicherten Messungen geprüft.

| Auditbefund | Behebung / Abnahme | Grenze |
|---|---|---|
| P0.1 Quellen/Splits | Nur curriculum_n3/n4_cycle0; Teacherhash, Dateienhash, initial_hash und Höhe/Seed-Splitkonflikt geprüft | Kein generisches Einlesen beliebiger Testordner |
| P0.2 Post-action-Events | Event1/2 bleiben Postframes; Training beginnt start+1, neuer Sourceindex=prefix | Synthetischer Off-by-one-Test bestanden |
| P0.3 Release | Zehn unmittelbar gültige Postzustände plus Releasephase6 am Event | Keine Behauptung zehn vollständig in Phase6 verbrachter Frames |
| P0.4 Pickup |5Frames Kontakt+30mmLift nur klar benannter Proxy; native Variante verlangt bekannte Graspwerte und neue korrekt gemessene Lowerkontakte | Altdaten nicht als echte Aufnahme freigegeben |
| P0.4 Nachlauf |50 weitere Frames nur Qualitätsnachweis; Aktionsfenster endet am bestätigten Lift | Fehlender Nachlauf wird abgelehnt |
| P0.5 Sampler | Vorhandene Phase → Episode → Abschnitt → Frame; B0/B dieselben konkreten Frameids | Keine Annahme aller sieben Übergangsphasen |
| P0.6 Gewichtmasse |.50 Original +.25 Replay +.25 normalisierter Übergangsloss; Q nur im Loss | Identische Einheitsgewichte ergeben gleiche Gradienten; Skalierungsinvarianz getestet |
| P0.7 Clearance |Scoreversion strict_contact_lift_v1_no_clearance: .50 konstanter Erhalt,.25 Ruhe,.25 Zentrierung | Keine gemessene Clearance; Erhaltterm wegen harter Gültigkeit konstant |
| P1.1 Informationsgewinn | Technischer Smoke misst endliche Losses und echte Updates | MSE/Gradienten pro Teacher/Phase aller drei Parents vor Produktion noch nötig |
| P1.2 Completiondrift | Original-only BCE mit historischen Positivgewichten; Regressiontest zeigt Actorupdates können gemeinsamen Completionlogit verändern | Keine Behauptung eingefrorener Completion |
| P1.3 Evaluator | Produktion fail-closed gesperrt | Onlinebenchmark/Devselektion noch nicht implementiert |
| P1.4 Tautologie | Strenge Erhaltung und Kontaktfreiheit sind harte Gates, Scorevariation stammt aus Ruhe/Zentrierung | Mindestdispersion/ESS und ausreichende Daten fehlen |
| P2 C | Nicht umgesetzt; keine Postsignale in alten 10D-Input eingemischt | Eigenständige Architekturablation bleibt später |

## Tatsächlich durchgeführte Prüfungen

1.17 Unittests bestanden: Pre-/Postverkettung, Zukunftsinput-Korruption, ungültige Aktion, Teacheraktionskorruption, Familienleck, reservierter Split, Kontakt-/Lift-/Nachlaufnegativfälle, native Graspnegativfälle, Aktionsfenstergrenzen, Gripperdict-Geometrie, Samplerpaarung, Gewichtmasse/Gradienten, strikt positive endliche Gewichte, Form-/Leermengenfehler und indirekte Completiondrift.
2.240 historische Sammlungsdateien eingelesen und Inputs aus Pre-action-Beobachtungen rekonstruiert. Alle Teacherdateien entsprechen den Herkunftshashes. Original-HDF5 entspricht `5222cbf96dc6218389d491fe7b99449295dcfc9bceb3bab8f8776ffff19fe6f8`.
3. Alle gespeicherten Aktionen dieser240Episoden wurden auf CUDA mit dem jeweiligen tatsächlichen Teacher einzelbildweise nachgerechnet; Toleranz1e-5. Ergebnis `prepared_action_audit_v1/manifest.json`. Das prüft Aktionen, **nicht** die inzwischen als mangelhaft erkannte historische Kontaktmessung.
4. Frühe rein geometrische Proxyextraktion fand84Episoden mit Fenstern. Artefakte `prepared_proxy_v1` und `prepared_action_audit_v1` sind **überholt und nicht trainingsbereit**. Nach zusätzlicher fünf Frames bestätigter Kontakt-plus-Lift-Anforderung verbleiben **0 akzeptierte Fenster** (`prepared_contact_lift_v2`). Das ist kein bewiesenes physisches Scheitern aller Übergänge, sondern ein Daten-/Messproblem: historische Kontaktbools fehlen verlässlich.
5. Je3 echte CPU-Optimizerupdates für B0/B, identische Parents und Frameids, endliche Losses, geänderte Parameter sowie gespeicherte/zurückgeladene Modell-/Optimizer-/RNG-Checkpoints. Letzter Smoke `smoke_cpu_v2`. Daten stammen ausdrücklich aus den frühen geometrischen Proxyfenstern; dies validiert nur die Rechenpipeline, **keine** Lernwirkung oder Datengültigkeit.
6. Native Collector-Smokes:20Frames auf technischem Seed498001; danach eine auf höchstens400Frames begrenzte technische Episode498002 mit echten Grasp-/Fingerkontaktpositiven. Synchronisierter maßgeblicher letzter Lauf: `native_collector_smoke_v4/validation.json`. Technische Episode zählt weder als Trainingsbeispiel noch als Erfolgsratenmessung. Quellenzustände/Inputs verkettet; wiederhergestellte Positionen müssen unter1e-9m abweichen und Kontakte/Grasp exakt übereinstimmen.

## Vor einem echten Lauf zwingend offen

- Neue synchronisierte Sammlung mit real gemessenem native Grasp, expliziten Fingergeometrien, versionierter Controller-/Messsemantik und unverändert vorab zugewiesenen Familien/Splits. Alte technischen Episoden sind ausgeschlossen.
- Mindestzahlen und Vielfalt entsprechend `training_plan.json`; kein automatisches Lockern bei Nullabschnitten. Qualitätsverteilungen, train-only Normalisierung, ESS und Beiträge je Teacher/Familie berichten.
- Ausgangs-MSE/Gradienten und Completiondiagnostik aller drei Parents, nicht nur ein Optimizer-Smoke.
- Online-Übergangsbenchmark mit vollständigem Simulator-/Controllerzustand und technisch belegter Restore-Reproduktion; vollständige neue3er/4er-Rollouts zusätzlich. Held-out-Testfamilien getrennt und einmalig nach Freeze.
- Devchecks bei0/3k/10k, Parent als Nullupdatekandidat, dokumentierter Tie-break, Endmodellfreeze; danach unabhängige Tests. Das reine Offline-MSE darf die Auswahl nicht ersetzen.
- Produktionsorchestrator mit unveränderlicher Deadline, gehashten Quellen/Plan, Stop-/Resume-Semantik und genau einem Coordinator. `--train` bleibt bis dahin gesperrt; `--plan` ist reserviert und aktiviert keinen Lauf.

Damit ist die **Grundidee technisch präzisiert**, ein bislang versteckter Messfehler gefunden und im neuen Collector behoben. Eine Verbesserung der Stapelrate ist damit noch nicht nachgewiesen.



## Abschließende Integration durch den Hauptagenten

Die17Tests wurden nach dem letzten Gewichtvalidierungsfix unabhängig erneut ausgeführt(root_unit_tests.log). training_plan.json und TRAINING_RUN_PLAN.md verwenden dieselbe tatsächlich implementierte Scoreversion(.50Erhaltkonstante/.25Ruhe/.25Zentrierung). Die alte fünfteilige Darstellung ist ein späterer Vorschlag, kein vorgetäuschter aktueller Score.

AUDIT_SIGNOFF.md bestätigt Daten-/Lernkern und Produktionssperre unabhängig. Für vollständige vorbereitete Replays fehlen ausdrücklich Sequencer.pair und interner Roboter-/OSC-Controllerzustand. Die bestandene Positions-/Kontaktrestauration ist deshalb keine Behauptung identischer nächster Controlleraktionen. Weitere gültige Native-Daten, Onlineevaluation/Devselektion und Produktionsaufsicht bleiben offen.
