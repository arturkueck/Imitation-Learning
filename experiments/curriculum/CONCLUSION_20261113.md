# Abschlussstand: BC, Curriculum und zweites Anfahren · 13.11.2026

Ziel war, das Stapeln von drei Würfeln mit Behavior Cloning zu verbessern und
die beobachteten Schwächen durch kontrollierte Versuche einzugrenzen. Der
aktuelle Abschluss belegt eine gezielte BC-Verbesserung auf einem neuen
Bestätigungspanel. Ein Nutzen geordneter Curriculum-Präsentation ist nicht belegt.

## Vorgehen und Entscheidungskette

1. **A/B/C bei 30.000 Updates:** A zeigt vollständige phasenausgewogene Daten,
   B und C dieselben Batches in gemischter bzw. X→XY→XYZ-Reihenfolge. Auf dem
   gemeinsamen neuen Dreierturm-Panel: A 40/28/26, B 48/56/50, C 52/42/46
   Erfolge je 100 Szenen pro Modellseed. B ist durchgängig besser als A; die
   geordnete Reihenfolge C übertrifft B nur in einem von drei Seeds.
2. **Phasendiagnose, 220 Versuche ohne Training:** Expertenphasen werden exakt
   aus Controller und Demonstrationen rekonstruiert. Experten-Präfixe erzeugen
   echte Greif-/Kontaktzustände, ohne Teleportation. Isolierte Teilfertigkeiten
   werden von vollständigen BC-Abläufen getrennt. Travel/Open gelingen in den
   30 getesteten Expertenkontexten jeweils vollständig. Bei 15/48 erreichten
   zweiten Lift-Starts fehlt im Gesamtrollout ein Griff; alle 15 scheitern.
   Kleine Abweichungen von einer strengen Lift-Schwelle werden nicht automatisch
   als Ursache eines Gesamtfehlers interpretiert.
3. **Gepaarte Expertenübernahme des zweiten Greifens:** Nur Approach,
   Grasp-Descend und Close werden ersetzt, danach wieder B. Gleiche Historie
   bis zum Eingriff, historische Kontrolle reproduziert. 26/60 → 45/60
   Gesamterfolge; 19 Gewinne, keine Verluste. Kein Lernen in diesem Versuch.
4. **Einzelphasen, 300 Episoden:** BC 26/60; nur Approach 45/60; nur
   Grasp-Descend 35/60; nur Close 26/60; kompletter Greifablauf 45/60.
   Approach ist der stärkste Ansatzpunkt. Jeder Experteneingriff ersetzt Aktion
   und Abschlussregel gemeinsam; er isoliert nicht Bewegung von Übergang.
5. **Gezieltes BC-Korrekturtraining:** Neue Expertenkorrekturen werden vom
   tatsächlich durch B erreichten Beginn des zweiten Anfahrens gesammelt.
   Getrennte Aktions- und Abschlusskopien erlauben die funktionale Auswertung
   beider Komponenten einzeln und gemeinsam, während die übrige Ausführung B bleibt.

## Daten, Modell und Lernen

Die drei B-Ausgangsmodelle haben je sieben unabhängige PhaseNet-MLPs mit Breite
128: zehn privilegierte Simulationsmerkmale, Aktionen XYZ/Greifer und ein
Phasenabschluss-Logit. Rotationen bleiben wie bisher null. Der Abschluss ist
kein Critic. Die ursprünglichen Demonstrationen stammen aus Zweier-Stapelaufgaben.

Neue Sammlung: 40 Trainings- und 10 Validierungsfamilien, jeweils mit allen drei
B-Controllern. Von 150 Sammelversuchen werden 135 akzeptiert: 108 Training,
27 Validierung. Tatsächlich enthalten sind 36 Trainings- und neun
Validierungsfamilien. Daraus entstehen 2.069 Trainings- und 499 Validierungsframes.
Die 15 Abbrüche erreichen das zweite Anfahren nicht; sie werden dokumentiert,
nicht durch andere Starts ersetzt. Ganze Anfangsszenen bleiben über alle
Controller und Frames in genau einem Split. Neue Bestätigungsszenen werden
nicht als Korrekturdaten genutzt.

Pro B-Modell werden vier Kopien jeweils 5.000 Updates fortgesetzt:
Replay-Aktion, Replay-Abschluss, Korrektur-Aktion und Korrektur-Abschluss.
Alle starten aus den ursprünglichen Gewichten und dem vollständigen AdamW-Zustand.
Trainiert wird die gesamte Phase-0-MLP, einschließlich versteckter Schichten;
Phase 1–6 bleibt bitgleich. Aktions-MSE und 0,1 × gewichtete Abschluss-BCE werden
in getrennten Kopien optimiert. Korrekturbatches mischen 32 alte Phase-0-Frames
mit 32 neuen Frames; Replay nutzt 64 alte Frames. Samplingpläne sind festgelegt
und zwischen Aktions-/Abschlusskopie gleich. LR 1e-4, Decay 1e-6, Gradientengrenze 10.

Die fünf Ausführungen sind ursprüngliches B, fortgesetzte Replay-Komposition,
nur neue Aktionen, nur neuer Abschluss sowie beide neuen Komponenten gemeinsam.
Einzel- und kombinierte Ausführung verwenden exakt dieselben gelernten Kopien;
die Kombination erhält keine zusätzlichen Updates. Das ist ein zusammengesetztes
Diagnosesystem, keine neue Schicht und keine Verdichtung zu einer gemeinsamen MLP.

Die neuen Ausgaben werden ausschließlich bei Platzierung 2, Phase 0, außerhalb
des Rückzugs aktiviert. Erstes Anfahren, Rückzug und alle anderen Phasen behalten
B. Der Kontext wird vom vorhandenen Sequencer vorgegeben. Die 0,8-Schwelle,
finale Clock-Korrektur und strenge Erfolgsdefinition bleiben gleich.

## Ergebnis auf neuen Bestätigungsszenen

Fester Endpunkt 5.000 Updates je Komponente; kein Best-of-Test und keine
Schwellenanpassung. Gesamterfolg: vollständiger Dreierturm für 50 aufeinanderfolgende
strenge Gültigkeitsframes ohne Fingerkontakt, bei höchstens 1.000 Schritten.

| Ausführung | Erfolge auf 150 Modell-/Szenenpaaren |
|---|---:|
| Ursprüngliches B | 85/150 |
| Replay-Fortsetzung | 92/150 |
| Nur Aktionen | 92/150 |
| Nur Abschluss | 78/150 |
| Aktionen + Abschluss | 118/150 |

Kombiniert: 78,7 % statt 56,7 % bei B, Unterschied +22,0 Prozentpunkte.
Gegen B: 34 gepaarte Gewinne, ein Verlust. Gegen Replay: 28 Gewinne, zwei Verluste.
Pro Modellseed steigt B 27/32/26 auf kombiniert 39/39/40 je 50 Starts; Replay
liegt bei 32/32/28. Beide neuen Komponenten gemeinsam übertreffen Replay bei
allen drei Modellseeds. Nur der neue Abschluss verschlechtert zwei Modelle.

Das bekannte Entwicklungspanel bleibt separat: B 26/60, Replay 30/60,
Aktion 27/60, Abschluss 23/60, kombiniert 45/60. Diese Werte werden nicht mit
der neuen Bestätigung zu einer Leistungskurve oder gemeinsamen Quote vermischt.

## Belastbare Aussage und Grenzen

Gezielte Expertenkorrekturen für das zweite Anfahren verbessern in diesem
Versuchsaufbau den vollständigen Stapelerfolg, wenn gelernte Aktionen und
gelernter Phasenabschluss gemeinsam eingesetzt werden. In der Auswertung
übernimmt kein Experte. Das Ergebnis betrifft trainierte Komponenten und
geht über den vorherigen Nachweis einer Expertenhilfe hinaus.

50 Bestätigungsszenen werden über drei Modellseeds geteilt: 150 Modell-/Szenenpaare
sind keine 150 unabhängigen Szenen. Es gibt keine breite Signifikanzbehauptung.
Die Bestätigung prüft neue Anfangszustände im selben Simulator, keine neue
Objektgeometrie, Hardware oder andere Aufgabe. Bestätigungsstarts gelten jetzt
als geöffnet und dürfen nicht still als neue Validierungs-/Trainingsquelle dienen.

Getrennte Aktions-/Abschlusskopien und der Kontext-Gate gehören zum Verfahren.
Eine einzelne gemeinsame MLP mit demselben Erfolg wurde nicht gezeigt.
Ein geordnetes Curriculum, autonomes Paarplanen, beliebige Turmhöhen und ein
allgemein gelöstes Datenproblem sind nicht belegt. Rückzug und langes Open
bleiben ohne neu demonstrierte vollständige Trainingsabdeckung. Die vorhandenen
Kontrollen geben keinen Anlass für einen zwingenden weiteren Trainingslauf,
um diesen gezielten BC-Befund als aktuellen Abschluss zu berichten.

## Reproduzierbarkeit, Modelle und Abschluss

Der Lauf ist COMPLETE und benötigte rund 68 Minuten. Zwölf Komponenten haben
je 5.000 zusätzliche Updates. Gespeichert sind die unveränderten B-Vorfahren,
Kompositionskarten, versionierte Zwischen-/Endcheckpoints, vollständige
Optimizerzustände, nächster Batchindex, feste Samplingpläne und RNG-Zustände.
Die Wiederaufnahme aller vier Komponententypen wurde technisch auf bitgleiche
Gewichte und Optimizerzustände geprüft. Nicht behauptet wird plattformübergreifende
Bitgleichheit. Originalmodelle wurden nicht überschrieben.

Protokoll, Eingangs-Hashes, Quellenkopien und Paket-/GPU-Umgebung liegen beim
Lauf. Sammelversuche, Splitfamilien, Datenhashes, Loss-/Validierungswerte sowie
vollständige Rollouts und gepaarte Veränderungen bleiben lokal erhalten.
Keine Checkpoint-Auswahl auf dem Bestätigungspanel. Keine automatischen
Folgeversuche, kein Herunterfahren; Schlafverhinderung wieder freigegeben.

Die Website erhält ausschließlich verdichtete Messwerte, Abbildungen, diese
Einordnung und Quellen-Hashes. Keine Modellgewichte, RNG-Zustände oder Rohdaten.
