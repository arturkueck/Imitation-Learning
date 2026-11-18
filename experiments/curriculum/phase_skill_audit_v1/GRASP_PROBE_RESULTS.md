# Ergebnis: Expertenübernahme beim zweiten Greifen

Abgeschlossener Lauf: `praxis/results/curriculum/second_grasp_probe_v1/night_001`.
Quellen: `plan.json`, `pairs.json`, `summary.json`, `provenance.json`,
`supervisor_status.json` und 120 komprimierte Ablaufspuren in diesem Verzeichnis.
Durchführung und Startbefehle: [GRASP_PROBE.md](GRASP_PROBE.md).

## Frage und kontrollierter Eingriff

Erklärt der zweite Greifablauf einen relevanten Anteil der Ausfälle beim
Drei-Würfel-Stapeln? Verglichen werden dieselben drei unveränderten B-Modelle
bei 30.000 Updates auf denselben 20 bereits geöffneten Entwicklungsszenen.
Die Kontrollbedingung verwendet vollständig BC. Die Eingriffsbedingung nutzt
den vorhandenen Experten ausschließlich für Approach, Grasp-Descend und Close
der zweiten Platzierung; ab Lift wieder dasselbe BC-Modell. Kein Teleportieren,
kein erzwungener Griff, keine Optimizer-Updates und keine neuen Trainingsdaten.

Erfolg bedeutet vollständiger Dreierturm für 50 aufeinanderfolgende Frames
gemäß bestehendem strengen Geometrie-/Kontakt-/Geschwindigkeitskriterium ohne
Fingerkontakt. Der bestehende Rückzugs-Guard und die finale Clock-Korrektur
gelten in beiden Bedingungen. Episodenhorizont: 1000 Schritte.

## Ergebnisse

| Modellseed | BC-Kontrolle | Expertenübernahme | Gepaarte Gewinne | Gepaarte Verluste |
|---|---:|---:|---:|---:|
| 1 | 9/20 | 15/20 | 6 | 0 |
| 2 | 9/20 | 15/20 | 6 | 0 |
| 3 | 8/20 | 15/20 | 7 | 0 |
| Gesamt | 26/60 (43,3 %) | 45/60 (75,0 %) | 19 | 0 |

Unterschied: +31,7 Prozentpunkte. Alle 26 vorher erfolgreichen Modell-/Szenenpaare
bleiben erfolgreich. Alle Kontrollausgänge reproduzieren die vorige Diagnose.
Anfangszustand und vollständige Aktions-/Simulationshistorie vor dem Eingriff
sind durch paarweise gleiche SHA-256 nachgewiesen. Damit betrifft der Vergleich
den ersetzten zweiten Greifablauf samt dadurch veränderten Folgezuständen.

| Zustand beim zweiten Lift in der Kontrolle | Paare | BC-Erfolge | Erfolge nach Expertenübernahme |
|---|---:|---:|---:|
| Griff erkannt | 33 | 26 | 30 |
| Kein Griff erkannt | 15 | 0 | 15 |
| Zweiter Lift nicht erreicht | 12 | 0 | 0 |

Insgesamt erkennen wir nach Expertenübernahme bei allen 48 erreichten zweiten
Lift-Starts einen Griff, gegenüber 33/48 in der Kontrolle. Alle 15 zuvor
griff-losen Fälle werden erfolgreich; zusätzlich verbessern sich vier Fälle,
in denen schon vorher ein Griff erkannt wurde. Der binäre Griffstatus allein
erklärt daher nicht die gesamte Verbesserung. Auch Griffpose, Anfahrzustand
oder die folgenden Bewegungen können beitragen; diese Größen wurden hier
nicht einzeln manipuliert.

## Aussage und Grenzen

Der zweite Greifablauf ist in diesen Entwicklungsszenen ein wirksamer
Ansatzpunkt: Seine Expertenübernahme verbessert die vollständige Aufgabe.
Das rechtfertigt, den zweiten Greifprozess und dessen Eingangszustände für
das nächste BC-Experiment zu priorisieren.

Es ist noch kein Nachweis einer verbesserten trainierten Policy oder eines
Curriculum-Vorteils. Approach, Descend-to-grasp und Close wurden gemeinsam
ersetzt; keine einzelne Phase ist damit als alleinige Ursache identifiziert.
Die 60 Paare bestehen aus drei Modellseeds auf 20 gemeinsamen Szenen und sind
keine 60 unabhängigen Szenen. Die bedingten 48 Lift-Starts schließen zwölf
vorher abgebrochene Versuche aus; der Nenner für Gesamterfolg bleibt 60.
Die zuvor reservierten Bestätigungsszenen bleiben geschlossen.

Es fehlen weiterhin Demonstrationen spezifischer Eingangszustände nach dem
ersten Platzieren/Rückzug sowie vollständiger Rückzug und langes Halten.
Diese Expertenübernahme erzeugt keine automatisch freigegebenen Trainingslabels
und löst die Datenabdeckung noch nicht. Vor Training sind Abdeckungsprüfung,
ein festgelegter Datensplit und ein kontrolliertes Lernprotokoll erforderlich.

## Reproduzierbarkeit und Ablage

`provenance.json` fixiert die verwendeten Modelle, direkt geprüfte Skripte,
die Clock-Adaption, den vorbereiteten Untersuchungsplan und das frühere
Kontrollergebnis mit SHA-256. Eingänge wurden vor und nach dem Lauf geprüft.
Das ist kein vollständiger eingefrorener Snapshot aller transitiven Imports
oder der gesamten Python-/Treiberumgebung; eine plattformübergreifend bitgenaue
Wiederholung wird nicht behauptet.

`pairs.json` enthält alle 60 Paare einschließlich nicht erreichter Eingriffe;
`traces/*.npz` enthält 120 vollständige Schrittverläufe. Spaltenschema und
technischer Importfehler des ersten Probelaufs stehen in `GRASP_PROBE.md`.
Smoke-Läufe sind aus den wissenschaftlichen Zahlen ausgeschlossen.

Der Lauf endete regulär nach rund 6 Minuten 42 Sekunden. Die Schlafverhinderung
wurde freigegeben; der PC wurde nicht heruntergefahren. Keine automatischen
Neustarts oder Folgeexperimente. Originalmodelle einschließlich Optimizer-
und RNG-Zuständen bleiben im Modellkatalog für spätere Fortsetzung erhalten.
