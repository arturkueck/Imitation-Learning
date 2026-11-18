# BC, Curriculum und Freigabephase: Stand 13.11.2026

## Aktueller Abschluss: gezielte BC-Korrekturen

Neue Bestätigung auf 50 gemeinsamen Anfangsszenen je drei Modellseeds:
ursprüngliches B 85/150, Replay-Fortsetzung 92/150, neue Aktionen 92/150,
neuer Abschluss 78/150, Aktionen und Abschluss kombiniert **118/150**.
Die kombinierte Ausführung gewinnt gegen B 34 Paare und verliert eines;
gegen Replay 28 Gewinne und zwei Verluste. Alle drei Modellseeds verbessern
sich gegenüber Replay. Entwicklung und neue Bestätigung bleiben getrennt.

Gelernt wird aus Expertenkorrekturen des zweiten Anfahrens: 150 Sammelversuche,
135 akzeptiert; 2.069 Trainings- und 499 Validierungsframes mit Split nach
ganzen Anfangsszenen. Zwölf getrennte Aktions-/Abschlusskomponenten erhalten
je 5.000 zusätzliche Updates. Neue Ausgaben gelten nur für das zweite Anfahren,
außerhalb des Rückzugs; sonst bleibt B. Kein Experte übernimmt während der Tests.

Dieser gezielte BC-Nutzen ist auf neuen Starts im selben Simulator bestätigt.
Getrennte Ausgabekopien und Kontext-Gate gehören zum Verfahren. 150 Modell-/
Szenenpaare sind keine 150 unabhängigen Szenen; die 50 Starts werden über drei
Seeds geteilt. Ein Vorteil geordneter Curriculum-Reihenfolge, eine einzelne
gemeinsame MLP, Hardware-Übertragung und allgemein gelöste Datenabdeckung sind
nicht belegt. Keine weitere Untersuchung ist für diesen eingegrenzten
Abschluss zwingend; weitergehende Aussagen erfordern neue Versuche.

[Vollständiges Vorgehen, Einzelphasenprüfung, Trainingsdesign, Ergebnisse und Grenzen](CONCLUSION_20261113.md).

## Vorheriger bestätigter Befund: Zeitkorrektur

Die Begrenzung des Zeitmerkmals der letzten Freigabe verbessert alle sechs
unveränderten gewöhnlichen 60k-Modelle auf einem neuen gepaarten Panel.
600 Dreierturm-Modell/Szenenpaare: **60 zusätzliche Erfolge, kein verlorener
Erfolg**. Alle 120 Zweierturm-Kontrollpaare sind bitgenau identisch.
Null Optimizerupdates; dies ist eine Ausführungskorrektur, kein neu trainiertes Modell.

| Modell | Original | Zeit begrenzt | Gepaarte Gewinne / Verluste |
|---|---:|---:|---:|
| mixed_seed1 | 44/100 | 56/100 | +12 / −0 |
| curriculum_seed1 | 32/100 | 60/100 | +28 / −0 |
| mixed_seed2 | 40/100 | 42/100 | +2 / −0 |
| curriculum_seed2 | 51/100 | 58/100 | +7 / −0 |
| mixed_seed3 | 37/100 | 39/100 | +2 / −0 |
| curriculum_seed3 | 50/100 | 59/100 | +9 / −0 |

100 frische Szenen je Modell; gleiche Szenen über alle Seeds. Die Szenen sind
keine unabhängigen Trainingsreplikate. Der praktische Review-Schwellwert wurde
erreicht; daraus folgt keine allgemeine Garantie oder automatische Aktivierung.

## Was die vorherigen Vergleiche zeigten

1. **30k, B gegen C:** Durchmischte Batchreihenfolge 49/54/49, Curriculum
   47/40/41 Dreiertürme je 100 Starts im ursprünglichen Endpanel. Damals war
   das Zeitproblem noch vorhanden; das ist keine neue zeitkorrigierte A/B/C-Auswertung.
2. **30k → 60k:** Auf einem anderen frischen Panel durchmischt 51→49,
   56→50, 52→48; Curriculum 52→41, 47→62, 47→60. Mehr Updates halfen nicht einheitlich.
3. **Feste Abschlussfunktion:** Bei fünf der sechs Modelle niedrigere
   Dreierturmraten als mit gewöhnlicher Fortsetzung. Kein stabiler Vorteil.
4. **Diagnose:** Phase-6-Zeitwerte waren im Training nur bis Schritt 17 enthalten.
   Bei längerer Ausführung drifteten Aktionen im ausgewählten Fehlerfall nach
   unten und erneuter Fingerkontakt unterbrach die geforderten 50 stabilen Frames.
   Der kleine Vorversuch betraf ausgewählte historische Fälle, die anschließende
   Zeitkorrektur-Bestätigung hingegen 100 neue Starts je Modell.

Die genannten Panels verwenden verschiedene reservierte Szenenbereiche.
Ihre absoluten Prozentwerte dürfen nicht als durchgehende Leistungskurve
verkettet werden. Quellen und SHA-256 stehen in reporting/measured.json.

## Abgeschlossener A/B/C-Vergleich

Abgeschlossen: drei neue Standard-BC-Modelle A; die sechs
ursprünglichen B/C-30k-Modelle werden mit geprüften gleichen Ausgangsgewichten
und Einstellungen wiederverwendet. Alle neun Endpunkte erhalten dieselbe
Zeitbehandlung und frische gepaarte Zwei-/Dreierturmtests.

- A gegen B: Änderung der Datenexposition bei durchmischter Reihenfolge.
- B gegen C: Reihenfolge desselben Batch-Multisets.
- A gegen C: Gesamtnutzen dieses Curriculums.

Die vorhandenen besseren zeitkorrigierten 60k-Curriculumwerte belegen den
isolierten Curriculum-Nutzen bei 30k noch nicht. Es gibt weiterhin ausschließlich
Zweier-Demonstrationen; höhere Ablagen, Recovery und autonome Paarplanung sind
keine durch zusätzliche Trainingsdaten bereits gelösten Fragen.

Ergebnisse bei 30k Updates auf dem gemeinsamen neuen Dreierturm-Panel:
A 40/28/26, B 48/56/50, C 52/42/46 Erfolge je 100 Szenen pro Modellseed.
B übertrifft A in allen drei Seeds; C übertrifft B in einem von drei Seeds.
Ein Vorteil der geordneten Curriculum-Reihenfolge ist damit nicht konsistent.
Quelle: `praxis/results/curriculum/abc_comparison_20261112/ready_001/result_summary.json`.

## 13.11.2026: Phasendiagnose und zweiter Greifablauf

Die Phasendiagnose mit drei unveränderten B-30k-Modellen umfasst 220 Versuche.
Travel und Open erreichen aus den fünf gemeinsamen Expertenstarts je
Platzierung jeweils 30/30 Diagnoseziele über alle drei Modelle. Vollständige
Ausführungen zeigen dagegen 15 zweite Lift-Starts ohne erkannten Griff;
alle 15 Gesamtversuche scheitern.

Der anschließende gepaarte Eingriff ersetzt ausschließlich Approach,
Grasp-Descend und Close der zweiten Platzierung durch den Experten; danach
wieder unverändertes BC. Auf den bestehenden 20 Entwicklungsszenen je Modell
steigen vollständige Dreierturm-Erfolge von **26/60 auf 45/60**:
19 Gewinne, keine Verluste. Erkannter Griff bei erreichten zweiten Lift-Starts:
33/48 gegenüber 48/48. Alle 15 zuvor griff-losen Fälle werden erfolgreich,
zusätzlich vier bereits griff-positive Fälle. Zwölf frühere Abbrüche bleiben
erfolglos und werden weiterhin im Gesamtnenner 60 mitgezählt.

Dies stützt eine gezielte Untersuchung des zweiten Greifablaufs und seiner
Eingangszustände. Es belegt keine Verbesserung eines trainierten BC-Modells
und keinen Curriculum-Vorteil. Die drei ersetzten Phasen sind nicht einzeln
isoliert; drei Modellseeds teilen dieselben 20 Szenen. Null Optimizer-Updates,
keine neuen Bestätigungsszenen. Keine Vermischung mit dem A/B/C-Endtestpanel.

[Ausführliches Ergebnis mit Seedwerten, Grenzen und Ablage](phase_skill_audit_v1/GRASP_PROBE_RESULTS.md).
[Durchführung und Reproduktionsbefehle](phase_skill_audit_v1/GRASP_PROBE.md).
