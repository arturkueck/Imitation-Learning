# Unterbrochener B0/B-Pilot: wissenschaftlicher Teilabschluss

Alle sechs Modelle erreichten 3.000 von geplanten 10.000 Updates. Beide Sessionprozesse fehlen bei der tatsächlichen Agentprüfung am 2026-10-24T18:42:30.621085+00:00. Der Lauf endete während der Entwicklungsbewertung und nicht regulär an einer Deadline. Die genaue Abbruchursache ist nicht ermittelt; Worker- und Startlogs enthalten keinen Python-Traceback. Keine belegte Ursache als Vermutung ausgeben.

Die letzten Statusdateien behaupteten weiterhin RUNNING/TRAINING. Eine externe Prozessinventur bestätigte dagegen das Fehlen von Supervisor35976 und Worker30588. Deshalb werden diese Statusdateien als veraltet archiviert. Kein blinder Neustart, keine neue Instanz, keine Deadlineverlängerung.

## Reale Rechenarbeit und Integrität

- Updates je Modell: {'B0_seed1': 3000, 'B0_seed2': 3000, 'B0_seed3': 3000, 'B_seed1': 3000, 'B_seed2': 3000, 'B_seed3': 3000}. Insgesamt 18000 Optimizerupdates, 30 % des geplanten Updatebudgets.
- Alle gespeicherten Actor-/Completionlosses und Gradientennormen endlich: True. Gespeicherte Samplehashes pro Seed/Update in B0/B identisch: True.
- Geprüfte Quellen-/Inputhashes: {'code_hashes': True, 'input_hashes': True, 'native_sources': True, 'frozen_manifest': True}. Jeder höchste Checkpoint enthält Update3000 und ist kein technisches Kurztestmodell.
- Je Modell 7.027 Originalpass-Äquivalente aller Mischbeispiele; tatsächlich gezogene Originalframes entsprechen 3.514 Originalpässen. Beides sind Normierungen, keine klassischen Epochen des gemischten Datensatzes. Vortraining und neue Simulation kommen hinzu.

## Vollständig gespeicherte Entwicklungsbewertungen

P2/P3: nächster Griff bei durchgehend erhaltenem Präfix mit zwei/drei Würfeln. F2/F3/F4: vollständige Türme. Ausschließlich Entwicklung; keine unabhängigen Endtestergebnisse.

| Modell | Updates | P2 | P3 | F2 | F3 | F4 |
|---|---:|---:|---:|---:|---:|---:|
| B0_seed1 | 0 | 9/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B0_seed1 | 3000 | 10/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B0_seed2 | 0 | 10/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B0_seed2 | 3000 | 8/20 | 3/20 | 9/10 | 3/10 | 2/10 |
| B0_seed3 | 0 | 7/20 | 4/20 | 8/10 | 3/10 | 2/10 |
| B_seed1 | 0 | 9/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B_seed1 | 3000 | 10/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B_seed2 | 0 | 10/20 | 3/20 | 9/10 | 4/10 | 2/10 |
| B_seed2 | 3000 | 8/20 | 3/20 | 9/10 | 3/10 | 2/10 |
| B_seed3 | 0 | 7/20 | 4/20 | 8/10 | 3/10 | 2/10 |

## Paarvergleich und Befund

Bei Seeds1 und2 sind nach3.000 Updates sämtliche aggregierten Entwicklungsquoten zwischen B0 und B gleich. Seed1 steigt beim P2-Übergang in beiden Armen von9/20 auf10/20; P3 bleibt3/20, vollständige2er/3er/4er bleiben9/10,4/10,2/10. Seed2 fällt bei P2 in beiden Armen von10/20 auf8/20 und beim vollständigen Dreierturm von4/10 auf3/10; P3 und F2/F4 bleiben gleich. Das liefert bisher keinen Hinweis auf einen Vorteil der Qualitätsgewichtung. Es beweist weder generelle Wirkungslosigkeit noch das Scheitern des gesamten Konzepts.

Beim dritten Seed ist die Bewertung B0/update3000 nur teilweise gespeichert; B/update3000 fehlt. Deshalb kein kompletter Drei-Seed-Armevergleich und keine nachträglich bevorzugte Auswahl anhand der vier vollständig bewerteten Kandidaten. Die transaktionale Auswahl in selected_development.json blieb für alle sechs beim vorher vollständig geprüften Update0. Das ist noch kein gemeinsamer Endmodellfreeze.

| Modell | Präfix | Erfolg / Gesamt | Erfolg / vorbereitet | Kontakt bei Fehlschlag |
|---|---:|---:|---:|---:|
| B0_seed1 | 2 | 10/20 | 10/18 | 8 |
| B0_seed1 | 3 | 3/20 | 3/13 | 8 |
| B_seed1 | 2 | 10/20 | 10/18 | 8 |
| B_seed1 | 3 | 3/20 | 3/13 | 8 |
| B0_seed2 | 2 | 8/20 | 8/18 | 9 |
| B0_seed2 | 3 | 3/20 | 3/13 | 9 |
| B_seed2 | 2 | 8/20 | 8/18 | 9 |
| B_seed2 | 3 | 3/20 | 3/13 | 9 |

Die identischen vorbereiteten Zustände ergeben pro vollständigem Panel18/20 vorbereitbare P2- und13/20 vorbereitbare P3-Fälle. Fehler der Teacher-Vorbereitung bleiben im Nenner; die bedingte Quote wird zusätzlich ausgewiesen. Kontaktspalten sind gezählte Ereignisse, keine bewiesenen alleinigen Ursachen des Scheiterns.

## Fehlerbild und Grenzen

Der Beispielvergleich Seed1/update3000 zeigt beim P3-Start521001 bereits nach vier Schritten einen Kontakt zum geschützten Turm und ungültiges Präfix. Ein erfolgreicher Start521000 hält dagegen den Turm über Pickup und50 Nachlaufframes; maximale gemessene untere Verschiebung etwa0,041mm. Das lokalisiert konkrete Kontaktfehler, ohne aus wenigen Episoden universelle Kausalität abzuleiten.

Bei vollständigen Vierertürmen Seed1/update3000 verbringt jeder der acht Fehlschläge zwischen1062 und1255 der1500 Schritte in Phase6; die beiden Erfolge nur85 bzw.89. Das deutet auf festhängende Ablauf-/Freigabebedingungen hin und ist keine präzise Messung des abschließenden Platzierungsfehlers. Für eine Diagnose in Millimetern fehlen in diesen kompakten Evaluationsresultaten vollständige Objektzeitreihen. Deshalb keine Genauigkeit erfinden.

Actor, sieben Phasen, Sequencer und Controller waren in beiden Armen identisch; Rotationen bleiben wie im Ausgangsmodell vorgegeben. Es wurde kein zusätzlicher Sicherheitscontroller trainiert. Completionloss wirkt nur auf Originalframes, teilt aber Hiddenlayer mit dem Actor. Einzelne Completion-Minibatchlosses sind keine unabhängige Completionvalidierung.

Nur49 neue Trainingsabschnitte, davon acht mit Präfix3, moderate Qualitätsvariation und strenge Erfolgsselektion begrenzen den Versuch. Die gewichtete effektive Abschnittszahl von48,89 gegenüber49 zeigt den kleinen Gewichtungskontrast. Zusätzliche Updates allein schaffen weder fehlende Turmbeobachtungen noch neue bessere Expertenaktionen.

## Unvollständige Tests, Kosten und Entscheidung

Kein Modell wurde für die unabhängige Schlussphase gemeinsam eingefroren. Bestätigung und reservierte Endtests wurden nicht gestartet. Sie sind UNGEMESSEN, nicht0/100. Kein90-%-Ziel ist nachgewiesen; kein Fünfertraining fand statt. Die Daten enthalten Drei-/Viererrollouts und sind kein reines Zweier-Zero-shot-Experiment.

Der letzte gespeicherte Evaluationsfortschritt liegt ungefähr36 Minuten nach Start; das Ende selbst wurde nicht protokolliert und liegt zwischen letztem Artefakt und dem jetzigen Agentcheck. Das ist keine exakt gemessene aktive GPU-/Simulatorzeit. Sammlung und technische Vorbereitung sind separat im DATASET_REPORT.md dokumentiert.

Vor einer Fortsetzung zuerst die Prozesslebensdauer des außerhalb des Agenten gestarteten Supervisors reproduzierbar absichern und einen geprüften Wiederaufnahmeweg für die unterbrochene Entwicklung implementieren. Vorhandene Optimizer-/RNG-Checkpoints bewahren. Danach einen neuen, ausdrücklich dokumentierten Fortsetzungsplan mit unverändert reservierten Endtests festlegen; kein Training aus Endtestergebnissen. Für den wissenschaftlichen nächsten Schritt sind insbesondere mehr unabhängig sichere Präfix3-Übergänge und eine separat kontrollierte Turmzustandsrepräsentation plausibel. Das ist ein Vorschlag, kein bereits bestätigtes Ergebnis.
## Zusätzlich erhaltene Teilbewertung Seed3 / B0 / Update3000

| Metrik | Erfolge / abgeschlossene Starts | vollständig |
|---|---:|---|
| prepared_prefix2 | 7/20 | True |
| prepared_prefix3 | 3/20 | True |
| full_stack2 | 9/10 | True |
| full_stack3 | 3/10 | True |
| full_stack4 | 1/7 | False |

Beim letzten Viererpanel wurden7/10 Starts abgeschlossen, davon1 erfolgreich. Start524007 war beim Abbruch in Bearbeitung und ist als möglicherweise verbraucht markiert. Er wird nicht automatisch wiederholt. Zwei weitere Starts wurden noch nicht begonnen. Diese teilweise Bewertung ist nicht mit einem vollständigen10erpanel gleichzusetzen.

Die stündliche Überwachungsautomation wurde nach diesem geprüften Teilabschluss gelöscht.
