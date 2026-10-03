# Arbeitstags-Lauf, 01.10.2026

Ziel: neue, vergleichbare Erkenntnisse innerhalb von sieben Stunden. Der produktive Lauf endet spätestens nach rund 6,5 Stunden; Ergebnisse werden bereits nach jedem Modell und jeder Auswertung geschrieben. Eine erfolgreiche Policy kann nicht vorab garantiert werden.

- StackTwo: ausschließlich zwei 4-cm-Würfel, grün B auf rot A, losgelassen und 0,5 Sekunden stabil. Dieselbe Platzierungsverteilung und Kameraperspektive wie bisher. 200 neue erfolgreiche Demos, Aufteilung 180/20.
- Drei RNNs, je bis zu 400 Epochen: Vision mit 5 Schritten Kontext; Vision mit 20 Schritten; Objektpositionen und Propriozeption mit 20 Schritten. Objektpositionen sind ein Diagnosebenchmark mit privilegiertem Simulatorwissen.
- Square: neues RNN-GMM, bis zu 400 Epochen. Bisheriges RNN mit Punktvorhersage (40 % bei 20 Tests) ist die Referenz. Keine unveränderte Fortsetzung des schwächeren Transformers oder BC.
- GMM-Validierung: Likelihood mit gelernter Varianz berechnen; die sehr kleine Streuung für Rollout-Aktionen verfälscht sonst den Validierungs-Loss. Die lokale Trainingskorrektur verändert nicht die spätere Aktionsausgabe.
- Alte Square-Modelle BC, RNN und Transformer sowie frühere beste StackFour-Checkpoints werden erneut geprüft. Handover wurde auf Datenbereitschaft geprüft: ein Demonstrationsdatensatz / validierter Expert fehlt weiterhin, daher kein Training.
- Neue Checkpoints werden alle 50 Epochen gespeichert. Der unter diesen Checkpoints beste Validierungsstand und der letzte Stand werden auf 15 Entwicklungsepisoden verglichen. Der so gewählte Checkpoint erhält 50 Tests auf neuen Seeds. Identische Anfangszustände werden für Vergleiche derselben Aufgabe geprüft. Dadurch bleibt der zusätzliche Speicherbedarf auf wenige GB begrenzt.
- Der auf Entwicklungsepisoden beste visuelle StackTwo- und Square-Kandidat erhält je 12 Robustheitsbedingungen mit 10 gepaarten Episoden. Der Objektpositions-Benchmark wird nicht als visuell störungsrobust dargestellt.
- Zusätzlich zum Gesamterfolg werden Greifen, Anheben, korrekt abgelegte Paare und versehentlich angehobener Basiswürfel gemessen.
- Alle neuen Videos zeigen vier Perspektiven und zwei zusätzliche Sekunden. Es werden repräsentative Rollouts aufgenommen, nicht jede Episode.

Dateien: `RESULTS.md` (laufende Übersicht), `status.json`, `logs/`, `evaluation/`, `videos/`, `robustness/`. `prior_results_audit.json` enthält die überprüften bisherigen Ergebnisse. `smoke/` enthält technische Vorabtests, keine Leistungsbewertung.

Der Pipeline-Prozess ist vom Agenten und Terminal entkoppelt. Er hält Windows während des Laufs wach; der Bildschirm darf ausgehen. Der Rechner muss eingeschaltet bleiben. Bei einzelnen Fehlern werden vorhandene Checkpoints und Teilergebnisse erhalten, und unabhängige Schritte fortgesetzt. Prozessfehler sind im Bericht sichtbar.
