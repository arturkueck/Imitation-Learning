# V3 Anschlussphase: abgeschlossen, aktive Aufnahme nicht freigegeben

Stand: 02.11.2026. Technischer Abschluss mit Exit0; keine laufenden Anschlussprozesse. **Kein wissenschaftlicher Nachweis einer funktionierenden aktiven Blickwahl.** Die endgültige kalibrierte Policy fordert kein einziges Zusatzbild an. Es wurde nicht nach Schlussdaten nachtrainiert oder nachkalibriert.

## Entscheidung und Wahrnehmungsprüfung

Alle sieben ursprünglichen Checkpoint-Hashes und sämtliche ursprünglichen Train-/Validation-Arrayhashes stimmen. 12.000 Trainings- und2.000 Modellvalidierungsfamilien sind disjunkt. M1/M2 jeweils Seeds1/2/3: je12.644 Updates und33,717333 tatsächlich trainierte Epochen, insgesamt75.864 Wahrnehmungsupdates. Keine Behauptung von60 abgeschlossenen Epochen.

M2 wurde allein anhand des Mittels der drei Seeds auf Modellvalidierung gewählt: balancierter Loss0,10222286 gegenüber M1 0,11654085. M2 hat dort5,73678mm Zuordnungspositionsfehler, auf Originalansichten5,27874mm und90,5459% 10-mm-Recall. V2-Originalreferenz:5,65688mm und87,7642%. M2 benutzt auf der robusten Validierung teilweise Handbildhistorie; der Vergleich ist kein Beweis, dass sein Einzelbildkontext M1 überlegen ist.

Späte Train-/Probe-/Validation-Kurven wurden getrennt geprüft. M2 Seeds1/2 verbessern sich noch, Seed3 verschlechtert seine Validation nach Epoche32 bei Probe um0,10; auch M1 Seed3 regrediert. Damit sind weitere Lernmöglichkeiten und Instabilität/Regression gemischt, nicht durchgängig bloßes Untertraining. Latest enthält Optimizer und RNG, aber der Teil-Epochen-Sampleroffset wurde durch die Validation mit0 überschrieben. Ein vollständiger High-Level-Sampler-Resume ist nicht verifiziert. **Keine zusätzliche Wahrnehmungsfortsetzung**; die drei validierungsgewählten M2-Best-Checkpoints bleiben eingefroren.

Die ursprüngliche Geometrie enthält1.728 indexierte Artefakte (576 Szenensnapshots mit Overlay/Input/Metrik). Ein Fünfer-Turm wurde visuell geprüft: grobe Ausrichtung stimmt, Restfehler bleiben sichtbar. Die ursprünglichen best_* Plotnamen tragen für alle Modelle die Endepoche33,72; maßgeblich sind die tatsächlichen Auswahl-Epochen in selection.json (M2:33,717/33,717/32).

## Implementiert und tatsächlich ausgeführt

Neue Dateien followup_core.py/followup_v3.py implementieren23 Beobachtungsmerkmale,19 kalibrierte Kandidatenmerkmale, präfixgebundene Kontexte, paarweise Gewinnlabels, Training, getrennte Kalibrierung und eingefrorene Schlusstests. Architektur, Loss, Seeds und zentrale Optimizerwerte wurden eingehalten. Zukunfts-RGB, unbekannte Sollgeometrie und robot_fraction gehen nicht in die Köpfe ein. Die erwartete Roboterverdeckung stammt aus Projektion bekannter Robotergeometrie; robot_fraction bleibt reines Diagnoselabel.

Die Kandidatenidentitäten werden unabhängig von Objekten aus dem festgelegten Posegitter vorgeschlagen. Kollisionsprüfung ist separat und ausdrücklich sim_reference. Ungültige Kandidaten erhalten kein erfundenes Gewinnlabel und bleiben als blocked im Journal. M2 behält alte Handbilder derselben statischen Szene; maximal zwei Zusatzaufnahmen. Geänderte feste Kamerabilder durch Armbewegung werden mit einem Kontext ohne die neue Handansicht kontrolliert. Zusätzlich wurden reine feste Kameras als Kontrolle ausgewertet.

Reservierte Request-Familien:4.000 Training,500 Validation,500 Kalibrierung. Training liefert23.838 Zustände und59.224 gültige Kandidaten;956 Kandidaten erreichen mindestens2mm Nettogewinn,56.560 haben negativen Nettogewinn. Positive Fälle sind damit selten (1,61% der Kandidaten). Need-Positive:607 Zustände. Alle drei Kopf-Seeds erhielten30 Epochen und je2.820 Updates, insgesamt8.460 Kopfupdates. Ausgewählte Epochen:30/29/30; beste Validation-Losses:0,12797068 /0,12793864 /0,12972373. Die Train-/Validation-Kurven sinken, aber das allein validiert keine nützliche Policy. Cyan/Orange-Abgleiche wurden auf16 festen Request-Validation-Familien alle fünf Epochen sowie bei0/Best/Final gespeichert; Endtest-Overlays separat.

## Kalibrierung und Ergebnis der aktiven Policy

Der separate Kalibrierungssplit enthält2.979 Zustände,7.404 gültige Kandidaten,164 hilfreiche Kandidaten und7.047 negative Gewinne. Keine Kombination des vorab festgelegten Schwellenrasters erfüllte gleichzeitig mindestens20 angenommene Zustände, höchstens5% negative Nettogewinne und positiven Gesamtnutzen. Selbst die beste Regel mit mindestens20 Fällen nahm36 Zustände an, davon17 mit negativem Nettogewinn (47,2%). Deshalb wurde vor der Erzeugung von Schlussfamilien die Policy explizit deaktiviert: Need1,01, Helpful1,01 und Gain1e9. policy_freeze.json hält dies mit Modellhashes fest.

| Schluss-Split | Familien | Gelernte Zusatzaufnahmen | Fehleränderung |
| --- | ---: | ---: | ---: |
| IID |2.000 |0 |0 |
| Kamera-Gitter-Holdout |1.000 |0 |0 |
| Geometrie-Holdout |1.000 |0 |0 |

Null schädliche übernommene Aufnahmen bei null Aufnahmen ist **keine** nachgewiesene niedrige Schadensquote: Nenner0, Wilson-Obergrenze1,0. Der Bootstrap [0,0] beschreibt nur die identische deaktivierte Policy und ist kein aktiver Nutzenbeleg. Need-Recall der deaktivierten Policy ist0; Precision ist undefiniert. Es gibt keine finale gelernte Bewegungs-/Aufnahmevalidierung mit positivem Request-Nenner. Die Offline-Datenerzeugung hat Zusatzansichten gerendert; diese geplanten Label-Aufnahmen sind keine vom Modell angeforderten Zusatzbilder.

Gewinn-MAE auf Validation/Kalibrierung:0,783/0,835 äquivalente mm, Schluss-IID0,872, Kamera-Holdout0,771 und Geometrie-Holdout3,835. Auch ein kleiner durchschnittlicher Regressionsfehler bei stark überwiegend negativen Labels belegt keine brauchbare Blickauswahl.

## Eingefrorene Wahrnehmungs-Schlusskontrollen

M0 ist V2, M1 die Variante mit einer ersetzten Handansicht und M2 die eingefrorene Historienvariante. Folgende **Einzelansichts-Kontexte ohne alte Handhistorie** verwenden gleiche Pose/Sollmenge; Mittel der drei Seeds. Darstellung: Zuordnungspositionsfehler in mm /10-mm-Recall. Pose0 ist die gemeinsame Originalansicht, Posen1..5 sind neue Gitter-Holdouts; sie werden nicht als beliebiger Kameradomänen-Transfer bezeichnet.

| Kamera-OOD-Pose | M0 | M1 | M2 |
| --- | --- | --- | --- |
| 0 | 5.36 / 87.9% | 4.61 / 92.1% | 5.00 / 90.6% |
| 1 | 6.16 / 83.8% | 4.83 / 91.6% | 5.35 / 89.5% |
| 2 | 6.12 / 84.3% | 4.81 / 91.9% | 5.32 / 89.9% |
| 3 | 8.19 / 71.2% | 5.71 / 88.2% | 6.28 / 86.0% |
| 4 | 8.15 / 71.3% | 5.68 / 88.4% | 6.27 / 85.7% |
| 5 | 25.48 / 2.7% | 9.04 / 67.9% | 8.90 / 68.1% |

M1 ist in diesen Einzelansichtskontexten häufig besser als M2. Dies ändert die vorher eingefrorene Variantenwahl nicht nachträglich. Auf Schluss-IID, Pose0: M2 Position5,225mm/Recall90,055%, M1 4,799mm/91,578%, M0 5,483mm/87,643%. Reine feste Kameras mit M2:8,230mm/73,293%. Diese feste-Kameras-Kontrolle verwendet dieselbe observable Sollmenge des vollständigen Kontexts, einschließlich eventuell erst durch die Handkamera sichtbarer Objekte.

**Geometrie-OOD scheitert deutlich.** Lange/dünne Quader wurden nur verstreut erzeugt. M2 Pose0:27,251mm Zuordnungspositionsfehler und8,137% 10-mm-Recall gegenüber5,056mm/92,126% auf der verstreuten IID-Kontrolle (jeweils Seedmittel). Äquivalenter Satzfehler:70,024mm gegenüber5,681mm. Viele Quader werden als mehrere zusätzliche Kästen interpretiert; die visuell geprüfte Schlussüberlagerung zeigt dieses Problem. Eine erfolgreiche Generalisierung auf solche Formen wird nicht behauptet. Zuordnungspositionen allein lassen fehlende/zusätzliche Objekte weg; Satzfehler, Missing/Extra und Recall werden deshalb daneben berichtet. Vollständige Seed-/Pose-/Anordnungswerte stehen in den *_frozen_benchmark.json/rows.json.

## Technische Validierung und Grenzen

Sechs fokussierte Tests bestanden (Zukunftspixel, Zukunftshistorie, GT/robot_fraction-Ausschluss, Missing/Extra-Strafen, maskierter Szenenfokus und bekannte Roboterprojektion). Ein erster kleiner Smoke führte ohne Requests zu Ende; ein gezielt erzwungener technischer Smoke prüfte echte Simulationserfassungen. Ein strikter bitweiser RGB-Vergleich scheiterte an genau einem festen-Kamera-Kanal um1/255. Nach Host-Nachweis des beendeten Prozesses wurde genau eine technische Korrektur vorgenommen: sehr enger Raster-Rundungsfilter (maximal1 Kanalwert, höchstens0,1% geänderte Kanäle), gemessenen Unterschied speichern und tatsächlich neu erfasste RGB/Kalibrierung verwenden. Größere Abweichungen bleiben ein Fehler. Das Originalfehlerlog ist erhalten.

Der reparierte technische Smoke mit getrennten, nicht reservierten Seeds endete erfolgreich:24 Familien,41 erzwungene Zusatzaufnahmen, maximal2, davon22 schädlich. Diese negativen Ergebnisse sind erhalten. Erzwungene Requests sind kein Beleg für eine erfolgreiche gelernte Auswahl.

Vor jeder tatsächlichen technischen Smoke-Aufnahme wurden vollständige Gelenkzustände als IK-Zeugen mit Vorwärtskinematik, Gelenk-/Greifergrenzen, Selbstkollisionen, statische Welt und beide gesamten Pfadstücke über die gemeinsame Ausgangskonfiguration unabhängig geprüft. Konservative swept AABBs schließen Objektüberschneidungen für Arm/Greifer/Kamera einschließlich Halterungsproxy aus; Wunsch-/Plan-/Ist-Pose und Bild bleiben getrennt im CaptureRequest. Das ist kinematische Simulation mit expliziter Simulatorreferenz, keine visuell bewiesene Realroboter-Freiraumlösung. Keine reale Bewegung wurde ausgeführt.

## Budget, Provenienz und Artefakte

Phase inklusive Review/Implementierung:09:02:19 bis10:02:41 Berlin, rund1h00m22s. Ihre unveränderte Maximaldeadline blieb15:02:19 Berlin; globale Sessiondeadline16:31:20 Berlin. Unabhängiger Supervisor und Worker waren sofort beim bestehenden Deadline-Guard registriert, query_ok=true/in_job=false. Exit0; beide PIDs sind in Host-Sicht beendet. Kein Neustart setzte das Budget zurück. Keine Deployments, Pushes, kostenpflichtigen Dienste oder zusätzlichen Agenten/Chats.

Nachprüfung: alle ursprünglichen und neuen Arrayhashes, sieben ursprüngliche Checkpoints, die drei ausgewählten Kopfhashes und der neue Source-Snapshot geprüft; alle Familien-Splits disjunkt, Kameragitter-Holdouts und dünne/lange verstreute OOD-Bereiche korrekt. Die Policy war vor Schlussdatenerzeugung eingefroren. 13.000 Journale wurden vollständig auf Hashkette/Zustandsfolge geprüft. Offline-Labelabdeckung:45.000 Wünsche,44.691 geplante/erfasste Kandidaten und309 blockierte; gelernte Schluss-Policy:4.000 Entscheidungen,0 Requests/Erfassungen. Diese Nenner bleiben getrennt. Details: followup_001/final_audit.json und journal_audit.json. Neue Ergebnisse/Checkpoints befinden sich ausschließlich in neuen Anschlussverzeichnissen; originale Resultate/Weights/Daten sind unverändert.

Wichtige Dateien unter followup_001: decision.json, protocol.json, phase.json, source/, checkpoints/, head_curves.json, head_loss.png, calibration.json, policy_freeze.json, *_head_metrics.json, *_head_reliability_gain.png, *_frozen_benchmark.json, *_summary.json, *_cases.json, geometry/, policy/ und observations/. TECHNICAL_REPAIR.md dokumentiert den einzigen Reparaturversuch; LAUNCH_REVIEW.md die zunächst wegen Verwechslung von Worker und Agent abgelehnte und nach Host-Belegen genehmigte Worker-Ausführung.

Empfohlener Abschlusswert: **review_only**, mit abgeschlossener Implementierung/Trainierung/Auswertung, aber nicht freigegebener aktiver Blickwahl. Keine weitere testgetriebene Optimierung in diesem Auftrag.
