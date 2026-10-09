# Explorative Teilidentifikation, vor Berechnung der neuen Matrix

Die Liveprobe zeigt gleiche vollständige Startzustände und reproduzierbare Referenzzweige, aber0/36 bestandene Antworten des alten Expert-OLS-K. Die Anker unterscheiden sich von den HDF5-Ankern median7,05mm; die Ergebnisse gelten daher für diese live entstandenen Simulatorzustände.

Als gezielte Folgeanalyse der **bereits erhobenen** Daten wird eine konstante partielle Aktionsantwort ohne Intercept regressiert: `(a_plus-a_minus) @ K_partial ≈ EEF_next_plus-EEF_next_minus`. Der Intercept entfällt beim paarweisen Unterschied. Keine Policy-Optimierung und keine zusätzlichen Rollouts.

Fit ausschließlich auf den ersten beiden der vier vorab ausgewählten Demos (demo_1,demo_116),18Achsenantworten. Prüfung auf den beiden anderen Demos(demo_132,demo_148),18Antworten, dieselben ursprünglichen Richtung-/Fehlergates. Alle Proben bleiben im Nenner; degenerierte Antworten separat. Keine Änderung des Splits, keine Modell-/Schwellensuche.

Diese Analyse ist **explorativ nach Kenntnis der alten K-Fehler**, kein unberührter Haupttest. Die zurückgehaltenen Antworten gehen nicht in den Matrixfit ein; ihre bisherigen Fehler unter K waren jedoch bereits bekannt. Ein gelungenes Modell der Aktionsantwort bestätigt noch nicht die Annahme `δ_next=δ+Δa@K_partial`, da auch physische Zustandsänderung, Orientierung, Geschwindigkeit, Greifer und Kontakt eine Rolle spielen.

Eine spätere Methode mit diesem K nutzt zusätzliche Simulatorinterventionen. Dieser Zugang und die vollständige Prefix-/Fitzeit gehören in die Kostenbilanz; sie darf nicht als ausschließlich aus Demonstrationen gelernte Verbesserung verkauft werden. Nach dieser Analyse weiterhin kein Policy-Training ohne Prüfung der verbleibenden Zustandsantwortannahme und kein Ersatzlauf für den fehlgeschlagenen Sensor-Pilot.
