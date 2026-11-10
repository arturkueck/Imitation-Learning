> **Abschluss der Vorbereitung:** Alle Startgates bestanden; aktuelle Abnahme in [EXECUTION_READINESS.md](EXECUTION_READINESS.md), Daten in [DATASET_REPORT.md](DATASET_REPORT.md). Frühere offene Punkte unten sind historische Zwischenstände. Freigabe zum Langlauf steht aus.

# Unabhängige Schlussabnahme des vorbereiteten B0/B-Kerns

24.10.2026. Erneut read-only geprüft: `transition_pilot.py`, `native_collector.py`, `TRAINING_RUN_PLAN.md`, `training_plan.json` und `IMPLEMENTATION_VALIDATION.md`. Diese Abnahme hat keine Simulation oder Optimierung gestartet und bestätigt keine empirische Lernwirkung. Die17 bestandenen Tests und technischen Smokes sind im Implementierungsbericht dokumentiert; hier wurden die aktuellen Codepfade unabhängig gelesen.

## Technisch geschlossen beziehungsweise sauber begrenzt

- **Gepaarte Intervention:** B0/B erhalten im Smoke dieselben konkreten Inputs/Labels und Samples. Nur Gewichte des neuen Übergangsanteils unterscheiden sich. Actorloss ist ausdrücklich0,50 Original +0,25 Replay +0,25 gewichteter Übergangsloss; die Normalisierung durch die Gewichtssumme bleibt im letzten Viertel. Positive/endliche Gewichte, Formen und Leermengen werden geprüft. Der train-only konstante Gewichtsnormalisator verändert diesen Loss nicht nochmals.
- **Sampler:** Nur verfügbare Phasen werden gezogen, danach Episode/Abschnitt/Frame. Kein Qualitätssampling zusätzlich zum gewichteten Loss; keine vorausgesetzte Vollständigkeit aller sieben Phasen.
- **Timing:** Post-action-Ereignisse werden nicht als Pre-action-Inputs benutzt. Trainierbares Fenster beginnt nach Release und endet einschließlich bestätigter Pickupaktion;50FrameNachlauf dient nur Qualitätsmetadaten.
- **Quellen:** Historische Inventur ist auf die beiden N3/N4-Sammlungsordner beschränkt, Split-/Familienkonflikte und Teacherhashes werden geprüft. Keine historischen Endtestrollouts werden als neue Trainingslabels eingelesen. Die alten C-Modellpfade unter `final_test` sind eingefrorene Teachergewichte, keine Freigabe der dortigen Testepisoden.
- **Historische Nativeflags:** Historische Extraktion setzt `verified_grasp=False`. Native Extraktion verlangt zusätzlich `row.native_collector=True` und passende Known-/Heldformen; historisches Fingersignal wird nicht still in Nativewissen umbenannt. Der derzeitige historische Bestand ergibt nach Kontakt-plus-Lift-Kriterium0 akzeptierte Fenster; das wird ausdrücklich als Mess-/Datenproblem beschrieben, nicht als0% physische Übergangserfolgsrate.
- **Kontaktkorrektur:** Neuer Collector löst das Gripperdictionary in konkrete Modelle und `contact_geoms` auf, prüft diese Kontaktgeometrien und ergänzt die alte Präfixmetrik um echte Finger-/Handkontaktfreiheit. Native Graspprüfung verwendet die dafür geeignete API. Die alte Implementierung und ihre Zahlen bleiben erhalten und werden nicht als korrigierte neue Erfolgsquoten ausgegeben.
- **Synchronisierung:** Neuer Collector synchronisiert Derived-State-Werte nach Reset und Step, speichert Pre-/Postzustände und prüft restaurierte Positionen/Kontakte/Grasp. Die geänderte Messsemantik wird gegenüber historischen Daten offen benannt.
- **Keine vorgetäuschte Produktionsbereitschaft:** Planstatus `DESIGNED_NOT_ACTIVATED`, `production_enabled=false`; `--train` bricht vor Updates hart ab; Default ist dry-run. Technische Seeds und Smokeoutputs sind ausdrücklich von Training/Modellwahl/Erfolgsraten ausgeschlossen. C, neue Phasen und Clearance bleiben eigene spätere Faktoren.

## Weiterhin verbindliche Produktionsblocker

1. Neue synchronisierte Native-Sammlung durchführen, vor Optimierung einfrieren und sämtliche Familien-/Teacher-/Qualitäts-/Aktionsgates tatsächlich bestehen. Der kurze positive Kontaktsmoke ersetzt weder ausreichende Datenmenge noch neue unabhängige Rollouts.
2. Qualitätsscore-Streuung, ESS und neue Actorgradienten je Parent/Phase/Teacher messen. Der konstante Erhaltterm erzeugt keine neue Information; gutes Sampler-/Lossverhalten beweist keine vorteilhafte Gewichtung.
3. Unabhängiger Online-Übergangsevaluator, neue Vollrollouts und ausschließlich entwicklungsbasierte Checkpointwahl fehlen. Der heutige `--train`-Blocker ist deshalb richtig und darf nicht lediglich entfernt werden.
4. **Vollständige Replayidentität ist noch nicht implementiert:** Der Collector speichert Phase, Schritte, Anker, Stage und Retreat, aber nicht `Sequencer.pair` und keinen vollständig serialisierten internen Roboter-/OSC-Controllerzustand. Die im Plan geforderte vorbereitete Startrestauration muss diese Größen rekonstruieren oder ausdrücklich speichern und anschließend erste Aktion plus nächsten Zustand reproduzieren. Das reine Restaurieren von MuJoCozustand und Würfelpositionen erfüllt diese Abnahme nicht.
5. Produktionsorchestrator, verbindliche UTC-Deadline, Quellenfreeze und unabhängig geprüfter Prozessabschluss fehlen. Die vorgeschlagenen acht Stunden sind keine aktivierte Deadline. Das relativ umfangreiche Endtestpanel muss vor Aktivierung anhand realer technischer Laufzeiten auf Machbarkeit geprüft werden; sonst Budget vorab gleichmäßig reduzieren, nicht einen Arm nachträglich kürzen.

## Urteil

**Bedingte Abnahme des dokumentierten Konzepts und des technischen Vorbereitungskerns; keine Freigabe eines vollständigen Trainingslaufs.** Der gewählte B0/B-Vergleich kann den Beitrag der Qualitätsgewichtung isolieren. Erst neue verifizierte Daten und eine valide Onlineevaluation ermöglichen eine Aussage über bessere Übergänge oder Stapelerfolge. Die Dokumentation macht diese Grenze zutreffend sichtbar.
