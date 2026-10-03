# Prüfung der Stapel-Daten und Diffusion-Fehler

Die laufende Square-Diffusion wurde nicht beendet, neu gestartet oder im Speicher verändert. Die Prüfung lief separat, ohne GPU-Training. Gespeicherte Datensätze und Checkpoints blieben erhalten.

## Demonstrationen und Schnittstelle

Je drei Demonstrationen aus Training und Validierung wurden mit ihren gespeicherten Aktionen vom gespeicherten Anfangszustand erneut simuliert: **6/6 erfolgreich**. Die Simulationszustände sind dabei nicht bitgenau identisch; die maximale gemessene Abweichung enthält auch Geschwindigkeiten und Controller-Effekte. Der Replay-Erfolg zeigt, dass diese Trajektorien grundsätzlich ausführbar sind.

Bei Wiederherstellung der aufgezeichneten Zustände passen die numerischen Beobachtungen weitgehend (maximal etwa 0,00056 über die geprüften Größen). Bildvergleiche bei Anfang, Mitte und Ende ergaben geringe mittlere Abweichungen, höchstens etwa 1,01 von 255 Graustufen. Eine vertikale Spiegelung wäre dagegen deutlich schlechter. Kein grober Bildformat-, Koordinaten- oder Aktionsversatz erkennbar. Die zusätzliche Videokamera-Einrichtung verändert die Policy-Kamera `agentview` nicht.

Die Expert-Aktionen sind außerhalb kleiner Abweichungen an Phasengrenzen reproduzierbar. In einem Demo unterscheidet sich bei rekonstruierten Beobachtungen der Öffnen/Schließen-Zeitpunkt; der Expert verwendet eine interne Phase und gespeicherte Ziele, die nicht separat im Datensatz enthalten sind. Ein reiner Zustand identifiziert diese zeitabhängigen Entscheidungen nicht immer eindeutig. Das ist ein plausibler Lernengpass, kein Nachweis fehlerhafter Erfolgslabels.

## Gesichtete Videos und Phasenwechsel

Bei Diffusion Vision, Seed 26000, wird B gegriffen und später Richtung A bewegt, aber nicht zuverlässig auf A losgelassen. Die State-Variante verharrt im Bereich des grünen Würfels statt die vollständige Sequenz zu erledigen. Diese Beispiele sprechen für Probleme bei Phasenwechseln und Ablaufsteuerung. Die Sichtung einiger Videos ist keine allgemeine Erfolgsquote. Die Kontaktbilder liegen neben diesem Bericht.

## Nachgewiesener Scheduler-Fehler

Die lokale robomimic-Funktion `run_epoch` ruft `on_gradient_step()` nach **Trainings- und Validierungsbatches** auf. Der batchweise Cosine-Scheduler der Diffusion Policy zählt deshalb bei 100 Trainings- und 20 Validierungsbatches **120 statt 100 Schritte pro Epoche**. Die Konfiguration plant hingegen 300×100=30.000 Schritte. Dadurch wird das Lernratenminimum bereits ungefähr bei Epoche 250 erreicht; danach steigt die Cosine-Lernrate wieder. Das passt zu den tatsächlichen Trainingslogs. Der niedrige Diffusion-Loss ist ein Entrauschungsverlust und keine direkte Garantie für gute Roboteraktionen.

Ein separater Test mit dem echten Epoch-Runner bestätigt: zwei Trainings- plus zwei Validierungsbatches erzeugen zuvor vier Scheduler-Schritte bei nur zwei Optimizer-Schritten. Mit der Korrektur entstehen genau zwei Scheduler-Schritte. Die neue, opt-in Trainingsdatei `train_model_corrected.py` schaltet den Scheduler nur im Trainingsmodus weiter. Bereits laufende Prozesse werden dadurch nicht verändert.

## Gezielter nächster Vergleich

Ein zusätzlicher Lauf wird unter `experiments/stack_followup_20261001` vorbereitet und wartet auf den vollständigen Abschluss des bestehenden Prozesses:

- State-Diffusion erneut mit identischen Daten, Architektur, Seed und 300 Epochen, ausschließlich mit korrigiertem Scheduler.
- Bisherige und neue Gewichte jeweils mit 8 bzw. **2 Aktionen** pro Neuplanung vergleichen (0,4 bzw. 0,1 Sekunden bei 20 Hz). Die Änderung des Ausführungshorizonts benötigt keine Änderung der Gewichte.
- Je Variante 20 Episoden auf identischen neuen Anfangszuständen, Teilstufenmetriken und Vierer-Ansicht-Videos mit zwei Sekunden Nachlauf.

Damit wird getrennt geprüft, ob der Scheduler und häufigeres Nachplanen helfen. Erst danach ist ein zusätzliches Training für eine vereinfachte Greifaufgabe begründet. Es wird kein paralleles GPU-Training zum bestehenden Lauf gestartet.

Rohdaten: `demo_replay.json`, `scheduler_check.json`, `scheduler_check.log`; Kontaktbilder: `dp_vision_0_grid.png`, `dp_state_0_grid.png`, weitere `*_grid.png`.
