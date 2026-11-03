# V4-Pilot: Abschlussprüfung am 03.11.2026

## Ergebnis und Grenze

Regulär abgeschlossen um **05:05:57 Europe/Berlin**, deutlich vor der unveränderten Deadline12 Uhr. Supervisor exit0, Supervisor und Hauptworker hostseitig beendet. Keine Fortsetzung und kein weiteres Experiment gestartet.

**Seitenansicht-Training B verarbeitet zusätzliche Seitenbilder wesentlich besser als Kontrollarm A. Eine Verbesserung der ersten Schätzung durch die Zusatzaufnahme ist jedoch im Mittel noch nicht erreicht.** Das vorab festgelegte A/B-Gate ist bestanden, misst aber primär B gegen A, nicht den Gewinn gegenüber der eigenen ersten Aufnahme. Deshalb keine Freigabe einer automatischen Nachkorrektur allein aufgrund dieses Gates.

## Daten und Integrität

1.000 neue Trainingsfamilien +333 unveränderte historische V3-Trainingsfamilien als Replay;256 neue Validierungsfamilien. Die unabhängige Prüfung in dataset_freeze.json meldet null Familien-, historische und Inhaltsüberschneidungen. Alle Replayfamilien ausschließlich historisches Training. Keine Endtests zur Modellwahl verwendet oder für diesen Abschluss geöffnet.

Konfigurationssiegel und sämtliche sechs ausgewählten Checkpoint-Dateien einschließlich SHA-Sidecars am Abschluss verifiziert. Jeder ausgewählte Checkpointhash unterscheidet sich vom jeweiligen V3-Startcheckpointhash. 66 Kurvenzeilen entsprechen Epoche0 bis10 für sechs Modelle. Alle sechs Spuren A1/B1/A2/B2/A3/B3 haben tatsächlich **420 Optimizer-Updates** erreicht. Gewählte Checkpoints A: Epochen10/5/10, B:10/9/10. Die Auswahl erfolgt nach demselben ausgewogenen Validierungsloss, nicht nach Endtests.

## Quantitative Bewertung

Mittelwerte über drei Seeds, ausgewählte Validierungscheckpoints:

| Kennzahl | A: bisherige Blickrichtungen trainiert | B: Seitenansichten trainiert |
|---|---:|---:|
| Ausgewogener gemeinsamer Validierungsloss |0,22545|0,17636|
| Szenenfehler nach Seitenaufnahme, mm-äquivalent |31,4296|13,3496|
| Szenenfehler nach alter Zusatzansicht, mm-äquivalent |12,2215|12,5879|

B reduziert den Seitenansicht-Szenenfehler gegenüber A um57,53 %, verbessert ihn in3/3 Seeds und verschlechtert alte Zusatzansichten gegenüber A nur um0,3663 mm-äquivalent. Damit ist das vorab definierte Gate erfüllt. Das sind Pilot-Validierungswerte, keine unabhängigen Endtestergebnisse.

**Innerhalb B, gleiche Zielmenge im Seitenkontext:** erste Schätzung11,9487 → nach Seitenaufnahme13,3496 mm-äquivalent, also **11,72 % schlechter**. Gemittelter Positionsabstand der zugeordneten Objektzentren: initial5,7727 → Seitenbild6,7005 mm. Dieser Positionswert berücksichtigt nur zugeordnete Objekte und ist keine Roboter-Platziergenauigkeit. Der Szenenfehler enthält zusätzlich Eckengeometrie und Strafen für fehlende/zusätzliche Objekte; er darf nicht als reiner Positionsfehler bezeichnet werden.234/256 Validierungsfamilien besitzen mindestens eine tatsächlich verfügbare zusätzliche Seitenansicht; die Mittelwerte enthalten auch die übrigen Familien.

## Loss und Overfitting

Epoch10-Mittelwerte (nicht mit ausgewogenem Checkpoint-Auswahlloss verwechseln):

| Arm | Train-Loss | Gemeinsamer Validation-Loss | Feste Train-Probe, gemeinsame Kontexte |
|---|---:|---:|---:|
| A |0,14310|0,24866|0,15918|
| B |0,16210|0,19597|0,12325|

Trainingsloss und gemeinsamer Validierungsloss haben unterschiedliche Blickmischungen; ihre absolute Differenz alleine beweist kein Overfitting. Die feste Trainingsprobe verwendet dieselben Auswertungskontexte wie die Validierung und bleibt niedriger: es besteht eine Generalisierungslücke. A2 hat sein bestes ausgewogenes Validierungsergebnis bereits in Epoche5, während der Trainingsloss weiter fällt: Hinweis auf Plateau/Overfitting in dieser Spur. B2 ist in Epoche9 am besten und in10 geringfügig schlechter; B1/B3 verbessern sich bis10. Bei B kein über alle Seeds konsistenter später Validierungseinbruch. Kein zusätzlicher Lauf zur Klärung gestartet.

loss.png visuell geprüft: alle sechs Spuren und drei Lossarten vorhanden. view_metrics.png vorhanden.384 dreifarbige 3D-Überlagerungen plus Eingabebilder und Szenen-JSONs vorhanden; exemplarisch best_epoch_10.00_B_seed1_scene0001_overlay.png visuell geprüft. Das Beispiel zeigt den Stapel plausibel, aber sichtbare Abweichungen; ein einzelnes Bild ersetzt keine aggregierte Qualitätsmessung.

## Laufzeit und Artefakte

Parallele Trainingsdatenerzeugung7.921,13 s (2h12min), Validierungsdatenerzeugung1.122,22 s (18min42s), jeweils inklusive Workerstart. Das sind tatsächliche Messungen dieses Piloten, kein kontrollierter Beschleunigungsfaktor gegenüber anderen Familien im seriellen Entwicklungstest. Restliche Zeit umfasst Prüfungen, Training, Validierung und 3D-Ausgaben.

Ergebnisse: results.json; Auswahl: selection.json; eingefrorenes B-Ensemble: perception_freeze.json; alle Trainingskurven: curves.json; Plots: loss.png/view_metrics.png; Geometrie: geometry/index.json. Alle Artefakte bleiben erhalten. Website-Text in WEBSITE_RESULT_DRAFT.md vorbereitet, **nicht veröffentlicht**.

## Empfohlener nächster Entscheidungsschritt

Zunächst anhand der gespeicherten Vorher-/Nachher-Szenen erklären, welche Fälle durch die Bildfusion schlechter werden. Danach separat Aufnahmebedarf, Blicknutzen und die Ablehnung schädlicher Aktualisierungen untersuchen. Nicht jede Zusatzaufnahme ungeprüft übernehmen. Das gehört zur noch offenen Anschlussphase; dieser Pilot hat keine trainierte aktive Aufnahmeentscheidung, keine rein visuelle Kollisionsfreiheit und keine reale Robotersicherheit nachgewiesen. Unbekannte Objektformen außerhalb des Quaderprotokolls sind ebenfalls nicht validiert.
