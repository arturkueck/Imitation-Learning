# Diagnose: Zeitmerkmal der letzten Freigabephase

Am 12.11.2026 wurden vorhandene Trajektorien ausgewertet und eine begrenzte
Simulation mit null Optimizerupdates durchgeführt. Bestehende Gewichte,
Trainingsdaten, Koordinator und Erfolgskriterium wurden nicht verändert.

## Konkreter Befund

Das Trainingsarray enthält in Phase 6 Zeitmerkmale von 0 bis 0,85, entsprechend
0 bis 17 Steuerschritten. Die vorhandene Policy erhöht den Phasenzähler weiter
und begrenzt ihn erst bei 100 Schritten (Zeitmerkmal 5). Der strenge
Aufgabenerfolg verlangt 50 aufeinanderfolgende gültige Frames. Die letzte
Freigabephase muss dadurch deutlich länger ausgeführt werden, als ihre
Demonstrationsdaten abdecken.

In der ausgewählten Szene 2026115004 gelingt die 30k-Ausführung aller sechs
Modellvorgeschichten, während die gewöhnliche 60k-Fortsetzung scheitert. Die
60k-Modelle erreichen zunächst 44 bis 47 aufeinanderfolgende gültige Frames.
Danach geht die Gültigkeit verloren. Beim vollständig instrumentierten
`mixed_seed1` werden die Z-Befehle zunehmend negativ; ab Freigabeschritt 52
berührt ein Finger den obersten Würfel erneut. Zu diesem Zeitpunkt bestehen
die Würfelkontakte und die Geometrie ist noch nahezu passend. Das ist genauer
als die frühere Vermutung eines sofortigen Zusammenbruchs nach dem Öffnen.
Die kurze Gültigkeitsunterbrechung um Freigabeschritt 5 tritt auch in
erfolgreichen Ausführungen auf und erklärt den späteren Unterschied nicht.

## Kontrollierter diagnostischer Eingriff

Alle 24 bereits ausgewählten historischen Modell-/Szenenkombinationen wurden
erneut simuliert. Nur in Phase 6 der zweiten Platzierung wurde das an die Policy
übergebene Zeitmerkmal bei dem aus den Trainingsdaten abgeleiteten Maximum
(17 Schritte) begrenzt. Tatsächliche Episode, physikalische Zeit, Stabilitätszähler
und maximale Episodenlänge laufen unverändert weiter.

Eine vollständige Basiswiederholung stimmt bitgenau mit der gespeicherten
historischen Trajektorie überein. Für jede Intervention wurden gleicher
Anfangszustand und bitgenau gleiche Vorgeschichte bis zum ersten geänderten
Zeiteingang geprüft. Zusätzlich wurden Eingangsvektoren, Finger-/Würfelkontakte
und Geschwindigkeiten gespeichert.

Ergebnis auf diesem bewusst nach Ausgang ausgewählten Diagnosepanel:

- Kontrolle: 12 erfolgreiche Modell-/Szenenkombinationen.
- Begrenztes Zeitmerkmal: 18 erfolgreiche Kombinationen.
- Sechs Gewinne, keine Verluste gegenüber der Kontrolle.
- Alle sechs Gewinne betreffen dieselbe Startszene 2026115004 mit sechs
  unterschiedlichen Modellvorgeschichten. Das sind keine sechs unabhängigen
  neuen Szenen und kein Nachweis einer allgemeinen Erfolgsrate von 75 Prozent.
- Die übrigen sechs Misserfolge bleiben bestehen; der Eingriff erklärt nicht
  sämtliche Fehler. Nicht erreichte letzte Freigabephasen können dadurch
  beispielsweise nicht verbessert werden.

Der Versuch zeigt eine kausale Wirkung dieser Eingangsbegrenzung in der
untersuchten Szene. Er stützt Zeitextrapolation in der letzten Freigabephase
als konkrete Ursache dieses Fehlermusters. Er bestätigt weder die allgemeine
Überlegenheit eines Curriculums noch einen Nutzen für reale Hardware.

## Nächster sinnvoller Schritt

Die Eingangsbegrenzung zuerst auf einem vorab festgelegten frischen gepaarten
Szenenpanel gegen die unveränderte Policy prüfen, ohne neue Gewichte zu lernen.
Erst danach entscheiden, ob die Zeitkodierung dauerhaft geändert oder die
Demonstrationen um längere stabile Freigabe-/Halteverläufe ergänzt werden.
Beides wäre eine neue, getrennt dokumentierte Versuchsversion. Der aktuelle
diagnostische Eingriff wurde nicht in bestehende Trainingspipelines übernommen.

## Artefakte

- `probe.py`: begrenzter Simulationseingriff, 15-Minuten-Maximum, kein Retry.
- `probe_001/plan.json`: abgeleitete Grenze, Umfang und Quellhash.
- `probe_001/baseline_check.json`: exakte historische Wiederholung.
- `probe_001/results.json`, `summary.json`: einzelne gepaarte Ergebnisse.
- `probe_001/*.npz`: Zustände und Kontakte vor und nach dem Eingriff.
- `probe_001/release_clock_probe.png`: Zeitmerkmal, Z-Aktion, Stabilität und Kontakt.

Die 24 Interventionsepisoden und eine zusätzliche Basiswiederholung wurden
innerhalb von rund 92 Sekunden abgeschlossen. Keine bestehenden Ergebnisse
oder Modellgewichte wurden überschrieben.
