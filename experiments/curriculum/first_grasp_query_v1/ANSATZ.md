# Arbeitsstand · Imitation Learning und Daten für das Stapeln

Das Projekt untersucht, wie die Auswahl, Aufbereitung und Präsentation
von Erfahrung zuverlässigere aus Demonstrationen gelernte
Roboterhandlungen ermöglicht. Behavior Cloning mit dem Simulatorstapel
ist die gemeinsame Referenz.

Der historische Reihenfolgevergleich hielt die Batches konstant. Auf
100 gemeinsamen Szenen je Trainingsseed ergab die gemischte Reihenfolge
154/300 Erfolge und X → XY → XYZ 140/300. Die Richtungsheuristik
lieferte in diesem Aufbau keinen konsistenten Zusatzvorteil. Die
Exposition der gezeigten Beispiele bleibt eine eigenständige
Erklärung und ein eigener experimenteller Faktor.
[Baselinevergleich](../../baselines/comparison_audit_20261117/REPORT.md)

Im Nachtlauf zur Herkunft von Anfahrbeispielen erreichten mit gleichem
Label- und Trainingsbudget die aus Lernerzuständen gelabelten Beispiele
359/450 und die aus Expertenzuständen 362/450 Erfolge. Beide halfen
gegenüber dem ursprünglichen BC und Wiederholen alter Beispiele.
Die Datenquelle allein lieferte keinen nachweisbaren Zusatznutzen.
[Abgeschlossener Vergleich](../targeted_correction_budget_v2/COMPLETED.md)

Die nächste Diagnose zeigte einen messbaren Engpass beim ersten
Absenken. Der Greifer erreichte die Zielposition, die gelernte
Abschlussentscheidung konnte aber ausbleiben. Eine Laufzeitregel
steigerte auf acht neu gesichteten schwierigen Familien mit drei
vorhandenen Modelllinien den Gesamterfolg von 5/24 auf 19/24.
Ein reiner Timeout erreichte 16/24. Bei den beiden Linien außerhalb der
Sichtung erzielten beide 12/16. Auf den normalen neuen Familien
erreichten beide Regeln 38/48 gegenüber 35/48 der Kontrolle.
Diese Eingriffe zeigen, dass die Abschlussentscheidung in einem Teil der
Fehlerfälle den Gesamterfolg beeinflusst. Die Lernwirkung neuer
Abschlusslabels wurde dabei noch nicht gemessen.

Der nächste Lauf untersucht deshalb **die Auswahl zusätzlicher
Expertenabfragen**. Ein zufälliger und ein gezielter Arm fragen pro
geeigneter Familie gleich oft an, trainieren gleich lang und unterscheiden
sich nur in der Wahl zweier Abfragefenster. Gemischtes BC und der
Timeout bleiben Referenzen. Der genaue [Versuchsplan](README.md)
definiert zehn neue gepaarte Trainingslinien, messbare Referenzlatenz,
disjunkte Szenenfamilien und den vollständigen Aufgabenerfolg.

Eine anschließende Curriculumfrage vergleicht dieselben festgelegten
Batches in gemischter und von einfachen zu schwierigen Übergängen
geordneter Folge. Damit lässt sich zeitliche Struktur unabhängig von
der durch die Abfragepolitik geänderten Datenexposition messen. Die
Schwierigkeit ist durch beobachtete Voraussetzungen und Referenzverhalten
zu begründen, einschließlich stabiler Übergänge und legitimer
Wartezustände. Der Freigaberückzug und die Nutzung eigener Trajektorien
oder eines Critic bleiben mögliche eigene Fragestellungen.
