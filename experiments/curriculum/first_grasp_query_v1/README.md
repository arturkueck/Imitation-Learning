# Nachtlauf · Gezielte Expertenabfragen beim ersten Griff

Vorbereitung für die Nacht 18.–19.11.2026, Europe/Berlin. Der Start ist
ein separater Befehl. Absolutes Ende am 19.11. um 09:00 Uhr, höchstens
zehn Stunden Laufzeit und zwei Minuten Auslaufreserve. Checkpoints,
vollständige Teilresultate und ein Terminalstatus bleiben lokal erhalten.

## Frage und Vergleich

Erhöht die gezielte Auswahl von Expertenabfragen beim ersten Absenken
den Anteil vollständiger Dreiertürme gegenüber zufälligen Abfragen bei
identischem Budget? Korrekturen sind auf die gelernte Entscheidung
beschränkt, ob das Absenken beendet wird. Der Primärvergleich prüft die
Auswahl der Beispiele. Die Frage nach ihrer Reihenfolge folgt in einem
Versuch mit exakt denselben Batches in gemischter und geordneter Folge.

Für jede von **zehn unabhängigen Initialisierungen** wird zuerst eine
neue gemischte BC-Linie mit 30.000 Updates aus zufälligen Gewichten
trainiert. Die ursprünglichen Demonstrationen und ihre Trennung bleiben
erhalten. Die zwei Lernarme beginnen je Linie an diesem gemeinsamen Punkt
und verarbeiten je 2.500 Updates mit 32 alten und 32 zusätzlichen
Beispielen pro Batch. Beide verwenden denselben Indexplan, dieselbe
Architektur, BCE-Gewichtung, Optimizereinstellungen und Beobachtung.
Bei der Auswertung stammen die Bewegung und alle anderen Übergänge aus
der gemeinsamen BC-Linie. Nur der Abschluss beim ersten Absenken stammt
aus der betreffenden Kopie. Original-BC und Original-BC mit dem
bisherigen Timeout nach 100 Phasenschritten sind zusätzliche feste
Referenzen. Der Rückzug nach der zweiten Freigabe gehört zu einer
separaten Methodenfrage.

Die Studie setzt das laufende Forschungsvorhaben zur gezielten
BC-Datenauswahl fort. Die Zahl der unabhängigen Trainingslinien ist
deshalb größer als drei. Bei erwarteten 5 Prozentpunkten relevantem
Effekt und als Planungsszenario 8 Prozentpunkten Streuung der gepaarten
Linieneffekte beträgt der Standardfehler bei zehn Linien etwa
2,5 Prozentpunkte. Die grobe 95%-Halbbreite auf der Linienachse liegt bei
5,7 Prozentpunkten. Das ist ein budgetierter Folgeversuch zur
Effektschätzung, kein garantierter Teststärkenachweis. Die Streuung
neuen Trainings ist vor dem Lauf unbekannt. Die gemeinsamen Szenen
werden bei der Unsicherheit zusätzlich berücksichtigt.

## Datenerhebung und Expertenregel

Die eingefrorene jeweilige BC-Linie erzeugt einen vollständigen gemeinsamen
Strom von Zuständen bis zum ersten Lift bzw. maximal 240 Frames. Jede
zweite Phase-1-Aktion ist ein Kandidat. Eine Familie ist geeignet, wenn
mindestens vier Kandidaten vorhanden sind. Beide Arme bekommen je
geeigneter Familie genau **vier Expertenabfragen**. Sie teilen den
ersten und letzten Kandidaten. Der Zufallsarm zieht zwei innere
Kandidaten ohne Zurücklegen. Der gezielte Arm bevorzugt innere Kandidaten
ab fünf verstrichenen Phasenschritten, höchstens 12 mm vom Ziel entfernt
und mit BC-Abschlusswert unter 0,8. Die übrige Rangfolge ist
Abstand in Metern plus 0,006 m mal Abschlusswert, bei Gleichstand zuerst
der spätere Schritt. Die Auswahl erfolgt vor den Expertenlabels.

Der Experte ist das feste bestehende `StackExpert`-Abschlussprädikat der
ersten Absenkphase. Nach mindestens fünf Aktionen und unter 6 mm Abstand
zum am Phaseneintritt verankerten Ziel meldet es den Wechsel. Die beiden
Arme bekommen dieselbe Expertenregel und unabhängig abgerechnete Aufrufe.
Alle Aufrufe, ausgewählten Frames, Überlappungen, Ausfälle, Labels und
Initialzustandshashes sind im Ledger sichtbar. Das Lernsignal ist ein
simuliertes Expertenlabel, keine beobachtete menschliche Abfragezeit.
Es müssen je Linie mindestens 100/160 geeignete Familien, vier
Prioritätsfamilien und acht Beispiele pro Klasse in jedem Arm vorhanden
sein. Fehlt die Abdeckung, wird das wissenschaftliche Ergebnis als
unvollständig dokumentiert. Szenen werden dabei weder ersetzt noch
nachgezogen.

## Messbare Schwierigkeit und Datenaufteilung

Version `first-lift-latency-v1`. Gemessen wird die Zahl der Kontrollframes
ab der Initialisierung bis zum Eintritt in die erste Liftphase mit
erkanntem Griff. Der feste historische Referenzcontroller ist
`mixed_s1_u30000`. Bei ausbleibendem Griff, ausbleibender Phase oder
verfehltem Horizont erhält die Familie den zensierten Wert 241.
Die beiden festen Grenzwerte sind das obere empirische Drittelquantil
und Zweidrittelquantil der 96 bereits geöffneten Kalibrierungsszenen aus
`first_grasp_clearance_v1`. Leicht liegt unter der ersten Grenze,
schwer ab der zweiten, mittel dazwischen. Der Plan speichert Grenzen,
Kalibrierungszeilen und den beobachteten Referenzerfolg je Gruppe.
Die Einstufung misst Schwierigkeit relativ zu einer festen Policy und
diesem Übergang. Sie beschreibt gewöhnliche Szenen innerhalb derselben
Domäne und verwendet keine Seedzahl als Schwierigkeit.

Die gemessenen Grenzen liegen bei **63 und 66 Frames**. Auf den
Kalibrierungsfamilien gelangen der Referenz 21/24 leichte, 30/39 mittlere
und 19/33 schwere Gesamtaufgaben. Das stützt die Einstufung für diesen
Referenzcontroller. Die Vorbereitung prüft zudem die festgelegten
Trainings- und Validierungsfamilien auf Abdeckung, ohne neues Training
oder eine Auswertung der Testfamilien.

| Rolle | Anzahl | Zweck |
|---|---:|---|
| Geöffnete Kalibrierung | 96 | Grenzen der Referenzlatenz und Zusammenhang mit Gesamterfolg |
| Neue Erhebung für Training | 160 | Phasenfenster und Familienabdeckung. Alle Schwierigkeitsgruppen sind zugelassen |
| Neue normale Validierung | 16 | Kontrollmessung auf unselektierten Starts |
| Neue schwere Validierung | 16 aus 96 | Festes schweres Panel nach Referenzlatenz |
| Neuer normaler Blindtest | 80 | Primärer Vergleich auf der unveränderten Startverteilung |
| Neuer schwerer Blindtest | 40 aus 320 | Ergänzender Vergleich auf schweren Starts |
| Techniktest | 8 separate Kennungen | Kleine Prüfung von Erhebung, Updates, Evaluator und Prüfpfad |

Alle Kandidatenbereiche stammen aus dem Plan. Je schwerem Panel werden
die ersten passenden Familien in der festgelegten Reihenfolge verwendet.
Alle Kandidaten und ihre Einstufung werden gespeichert. Normale Familien
bleiben unabhängig von Schwierigkeit oder Erfolg im Nenner. Jede
Simulatorszene mit sämtlichen Fenstern und Wiederholungen hat genau eine
Rolle. Die beiden Testbereiche werden erst nach Hash-Fixierung aller
Endcheckpoints mit der festen Referenz eingestuft. Das Ergebnis der
trainierten Arme beeinflusst weder die Schwellen noch die Panel-Auswahl.
Die Checkpointregel ist der feste letzte Update. Die Validierung dient
in dieser Studie als getrennte Diagnose ohne Checkpointselektion.

Die Vorbereitungsprüfung der ersten Fassung fand 15 schwere Familien in
64 Validierungsstarts. Daraufhin wurden vor Trainingsstart die festen
Kandidatenpools auf 96 beziehungsweise 320 vergrößert. Die Grenzwerte,
Testzielzahlen und Auswahlregel blieben gleich. Der erste
Validierungspool ist im zweiten vollständig enthalten. Der zunächst
reservierte schwere Testpool wurde vor Öffnung verlegt und vergrößert.

## Entscheidung und Betrieb

Primär vollständiger Dreierturm mit 50 strengen gültigen Frames innerhalb
von 1.000 Aktionen auf dem normalen Blindtest. Gleiche Anfangszustände,
gleicher Sequencer, Freigabeuhr und dasselbe Budget je Modelllinie. Im
Bericht stehen gepaarte Gewinne/Verluste, Ergebnisse je Linie und
Panel sowie ein zweiseitig resampeltes 95%-Intervall über Linien und
Szenenfamilien. Die Entscheidungsregel verlangt mindestens +5
Prozentpunkte gegenüber zufälligen Abfragen und eine positive untere
Intervallgrenze im normalen Testpanel. Andere Panels und Referenzen
sind ergänzend. Der Bericht führt alle vollständigen Paare auf.

Der Plan umfasst 350.000 Optimizerupdates und höchstens 6.080 gewertete
Szenenepisoden, zusätzlich kurze Erhebungs- und Einstufungspräfixe. Die
bisherigen BC-/Simulatorläufe dienen als Durchsatzreferenz. Bei Erreichen
der Frist sind Teilresultate als solche gekennzeichnet. Der Supervisor
prüft Prozess und Frist, hält den Rechner während der Arbeit wach und
dokumentiert den Abschluss. Ein vorhandener Lauf wird nicht automatisch
neu gestartet. Eine Datei `STOP` im jeweiligen Laufordner fordert den
Abbruch an.

```powershell
praxis/.venv/Scripts/python.exe experiments/curriculum/first_grasp_query_v1/night.py verify --output praxis/results/curriculum/first_grasp_query_v1/ready_002
praxis/.venv/Scripts/python.exe experiments/curriculum/first_grasp_query_v1/night.py run --output praxis/results/curriculum/first_grasp_query_v1/ready_002
```
