# Einordnung anhand der Gesamtsynthese

Die Gesamtsynthese wurde vor Vorbereitung dieses Wiederholungsstarts gelesen. Ihre Empfehlungen sind wissenschaftliche Einordnung; dieser optionale Zusatztest bleibt vom ursprünglichen Vergleich getrennt. Die vorhandenen Forschungsfragen benötigen laut Synthese kein weiteres Training.

- C hat bereits 2/40 stabile Stacks erzielt. Ein vollständig funktionsloser Diffusionsstack ist damit keine passende Ausgangsbehauptung.
- Einzelsamples, Offline-Stärke und Teilphasen beweisen keine zusammenhängende erfolgreiche Trajektorie. Maßgeblich bleibt der vorab definierte gehaltene 2-cm-Transport.
- Volle Expert-Lifthöhe und exaktes Timing sind nach den Direct-Gegenbeispielen nicht notwendige Aufgabenvoraussetzungen. Die Erfolgsdefinition verlangt weiterhin nicht die Expert-Vollhöhe 1,045 m; sie behält den historischen Transportgate 0,98 m bei.
- Häufige frühe Grasp-Verluste und Öffnungskommandos sind relevant, jedoch nicht kausal isoliert. Der neue Test verändert keine Gripper-Actions oder Gates der Policy.
- DDIM-/Replanning-Sweeps wurden bereits untersucht. Dieser Test bleibt bei DDIM-10 und zwei ausgeführten Actions; kein neuer Sweep.
- Online-B→A-Bewegungscosinus, Offline-EEF→A-Actioncosinus und Expert-Richtungscosinus sind getrennte Kennzahlen. Sie werden nicht gleichgesetzt.
- Ein positives Resultat zeigt Lernfähigkeit einer vereinfachten Aufgabe bei einer Initialisierung und diesem Budget. Es belegt keine robuste vollständige Stack-Policy und keine Fehlerfreiheit der Implementierung.
- Ein negatives Resultat beweist keinen Implementierungsfehler. Griffhaltung, Closed-loop-Zustandsabweichungen, Budget und die durch Kürzung veränderte Trainingsverteilung bleiben mögliche Erklärungen. End-Padding wiederholt weiter die letzte Transportaction; diese Änderung der Supervision ist durch das Abschneiden bedingt.

Die neue Referenz `C_existing_simple_task.json` wertet ausschließlich vorhandene C/Seed-1-Traces mit exakt derselben vereinfachten Erfolgsfunktion aus, inklusive Prüfung aller Präfixe auf den ersten Erfolg. Keine neue Policy-Inferenz oder Simulatorrollouts. Dieser Vergleich trennt vorhandene frühe Fähigkeiten vom möglichen Effekt des Präfixtrainings; er ist kein unabhängiger neuer Testdatensatz.

## Referenzbefund vor einem erneuten Training

| Kennzahl | Bestehendes C/Seed 1 |
|---|---:|
| Greifen | 27/40 |
| Gehaltener Lift über 0,88 m für drei Frames | 24/40 |
| Transport gestartet | 24/40 |
| Vereinfachter gehaltener 2-cm-Zieltransport | **23/40 (57,5 %)** |
| Stabile Stacks im ursprünglichen vollständigen Test | 2/40 (5 %) |

Die Auswertung endet jeweils am ersten vereinfachten Erfolg innerhalb der verfügbaren Originaltrace-Präfixe (höchstens 500 Frames). Ein späterer Release macht einen bereits erreichten frühen Erfolg nicht rückwirkend ungültig. Native ursprüngliche Success-/Tail-Abbruchpunkte begrenzen die verfügbaren Traces; es wird kein frischer 500-Frame-Replay behauptet.

Damit ist die bisherige Grundfähigkeit zum zusammenhängenden Greifen/Liften/kurzen Transport bereits positiv gezeigt. 13 der 40 Starts enthalten keinen Grasp, drei weitere keinen gehaltenen Lift, ein weiterer erfüllt trotz Transportbeginn nicht den kompletten vereinfachten Erfolg. Das präzise Stack-Ende ist daher nicht die einzige mögliche Schwierigkeit. Ein weiteres Präfixtraining beantwortet jetzt die engere neue Frage, ob Entfernen später Supervision diese frühe Zuverlässigkeit verbessert. Es ist kein notwendiger Implementierungs-Sanity-Nachweis mehr und wird nicht automatisch gestartet.

Die fehlgeschlagene Vorbereitung vom 02.10. bleibt vollständig erhalten. Der Wiederholungsordner vom 03.10. enthält identische Daten und Lernparameter, mit korrigiertem Hintergrund-Logging. Ein kurzer versteckter Logging-Selbsttest prüft nur Eltern-/Kindprozess-Ausgaben, ohne Modell oder Training. Noch kein Trainingsprozess gestartet.
