# Ein technischer Reparaturversuch: immutable Szene statt neuem Settling

Der ursprüngliche Validierungsprozess ist nachweislich mit Exit 1 an Index 138 beendet. Log und 138 bereits abgeschlossene Familien bleiben erhalten. Keine Modelltrainierung oder Parameteränderung.

Gezielte Reproduktion: Objektabmessungen stimmen bis 3,14e-9 m; beim erneuten physikalischen Settling verschieben sich drei Teile einer Wand um etwa 0,164 mm. Ein Seed allein fixiert den Kontaktlöserzustand nicht. Die bisherige Grenze von 1e-5 m wurde nicht gelockert.

Korrektur: Farben/Geometriekonfiguration mit demselben Seed und passenden gespeicherten Abmessungen rekonstruieren, danach die bereits gespeicherten, tatsächlich gesetzten Objektpositionen und -rotationen direkt als Simulationszustand laden. Die ursprünglichen festen Kamerakalibrierungen werden ebenfalls geladen. Genaue Objektgeometrie bleibt ausschließlich Simulationszustand/Kollisionsquelle, kein Blickzielinput. Ein fokussierter Test auf Index 138 ergibt 0,0 m Positionsabweichung. Die originale Beleuchtung war nicht separat serialisiert; deren vollständige photometrische Identität wird nicht behauptet.

Fortsetzung ab Index 138, dieselben 200 Familien, dieselbe Bank mit 26 verifizierten Zertifikathashes, unveränderte Sicherheitsabstände, Blickwinkelregeln und Modellgewichte. source/ bleibt erhalten; source_repair_001/ enthält den Reparaturstand. Keine Ergebnisse werden überschrieben. Aktive Rechenzeit wird aus Bankaufbau plus Familienmessungen ausgewiesen; Diagnose-/Reparaturwartezeit ist separat im Log nachvollziehbar.

Die nachfolgende tatsächliche Bilderfassung stellt für jede akzeptierte Ansicht den exakten gespeicherten Objektzustand her und zertifiziert den gesamten Nachführungsabschnitt erneut in dieser Referenzwelt. Damit werden auch die vor dem Abbruch geplanten Zielkorrekturen unabhängig geprüft.
