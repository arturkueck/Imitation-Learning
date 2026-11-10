# Startprüfung abgeschlossen – Freigabe ausstehend

Alle vorab definierten Daten- und Signalprüfungen sind bestanden. Verbindlicher Plan ist READY_PLAN_v2.json; START_READINESS.json bindet dessen Hash. Es existiert keine Startfreigabe und kein produktiver Trainingsprozess.

- 200 neue Episoden; 49 Trainings- und 32 Validierungsabschnitte, getrennte Familien und drei Teacher.
- 49 technische Tests bestanden. Zusätzlich wurden auf dem echten eingefrorenen Datensatz alle sechs Modelle mit je drei GPU-Updates geprüft. Diese technischen Modelle werden verworfen; der Langlauf startet aus den ursprünglichen Parents.
- Fehlerhafte Greifer-Dictionary-Kontaktabfrage korrigiert; native Grasp-/Kontaktlabels, vollständiger Zustandsreplay, Onlineauswertung, gemeinsame Checkpointauswahl und persistierte Teilresultate implementiert.
- Datensatz, Originalarrays, Replayepisoden, Parents, Benchmarks und tatsächlich importierter Simulatorcode sind per Hash gebunden. Änderung verhindert den Start.
- Ein Supervisor, Prozesssperre, feste Deadline, Teilresultate bei Timeout und Wachhaltefreigabe sind vorbereitet. Keine automatische Wiederholung reservierter Tests.

## Konkreter freizugebender Lauf

Sechs Modelle: B0 und B aus denselben drei Parents, je maximal 10.000 Updates. Batch 64, Lernrate 3e-5; 50 % Original, 25 % bisheriger Replay, 25 % neue sichere Übergänge. B0 nutzt Einheitsgewichte, B ausschließlich Qualitätsgewichte auf dem neuen Viertel. Dieselben Samples und Controller in beiden Armen; keine neuen Skriptexpertenaktionen, kein RL, keine zusätzliche Sicherheitssteuerung. Die vorhandenen sieben Phasen und der vorhandene Sequencer bleiben identisch.

Maximal acht Stunden ab ausdrücklichem Go: spätestens nach fünf Stunden Optimierung/Entwicklung beenden, drei Stunden für Bestätigung, reservierte Tests und Bericht vorsehen. Wenn Tests das Budget überschreiten, ehrlich Teilresultate ausweisen; Deadline nicht verlängern. Agentkontrolle einmal pro Stunde, nur wesentliche Änderungen melden. Der technische Supervisor kontrolliert unabhängig die Prozessdeadline.

Auswahl auf Entwicklung bei 0/3000/10000 Updates, einschließlich unverändertem Parent als Nullupdate-Kandidat. Alle sechs Modelle vor Bestätigung und reservierten Endtests gemeinsam einfrieren. Primär Turmerhalt während nächster Aufnahme; vollständige Zwei-/Drei-/Vierertürme separat. Vorbereitete Türme sind keine vollständigen Stapelerfolge. Kein Fünfertraining und kein versprochenes 90-%-Ergebnis.

## Unvermeidbare Unsicherheit

Die Qualitätsgewichtung ist nur moderat verschieden; nur acht Trainingsabschnitte enthalten bereits drei gestapelte Würfel. Ein Nullergebnis ist plausibel. Die kleinen und teilweise nicht vorbereitbaren Entwicklungspanels liefern begrenzte Aussagekraft; ihre Coverage und bedingte Leistung müssen separat berichtet werden. Dieser Pilot prüft zunächst Gewichtung, nicht die zusätzliche Architektur mit expliziten Turmfeatures.

Webdaten sind gefunden, aber nicht direkt kompatibel. Eine Retargeting-Pipeline wäre ein eigener Versuch. Details: PUBLIC_DATASET_REVIEW.md. Messzahlen und Datensatzgrenzen: DATASET_REPORT.md.
