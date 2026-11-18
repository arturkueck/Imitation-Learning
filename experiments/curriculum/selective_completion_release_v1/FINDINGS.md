# Selektiver Abschluss, Freigabe und Objektinformation: Ergebnis

18.11.2026. **COMPLETE: 354 Episoden in 52 Fallgruppen, 17,7 Minuten,
null Optimizerupdates.** Vorher elf gezielte Tests und ein technischer
Smoke mit 21 Episoden. Alle Integritaetspruefungen bestanden; Worker Exitcode 0,
Wachhaltezustand freigegeben. Drei vorhandene Modelllinien blieben eingefroren.
Nachtlauf, vorherige Untersuchungen und Checkpoints sind unveraendert.

## Ergebnis der drei Fragen

1. **Selektive Abschlusskorrektur:** Bei den bekannten zweiten Griffstillstaenden
   loest die spaete Bereitschaftsregel den lokalen Stillstand in 6/6 Paaren
   und rettet 3/6 Gesamtaufgaben. Ein reiner Timeout rettet 1/6. Die vier
   zuvor durch einen pauschalen Austausch geschaedigten Erfolgskontrollen
   bleiben 4/4 erfolgreich. Die Rettungen betreffen eine einzige Anfangsfamilie
   bei drei geerbten Parents, keinen allgemeinen Wirksamkeitsnachweis.
2. **Ablage und Freigabebewegung:** Keine der fuenf alternativen Kombinationen
   rettet einen der drei bekannten zweiten Freigabefehler. Die drei
   zugeordneten Erfolgskontrollen bleiben bei allen Kombinationen erfolgreich.
   Das geometrische Veto und die getesteten Bewegungsregeln genuegen nicht,
   um diese Fehler zu beseitigen.
3. **Zusaetzliche Objektinformation:** Die konkrete Objekt-XY-Rueckfuehrung
   zeigt keinen Vorteil im vollstaendigen Erfolg. Sie verbessert im
   auffaelligen Fall die XY-Lage, hinterlaesst aber Fingerkontakt. Die
   festgelegte Aehnlichkeitspruefung findet zudem keine widerspruechliche
   Ablagebereitschaft bei aehnlichen vorhandenen Eingaben. Eine
   Informationsluecke als Ursache schlechter Leistung ist hier weiter offen.

## Umfang, Auswahl und Vergleichbarkeit

| Panel | Modell-/Szenenpaare | Arme | Episoden |
|---|---:|---:|---:|
| 12 neue, vorher nicht zugewiesene Kalibrierungsfamilien x 3 Parents | 36 | 8 | 288 |
| Bekannte zweite Griffstillstaende: 2 Familien x 3 Parents | 6 | 3 | 18 |
| Erfolgskontrollen, die der fruehere pauschale Griffabschluss verlor | 4 | 3 | 12 |
| Bekannte zweite Freigabefehler | 3 | 6 | 18 |
| Urspruenglich zugeordnete erfolgreiche Freigabekontrollen | 3 | 6 | 18 |

Alle neuen Familien werden als geoeffnete Kalibrierung gefuehrt. Bekannte
Fehler und Kontrollen sind separat ausgewertet. Keine Faelle wurden nach
Einsicht ergaenzt oder ersetzt. Ganze Anfangsszenenfamilien bleiben zusammen;
wiederverwendete Szenen und Parents sind keine unabhaengigen Wiederholungen.
Es gibt keine neuen unabhaengigen Trainingsinitialisierungen.

Alle Eingriffe betreffen nur die zweite Platzierung ausserhalb des Rueckzugs.
Gleiche Anfangszustaende, Gewichte, 0,8-Abschlussschwelle, Clock-Korrektur,
Sequencer und physikalische Erfolgskriterien. Erfolg bleibt ein vollstaendiger
Dreierturm ueber 50 aufeinanderfolgende strenge Frames bei gleichem
1000-Frame-Horizont. Nicht erreichte Phasen bleiben im Nenner.

Die 16 geoeffneten Kontrollen reproduzieren ihre archivierten Resultate.
Zustand und Historie wurden am ersten tatsaechlichen Eingriff gegen die
Kontrolle desselben Frames geprueft. Ohne Eingriff muss die gesamte
Trajektorie identisch sein. Innerhalb derselben Veto-Bedingung haben die
Freigaberegeln zusaetzlich identische Phase-6-Eingangszustaende.

## Spaeter Abschluss: Zustand gegen Timeout

Beide Varianten respektieren jeden vorhandenen BC-Abschluss und veraendern
die aktuelle BC-Bewegung nicht. Eine zusaetzliche Entscheidung erfolgt erst
nach mindestens 100 verstrichenen Phase-1-Aktionen, dem Cap der vorhandenen
Eingabeuhr. Die Bereitschaftsvariante verlangt zusaetzlich 20 aufeinanderfolgende
Frames mit EEF-Abstand < 6 mm zum gespeicherten Phasenanker plus 3 mm in Z.
Diese Geometrie wird aus den vorhandenen Policymerkmalen berechnet; es gibt
keinen zusaetzlichen Objektsensor. Die externe Hysterese fuegt einen Zaehler hinzu.

| Bekannte Griffstillstaende | Lokale Phase verlassen /6 | Vollstaendige Aufgaben /6 |
|---|---:|---:|
| Original-BC | 0 | 0 |
| Spaeter Timeout | 6 | 1 |
| Spaete Bereitschaft | 6 | 3 |

Beim Timeout erfolgt der Uebergang jeweils nach 100 Schritten, in allen sechs
Faellen ohne aktuell erfuellte Bereitschaft. Die zustandsabhaengige Regel
wartet **122 bis 166 Schritte**, jeweils bis 20 zusammenhaengende Bereitschaftsframes
vorliegen. Die unveraenderten BC-Abschlusswahrscheinlichkeiten liegen dann
zwischen etwa 0,0007 und 0,0104, weit unter 0,8.

In Szene 2026193009 gelingen danach alle drei Parent-Verlaeufe; der Timeout
gelingt dort nur bei Parent 1. Szene 2026193011 verlaesst bei beiden Eingriffen
die Griffphase und scheitert bei allen Parents spaeter. Lokaler Fortschritt
ist daher weiter vom vollstaendigen Erfolg zu trennen.

Die vier bekannten Erfolgskontrollen schliessen selbst rechtzeitig ab:
kein Fallback-Eingriff, unveraenderte Trajektorien, 4/4 Erfolge. Gegenueber der
frueheren pauschalen Regel wurden sowohl Platzierungsumfang als auch
Eingriffszeitpunkt und Bedingung eingegrenzt. Die vermiedenen Schaeden lassen
sich deshalb nicht allein einem einzelnen dieser Unterschiede zuschreiben.
Der jetzige Timeout/Bereitschaftsvergleich haelt Umfang und Mindestzeit gleich.

## Neue Kalibrierung: Erhaltung gezeigt, Rettungswirkung nicht geprueft

Auf den zwoelf neuen Anfangsszenen erreichen **alle acht Varianten dieselben
28/36 Gesamtaufgaben**, ohne gepaarte Gewinne oder Verluste. Je Parent sind
das 9/12, 9/12 und 10/12. Ein Vergleich dieser Quote mit der vorherigen
18-Szenen-Untersuchung waere kein Methodenvergleich bei gleichen Szenen.

Die acht Fehlschlaege enden bereits in der **ersten** Platzierung:
einmal Phase 1, sechsmal Phase 6, einmal Phase 4. Sie erreichen keinen der
hier untersuchten zweiten Griffe. Alle 28 erreichten zweiten Griffe und
Freigaben sind bereits in der Kontrolle erfolgreich.

Deshalb werden beide spaeten Griffregeln auf dem neuen Panel **kein einziges
Mal ausgeloest**. Dieses Panel belegt keinen frischen Rettungseffekt fuer die
Griffkorrektur. Die neue Freigaberegel wird dagegen in 28 Paaren angewendet,
das Veto blockiert in 22 davon mindestens einen Abschlussversuch; kein
Gesamterfolg geht dadurch verloren. Auch das ist bei kleiner, abhaengiger
Stichprobe keine allgemeine Unbedenklichkeitsgarantie oder Gleichwertigkeit.

Die Fallzahl bleibt wie geplant unveraendert. Es wurden nach dem Ausbleiben
neuer Zielphasenfehler keine guenstigen oder zusaetzlichen Szenen gesucht.

## Faktorieller Freigabevergleich

Bei identischer Ablagebedingung wurden drei Bewegungsregeln verglichen:
Original-BC, EEF an der Freigabe-Eingangsposition halten, und Objekt-XY-
Rueckfuehrung in den ersten 20 Freigabeaktionen. Alle oeffnen den Greifer;
beide neuen Regeln verwenden denselben begrenzten P-Gain, dieselbe
Hoehenreferenz und feste Rotation. Nach 20 Aktionen wird bei Objektfeedback
die erreichte EEF-XY-Position gehalten. Jedes Profil wurde ohne und mit dem
vorher definierten Ablageveto geprueft.

| Ablageveto | Bewegung | Bekannte Fehler: Erfolge /3 | Erfolgskontrollen /3 |
|---|---|---:|---:|
| aus | BC | 0 | 3 |
| aus | EEF halten | 0 | 3 |
| aus | Objektfeedback | 0 | 3 |
| an | BC | 0 | 3 |
| an | EEF halten | 0 | 3 |
| an | Objektfeedback | 0 | 3 |

Alle gepaarten Erfolgsdifferenzen und deren deskriptive faktorielle
Interaktionen sind hier null. Das ist kein statistischer Nachweis der
Gleichwertigkeit: Die kontinuierlichen physikalischen Verlaeufe unterscheiden
sich erheblich. Bei einem bekannten Fehler verhindert das Veto ausserdem den
Eintritt in Phase 6; dieser Fall bleibt voll im Nenner.

## Auffaelliger Freigabefall: Position und Fingerfreiheit getrennt

Parent 3, Szene 2026189042, zweite Platzierung. Der Freigabeeintritt ist
innerhalb jedes Veto-Arms ueber die drei Bewegungsregeln exakt gleich:
ohne Veto XY 25,27 mm / Hoehe 90,01 mm, mit Veto XY 6,78 mm / Hoehe 38,32 mm.

| Variante | XY am Episodenende [mm] | Fingerkontakt am Ende | Laengste streng gueltige Folge /50 |
|---|---:|---|---:|
| BC | 11,10 | nein | 0 |
| EEF halten | 74,82 | nein | 0 |
| Objektfeedback | 9,33 | nein | 0 |
| Veto + BC | 10,81 | nein | 0 |
| Veto + EEF halten | 10,89 | nein | 0 |
| Veto + Objektfeedback | 8,59 | **ja** | **2** |

EEF-Halten ohne vorherige Ablagekorrektur laesst den Wuerfel in diesem Fall
vom Turm fallen. Eine Halteregel ist in solchen Eingangszustaenden somit
keine neutrale oder garantiert bessere Bewegung. Objektfeedback veraendert
die XY-Lage deutlich, erreicht aber keinen vollstaendigen Erfolg.

Bei **Veto + Objektfeedback** sind am Ende Hoehenabstand 39,55 mm,
Wuerfelkontakt und gueltiger unterer Zweierturm vorhanden. Der Quellwuerfel
ist nicht als gegriffen erkannt, bewegt sich kaum und liegt innerhalb der
9-mm-Grenze. Dennoch besteht in **allen letzten 50 Frames Fingerkontakt**.
Kontaktfreiheit ist Teil des unveraenderten Gesamterfolgs. Eine geoeffnete
Greiferaktion und `held=false` sind nicht gleichbedeutend mit Kontaktfreiheit.

Diese Kontaktbeschreibung ist eine ergaenzende Analyse der gespeicherten
Traces, kein nachtraeglicher neuer Primaerendpunkt. Ein zusaetzlicher
Rueckzug oder eine andere Oeffnungsregel wurde nicht getestet. Ob eine
gezielte Handfreigabe den Fall wirklich rettet, ist eine konkrete weitere
Interventionsfrage; das Endsignal allein beweist diese Gegenmassnahme nicht.

## Informationsfrage: fehlendes direktes Merkmal ist noch kein Leistungsnachweis

Auf 1076 vorab gleichmaessig abgetasteten Kontrollframes der neuen Familien,
je Parent und zweiter Phase 5/6 getrennt, ergab die feste Naehepruefung:

- keine exakt gleichen zehn-dimensionalen Eingaben zwischen verschiedenen Familien;
- 153 aehnliche Framepaare unter den vorab festgelegten Einheiten/Toleranzen;
- kein Paar davon mit unterschiedlicher fester Ablagebereitschaft;
- folglich auch kein solches Paar mit mindestens 5 mm unterschiedlicher XY-Abweichung.

Die Toleranzen wurden nicht nachtraeglich gelockert. Diese Nullbefunde
beweisen weder vollstaendige Beobachtbarkeit noch die Nutzlosigkeit neuer
Merkmale. Insbesondere enthaelt das neue Panel keine scheiternden zweiten
Platzierungen. Die gepruefte Ablagebereitschaft ist zudem eine Vergleichsregel
und kein allgemeingueltiges Label fuer einen optimalen Abschluss.

Objektfeedback nutzt privilegierte Simulatorpositionen und eine andere
Feedbackreferenz. Sein Vergleich mit EEF-Halten ist keine reine Featureablation
eines ansonsten identischen trainierten Modells. Ein allgemeiner Nutzen
zusaetzlicher Objektmerkmale fuer Lernen oder Robustheit wurde nicht geprueft.
Die fruehere Codebeobachtung, dass solche Groessen nicht direkt im BC-Vektor
stehen, bleibt richtig; die weitergehende Leistungshypothese bleibt offen.

## Konsequenz fuer die weitere Methodik

1. **Gezielte Terminierung ist ein konkreter Kandidat:** Die vorhandenen
   Greifermerkmale plus Hysterese reichen hier zur Korrektur eines Teils der
   bekannten Stillstaende. Vor einer allgemeinen Behauptung braucht es eine
   vorab geplante Pruefung mit neuen kritischen Familien und Erfolgskontrollen;
   die hier gerettete einzelne Familie reicht dafuer nicht.
2. **Vollstaendige Freigabe definieren:** Objektlage, Erkennung eines Griffs,
   Fingerkontakt und Aufloesung des Handkontakts getrennt messen. Fuer den
   auffaelligen Fall ist eine kontrollierte Handfreigabe nach hergestellter
   Ablage jetzt eine praezise Hypothese. Sie darf nicht durch Lockerung der
   50-Frame-/Kontaktdefinition ersetzt werden.
3. **Kein Architekturwechsel allein aus fehlenden Eingabefeldern:** Ein
   spaeterer Lernvergleich muss Information, Labeldefinition und Optimierung
   bei sonst gleichen Bedingungen trennen. Mehr Parameter oder Updates sind
   aus diesen Daten keine begruendete naechste Intervention.
4. **Bestaetigung und Training getrennt:** Alle bisherigen Diagnosefamilien
   bleiben geoeffnet. Fuer einen nachfolgenden wissenschaftlichen Lernvergleich
   mehr als drei vorab begruendete unabhaengige Trainingsinitialisierungen,
   geeignete normale/kritische Panels und unverbrauchte Blindtestfamilien
   gemaess AGENTS.md planen. Kein solches Training wurde gestartet.

## Schwierigkeit und Grenzen

Die neuen Familien wurden nicht nach Erfolgen ausgewaehlt. Anfangs-EEF-/
Quellabstaende und alle drei XY-Abstaende der Wuerfelmitten sind in Metern
gespeichert. Es gibt keine als validiert ausgegebene Schwierigkeitsskala und
keine aus der Seednummer abgeleiteten Klassen. Die Panel-Eignung fuer einen
bestimmten Fehlermechanismus wird ueber tatsaechliche Exposition ausgewiesen.

Gezielt ausgewaehlte Fehleranker, verschiedene Parents derselben Szene und
zusammenhaengende Frames sind keine unabhaengigen Stichproben. Es werden keine
Wirksamkeitsintervalle fuer neu trainierte Modelle und keine Teststaerkegarantie
aus diesen Zahlen abgeleitet. Gleichbleibende Gesamtquoten schliessen lokale
Bewegungsschaeden nicht aus; der abgefallene Wuerfel ist ein konkretes Beispiel.

## Ablage und Reproduktion

Lauf: `praxis/results/curriculum/selective_completion_release_v1/run_001`.

- `plan.json`, `sources/`, `provenance.json`: eingefrorene Regeln, Auswahl und
  transitive lokale Hilfsmodule, einschliesslich dynamisch importierter Quellen.
- `groups.json`, `traces/*.npz`, `trace_schema.json`: alle Paarvergleiche,
  tatsaechlichen Policyeingaben, Aktions- und Simulationsverlaeufe.
- `analysis.json`, `REPORT.md`: Endpunkte, volle Nenner, Exposition,
  Parent-Ergebnisse, gepaarte Kontraste und faktorielle Effekte.
- `findings.png/pdf`, `figure_provenance.json`: Gesamtvergleich und Freigabekurven.
- `mechanisms.png/pdf`, `critical_terminal_context.json`, `supplement_provenance.json`:
  ergaenzende Darstellung von Griffrettungen und Kontaktfehler, aus vorhandenen Traces.
- `integrity.json`, `supervisor_status.json`: Archivkontrollen reproduziert,
  gleiche Historien bis zum Eingriff, unveraenderte Quellen/Parameter,
  Exitcode 0 und freigegebener Wachhaltezustand.

Die deterministischen Auswertungen `analyze.py`, `render_findings.py` und
`supplement.py` benoetigen nur den Laufordner, keinen Simulator oder Optimizer.
Historische Dateien und Versuchsergebnisse bleiben erhalten.
