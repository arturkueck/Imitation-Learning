# Controllervergleich: geometrisch geprüfte Rückzugsfreigabe

Entwicklungsversuch auf20 neuen gepaarten Starts pro eingefrorenem Parent. Keine Trainingsupdates, keine alten Endtestrollouts.

| Parent | Baseline /20 | Geometrisches Gate /20 | Gewonnen / verloren | Bestätigte nächste Aufnahme Baseline / Gate | Gate-Timeouts |
|---|---:|---:|---|---|---:|
| 1 | 11 | 18 | 7 / 0 | 4 / 17 | 0 |
| 2 | 9 | 17 | 8 / 0 | 5 / 17 | 0 |
| 3 | 9 | 15 | 6 / 0 | 6 / 14 | 0 |

Das Gate verlangt20 mm vertikale Trennung aller Greiferkontaktgeometrien über dem unteren Turm für drei gültige, kontaktfreie Frames sowie den gelernten Phase0-Abschluss. Boxen werden exakt entlang Welt-Z begrenzt; Meshes konservativ mit Bounding-Sphären. Der bestehende gelernte Phase0-Bewegungskopf wird weiter ausgeführt; kein geskriptetes XYZ-Kommando. Ein Rückzug ohne Freigabe nach200 Frames zählt als Controllerfehlschlag.

„Bestätigte nächste Aufnahme“: fünf native Griff+30mm-Lift-Frames und anschließend50 Frames kontinuierlich gültiger unterer Turm seit Freigabe. Dieser Zusatzwert ist eine Übergangsdiagnose; der vollständige Dreierturmerfolg bleibt das ursprüngliche50-Frame-Kriterium.

Grenzen: kleine Entwicklungspanels, drei verwandte Parents und privilegierte Simulatorgeometrie. Vertikale Freigabe prüft nicht den gesamten folgenden Bewegungskorridor. Keine Aussage zu neu gelernten Gewichten oder visuellem Closed Loop. Keine unabhängige Endtestbestätigung.

Baseline-Collector wurde im getrennten technischen Probelauf bitgenau gegen den vorhandenen nativen Collector geprüft. Hauptlauf prüft identische Initialzustände und identische Zustände/Aktionen bis zum ersten Rückzugsframe. Alle Gatefreigaben werden gegen die gespeicherten geometrischen Kriterien geprüft.