# Bewertung nach Abschluss · 01.11.2026

Der Nachtlauf ist regulär nach91vollständigenEpochen beendet. Alle6Modelle
absolvierten34.125Updates. Modellauswahl auf Validierung, ausgewählte Epochen87–90.
Es wurde kein neues Training zur Auswertung gestartet.

## Technischer Fehler der ursprünglichen Schlussprüfung

Die ursprünglichen2.000IID- und512Geometrieverschiebungsszenen hatten ausschließlich
schwarze RGB-Bilder und Sichtbarkeitslabels0. Dadurch wurden die tatsächlich
vorhandenen5.683bzw.1.411Objekte bei der Auswertung als unbeobachtbar behandelt.
Die ursprünglichen Testzahlen in run_001/results.json sind **ungültig**.
Ein regulärer Prozessexit war hier kein Nachweis gültiger Evaluationseingaben.

Ein frischer Renderprozess erzeugte dieselben Szenen korrekt. repair_tests.py
prüfte für ALLE2.512Szenen exakte Gleichheit von Positionen, Größen, Rotationen,
Kamerastrahlen, Objektmasken, Objektzahl, Anordnungstyp undFamilien-IDs. Nur
RGB/Sichtbarkeit wurden neu erzeugt. Die sechs vorab eingefrorenen Checkpoint-
Hashes wurden vor und nach der Auswertung geprüft. Keine Optimizerupdates,
keine neue Auswahl, keine Hyperparameteranpassung auf den Schlusswerten.
Originaldateien bleiben erhalten. Reparergebnisse: run_001/test_repair_001/.
Die konkrete Ursache der schwarzen Bilder im ursprünglichen langen Prozess ist
nicht bewiesen; Neuinitialisierung des Renderkontexts ist ein Verdacht. Ein
isolierter frischer Prozess behebt den beobachteten Fehler.

Für künftige Läufe: RGB-Dynamikbereich und beobachtbare Zielobjekte vor JEDEM
Split prüfen, Testgenerierung isolieren und bei leeren/ungültigen Eingaben
fail-closed statt Nullverluste/scheinbare100%Anzahl ausgeben.

## Ergebnisse ausgewählter eingefrorener Modelle

Mittelwerte über3Trainingsseeds; keine unabhängige große Stichprobe an Modellseeds.
Die Szene-Starts sind zwischen Kameravarianten gepaart.

| Panel / Kameras | Zuordnungsfehler | Anzahl korrekt | erkannt UND Position≤10mm |
|---|---:|---:|---:|
| 2.000neueIID-Szenen / fest | 5,95mm | 96,35% | 88,52% |
| 2.000neueIID-Szenen / fest+Hand | 5,11mm | 96,65% | 91,89% |
| 512veränderteQuaderszenen / fest | 17,43mm | 60,03% | 25,89% |
| 512veränderteQuaderszenen / fest+Hand | 14,92mm | 66,54% | 35,37% |

Zuordnungsfehler beinhaltet geometrisch zugeordnete Slots, auch unterhalb der
Detektionsschwelle; er ist deshalb zusammen mit Recall zu lesen. Die Anzahl ist
proSzene, Recall pro beobachtbaremObjekt. 'Erkannt und≤10mm' bewertet Position,
nicht zusätzlich richtige Größe/Orientierung oder erfolgreiche Montage.

Das veränderteQuaderpanel ändert Geometrie UND beschränkt die Anordnung auf
verstreuteObjekte. Es ist keine vollständig disjunkte unbekannteFormklasse:
Teile seiner Größenbereiche überschneiden sich mit trainierten Brücken.
Der trotzdem große Einbruch zeigt eine deutliche Übertragungsgrenze, aber keine
isolierte kausale Zerlegung von Form, Größe und Anordnung.

Auf16ausgewähltenValidierungsszenen jeModell liegt der mittlere geometrische
Szenenscore bei etwa0,67–0,71 und Größenfehler bei etwa3,1–3,8mm. Dies ist nur
ein Diagnosepanel, kein vollständiger Endtest über alleGeometriemetriken.
Winkelkennzahlen sind zusätzlich anfällig für die Konvention vertauschter
lokaler Boxachsen bei gleichzeitig vertauschten Abmessungen. IoU/Eckenfehler
und eine kanonische, symmetriebewusste Posebewertung sollten zusammen betrachtet
werden. Optisch gute Überlagerungen beweisen keine präzise Steckmontage.

## Urteil und nächste Entwicklung

Als kompakter Wahrnehmungsprototyp unter ähnlichen Simulationsbedingungen
brauchbar. Keine Freigabe für autonome reale Lego-Montage, keine bereits gelernte
Greif-/Bau-/Kollisionspolicy. Der Verlauf der letzten sechs Epochen ist weitgehend
ein Plateau; bloß länger auf derselben Verteilung zu lernen ist nicht die
priorisierte Verbesserung.

Prioritäten für neue, getrennt geplante Entwicklung:

1. Geometrieabdeckung/Material/Licht/Hintergrund und stärkere Verdeckungen
   verbreitern. Position, Abmessungen und symmetrie-/achsenkonsistente Ausrichtung
   getrennt messen. Neue reservierte Starts; verbrauchte Testpanels nicht zur
   weiteren Hyperparameterwahl verwenden.
2. Poseunsicherheit auf neuen Entwicklungsdaten kalibrieren. Hoher
   Detektionsscore ist keine Garantie genauer Pose. Vorhandene drei Modelle
   können nach Objektzuordnung als Disagreement-Signal dienen.
3. Aktive Wahrnehmung: festeKameras→Unsicherheit/unerklärteBildbereiche→kollisions-
   geprüfte zusätzlicheHandansicht→erneuteFusion→erneutePrüfung. Der aktuelle
   Dreibildeingang akzeptiert jeweils zwei festeAnsichten plus eineHandansicht;
   mehrere zeitlicheAnsichten benötigen zusätzlicheFusion/Tracking.
4. Handkamera-Poseverteilung erweitern: bislang nur kleineGelenkwinkelvariationen,
   kein Nachweis für beliebig neueNahansichten oder aktiveKamerabewegungen.
5. Kollisionskarte aus der gesamten sichtbarenUmgebung aufbauen. Nur erkannte
   Boxen sind unzureichend: überseheneObjekte fehlen sonst auch alsHindernisse.
   GanzenArm undgeplanteBahn gegen dieKarte prüfen, Unsicherheit/Unbekanntes
   berücksichtigen, Sicherheitsabstände anhandFehlerverteilungen bestimmen.
   Dies braucht diebekannteRobotergeometrie/Kalibrierung, keine manuell in die
   Simulation übertragenen Modelle jedes neuen realenObjekts.

Technisch verwandte Primärquellen:
- Aktive Blickwahl: https://arxiv.org/abs/2409.14891
- Szenen-/Robotergeometrie und Kollisionsprüfung:
  https://moveit.picknik.ai/main/doc/examples/planning_scene/planning_scene_tutorial.html
