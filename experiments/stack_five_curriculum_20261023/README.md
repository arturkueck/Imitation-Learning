# Freigegebener Fuenferturm-Pilot

Nutzerfreigabe: Okay go. Sessionstart 23.10.2026 21:17:08 UTC (23:17:08 Berlin).
Harte Deadline 24.10.2026 09:17:08 UTC (11:17:08 Berlin), Training endet spaetestens 07:17:08 UTC (09:17:08 Berlin). Einschliesslich Vorbereitung, Sammlung, Training und Tests. Keine Verlaengerung.

Eine unabhaengige technische Prozessaufsicht kontrolliert Deadline und STOP-Datei; Agentanalyse nur einmal je Stunde. Keine weitere Trainingsinstanz starten. Supervisor beendet seinen Worker-Prozessbaum und gibt die Wachhaltesperre am Ende frei.

Curriculum 3 -> 4 -> 5 mit unveraenderter Architektur. Pro Hoehe ein begrenzter Sammel-/Updatezyklus; maximal 120 neue Versuche (erste100 Training, letzte20 Validierung). Mindestens20 vollstaendige Trainingserfolge und3 Validierungserfolge vor Training. Aufstieg nur mit mindestens einem Teacher, der 30/50 UND 30/50 komplette stabile Tuerme auf zwei neuen Entwicklungsbloecken schafft. Einzelne bestandene Teachers erzeugen den gemeinsamen Datenpool; alle drei Lernreplikate werden getrennt ausgewiesen. Bei fehlendem Gate endet dieser Aufstieg, die blockierte Stufe wird nicht als trainiert gemeldet.

Drei Parents sind alle C-Modelle der vorigen entwicklungsselektierten Self-Imitation-Session. Kein Parent wird anhand der neuen Endtests gewaehlt. Batch64:32 Originalexpertendaten,16 fruehere Hoehen,16 neue Hoehe. Fruehere Hoehen gleichverteilt, dann Phase/Episode/Frame. Completion-BCE nur Originaldaten. AdamW3e-5, Clip10. Maximal30k/30k/120k Zusatzupdates je Seed. Der direkte Fuenfer-Self-IL-Arm beginnt mit denselben Parents, hat keine neuen Zwischenhoehendaten, dieselben Datengates und maximal180k Zusatzupdates je Seed. Unterschiedliche realisierte Kosten bei Blockade sind transparent; daraus keine budgetgleiche Effizienzaussage ableiten. Kein Scratch-RL-Vergleich.

Neue technische Umgebung erzeugt echte N Objekte bis5. Erfolg prueft Basis, alle benachbarten Kontakte, XY<=9mm, Hoehenabstand40mm+-8mm, niedrige Geschwindigkeiten und keinerlei Greiferkontakt;50 durchgaengig gueltige Frames. Horizont500*(N-1). Sieben BC-Phasen mit gelerntem Aktions-/Abschlusskopf; der externe Sequencer waehlt nach Freigabe/stabilem Praefix das naechste Paar. Rueckzug verwendet die gelernte Phase0, keine neuen Expertenaktionen. Vorbereitete Tuerme nur technischer Metriktest, keine Rollout-Erfolge oder Trainingsdemos.

Alle Seeds stehen vorab in protocol.json. Endtests360000+1000*N getrennt von Entwicklung/Sammlung; Modelle davor einfrieren. Ziel mindestens90/100 vollstaendige stabile Fuenfertuerme auf JEDEM der drei Seeds eines Arms. Fehlende Tests nie als0/100 ausgeben. Self-Imitation mit3/4/5-Daten belegt keine reine Zweier-Zero-shot-Generalisation. Ergebnisse/Fehler/Updates/Datenkosten und Hoehen-/Uebergangsfehler in RESULTS.md dokumentieren, manuelle vertiefte Analyse beim stündlichen Check ergaenzen.

Technische Vorpruefung: initialer positiver Physiktest vor Kontaktberuhigung schlug fehl; nach250 reinen Physikschritten sind vorbereitete2/3/4/5-Tuerme gueltig, versetzter oberster Wuerfel jeweils ungueltig. Kein Erfolgskriterium gelockert. Der natuerliche technische Fuenferrollout399001 war erfolgreich in685 Schritten mit drei Paarwechseln; er bleibt von Sammlung/Entwicklung/Endtest getrennt und beweist keine Erfolgsquote. Zwei je5-Update-Smokes pruefen Optimierung/Mischung; sie sind keine Produktionsmodelle.

Nach Ende: Prozessende/Wachhaltefreigabe pruefen, Daten-/Ergebnisbericht vervollstaendigen und erledigte Automation loeschen.
