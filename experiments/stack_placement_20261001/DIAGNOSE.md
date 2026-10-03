# Diagnose: vom Anheben zum Stack

Der dominante Fehler liegt im **Transport und der horizontalen Positionierung**, bereits vor dem eigentlichen Release. Die erneute Baseline hebt 13 Würfel an: **9 erreichen nicht einmal den 3-cm-Zielbereich**, die übrigen **4 verfehlen die 9-mm-Positioniertoleranz**. Kein Versuch erreicht korrektes Absenken oder korrektes Loslassen auf dem Ziel. Vorzeitige Öffnungsbefehle treten zusätzlich auf, erklären den fehlenden Transport aber nicht allein.

## Vergleich auf festen Starts

Alle Varianten verwenden denselben korrigierten State-Diffusion-Checkpoint, 2 ausgeführte Aktionen je Neuplanung, Seeds 46000–46019 und 500 Schritte. Die Anfangszustände wurden gegen die bisherigen SHA-256-Hashes geprüft. Kein Training, kein Datenumbau, keine Checkpointänderung.

| Variante | Greifen | Anheben | Positionieren | Absenken | Release | Stack |
|---|---:|---:|---:|---:|---:|---:|
| Bisheriger Bestwert: Scheduler korrigiert, 2 Aktionen | 17/20 (85%) | 14/20 (70%) | nicht protokolliert | nicht protokolliert | 0/20 | 0/20 |
| Diagnose-Baseline | 17/20 (85%) | 13/20 (65%) | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) |
| Nur Öffnungssperre | 17/20 (85%) | 13/20 (65%) | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) |
| Nur XY-Korrektur | 17/20 (85%) | 13/20 (65%) | 12/20 (60%) | 11/20 (55%) | 10/20 (50%) | 9/20 (45%) |

Der neue Baseline-Lauf reproduziert die Greifrate und alle Null-Erfolge, aber Seed 46019 wird diesmal nicht als angehoben gezählt (13 statt 14). Gleiche Starts und Zufallsseeds garantieren hier keine bitidentischen GPU-/Simulationsverläufe; auch vor dem Eingriff gibt es kleine numerische Unterschiede. Deshalb sind die **neu instrumentierte Baseline und die zwei Eingriffe** der Hauptvergleich; der historische Bestwert bleibt separat sichtbar. Die zwei Eingriffe wurden nicht kombiniert.

## Phasen und Messregeln

1. Greifen: ursprüngliches kontaktbasiertes Grasp-Prädikat.
2. Anheben: ursprüngliche Metrik, B-Zentrum > Tischhöhe +80 mm.
3. Transport: nach Anheben XY-Abstand zu A <30 mm und B mindestens 32 mm höher.
4. Positionieren: dieselbe Bedingung, aber XY <9 mm.
5. Absenken: Positionieren plus B-A-Höhendifferenz 40±8 mm.
6. Release: passende Geometrie plus Würfelkontakt und kein Grasp von B.
7. Stack: unverändertes Umgebungsprädikat, einschließlich Geschwindigkeitsgrenzen, ohne Grasp und 0,5 Sekunden stabil.

Die Phasenmetriken zählen mindestens einen passenden Simulationsschritt. Ein Release ist daher noch kein stabiler Stack. Ein vollständiger Greiferrückzug ist nicht Teil des bisherigen Erfolgskriteriums. Die neuen Läufe stoppen wie bisher bei Erfolg oder 500 Schritten; sie bestätigen **keine zusätzliche 2-Sekunden-Nachlaufstabilität**.

## Zustands- und Aktionsbefunde

In der Baseline beträgt der kleinste XY-Abstand nach Anheben über die 13 Fälle zwischen 11,6 und 139,6 mm, Median 87,1 mm. Es geht überwiegend um Zentimeterfehler, nicht eine knapp verfehlte Release-Höhe. Beispiel Seed 46000: gehaltenes Anheben bei Schritt 149, erstes Öffnen bei 170, noch etwa 107 mm vom Ziel entfernt; trotz wiederholtem Öffnen/Schließen bleibt der Würfel mindestens 87 mm entfernt. Seed 46006 nähert sich bis etwa 40 mm, öffnet dann und erreicht ebenfalls keine Positionierung.

Die Baseline hat in jedem angehobenen Fall Öffnungswechsel (4–43 Wechsel pro Episode). Die Finger reagieren: bei Seed 46000 wächst ihre Trennung zwischen Schritt 200 und 220 von etwa 39,5 auf 75,9 mm, während der Grasp verloren geht. Kein Hinweis auf ein grundsätzlich funktionsloses Öffnungssignal. Einzelne kurze negative Befehle führen wegen der Gripper-Dynamik nicht sofort zum Kontaktverlust.

Die mediane Neigung der nächsten horizontalen Würfelfläche liegt je angehobener Baseline-Episode bei etwa 0,2–13,9 Grad, Median über Episoden 2,6 Grad. Die Auswertung berücksichtigt die 90-Grad-Symmetrien eines gleichseitigen Würfels. Orientierung kann einzelne Kontakte verschlechtern, ist aber kein überzeugender alleiniger Grund für die weit verbreiteten großen XY-Fehler. Die Demos enthalten durchgängig Null-Rotationsaktionen; die Policy erzeugt kleine zusätzliche Rotationsaktionen.

## Die zwei isolierten Eingriffe

**Öffnungssperre:** Nach erstmaligem gehaltenem Anheben wird ausschließlich ein Öffnungsbefehl außerhalb XY <9 mm und Höhe 40±8 mm durch Schließen ersetzt. Alle sechs Armaktionsdimensionen bleiben unverändert. Die Prüfung zeigt, ob vorzeitiges Öffnen allein den Ablauf verhindert. Sie enthält keinen Zieltransport und erzwingt kein späteres Release.

**XY-Korrektur:** Nach gehaltenem Anheben ersetzt ausschließlich ein proportionaler Regler die zwei horizontalen Aktionen: `clip(-0.6 * (B_xy - A_xy) / 0.05, -1, 1)`. Er wirkt nur solange B tatsächlich gegriffen ist. Höhe, Rotation und Gripper bleiben Policy-gesteuert. Zielpositionen sind bereits in den State-Beobachtungen verfügbar; der Regler ist dennoch eine explizite diagnostische Steuerung und kein gelernter Policy-Erfolg.

Die Öffnungssperre allein führt nur 3/13 angehobene Würfel in den 3-cm-Zielbereich und keinen in die Positioniertoleranz. Sie behebt den Engpass daher nicht. Daraus folgt nicht, dass die Gripperentscheidung unwichtig wäre; ein ständig geschlossener Gripper führt die Policy auch in Zustände außerhalb der erfolgreichen Demos.

Die XY-Korrektur verschiebt den Engpass nach hinten: 12 Positionierungen, 11 Absenkungen, 10 geometrische Releases, 9 stabile Stacks bei 13 Anhebungen. Damit kann die unveränderte Höhen-/Gripperpolicy bei korrekter lateraler Führung häufig erfolgreich abschließen. Verbleibende Fälle: Seed 46008 verliert den Würfel vor der Ausrichtung; Seed 46015 positioniert, senkt aber nicht passend ab; Seed 46014 erreicht die Absenkgeometrie ohne korrektes Kontakt-Release; Seed 46002 hat nur einen korrekten Release-Schritt und stabilisiert sich nicht.

## Demonstrationsdaten und Hypothesen

Alle 200 Demos enthalten einen Schließen→Öffnen-Übergang beim Ziel. Beim Öffnungsbeginn: XY-Median 2,51 mm, Maximum 8,71 mm; Höhendifferenz-Median 40,44 mm, Bereich 38,05–44,15 mm. Der Übergang fehlt daher nicht grundsätzlich und seine Geometrie ist konsistent. Frühere gespeicherte Aktionsreplays waren bei 6/6 geprüften Train-/Validierungsdemos erfolgreich.

Der Expert nutzt jedoch eine interne Phase, gespeicherte Ziele und 20-Schritt-Verweilzeiten. Diese Variablen fehlen als direkte Labels in den Beobachtungen. Zwischen letztem Schließen und erstem Öffnen ändern sich Positions-/Fingermerkmale median nur um 1,35 mm (gemeinsame euklidische Distanz), die EEF-Orientierung median um 0,045 Grad. Das beweist keine identischen Eingaben, macht zeitabhängige Aktionswahl bei ähnlicher Geometrie aber plausibel. Die Policy sieht nur eine kurze Beobachtungshistorie. Die erfolgreichen Demos bieten kaum Abdeckung für die tatsächlich auftretenden Fehlgriffe, verfrühten Releases und Wiederholungsversuche.

Die Demos enden 15–18 Schritte nach dem Öffnen; der Expert würde erst nach 20 Schritten in den Rückzug wechseln. Damit gibt es **keine vollständige Rückzugsphase in diesen Daten**. Das ist ein separater Abdeckungsfehler, erklärt jedoch nicht den schon davor beobachteten Transportausfall.

Wahrscheinlichste Hypothesen, nach Evidenz geordnet:

- **Unzuverlässige laterale Zielsteuerung bzw. Lift→Transport-Phasenwahl:** durch große XY-Fehler und den isolierten XY-Test stark gestützt.
- **Vorzeitige/wechselnde Gripperentscheidung als zusätzlicher Phasenfehler:** direkt sichtbar; die Öffnungssperre prüft, ob dessen Behebung allein genügt.
- **Verdeckte Expert-Phase und fehlende Recovery-/Rückzugsdaten:** plausible Lernursache, durch Datenbefunde gestützt, in dieser Runde nicht durch neues Training kausal getestet.

Action Chunking ist nicht vollständig ausgeschlossen: 2 Aktionen entsprechen 0,1 Sekunden ohne Neuplanung, und kurzzeitige Gripperwechsel bleiben möglich. Beide Tests behalten aber denselben Chunk und Replanning-Takt. Der Erfolg allein durch XY-Korrektur zeigt, dass dieser Takt den Task grundsätzlich zulässt. Ein weiterer Horizont- oder Trainingsvergleich wäre hier keine isolierte Bestätigung der Hauptdiagnose.

## Nachvollziehbare Artefakte

- `analysis.json`: Phasenmetriken, erste Ereignisschritte, Öffnungswechsel und Zielabstände je Start.
- `data_audit.json`: Demonstrationsabdeckung und Übergangsstatistik.
- `verification.json`: identische Starthashes, erlaubte Aktionsdimensionen und Aktivierung erst nach gehaltenem Anheben geprüft.
- `baseline/`, `release_gate/`, `xy_feedback/`: NPZ mit allen Zuständen, ausgeführten und ursprünglichen Policy-Aktionen; Ergebnisse und repräsentative MP4s.
- `trace_46000.png`, `trace_46003.png`, `trace_46006.png`: direkte Zeitverlaufsvergleiche.
- `README.md`: Spaltenschema, Messregeln und Reproduktionsbefehle.

Für sieben Starts ohne gehaltenes Anheben kann keiner der Eingriffe aktiv werden. Diese exakt unveränderten Baseline-Trajektorien wurden übernommen und ausdrücklich markiert. Die übrigen 13 Starts wurden je Eingriff neu simuliert. Ergebnisse beruhen auf einem Checkpoint und 20 festen Starts; daraus folgt keine allgemeine Erfolgsrate auf neuen Starts.
