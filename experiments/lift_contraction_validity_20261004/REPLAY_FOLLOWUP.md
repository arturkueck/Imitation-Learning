# Replaykorrektur vor Wiederholung der Diagnose, kein Policy-Training

Die erste Untersuchung verfehlt die unveränderte Rekonstruktionsgrenze. Der Wrapper `env.reset_to` setzt Simulatorzustand und Beobachtungen, garantiert jedoch nicht das Auffrischen zwischengespeicherter Controllerdaten. Zudem kann ein frei abgespielter Expertpräfix bereits vor dem Anker von der Aufnahme abweichen; dessen History ist dann nicht dieselbe wie in der Demo.

Gezielte Korrektur vor dem nächsten Diagnoseaufruf:

1. Gleiches XML, gleiche gespeicherte Initialzustände und gleiche Expertaktionen. Nach dem Laden die Nullraumreferenz des Armcontrollers auf die aufgezeichneten initialen Gelenkpositionen setzen.
2. Vor jeder Expertpräfixaktion den jeweiligen gespeicherten Zustand setzen und die Controllerzustandsdaten mit `update(force=True)` auffrischen. Gripperaktionen werden weiter durch den ursprünglichen Präfix aufgebaut.
3. Am Anker ebenfalls Controllerdaten auffrischen. Dann dieselben Referenz- und ±0,1-Aktionszweige ausführen.

Dies untersucht die Rekonstruktion der ursprünglichen Transitionen und ist kein neuer Trainingslauf, keine Veränderung von K und keine Lockerung der Gates. Dieselben12 Trainingsdemos,36 Anker und108 Achsenproben. Erste Rohdaten und der originale Diagnosecode bleiben unter `source_diagnosis` erhalten; neue Ergebnisse unter `intervention_teacher_forced.json`, eigener Log und Sourcehash.

Fällt die Referenzabweichung unter die ursprüngliche 0,5 mm-Grenze und die Aktionsantwort weiterhin durch, ist die Gegenprüfung des Expert-OLS-K stärker. Besteht die Rekonstruktion weiterhin nicht, bleiben die Aussagen über die Datenaufnahme begrenzt. Ein gutes neues Replay allein autorisiert kein B3-Training: Die Aktionsantwortgates müssen ebenfalls bestehen. Kein automatisch neu gestarteter Sensor-Pilot.
