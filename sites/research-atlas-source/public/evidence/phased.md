> **Messkorrektur24.10.2026:** Die zusätzliche Fingerkontaktfreiheitsprüfung war wegen eines Gripper-Dictionary-Fehlers nicht zuverlässig. Historische Quoten gelten für die damalige Metrik. [Details](../stack_five_curriculum_20261023/MEASUREMENT_CORRECTION.md).

# Bericht 2: Zweiter Trainingsblock und Abschlussanalyse

**Das90%-Ziel ist verfehlt.** Die drei final ausgewaehlten Modelle erreichen62/100,48/100 und50/100 stabile vollstaendige Dreiertuerme auf den reservierten neuen Starts84000–84099. Alle300 Episoden sind vollstaendig. Die Modelle wurden vor dem ersten Test anhand der Entwicklung ausgewaehlt, kopiert und gehasht; nach Testbeginn keine Optimierung oder Modellauswahl. Die drei Modelle verwenden dieselben100 Szenen, also keine300 unabhaengigen Trainingsreplikate.

![Ergebnisse](final_results.png)

| Seed | Ausgewaehlte kumulative Updates | Entwicklung | Neuer Test | Wilson95%-Intervall |
|---|---:|---:|---:|---|
| 1 | 327000 | 6/10 | 62/100 | [52.2%, 70.9%] |
| 2 | 285000 | 8/10 | 48/100 | [38.5%, 57.7%] |
| 3 | 102000 | 7/10 | 50/100 | [40.4%, 59.6%] |

## Zwei Trainingsbloecke und Zeitbilanz

| Seed | Block1 Updates insgesamt | Block2 Ausgangscheckpoint | Zusaetzliche Block2 Updates | Kumulativ nach Block2 |
|---|---:|---:|---:|---:|
| 1 | 210000 | 204000 | 180000 | 384000 |
| 2 | 207000 | 165000 | 179347 | 344347 |
| 3 | 207000 | 96000 | 177000 | 273000 |

Block1: 3.986h Prozesslaufzeit, 74.2min gemessene Optimierung insgesamt. Block2: 2.927h Prozesslaufzeit, 63.1min Optimierung insgesamt. Der Rest entfiel vorwiegend auf Simulation und Auswertung. Block2 lief rund2h56min statt voller3–4h: die verspaetete Zwischenanalyse kostete Zeit. Die urspruengliche Deadline16:19:19 Uhr Berliner Zeit wurde nicht verlaengert. Nicht alle in Block1 trainierten Updates liegen auf dem Elternpfad der ausgesuchten Block2-Modelle, weil fruehere best-Checkpoints statt latest fortgesetzt wurden.

Block1-Bestwerte:4/10,7/10,5/10. Block2-Bestwerte:6/10,8/10,7/10. Das sind ausgewaehlte Werte auf wiederholten Entwicklungsstarts, kein unverzerrter Nachweis einer allgemeinen Verbesserung. Fuer Block1 wurde kein gleich grosser unabhaengiger Endtest auf denselben reservierten Starts nachgeholt. Die Behauptung einer gesicherten Testverbesserung von Block1 zu Block2 waere deshalb nicht gedeckt.

## Was bewirkt der eingefuegte Rueckzug?

Ausfuehrungsablation nach Abschluss aller Tests auf ausschliesslich alten Entwicklungsstarts: identische final eingefrorene Gewichte, identische zehn Initialzustand-Hashes, gleicher Erfolgstest und gleiche Schwelle. Einziger variierter Faktor ist die Wiederverwendung des gelernten offenen Anflugkopfes als zusaetzliche Rueckzugsphase. Es werden keine Testresultate fuer diese Diagnose zurueck ins Training gegeben.

| Seed | Ohne Rueckzug | Mit Rueckzug | Gewonnene Starts | Verlorene Starts |
|---|---:|---:|---:|---:|
| 1 | 4/10 | 6/10 | 4 | 2 |
| 2 | 7/10 | 8/10 | 1 | 0 |
| 3 | 3/10 | 7/10 | 4 | 0 |

Damit ist auf diesen Szenen ein positiver Ausfuehrungseffekt des Rueckzugs sichtbar (+2,+1,+4 Erfolge); bei Seed1 gehen zugleich zwei zuvor geloeste Starts verloren. Das ist ein lokaler gepaarter Entwicklungsbefund. Drei Seeds und zehn wiederverwendete Szenen erlauben keine breite Signifikanzbehauptung. Die zusaetzliche niedrigere Trainingslernrate wurde nicht separat randomisiert; der gesamte Blockvergleich isoliert ihren Einfluss nicht.

## Verbleibender Fehlermechanismus

| Seed | Erste stabile Paarplatzierung | Zweite Fertigkeit begonnen | Fehlschlaege am Ende in zweiter Phase6 |
|---|---:|---:|---:|
| 1 | 98/100 | 98/100 | 30 |
| 2 | 98/100 | 98/100 | 46 |
| 3 | 96/100 | 96/100 | 46 |

Die erste Platzierung ist auf neuen Szenen mit98/100,98/100 und96/100 sehr zuverlaessig. Der Engpass ist weiterhin die Komposition nach der ersten Platzierung. Bei30/46/46 Fehlschlaegen steht die Policy am Ende in Phase6 des zweiten Paars; ein Endphasenlabel allein identifiziert jedoch nicht den Entstehungszeitpunkt.

Alle300 Testzeitreihen wurden auf endliche Werte geprueft und der Erfolg aus mindestens50 durchgehenden valid3-Frames erneut berechnet. Fuer jeden fehlgeschlagenen Versuch mit erstem Stapel wurde der erste Verlust der unteren A/B-Geometrietoleranz nach dem Erfolg der ersten Paarplatzierung untersucht, einschliesslich Rueckzugszeit. Bei den Seeds1/2/3 liegt dieser erste Verlust in31/45/16 Faellen waehrend Phase0 des zweiten Paars, in2/2/6 waehrend Phase1, in0/1/14 waehrend Phase2 und in0/0/1 waehrend Phase6. Bei3/2/9 bleibt die untere Geometrie innerhalb der Toleranz. Fuer diese Zaehler ist eine kurzzeitige Verletzung hinreichend; sie beweist weder irreversiblen Kollaps noch eine konkrete Kontaktkraftursache.

Der Rueckzug verbessert einzelne Uebergaenge, verhindert die Stoerung des unteren Turms bei der folgenden Anflug-/Greifbahn aber nicht verlaesslich. Es bleiben auch Fehler mit erhaltener unterer Geometrie, die Platzierung, Freigabe, Kontakt oder Stabilitaet des dritten Wuerfels betreffen. Die Hypothese eines ausschliesslichen Hoehenproblems ist deshalb zu eng; ebenso waere eine reine Loslasskorrektur unzureichend.

## Was ist gelernt, was ist vorgegeben?

Trainiert wurden sieben aktions- und abschlussvorhersagende Koepfe ausschliesslich aus den180 Zwei-Wuerfel-Trainingsdemos;20 Demos blieben Validierung. XYZ-/Greiferaktionen sind gelernt. Fest vorgegeben sind Phasenreihenfolge, Wahl der Paare, die zusaetzliche Wiederholung von Kopf0 beim Rueckzug, Objektauswahl/Anker sowie ein physisches Stabilitaetsgate. Rotationsaktionen bleiben wie alle Trainingslabels null. Privilegierte Objektpositionen und Simulator-Kontaktchecks werden verwendet. Es ist keine autonome Planung und kein neu aus Daten erlernter Rueckzugspfad. Dieses Strukturwissen muss bei jeder IL-Generaliserungsaussage genannt werden.

Die Ergebnisse zeigen reale, aber begrenzte Komposition gelernter Bewegungen zu drei Wuerfeln ohne Drei-Wuerfel-Trainingsdemos. Sie zeigen weder90% Zuverlaessigkeit noch weniger Epochen bis zu diesem Ziel. Mit phasenbalanciertem Sampling, Batch64 und teils frueheren Elterncheckpoints sind historische uniforme Batch8-Epochen nicht direkt vergleichbar.

## Entscheidung und Artefakte

Beide autorisierten Trainingsbloecke und beide Berichte sind abgeschlossen. Kein dritter Trainingslauf. Als naechste wissenschaftliche Untersuchung bietet sich eine kontrollierte Anflugbahn-/Freiraumdiagnose an: Wo beruehren Roboter oder bewegter Wuerfel den bestehenden Turm, und hilft eine klar ausgewiesene Bahnstruktur? Erst danach eine gezielte neue Methode. Die hier bereits gesehenen84000er Teststarts gelten bei weiterer Entwicklung als verbraucht; ein spaeterer Endnachweis benoetigt neue reservierte Starts.

Belege: REPORT_1.md, block1_trace_diagnosis.json, block2_trace_diagnosis.json, final_trace_analysis.json, final_lower_onset.json, final_test/selection.json und seed*_test3.json sowie saemtliche NPZ-Zeitreihen; retreat_ablation/results.json enthaelt die gewonnenen/verlorenen Starts. Hashes der drei finalen Modelle wurden erneut mit der vor Testbeginn gespeicherten Auswahl abgeglichen. Beide Trainingsprozesse endeten mit Returncode0. Prozessende des Coordinators und Freigabe seiner Wachhaltesperre werden im Abschlusscheck separat verifiziert.

Abschlusscheck: Coordinator meldet COMPLETED und coordinator_finished=true. Alle geprueften bekannten Sessionprozess-IDs sind beendet; damit ist die an den Coordinator-Thread gebundene Wachhaltesperre freigegeben. Der SHA-256 des originalen Zwei-Wuerfel-Datensatzes ist unveraendert. Siehe process_closeout.json und letzter Eintrag in agent_checks.jsonl.
