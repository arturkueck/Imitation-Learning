# Kontrolliert beendeter Machbarkeitsvorversuch

Der Per-Szene-Planer wurde über STOP_REQUESTED kontrolliert beendet; der Prozess ist mit Exit 1 beendet. Das ist ein bewusstes Ressourcenende, kein behaupteter Trainingsabsturz. Logs und alle erzeugten Familien bleiben erhalten. Es gab keine Optimizerupdates und keinen Haupttrainingsstart.

Nach 30 Familien waren etwa 388 Sekunden verstrichen. Eine vollständige neue IK-/Armwegplanung je Szene würde die geplante Datenerzeugung stark verteuern. Der folgende, separat bezeichnete pilot_002 prüft deshalb eine vorberechnete statische Kamerabank. Diese Methodenänderung betrifft ausschließlich den Machbarkeitspilot, nicht laufende wissenschaftliche Trainingsparameter.

Zusätzlicher Befund: Die ursprüngliche modulo-basierte Zuordnung langer/dünner Formen korrelierte mit der Blickfamilie. pilot_002 verwendet eine separate deterministische, über Blickfamilien geschichtete Auswahl. Ergebnisse aus pilot_001 dienen als Planungs-/Bankquelle und dürfen nicht als unabhängige Testevidenz verwendet werden.

Die weiche Vier-Sekunden-Suchvorgabe war keine harte Zeitobergrenze; einzelne vollständige Kollisionsprüfungen liefen länger. Tatsächliche Zeiten stehen in families.jsonl.
