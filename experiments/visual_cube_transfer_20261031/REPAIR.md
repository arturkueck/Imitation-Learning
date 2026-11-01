# Technischer Dateizugriffsfehler

run_001 endete vor dem reservierten Endtest mit PermissionError / WinError 5
beim atomaren Ersetzen von status.json. Der Pythonprozess wurde nachweislich
beendet (Exitcode 1). Der unmittelbare Dateizugriffsfehler ist dokumentiert;
welcher andere Prozess gegebenenfalls kurzzeitig die Datei sperrte, ist unbekannt.

Kleine Korrektur: höchstens zehn Versuche des atomaren Ersetzens mit kurzen
Wartezeiten, nur für PermissionError. Kein Wechsel von Daten, Lernparametern oder
Architektur. Separater Test prüft wiederholtes Schreiben und Lesen.

run_002 verwendet unveränderte Renderdaten aus run_001. Alle vier Modelle werden
mit den vorab bestimmten Seeds neu initialisiert und symmetrisch trainiert.
Dies ist kein exaktes Resume. Unvollständige Checkpoints bleiben in run_001;
sie werden nicht als zusätzliche Replikate gewertet. Die angefallenen Updates
des abgebrochenen Laufs sind zusätzliche Kosten. Kein Endtestbefund lag bei
dieser Reparatur oder der Entscheidung zum erneuten Lauf vor.
