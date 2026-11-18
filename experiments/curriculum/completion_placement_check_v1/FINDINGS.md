# Abschlussentscheidungen und Ablage: Ergebnis vom 18.11.2026

**COMPLETE.** 354 Episoden in 60 gepaarten Fallgruppen, 21,9 Minuten,
**null Optimizerupdates**. Vorher acht gezielte Tests und ein getrennter
technischer Smoke mit 23 Episoden. Alle Integritaetspruefungen bestanden.
Der abgeschlossene Nachtlauf und seine Checkpoints sind unveraendert.

Die Diagnose prueft Ursachen und Nebenwirkungen mit eingefrorenen Modellen.
Sie liefert keine freigegebene neue Policy und keinen neuen Trainingslauf.

## Was genau verglichen wurde

- 18 vorher nicht zugewiesene Anfangsszenen, je mit den drei bestehenden
  sammlungsfremden Targeted-Kompositionen: **54 Modell-/Szenenpaare** mit
  sechs Armen, also 324 Episoden. Die Szenen sind jetzt geoeffnete Kalibrierung.
- Sechs bereits bekannte erfolglose Freigabefaelle mit fuenf Armen: 30 Episoden,
  separat ausgewertet. Diese sechs Paare stammen aus vier Anfangsszenen.
- Keine neuen unabhaengigen Trainingsinitialisierungen. Die vorhandenen drei
  Parentlinien und dieselben Szenen ueber Parents sind abhaengige Wiederholungen.
- Vollstaendiger Erfolg weiterhin: Dreierturm ueber 50 aufeinanderfolgende
  strenge Geometrie-/Kontakt-/Geschwindigkeitsframes. Gleicher Horizont,
  Sequencer, Retreat-Guard und dieselben eingefrorenen Gewichte.

Auswahl, Regeln, sechs Arme, Umfang und Zeitobergrenze wurden vor Ausfuehrung
festgelegt. Nicht erreichte Kontexte und alle erfolglosen Episoden bleiben erhalten.

## Gesamterfolg auf den neuen Kalibrierungsfamilien

Gewinn/Verlust meint den gepaarten Wechsel des vollstaendigen Aufgabenerfolgs
gegenueber der eigenen unveraenderten Kontrolle derselben Szene und Parentlinie.

| Eingriff | Erfolge / 54 | Gewinne | Verluste | Erfolge je Parent 1 / 2 / 3, jeweils /18 |
|---|---:|---:|---:|---|
| Unveraenderte Kontrolle | 36 | 0 | 0 | 12 / 12 / 12 |
| Expertenabschluss beim Absenken zum Griff, Phase 1 | 37 | 5 | 4 | 14 / 11 / 12 |
| Expertenbewegung bei der Ablage, Phase 5 | 33 | 1 | 4 | 12 / 10 / 11 |
| Expertenabschluss bei der Ablage, Phase 5 | 21 | 0 | 15 | 7 / 7 / 7 |
| Bewegung und Abschluss bei der Ablage | 33 | 1 | 4 | 12 / 10 / 11 |
| Zusaetzliches Ablageveto | 35 | 0 | 1 | 11 / 12 / 12 |

**Keine der geprueften Regeln zeigt hier einen belastbaren allgemeinen Vorteil.**
Der Nettogewinn von einer Aufgabe beim Griffabschluss verdeckt vier verlorene
Erfolgskontrollen und unterschiedliche Effekte zwischen den Parents. Der
pauschale Ablageabschluss verliert dagegen bei jedem Parent fuenf Aufgaben.
Weder die Expertenregel noch ein strengeres Veto ist somit automatisch eine
Verbesserung der bestehenden Policy.

## Abschlussfehler beim zweiten Greifen sind reproduzierbar

In der unveraenderten Kontrolle bleiben **sechs Modell-/Szenenpaare** beim
zweiten Absenken zum Griff, Phase 1, stehen, obwohl die vorhandene Expertenregel
in mindestens 20 Frames Bereitschaft meldet. Das sind genau **zwei physische
Anfangsszenen**, 2026193009 und 2026193011, jeweils bei allen drei Parents.

Mit dem Griffabschluss-Eingriff verlassen alle sechs Faelle diese Phase:

- Szene 2026193009 gelingt danach bei allen drei Parents vollstaendig.
- Szene 2026193011 erreicht bei allen drei Parents die Freigabe, scheitert
  aber weiterhin an der Gesamtaufgabe.

Die fuenf Gesamtgewinne dieses Arms betreffen drei Familien; die vier Verluste
betreffen zwei andere Familien. Drei der Gewinne stammen aus Szene 2026193009.
Weitere Gewinne entstehen aus veraenderten Verlaeufen und duerfen nicht alle
als Reparatur eines beobachteten Stillstands bezeichnet werden.

Der Arm ersetzt den Abschluss in beiden Platzierungen; er ist keine isolierte
Intervention nur beim zweiten Greifen. Vergleiche spaeterer Phasenkontexte
sind daher bedingt auf die jeweils erreichte Vorgeschichte. Der gepaarte
Gesamteffekt ist eindeutig, seine Aufteilung auf einzelne spaetere Ereignisse
bleibt eine weitergehende Ursachenfrage.

## Nicht erfuellte Ablagebereitschaft ist kein ausreichender Fehlernachweis

Das vorab definierte Veto verlangt XY <= 9 mm, Hoehendifferenz 40 +/- 8 mm,
Wuerfelkontakt, geringe Quellwuerfelgeschwindigkeit und gueltigen unteren Turm,
drei Frames lang, bei mindestens fuenf Phase-5-Aktionen. Kontakt zum noch
greifenden Greifer wird dabei zugelassen. Es prueft diese Bedingungen vor
der aktuellen Aktion; der Eingang in die Freigabe wird zusaetzlich danach gemessen.

Die unveraenderte Kontrolle zeigt:

- Bei der ersten Ablage enden **22 von 32** Austritten ohne dieses Kriterium
  spaeter trotzdem mit vollstaendigem Aufgabenerfolg.
- Bei der zweiten Ablage sind es **17 von 25** Austritten.

Dies sind abhaengige Phasenereignisse, keine 57 unabhaengigen Episoden. Ein
Wuerfel darf nach dem Oeffnen noch absinken und sich beruhigen. Aus fehlendem
Kontakt oder nicht abgeschlossener Beruhigung vor dem Oeffnen folgt daher
nicht automatisch ein verfruehter oder falscher Uebergang.

Das Veto verhindert in seinen neuen Kalibrierungsverlaeufen alle Austritte ohne
die definierte Bereitschaft, rettet aber keine zusaetzliche Gesamtaufgabe und
verliert eine Erfolgskontrolle. Bei der zweiten Ablage bleiben zudem vier
erreichte Faelle in Phase 5. Die Einhaltung eines lokalen Zusatzkriteriums
ersetzt den Nachweis einer besseren Gesamtaufgabe nicht.

## Bekannte Freigabefaelle: Ablage und Freigabe wirken zusammen

Die reine Phase-5-Bewegungsuebernahme rettet **einen der sechs** bekannten
Fehlerpaare: Parent 1, Szene 2026189056, zweite Platzierung. Abschlussuebernahme,
Kombination und Veto retten dort jeweils keine Gesamtaufgabe. Der Nutzen der
Bewegung in diesem Fall haengt somit vom weiterverwendeten BC-Abschluss ab.
Diese gezielt ausgewaehlten sechs Fehler liefern keine allgemeine Erfolgsquote.

Im zuvor auffaelligen Fall **Parent 3 / Szene 2026189042**:

| Variante | Eintritt in Freigabe: XY [mm] | Hoehenabstand [mm] | Bereitschaft bei Eintritt | Gesamterfolg |
|---|---:|---:|---|---|
| Kontrolle | 25,27 | 90,01 | nein | nein |
| Expertenabschluss | 7,23 | 38,56 | ja | nein |
| Bewegung und Abschluss | 7,52 | 38,73 | ja | nein |
| Veto | 6,78 | 38,32 | ja | nein |

Das Veto verzoegert den Uebergang um 16 Frames und stellt im Eingangszustand
die definierte Geometrie, Kontakte und Geschwindigkeitsbedingung her.
Nach der Freigabe steigt der XY-Versatz dennoch wieder; am Episodenende liegt
er bei **10,81 mm**, oberhalb der unveraenderten 9-mm-Erfolgsgrenze. Es entsteht
kein einziger streng gueltiger Gesamtframe. Die Hoehe liegt schliesslich bei
39,40 mm, der Fingerkontakt ist dann aufgehoben.

Damit ist belegt: Der schlechte Eingangszustand laesst sich in diesem Fall
verbessern, ohne die Aufgabe dadurch zu retten. Die zuvor vermutete
Ablagebedingung allein erklaert diesen Freigabefehler nicht. Welche Anteile
Freigabebewegung, Kontaktkraefte und Eingangszustand jeweils beitragen, ist
mit diesem Eingriff noch nicht vollstaendig getrennt. Die alten Phase-6-
Uebernahmen begannen in anderen Eingangszustaenden und beantworten diese
Wechselwirkungsfrage ebenfalls nicht.

## Beobachtungsgrenze des Modells

Die Codepruefung bestaetigt: Der Abschlusskopf sieht zehn Merkmale aus
Greiferposition relativ zum Phasenanker, Greiferquaternion, zwei
Greifergelenkpositionen und Phasenuhr. Aktuelle Quellwuerfelpose,
Wuerfelkontakt und Wuerfelgeschwindigkeiten sind nicht direkt enthalten.
Der Kopf ist ein Feedforward-Netz ohne rekurrenten Zustand.

Das geometrische Veto benutzt zusaetzliche Simulatorinformationen. Es hat
somit einen anderen Beobachtungsvertrag. Sein moeglicher Nutzen waere nicht
allein eine bessere Klassifikation bei denselben Informationen. Auch die
Expertenregel ist ein definierter positionsbasierter Ablauf und kein
unfehlbarer Wahrheitsstandard fuer spaeteren Stapelerfolg.

Details und Codepfad: [OBSERVATION_CONTRACT.md](OBSERVATION_CONTRACT.md).

## Folgerung fuer die Methodik

1. **Gezielte Abschlusskorrektur als eigene Frage:** Kann eine selektive,
   zustandsabhaengige Korrektur die nachgewiesenen Stillstaende beheben und
   erfolgreiche Uebergaenge erhalten? Die gepruefte pauschale Uebernahme
   beantwortet das noch nicht positiv. Keine allgemein niedrigere Schwelle
   aus den ausgewaehlten Rettungen ableiten.
2. **Uebergang an Folgezustaenden bewerten:** Ablagebereitschaft und Erfolg
   nach der Freigabe getrennt messen; die gemeinsame Wirkung von
   Ablageeingang und Freigabebewegung waere eine passende weitere Ursachenpruefung.
3. **Information, Label und Optimierung getrennt kontrollieren:** Vor einem
   neuen Training explizit entscheiden, welche messbaren Objektinformationen
   benoetigt werden und was ein korrektes Abschlusslabel bedeuten soll.
   Mehr Updates auf dem gleichen Vertrag sind keine aus dieser Diagnose
   abgeleitete Loesung.
4. **Naechste Bestaetigung separat planen:** Mehr als drei begruendet geplante
   unabhaengige Trainingsinitialisierungen gemaess AGENTS.md, passende
   Kontrollen, ganze Familien getrennt, neue Blindtestfamilien. Diese neuen
   Kalibrierungsszenen bleiben geoeffnet. Kein nachfolgendes Training gestartet.

## Schwierigkeit, Messmerkmale und Aussagegrenzen

Die 18 Familien wurden nicht nach Erfolgen oder geometrischen Merkmalen
ausgewaehlt. Ihre Nummer besitzt keine Schwierigkeitsskala. Anfangsmerkmale
und Hashes sind gespeichert; eine validierte Einteilung leicht/mittel/schwer
ist damit noch nicht hergestellt. Aus der kleineren Erfolgsquote als im
Nachtpanel wird keine pauschal hoehere Schwierigkeit abgeleitet.

**Benennungskorrektur fuer die Rohmerkmale:** `transport_2_xy_m` speichert
den Anfangsabstand von Wuerfel 2 zu Wuerfel 1 an dessen urspruenglicher
Position. Nach der ersten Platzierung befindet sich Wuerfel 1 woanders.
Das Feld ist daher ein Anfangs-Abstandsmerkmal und keine exakte geplante
zweite Transportstrecke. Diese Klarstellung betrifft die Interpretation;
Interventionen, Auswahl und Ausgaenge haengen nicht davon ab. Die eingefrorenen
Dateien bleiben erhalten.

Die kleine geoeffnete Kalibrierung und drei geerbten Parents erlauben keine
generelle Wirksamkeitsgarantie oder Aussage zur Streuung neuen Trainings.
Es wurden keine Testfamilien nachtraeglich zu neuen Blindtests erklaert und
keine erfolgreichen Seeds ausgesucht oder ergaenzt.

## Artefakte und Nachvollziehbarkeit

Lauf: `praxis/results/curriculum/completion_placement_check_v1/run_001`.

- `plan.json`, `provenance.json`, `sources/`: vorab eingefrorene Eingriffe und Quellen.
- `seed_audit.json`: Konfliktpruefung vorhandener Experiment-/Curriculumplaene;
  unprotokollierte historische Starts koennen dadurch nicht ausgeschlossen werden.
- `groups.json`, `traces/*.npz`, `trace_schema.json`: alle Einzelergebnisse und Verlaeufe.
- `REPORT.md`, `analysis.json`: vorab definierte deskriptive Endpunkte.
- `READINESS_AUDIT.md`, `readiness_audit.json`, `placement_exits.csv`:
  ergaenzende Kreuztabellen mit spaeterem Gesamterfolg; Bereit-/Nicht-bereit-
  Bedingungen wurden nicht nachtraeglich veraendert.
- `findings.png`, `findings.pdf`, `figure_provenance.json`: grafische Auswertung;
  der bekannte Geometriefall zeigt die ersten 200 Frames ab Ablageeintritt.
- `integrity.json`, `supervisor_status.json`: Quell-/Parameterhashes bestaetigt,
  alle sechs Archivkontrollen reproduziert, identische Historie bis zum Eingriff,
  gepaarte Initialzustaende, keine neuen Zustaende identisch mit den Nachtstarts,
  Worker Exitcode 0, Wachhaltezustand freigegeben.

Die Rohbelege bleiben lokal; keine Checkpoints oder Ergebnisse wurden ersetzt.
