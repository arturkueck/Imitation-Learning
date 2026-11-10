# Fehlerdiagnose: Trainings- und Validierungsrollouts

340 eingefrorene Dreierturm-Sammelversuche (240 Train, 100 Valid). Keine Endtestdatei gelesen. Keine Modelle oder Simulatoren geladen. Alle verwendeten Rohdaten vorab per SHA-256 geprüft.

## Wichtigste Befunde

- In 323/325 Episoden mit Paarwechsel endet der markierte Rückzug nach genau einem Steuerframe (20 Hz:50 ms). Das tritt auch bei Erfolgen auf und ist für sich kein kausaler Fehlernachweis.
- Bei gescheiterten Episoden mit erster bestätigter Ablage verliert das untere Präfix in97/98 Train- und43/44 Valid-Episoden später seine Gültigkeit. Sämtliche ersten Verletzungen liegen nach dem Paarwechsel in Bauabschnitt2; am häufigsten im Anflug auf den nächsten Quellwürfel.
- Die akzeptierten Fehlversuchabschnitte machen nur1.28–1.29% aller C-Actorbeispiele aus. D erhöht deren normierten Loss-Anteil lediglich auf1.31–1.32%. Der bisherige Pilot setzt diesen Teil der Idee daher nur schwach ein.
- Priorität: Rückzugsabschluss und Anflugkorridor getrennt auf frischen Entwicklungsfamilien prüfen. Eine Erweiterung der Policyeingaben ist noch kein belegter Reparaturbedarf.

## Beobachteter Fortschritt

Die Kategorien beschreiben den am weitesten erreichten bestätigten Meilenstein. Sie beweisen keine Ursache. „Transport“ ist eine zusätzliche Diagnoseheuristik (fünf gehaltene/angehobene Frames innerhalb 30 mm XY zum Ziel, Phase≥4), keine nachträgliche Erfolgsdefinition.

| Kategorie | Train | Valid |
|---|---:|---:|
| final_placement_or_stability_not_confirmed | 75 | 40 |
| first_pickup_not_confirmed | 5 | 2 |
| first_placement_not_confirmed | 5 | 2 |
| first_transport_not_confirmed | 1 | 0 |
| second_lift_not_confirmed | 4 | 0 |
| second_pickup_not_confirmed | 19 | 4 |

Train: 131/240 erfolgreich; Valid: 52/100 erfolgreich.

## Unterer Turm nach erster Freigabe

| Beobachtung, nur gescheiterte Episoden | Train | Valid |
|---|---:|---:|
| failed_with_first_release | 98 | 44 |
| failed_with_prefix_loss | 97 | 43 |
| first_prefix_loss_contact | 84 | 39 |
| prefix_loss_regained | 14 | 7 |
| failed_with_first_lift | 104 | 46 |
| failed_with_second_lift | 75 | 40 |

Die Bezugsgrößen unterscheiden sich: Freigabe/Lift beziehen sich auf alle Fehlschläge; erste Kontaktverluste und Wiedererholung auf Episoden mit Präfixverlust. Ein ungültiger Präfixframe ist kein nachgewiesener Einsturz. Einseitiger Fingerkontakt, Geschwindigkeitsgrenzen oder kurzzeitiger Kontaktverlust können ebenfalls auslösen.

Erste Präfixverletzung nach ausgeführter Aktionsphase (Mehrfachzählungen ausgeschlossen):

| Aktionsphase | Train | Valid |
|---|---:|---:|
| approach | 69 | 34 |
| close_gripper | 4 | 0 |
| descend_to_source | 18 | 6 |
| descend_to_target | 1 | 2 |
| release_wait | 5 | 1 |

Alle ersten Präfixverletzungen gescheiterter Episoden mit Verlust treten in Bauabschnitt2 auf, nicht während des als `retreat` markierten Rückzugs. Die schnell folgende Anflugbewegung ist deshalb der engere Diagnosefokus.

| Erste Verletzung: gleichzeitig gemessene Merkmale | Train /97 | Valid /43 |
|---|---:|---:|
| first_prefix_loss_speed_exceeded | 90 | 38 |
| first_prefix_loss_rotation_exceeded | 90 | 40 |
| first_prefix_loss_xy_exceeded | 1 | 1 |
| first_prefix_loss_missing_cube_contact | 0 | 0 |

Merkmale überlappen. An der ersten Verletzung bestehen die Würfelkontakte häufig noch; Geschwindigkeit und Fingerkontakt reagieren früher als ein sichtbarer Geometrieverlust. Das ist keine kausale Kollisionsrekonstruktion.

## Rückzugsabschluss vor dem nächsten Anflug

Höhenabstand ist Greiferreferenzpunkt minus Oberfläche des oberen unteren Turmwürfels. Das ist kein geometrischer Kollisionsabstand des ganzen Greifers. Quantile: Minimum / Median / Maximum.

| Split / Ausgang | N mit Paarwechsel | Davon1 Rückzugsframe | Rückzugsframes min/med/max | Höhenabstand [mm] min/med/max |
|---|---:|---:|---|---|
| train/failure | 98 | 98 | [1.0, 1.0, 1.0] | [-14.5, -13.3, -10.9] |
| train/success | 131 | 130 | [1.0, 1.0, 15.0] | [-14.5, -13.4, 99.6] |
| valid/failure | 44 | 43 | [1.0, 1.0, 16.0] | [-14.2, -13.4, 100.9] |
| valid/success | 52 | 52 | [1.0, 1.0, 1.0] | [-14.5, -13.4, -13.0] |

Im eingefrorenen Sequencer (`run_001/source_snapshot/02_runner.py`, `Sequencer.advance`) wird der normale Anflugkopf für den Rückzug wiederverwendet. Sobald dessen gelernte Phasenentscheidung die Phase0 verlässt, wird ohne zusätzliches Freiraumgate zum nächsten Paar gewechselt. Der normale Phase0-Abschluss ist damit die technische Rückzugsfreigabe. Das erklärt die Einframe-Übergänge im Kontrollfluss; ob ein anderes Gate die Gesamtaufgabe verbessert, benötigt einen separaten Vergleich.

Die Diagnose verändert diesen Controller nicht. Die gespeicherten Endwahrscheinlichkeiten und Höhengewinne pro Episode stehen in episodes.json. Greiferreferenzpunkt und Würfeloberfläche beschreiben keinen vollständigen Kollisionsabstand.

## Warum so wenige übernommene Fehlversuchabschnitte?

| Erstes Paar: Gate-Ergebnis | Train | Valid |
|---|---:|---:|
| accepted | 7 | 4 |
| no_release_event | 11 | 4 |
| prefix_interrupted_with_contact | 88 | 40 |
| prefix_interrupted_without_contact | 3 | 0 |

## Tatsächlicher Trainingsanteil der Fehlversuchabschnitte

Exakte Rekonstruktion der vorhandenen C/D-Sampler für je5000 Updates. Die Gewichte ändern den Loss, nicht die Auswahl.

| Parentseed | Fehlversuchbeispiele /80000 eigene | Anteil an allen320000 Actorbeispielen | D: normierter Loss-Anteil |
|---|---:|---:|---:|
| 1 | 4137 | 1.29% | 1.32% |
| 2 | 4130 | 1.29% | 1.32% |
| 3 | 4093 | 1.28% | 1.31% |

Qualitätsgewichte aller eigenen Trainingsabschnitte: min=0.7159, max=0.9682, Standardabweichung=0.0553. Dies ist die Verteilung pro Abschnitt, nicht pro gesampeltem Frame.

## Grenzen und nächste Entscheidung

Die aktuelle Policy sieht laut eingefrorenem method.py nur10 Werte: Greifer relativ zu gecachtem Anker(3), Greiferorientierung(4), Fingerstellung(2), Phasenzeit(1). Phase wählt einen separaten Kopf. Explizite restliche Turmgeometrie, aktuelle Objektpose und nativer Griffstatus fehlen. Diese Eingabenbeschränkung ist belegt; dass sie den konkreten Fehler verursacht, ist damit nicht nachgewiesen.

Der nächste gezielte Versuch sollte den Übergang vom platzierten Zweierturm zum Anflug auf Würfel3 untersuchen. Auf frischen Entwicklungsfamilien Abschluss des wiederverwendeten Rückzugskopfs, Greiferfreiraum und nächsten Bewegungskorridor instrumentieren. Erst bei nachgewiesener vorzeitiger Freigabe den Controller separat vergleichen; bei nicht unterscheidbaren Gefahrenzuständen die Turmeingaben separat ergänzen. Architektur, Controller und Datenstrategie nicht gleichzeitig ändern.

Die strengen bisherigen Aufnahmegates bleiben unverändert. Frühere gute Greif-/Anhebeabschnitte werden durch diese Diagnose sichtbar, sind aber ohne separat eingefrorene Labels und Prüfung noch keine neuen Trainingsdaten. Die Endtests bleiben für zukünftige Methoden-/Checkpointauswahl gesperrt.

Maschinenlesbare Details: summary.json und episodes.json; Hashnachweise: provenance.json.