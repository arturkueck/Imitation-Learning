# Minimale Aktionsprobe ohne Zurücksetzen am Anker

Die Teacher-Forcing-Replaykorrektur reproduziert die nächste Demo-Beobachtung ebenfalls nicht; sie erhöht den Medianfehler auf 3,493 mm. Daraus folgt keine vollständige Rekonstruktion der Controllerhistorie. Weitere Policy-Trainings mit dieser Annahme bleiben ausgesetzt.

Eine kleinere unabhängige Probe trennt jetzt die Frage nach der Aktionsantwort im **aktuellen Simulator** von der Frage nach der Reproduktion der Aufnahme. Vor Ausführung festgelegt:

- Erste vier der bereits festgelegten zwölf Train-Demos, dieselben drei Zeitanteile: zwölf Anker,36 Achsenproben.
- Jeder Zweig erhält denselben RNG-Seed, dasselbe XML und denselben initialen Simulationszustand. Die Nullraumreferenz wird einmalig auf die gespeicherten initialen Gelenkpositionen gesetzt. Anschließend vollständige Simulation des unveränderten Expertaktionspräfixes.
- Am Anker kein Zurücksetzen auf HDF5-Zustände und kein Teacher Forcing. Jeder Zweig ist ein vollständiger, deterministischer Verlauf mit aufgebauter Controller-/Gripperhistorie. Identische vollständige Simulationszustände vor dem Fork prüfen (Normabweichung≤1e-9); Referenz-/Referenz-Wiederholung ≤1µm.
- Dieselben ±0,1 Aktionsänderungen und derselbe vorhandene OLS-K. Richtung/Kosinus und relativer Fehler mit den ursprünglichen0,8/0,5Schwellen berichten. Kleine Antworten<10µm getrennt ausweisen.
- Abstand des live entstandenen Ankers zur aufgezeichneten EEF-Position und Referenzabweichung zur Demo berichten. Diese Probe beantwortet die aktuelle Simulatorantwort an live entstandenen Zuständen; sie validiert weder die aufgezeichneten Anker noch Demo-basierte Gültigkeitsgewichte.

Keine Policy wird trainiert, keine Hyperparameter werden gesucht. Originalreplays bleiben unverändert. Der minimale folgende Methodenversuch wäre eine partielle Aktionsidentifikation auf einem Trainingsanteil solcher Zweige und Prüfung auf anderen Demos/Ankern. Das wäre zusätzlicher Simulatorzugriff und muss als solcher gegen eine rein datenbasierte Methode kontrolliert werden.
