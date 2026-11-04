# Q1: Qualität bestehender 3D-Rekonstruktionen lernen

Nach Nutzerfreigabe am03.11.2026 um16:17 Uhr Berlin gestartet; feste Deadline04.11.2026 04:17 Uhr. Aktueller Stand in `prepared_001/RUN_STATUS.md` und status.json. Versiegelter Plan: `prepared_001/config.json`. Keine Änderungen an Vision-Gewichten, Kameraregeln oder Geometrieoptimierung. Der neue Kopf gehört zum Bereich Vision und bewertet die Rekonstruktion; er bewertet weder die physische Stabilität einer Platzierung noch steuert er Gelenke.

## Entscheidung aus dem Benchmark

Die100-Szenen-Evaluation zeigt: Geometrie verbessert den Mittelwert, aber19/100 Szenen werden materiell schlechter;76/357 angenommene lokale Objektkorrekturen sind schädlich. Die Kameraausrichtung funktioniert, die Übernahmeprüfung ist noch unzuverlässig. Daher zuerst **Qualität und Übernahme lernen**, erst danach den Aufnahmebedarf beziehungsweise Nutzen einer weiteren Seite trainieren. Bei gleichzeitiger Änderung dieser Module wäre unklar, ob bessere Bilder, bessere Geometrie oder bessere Auswahl den Unterschied verursacht haben.

Q1 entscheidet je erkanntem Objekt zwischen Anfangsschätzung und den bereits erzeugten Vorschlägen nach Seite1/2. Ein besser bewerteter älterer Vorschlag bleibt verfügbar. Die Auswahl wird nicht in die Vorschlagserzeugung zurückgespeist: deren Zustände bleiben eingefroren und entsprechen damit der Trainingsdatenverteilung. Die Kameraregel bleibt für die Erhebung unverändert; beide Seiten werden soweit möglich als Vergleichsdaten aufgenommen.

## Modell

48 beobachtbare, deklarierte Merkmale → Linear128 → GELU → Dropout0,1 → Linear64 → GELU → Dropout0,1 → Linear4. **14.788 trainierbare Parameter pro Modell**, drei Seeds1/2/3, anschließend gleichgewichtiges Ensemble. Zwei versteckte Schichten, keine neue CNN. Die bestehende visuelle Merkmalsverarbeitung bleibt im eingefrorenen B-Ensemble.

Ausgabe: drei Klassenlogits für schädlich/neutral/hilfreich sowie ein linearer erwarteter Gewinn. Die Wahrscheinlichkeiten entstehen erst durch Softmax samt nachgelagerter Kalibrierung. Features: Ensemble-Konsens/-Abweichung, geschätzte Größen und Form, Pose-/Größenänderung, Trackinglänge, Reprojektionsfehler, Parallaxe, Punktwolkenkondition, Oberflächenabstände, Bildkantenkonsistenz und bekannte Tischhöhe. Vollständige Reihenfolge in q_features.NAMES. Keine GT-Objektpositionen und keine zukünftigen Aufnahmen in den Eingaben. Die nach einer Aufnahme beobachtete Bildkonsistenz ist zulässig, denn Q1 entscheidet **nach** der Aufnahme über die Geometrieübernahme.

## Zielwerte und Loss

Simulations-GT erzeugt nur Zielwerte: Gewinn = Fehler der Anfangshypothese minus Fehler des Kandidaten, auf einer festgehaltenen anfänglichen Objektzuordnung. Lokales Fehlermaß: Positionsabstand in Millimetern +0,25×symmetriebewusste Eck-RMSE. Gewinn <−1 bedeutet schädlich, >+1 hilfreich, sonst neutral. Nicht zugeordnete Erkennungen erhalten kein lokales Trainingslabel; die Gesamtbewertung enthält dennoch alle fehlenden/zusätzlichen Objekte. Q1 kann Objektzahlen nicht korrigieren.

Loss: familiengewichtete Cross-Entropy mit Klassenkosten[3,1,1] +0,5×Huber-Loss auf dem durch10 skalierten Gewinn (Ziel für Regression auf±25 begrenzt, Huber-Delta0,5). Familiengewichtung verhindert, dass Szenen mit vielen Objekten/Versionen die Loss allein dominieren. Feature-Normalisierung ausschließlich aus dem neuen Trainingssplit, Begrenzung der normalisierten Werte auf±8. Rohwerte und unbeschnittene Zielgewinne bleiben erhalten.

## Neue Daten und saubere Trennung

| Rolle | Neue Familien | Verwendung |
|---|---:|---|
| Request-Train |2.000|Gewichte und Feature-Normalisierung|
| Request-Validation |400|Checkpointwahl und Early Stopping|
| Calibration/Temperature |200|Temperatur und Klassenbias des Ensembles|
| Calibration/Policy |200|Schwelle für Übernahme, bei unveränderten Gewichten|
| Calibration/Audit |200|Unabhängige Prüfung der bereits fixierten Schwelle|
| Reserved-Test |400|Einmalige Endbewertung, erst nach bestandenem Audit|

Zusätzlich vier neue Entwicklungsfamilien für den bereits ausgeführten technischen Preflight; diese fließen nicht ins Training ein. Hauptplan insgesamt3.400 frische Familien; alle Ansichten, Objektvorschläge und beide Seiten derselben Familie bleiben in derselben Rolle. Kein Replay alter Trainings-, Validierungs- oder Benchmarkfamilien für Q1. Die bisherigen100 Benchmark-Szenen bleiben Entwicklung und sind für den neuen Trainingssplit gesperrt.

Historischer Identitäts-/RGB-/Geometrieindex, neue getrennte Seed-Namensräume, transaktionale Inhaltsansprüche und versiegelte Roh-/Featuremanifeste sichern die Trennung. Historische Daten werden nur für diese Überschneidungsprüfung indexiert. Der private Erhebungsadapter trägt die richtige Rolle ins Register ein und wird im neuen Quellcodesiegel dokumentiert. Vorhandene Rohdaten oder Checkpoints werden nicht überschrieben. Bei partieller Erhebung ist eine gezielte Wiederaufnahmeprüfung nötig, kein blinder Neustart.

## Optimierung und Überwachung

AdamW, Lernrate0,001 mit Cosinus-Absenkung auf ungefähr0,0001, Weight Decay0,0001, Batch256, FP32 auf CPU, Gradient-Clipping1. Maximal80 Epochen pro Seed; Early Stopping nach10 Epochen ohne verbesserte Validierungsloss. Beste Checkpoints ausschließlich anhand der Validierungsloss. Ein ungelernter Epoche0-Checkpoint darf nicht als trainierter Kopf freigegeben werden.

Pro Seed: Train-/Validation-/feste Train-Probe-Loss, Epochen, Updates, beste und letzte Checkpoints. Plots in loss.png während und nach dem Training. Die feste Probe umfasst die ersten128 Trainingsfamilien mit verfügbaren Beispielen und verwendet Evaluationsmodus. Wegen Dropout kann sie niedriger als die laufende Trainingsloss liegen. Das ist allein kein Overfittingbeleg.

## Übernahme und ehrlicher Erfolgs-Gate

Unveränderte harte Geometrie-/Beobachtungsprüfungen bleiben Voraussetzung (unter anderem endliche, konvergierte Anpassung, genug Unterstützung, begrenzte Poseänderung und konsistente Ausgangsansichten). Nur die bisherige reine Kantenverbesserungsschwelle wird durch den gelernten Qualitätsentscheid ersetzt. Zwischen zulässigen Vorschlägen entscheidet vorhergesagter Gewinn; bei Gleichstand gewinnt der ältere. Ohne ausreichend hilfreichen/risikoarmen Vorschlag bleibt die Anfangsschätzung.

Kalibrierungsrollen sind getrennt:200 Familien für Temperatur/Klassenbias, andere200 für eine vorab festgelegte Risikoschwellenliste. Mindestkriterien: hilfreiche Wahrscheinlichkeit≥0,5, vorhergesagter lokaler Gewinn≥1 mm-äquivalent, empirisch höchstens5 % materiell verschlechterte Familien, Änderungen in mindestens20 % der Familien und mindestens30 geänderte Familien sowie besserer mittlerer Szenenfehler als die Anfangsschätzung.

Weitere200 Auditfamilien prüfen die unveränderte Wahl. Es werden auch95-%-Wilson-Intervalle auf Familienebene berichtet. Die5-%-Marke ist ein **empirisches Simulationsziel**, keine reale Sicherheitsgarantie. Scheitern Risiko, Nutzen oder Abdeckung, bleibt Q1 ein Forschungsartefakt: keine Lockerung der Schwellen, kein automatisches Weitertraining und kein Öffnen des Endtests. Ein trivialer Kopf, der alles ablehnt, besteht die Abdeckungs-/Nutzenanforderung nicht.

Nach bestandenem Audit:400 frische Endtestfamilien, keine weitere Checkpoint-/Schwellenwahl. Berichtet werden Risiko, Nutzen, Abdeckung, Konfusionsmatrix, Kalibrierung und Vorher-/Nachher-Fehler. Die ursprünglichen Rohdaten enthalten ebenfalls den Vergleich zum alten RGB-Gate sowie Objektzahl/Anordnung/lange Quader für getrennte Abschlussberichte. Endtests dürfen später nicht für Nachtraining umgeteilt werden.

## Zeit und Startfreigabe

Geplant sind **maximal12 Stunden ab tatsächlichem Start**, einschließlich Erhebung und Auswertung. Die100-Szenen-Evaluation benötigte mit zwei Workern949,85 Sekunden; lineare Hochrechnung für3.400 Familien etwa9 Stunden. Das ist eine Größenordnung, keine Zusage. Der neue Kopf selbst ist klein und wird voraussichtlich nur Minuten benötigen; die Bildfolgen/Geometrie sind der Hauptaufwand. Zwei Worker, da vier die Windows-/CUDA-Speichergrenze überschritten.

quality.py start verlangt explizit --start-training und ein festes Budget. launch.ps1/runtime.py bereiten einen unabhängigen Hintergrundprozess mit Wachhalten und eigener Deadlineüberwachung vor. Fünf Minuten vor Ablauf kontrollierter Stopp, bei Ablauf Ende ausschließlich der zugehörigen Prozessfamilie. Keine automatische Wiederholung oder Verlängerung. Ein zweistündlicher Agenten-Watcher kann beim freigegebenen Start eingerichtet werden; normale Zustände bleiben still.

Der abgeschlossene Preflight hatte nur neue Entwicklungsdaten erzeugt und einen untrainierten Kopf vorwärts geprüft. Anschließend hat der Nutzer diesem konkreten Plan zugestimmt. Der jetzt gestartete Lauf beginnt mit neuer Datenerzeugung; neuronale Updates und bestandene Qualitäts-Gates sind ausschließlich aus den tatsächlichen späteren Artefakten abzulesen.
