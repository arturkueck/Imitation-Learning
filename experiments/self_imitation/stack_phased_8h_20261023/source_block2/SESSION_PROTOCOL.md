# Zwei Trainingsbloecke mit echter Agentenanalyse, 23.10.2026

Nutzerauftrag: etwa acht Stunden, zuerst vier Stunden Training, vertiefte Analyse durch den Agenten, dann drei bis vier Stunden zweites Training, zwei weitere Berichte. Die Gesamtdeadline ist verbindlich und steht nach Start in session.json. Trainingsbloecke enthalten Optimierung und regelmaessige Simulationstests; reine GPU-Optimierungszeit wird getrennt protokolliert. Keine Behauptung von acht Stunden GPU-Training. Vorbereitung und kurzer Funktionscheck werden separat ausgewiesen.

## Wissenschaftliche Basis

Die vorherige Hoehenablation zeigte auf den untersuchten Starts keinen stabilen Erfolg ab +2 cm, obwohl einzelne Modelle bei 0 cm erfolgreich waren. Das begruendet eine Hoehen-/Phasen-spezifische Methode, nicht bloss weitere Updates desselben Modells.

Block 1: phase-conditioned BC aus exakt denselben 180/20 Zwei-Wuerfel-Demos. Der urspruengliche programmierte Experte rekonstruiert interne Phasen und Abschlusslabels aus gespeicherten Zustaenden. Es werden keine neuen Demonstrationen erzeugt. Rekonstruierte Aktionen werden gegen alle Originalaktionen geprueft. Freie Drei-Wuerfel-Szenen bleiben Evaluation. Die bekannten 61000er/63000er Starts sind Entwicklung, keine finalen Testdaten.

Sieben gelernte MLP-Koepfe (10→128→128→5). Vier aktive Aktionswerte XYZ und Greifer plus Abschlusslogit. Rotationsaktionen sind im Datensatz exakt null und bleiben deshalb explizit null. Eingaben: EEF minus beim Phaseneintritt eingefrorener Objektanker, EEF-Quaternion, Greiferpositionen, Phasenschrittzaehler. Anker ist der bewegte Wuerfel fuer Phasen 0–3 und das Ziel fuer Phasen 4–6. Keine vorgegebenen Zieloffsets oder XYZ-Expertenaktionen zur Inferenz. Die lokale Objektverankerung soll Hoehenuebertragung ermoeglichen.

**Vorgegebene Struktur:** Reihenfolge der sieben Teilphasen sowie Reihenfolge der Wuerfelpaare. Phasen 0–5 schalten anhand des gelernten Abschlusslogits (Schwelle 0,8). Nach Phase 6 wird das naechste Paar erst bei zehn Frames physisch gueltigem Zweierstapel gewaehlt. Keine gelernte Planung beanspruchen. Der Rueckzug (Phase 7 des alten Experten) fehlt in den Daten; keine erfundene Supervision und kein versteckter Rueckzugscontroller. Fuer drei Wuerfel werden die sieben Phasen erneut auf das naechste Paar angewendet.

Batch 64, Phasen gleichwahrscheinlich und innerhalb jeder Phase gleichwahrscheinlich Frames ziehen. Actor-MSE auf vier Aktionen plus 0,1 * positiv gewichtete BCE fuer Abschluesse 0–5; positive Gewichtung aus ausschliesslich Trainingsframes. Phase 6 hat keine Abschlusslabels. AdamW 1e-4, Weight Decay 1e-6, 500 Updates Warmup, Gradientennorm begrenzt auf 10. Drei Trainingsseeds 1,2,3. Kein Vergleich dieser Datenpasszahlen mit historischen Batch8/Uniform-Epochen ohne Samplinghinweis. Echte Updates, gezogene Beispiele, Optimierungszeit und Evaluationszeit berichten.

Im ersten Block wechseln die drei Seeds nach je 3.000 Updates. Danach je Seed zehn Zweier- und zehn Dreier-Entwicklungsstarts 63000–63009 (jeweils wiederholt, Modellwahl moeglich). Anders als beim letzten Pilot wird Dreierkompetenz von Anfang an getestet. Aktions-/Phasen-/Positionszeitreihen jeder Evaluation bleiben gespeichert. 500/1000 Schritte bei20Hz; 50 durchgehend gueltige Frames mit Kontakten, keinem Greiferkontakt und niedrigen Geschwindigkeiten, wie im vorherigen strengen Benchmark. Keine Tests auf nur vorbereiteten Stapeln als Dreier-Erfolg ausgeben.

Checkpointwahl vorab: best.pth wird bei verbessertem vollstaendigem Dreier-Dev-Erfolg gespeichert, bei Gleichstand entscheidet Zweier-Dev-Erfolg, bei weiterem Gleichstand bleibt der fruehere Checkpoint. best.json dokumentiert die genaue Runde. latest und jede fuenfte Runde bleiben zusaetzlich erhalten. Zwischenanalyse darf weitere vorhandene Kandidaten diagnostizieren, eine abweichende Auswahl muss als Entwicklungsentscheidung dokumentiert werden.

Die neue Methode aendert Architektur, Aktionshorizont, Sampling, Rotationsausgabe und strukturierte Phasen gleichzeitig. Historische Modelle sind Kontext, kein isolierter kausaler Vergleich. Zwischenanalyse muss festhalten, ob Erfolg aus der gelernten Bewegung plus vorgegebener Struktur kommt. Fuer Block 2 einen begruendeten Faktor oder gezielte Fortsetzung waehlen und die Vergleichbarkeit offenlegen.

## Zeitplan und Steuerung

1. Sessionstart und absolute UTC-Zeitgrenzen werden in session.json eingefroren. Block 1 arbeitet vier Stunden bis block1_deadline, cooperative Stop plus externer Prozessbaum-Watchdog.
2. Ein Chat-Heartbeat prueft alle zehn Minuten. Unveraenderte Zwischenstaende bleiben still, echte Agentpruefungen in agent_checks.jsonl festhalten. Keine erfundenen Pruefungen durch den Agenten; der Watchdog ist nur ein Prozesswaechter.
3. Nach Block 1 liest der Agent Logs, Lernkurven, phasenweise Validierung, Tracefehler und Checkpointhashes; fertigt REPORT_1.md mit inhaltlicher Diagnose an. Zusaetzliche gezielte Replays sind autorisiert. Keine automatische Textschablone als tiefgehende Agentenanalyse verkaufen.
4. Erst danach schreibt der Agent block2_decision.json mit agent_analysis_complete=true, Begruendung und vollstaendigem plan. Der Coordinator startet den zweiten Block automatisch. Ohne diesen echten Analyseschritt startet er nichts. Block2 endet spaetestens30Minuten vor Gesamtdeadline, damit Abschlusstests und REPORT_2.md in die acht Stunden passen. Analyse-/Schedulingverzoegerungen transparent berichten; Gesamtdeadline nicht heimlich verlaengern.
5. Nach Block 2 bewertet der Agent die Verbesserung, fuehrt soweit zeitlich moeglich die vorab getrennten Tests aus und erstellt REPORT_2.md. 90%-Ziel: mindestens90/100 auf JEDEM der drei Trainingsseeds. 100 frische Starts 84000–84099 sind exklusiv fuer den abschliessenden Test vorgesehen; keine Optimierung/Modellwahl anhand dieser Starts. Erweist sich die Methode als klar gescheitert oder reicht die Zeit nicht, Umfang und fehlende Tests ausweisen, keine0/100 erfinden. Keine Garantie von90%.
6. Erst nach beiden Berichten und verifiziertem Prozessende wird die Automation pausiert. Falls die Deadline ohne vollstaendige Ergebnisse erreicht wird, genaue Teilergebnisse und Ursache berichten. Kein Training nach Gesamtdeadline.

Bei technischem Fehler sind Diagnose, Korrektur und ein explizit dokumentierter Neustart innerhalb der unveraenderten Deadline autorisiert. Alte Outputs erhalten; keine blinden Wiederholungen oder parallelen Trainings. Wissenschaftlich schlechte Scores sind kein technischer Fehler. Keine neuen Trainingsdaten oder RL-Updates. Ein Aendern der Methode in Block2 darf nur aus der Zwischenanalyse folgen und muss mit Code-/Konfigurationssnapshot nachvollziehbar sein.

## Ausgaben und Fortsetzung

- session.json, status.json, active_child.json: Laufgrenzen und Prozesse.
- block1_plan.json; block1/seed*/latest.pth und periodische Snapshots; learning_curve.json und *_traces/*.npz.
- block2_decision.json/plan: echter Agententscheid nach REPORT_1.md; block2/ analog.
- REPORT_1.md und REPORT_2.md: die zwei angeforderten Berichte, jeweils mit Messwerten, Interpretation, Einschraenkungen, Zeiteinsatz und naechster Entscheidung.
- STOP-Datei beendet nur diese Session. Wachhaltemodus wird nach Abschluss/Deadline freigegeben.
- Block1-Code wird vor Start in source_block1 eingefroren. Vor methodischer Block2-Aenderung erneut Snapshot source_block2 samt Hashes anlegen. Kein vorheriger Bericht/Checkpoint wird ueberschrieben.

## Konkreter Agentauftrag am ersten Uebergang

Trainingsstatus und echte Updatezahlen lesen. Beste vollstaendige Dreier-Dev-Checkpoints je Seed anhand gespeicherter Runde bestimmen (bei Gleichstand offline Fehler und Phasendiagnose explizit als Entwicklungskriterium deklarieren). Checkpoints existieren nur bei Runde1 und jeder5.Runde sowie latest; niemals die Gewichte einer nicht gespeicherten Runde behaupten. Vollstaendige Bewertungen der erhaltenen Kandidaten nachholen. Replays unterscheiden fruehes/falsches Phasenende, Stillstand, Griffverlust, Zielkontakt und stabilen Turm. Fuer Hoehenablation kann die bestehende HeightStack-Umgebung mit Policy aus method.py verwendet werden, Metrik unveraendert, keine Trainingslabels. Dann REPORT_1.md schreiben und Phase2-Plan erstellen.

Block2-Plan-Schema: name='block2', seeds=[1,2,3], lr, completion_lambda, threshold, width=128, updates_per_round=3000, dev_episodes=10, train_deadline=session.deadline-1800, parents={"1":absoluteCheckpoint,...}, restore_optimizer=true. Neue Initialisierung nur bei nachvollziehbar geaenderter Architektur und klarer Kennzeichnung. Entscheidung enthaelt agent_analysis_complete=true, rationale und plan. Der Coordinator liest die Entscheidung; keinen zweiten Coordinator starten. Bei Bedarf lernratenspezifisches Fortsetzen ist moeglich; Erfolg der ersten Methode bestimmt die Wahl, nicht die Wunschrate.
