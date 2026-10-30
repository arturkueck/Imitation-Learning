# Messkorrektur vom 24.10.2026: Greiferkontakt

Bei der Vorbereitung des nächsten Übergangspiloten wurde ein technischer Fehler in der historischen Kontaktprüfung gefunden und unabhängig durch zwei Agenten geprüft.

`env.robots[0].gripper` ist in der verwendeten Robosuite-Umgebung ein Dictionary mit dem Schlüssel `right`. `env.check_contact(gripper, cube)` unterstützt dieses Dictionary nicht; es interpretiert dessen Schlüssel als Geometrienamen. Dadurch kann es trotz realer Fingerkontakte `False` liefern. Der native `_check_grasp` unterstützt Dictionaries dagegen ausdrücklich.

Konkreter Diagnosebeleg: gespeicherter Trainingszustand aus `datasets/curriculum_n3_cycle0/215000.npz`, nächster Quellwürfel C während des Anhebens. Im selben restaurierten Simulatorzustand ergibt die alte Dictionary-Abfrage `False`, die Abfrage über die einzelnen GripperModel-Geometrien `True` und `_check_grasp` ebenfalls `True`. Die Rekonstruktion nach `sim.forward()` weicht um ungefähr0,465mm von den damaligen geloggten abgeleiteten Positionen ab. Sie dient deshalb nicht zur nachträglichen exakten Neubenotung von Episoden, belegt aber den Fehler der zeitgleichen alten/korrekten Kontaktabfrage eindeutig.

## Folgen für die bisherigen Ergebnisse

- Die gespeicherten `fingers`-Flags belegen **keine vollständige Fingerkontaktfreiheit**. Historische Qualitätsanalysen dürfen daraus weder saubere Rückzüge noch erfolgreiche Aufnahmen ableiten.
- Der bisherige Enderfolg prüfte weiterhin Geometrie, Würfelkontakte, Geschwindigkeiten und den nativen Ausschluss eines gehaltenen Würfels. Nur die zusätzliche Behauptung „keinerlei Greiferkontakt“ war nicht korrekt implementiert. Einseitige Kontakte können trotz ausgeschlossener vollständiger Griffe unerkannt geblieben sein.
- Die veröffentlichten Zählwerte sind Ergebnisse der **damaligen implementierten Metrik**, keine nachträglich bestätigten Ergebnisse unter einer korrigierten kontaktfreien Metrik. Die tatsächlichen korrigierten Quoten sind unbekannt. Sie werden nicht aus unvollständigen Logs erfunden.
- Alte reservierte Endtests werden nicht erneut für Optimierung benutzt. Originaldaten, Checkpoints, Quellcode-Snapshots und Rohlogs bleiben unverändert.

Die neue Implementierung im Nachfolgeordner `stack_transition_quality_20261024/native_collector.py` fragt alle einzelnen Greifergeometrien ab, speichert sowohl Kontakt als auch nativen Griffstatus und verschärft die neue Präfixprüfung entsprechend. Neue und historische Erfolgszahlen müssen deshalb mit ihrer Metrikversion angegeben werden. Bei einem neuen B0/B-Vergleich benutzen beide Arme dieselbe korrigierte Messung und neue Starts.

Dies ist eine Messkorrektur, keine Behauptung, dass die Korrektur allein die Policy verbessert oder die bisherige niedrige Fünferleistung erklärt.
