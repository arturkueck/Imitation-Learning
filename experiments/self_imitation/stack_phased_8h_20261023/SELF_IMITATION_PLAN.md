# Eigene erfolgreiche Rollouts als neue Trainingsdaten

Stand23.10.2026. Entscheidungsvorlage nach Diskussion mit zwei unabhaengigen Agenten. Dies ist ein neuer Versuchsplan, kein gestartetes Training und keine behauptete Verbesserung.

## Entscheidung

**Ein begrenzter kontrollierter Versuch lohnt sich.** Die Daten heissen erfolgsgefilterte Policy-Demonstrationen bzw. Self-Imitation-Daten, nicht ungeprueft neue Expertenlabels. Eine erfolgreiche Episode kann unnoetige Bewegungen, knappe Kontakte und Fehler enthalten. Erfolg bewertet die gesamte Episode; er garantiert nicht, dass jede einzelne Aktion optimal ist.

Wissenschaftliche Trennung: Bisher wurde ausschliesslich auf Zwei-Wuerfel-Demos trainiert. Danach erfolgreiche eigene Drei-Wuerfel-Rollouts zum Training hinzuzufuegen veraendert die Datenbedingung. Die korrekte neue Hypothese lautet: **Aus Zwei-Wuerfel-Expertendemos bootstrappen und durch erfolgreiche eigene Drei-Wuerfel-Erfahrung verbessern.** Eine spaetere90%-Rate waere kein reiner Zero-shot-Transfer aus ausschliesslich Zwei-Wuerfel-Trainingsdaten. Der bisherige Versuch samt Gewichten, Tests und Berichten bleibt eingefroren.

## Bisheriger Verlauf und belastbare Ergebnisse

1. Originaldaten:200 erfolgreiche synthetische StackTwo-Demos eines programmierten Experten,180/20 Trajektoriensplit,27.322/2.974 Trainings-/Validierungsframes bei20Hz; zwei4cm-Wuerfel, Panda. Bilder wurden nicht zum Training verwendet. Vollstaendiger Rueckzug und erhoehte Zielstapel fehlen.
2. Direkte absolute/relative Chunkregression: relative Darstellung verbessert Zweierstapel, aber0/100 Dreiertuerme bei den zwei zum Haupttest zugelassenen Modellen. Hoehenablation auf exakt gepaarten Quell-/Roboterzustaenden: kein stabiler Erfolg bei+2bis+4cm auf den untersuchten75 Versuchen; keine universelle Hoehengrenze bewiesen.
3. Neue phasenstrukturierte BC mit gelernten Aktionen/Abschluessen und vorgegebener Phasen-/Paarreihenfolge: Vierstundenblock, anschliessende Agentenanalyse, zweiter Block mit kleinerer Lernrate und expliziter Wiederverwendung des offenen Anflugkopfs als Rueckzug. Keine neuen Trainingsdemos, keine RL-Updates.
4. Endtest auf100 neuen Starts pro Modell:62/100,48/100,50/100 stabile Dreiertuerme. Erste Paarplatzierung98/100,98/100,96/100. Der Engpass liegt vor allem in der Erhaltung des unteren Stapels beim naechsten Anflug/Greifen, daneben Kontakt-/Platzierungs-/Stabilitaetsfehler.
5. Ein nach Dreier-Testleistung ausgewaehltes Modell (Seed1,327.000 kumulative Updates, Batch64, ca.766 phasenbalancierte Datenpass-Aequivalente) erzielt98/100 Zweierstapel auf weiteren neuen Starts. Bei seinen62 erfolgreichen Dreiertuermen: durchschnittlicher horizontaler C–B-Mittenversatz2,87mm,95%-Quantil5,56mm; diese Genauigkeit gilt ausschliesslich fuer Erfolge.

Die Resultate nutzen privilegierte Simulatorzustaende, feste Teilphasen-/Paarreihenfolge und physische Abschlussgates. Es ist keine autonom gelernte Planung. Details: REPORT_1.md, REPORT_2.md, third_cube_accuracy.json, two_cube_test_seed1/REPORT.md und vorherige Berichte in ../stack_composition_20261023/.

## Zwei Agenten: Argumente und Bewertung

**Agent1 – dafuer:** Die erfolgreichen eigenen Episoden enthalten genau die fehlenden Zustaende: Uebergang aus dem Zweierstapel, erhoehtes Ziel und komplette dritte Platzierung. Ein gemischter Datensatz kann diese unterrepräsentierten Zustandsbereiche fuer einen Student oder einen weitertrainierten Teacher erhalten. Unterschiedliche Lehrer liefern verschiedene erfolgreiche Verlaeufe. Die lokale Erfolgshaeufigkeit macht eine Sammlung praktisch moeglich.

**Agent2 – Gegenargumente:** Erfolgsselektion bevorzugt leichte Starts, konserviert auch riskante Aktionen und liefert keine Korrektur auf den eigentlichen Fehlzustaenden. Wiederholte Szenen und verwandte Checkpoints sind keine unabhaengigen Demos. Phasenabschluss- und Rueckzugslabels koennen falsch rekonstruiert werden. Bereits ausgewertete Endteststarts duerfen nicht zugleich als neue Trainingsbasis und weiterhin als unabhaengiger Endtest behandelt werden. Mehr Rechenzeit und die Menge neuer Daten muessen kontrolliert werden.

**Abwaegung:** Zusaetzliche Rollouts koennen relevante Zustaende liefern, aber reine Selbstkopie besitzt keinen automatischen Verbesserungsmechanismus. Erfolg muss deshalb gegen eine Fortsetzung auf Originaldaten mit demselben Budget verglichen werden; Originaldaten bleiben als Anker im Training.

Ein weiterer Einwand von Agent2 ist direkt am Modell nachvollziehbar: Seine10 Eingaben enthalten die EEF-Lage relativ zu einem einzigen Anker, Orientierung, Fingerzustand und Phasenzeit. Die Lage des restlichen Turms und der Hindernisfreiraum fehlen. Eine neue erfolgreiche Bahn kann nachgeahmt werden, aber eine geometrieabhaengige Ausweichentscheidung ist bei ansonsten identischen Inputs nicht automatisch unterscheidbar. Eine Erweiterung um Turm-/Freiraumfeatures waere eine begruendete eigene Methodenablation, nicht stillschweigend Bestandteil dieses Datenversuchs.

Die Agenten gewichten zwei Entscheidungen unterschiedlich: Agent1 bevorzugt mehrere Teacher und eine Mischungsverhaeltnis-Ablation; Agent2 einen zusaetzlichen Zwei-Wuerfel-Selbstdaten-Kontrollarm und strengere Bahnqualitaetsfilter. Fuer den ersten belastbaren Hauptvergleich priorisieren wir nachfolgend die Zwei-/Drei-Wuerfel-Datenkontrolle. Ein harter Filter auf durchgehend erhaltene untere Geometrie kann nützliche Recoveryverlaeufe ausschliessen; deshalb im Hauptpilot zunaechst als Qualitaetskennzahl dokumentieren, eine strengere Filtervariante vorab separat definieren. Beide Entscheidungen bleiben im Bericht sichtbar.

Ein besonders wichtiger mathematischer Punkt: Fuer einen deterministischen Actor und einen exakt identisch initialisierten Student gilt auf vollstaendigen Inputs x mit eigenem Label a=f_theta0(x) zunaechst L=||f_theta0(x)-a||²=0, also kein Actor-Lerngradient. Das gilt unabhaengig davon, ob x im alten Datensatz vorkam. Originaldaten-Updates koennen anschliessend einen Replay-Erhaltungsgradienten erzeugen. Andere Teacher, andere Studentinitialisierung oder explizite Regularisierung koennen den Lernimpuls ebenfalls aendern. Das ist keine Garantie besserer Closed-Loop-Leistung. Pseudolabels fuer Phasenabschluesse koennen trotz identischer Actorlabels andere Gradienten erzeugen; diese sind nicht mit verifizierten Expertenkorrekturen gleichzusetzen.

## Welche bisherigen Erfolge sind vorhanden?

Maschinenlesbar: self_imitation_inventory.json. Ausgewaehlte Block1-Dev-Checkpoints enthalten16 erfolgreiche Episoden, aber nur9 unterschiedliche Startseeds. Block2 enthaelt21 erfolgreiche Episoden, ebenfalls nur9 unterschiedliche Startseeds. Der abschliessende Drei-Wuerfel-Test enthaelt160 erfolgreiche Modell-Episoden aus71 unterschiedlichen Startseeds. Diese Testepisoden werden in diesem Plan archiviert und nicht als Trainingsquelle benutzt.

Die bisherigen Entwicklungsrollouts koennen zur Collector-/Replay-Pruefung dienen. Neun Szenen sind zu wenig fuer einen belastbaren neuen Datensatz. Wenn alte Testepisoden spaeter bewusst als Training verwendet werden sollen, muessen sie zu Entwicklungs-/Trainingsdaten umdeklariert und neue Endtests reserviert werden; ihre alten Scores bleiben historische Ergebnisse. Hauptvorschlag: frische Sammelstarts mit korrektem Logging.

## Technische Datenluecke: NPZ nicht direkt importieren

Im bisherigen evaluate() wird zuerst env.step(action) ausgefuehrt und danach die Beobachtung protokolliert. Die trace-Zeile kombiniert damit Aktionen a_t mit Positionen aus s_(t+1). Phasen und Abschlusswahrscheinlichkeiten stammen dagegen aus der Entscheidung vor dem Schritt. Greiferquaternion, Fingerpositionen, exakter gecachter Anker und lokaler Phasenschritt fehlen als vollstaendige Pre-action-Inputs. Ein direktes Training aus diesen Zeilen wuerde zeitlich falsche Paare erzeugen.

Ein verifiziertes deterministisches Replay ab initial mit den gespeicherten Aktionen koennte die fehlenden Werte rekonstruieren. Dazu initiale Szene, Controllerzustand und Policy-Zustand herstellen, vor jedem Schritt vollstaendige Inputs gewinnen und die folgenden Zustaende/alten Aktionen/Phasen sowie Terminalerfolg nachrechnen. Akzeptanz nur bei passender Rekonstruktion; sonst Fall verwerfen und Grund dokumentieren. Nicht einfach Ziel-/Quellpositionen eine Zeile verschieben und fehlende Variablen erraten.

Sicherer Hauptpfad: neuer Collector speichert **vor jedem Schritt** die reale volle Beobachtung, exakt benutzten10D-Input, Aktion, aktive Phase, Phasenschritte, gecachten Anker, Paarindex, Rueckzugsflag und Teachercheckpoint-Hash. **Nach dem Schritt** naechste Beobachtung, Geometrie/Kontakte, Geschwindigkeiten, Erfolg und die tatsaechlich eingetretenen Controllerereignisse. Initialzustand inklusive Modell-/Controllerkonfiguration und RNG sichern. Ursprung und Zeitrichtung jeder Spalte festlegen.

Abschlusslabels0–5: tatsaechlicher gelernter Phasenwechsel als Pseudolabel mit Teacherherkunft, keine unabhängige Expertenwahrheit. Phase6 hat im Original keine gelernten Abschlusslabels; Paarwechsel erfolgt per physischem Gate. Rueckzug nutzt Kopf0 mit anderem Anker und muss als gesonderter Controllerkontext gespeichert werden. Modell-/Orchestrierungswechsel sind keine normalen naechsten Phasen. Erfolg am Episodenende darf nicht pauschal als Abschlusslabel fuer jeden Frame gesetzt werden.

## Konkreter, begrenzter Pilot

Noch nicht auf Kollisionen mit anderen Experimenten gepruefte vorgeschlagene Seedbereiche; vor Start zentral registrieren und einfrieren:

| Zweck | Vorschlag | Regel |
|---|---|---|
| Sammlung Training |90000–90299|300 Versuche; Teacherzuweisung vorab fest, ganzer Start ist eine Gruppe|
| Sammlung Validierung |90300–90399|100 weitere Versuche; keine Trainingsfenster daraus|
| Closed-Loop-Entwicklung |92000–92049|50 Starts je Modell/Arm, keine Optimierungslabels|
| Endtest |95000–95099|einmalig100 Starts je Trainingsseed nach Modellauswahl|
| Zweier-Regressionskontrolle |96000–96049|50 neue Starts je Modell; Ergebnis getrennt|

Drei eingefrorene aktuelle Teacher mit protokollierten Hashes, Zuweisung nach Start-ID modulo3, jeweils ein Versuch pro Start; keine nachtraegliche Auswahl des erfolgreichsten Teachers fuer denselben Start. Fixes Budget400 Sammelversuche, keine Sammlung bis eine gewuenschte Erfolgsquote entsteht. Auf Basis bisheriger Raten sind erfolgreiche Episoden wahrscheinlich; genaue neue Ausbeute bleibt offen. Akzeptierte und verworfene Versuche sowie Herkunft vollstaendig protokollieren. Split auf Ebene der Start-/Szenenfamilie vor Erfolgsfilterung festlegen, nie nach Frames oder nur unterschiedlichen RNG-Nummern bei identischer Szene.

Fuer den unten priorisierten Zwei-Wuerfel-Kontrollarm kommen getrennt400 Zwei-Wuerfel-Versuche mit eigener vorab registrierter Seedliste hinzu; somit maximal800 Sammelversuche fuer den vollen Dreiarmvergleich. Teacherzuweisung und Splitregeln in beiden Aufgaben gleich halten. Kleinere Vorstudie A gegen C ist moeglich, identifiziert aber keinen spezifischen Vorteil der Dreierdaten gegen allgemeine zusaetzliche Selbstdaten. Unterschiedliche Ausbeute der Erfolgsfilter getrennt ausweisen; innerhalb des Trainings ist das Selbstdatengewicht in beiden Armen gleich.

Akzeptanz: voller A/B/C-Turm aus freier Tischszene, 50 kontinuierlich gueltige Frames mit demselben Geometrie-/Kontakt-/Greiferkontakt-/Geschwindigkeitskriterium, endliche Daten, vollstaendige Metadaten. Lagefehler, Laufzeit, minimale untere Stabilitaetsmarge und Kontakte zusaetzlich erfassen. Fuer den Hauptpilot keinen nachtraeglich passend gemachten Schoenheitsfilter; optionale strengere Qualitaetsfilter waeren ein eigener Arm. Wenn die Sammlung kaum neue zulaessige Starts oder keine brauchbare Validierung liefert, Ergebnis als Daten-Gate-Fehlschlag berichten und kein uninterpretierbares Training starten.

Zunaechst Instrumentierung auf zwei alten Entwicklungsfaellen pruefen. Dann Sammlung und Integritaetsaudit. Erst bei korrekten Pre-action-Inputs, disjunkten Szenengruppen und vollstaendigen Labels trainieren.

## Trainingsarme und notwendige Kontrollen

Gleiche Architektur, Controller einschliesslich Rueckzug, trainierbare Koepfe und initiale Parameter je Trainingsseed; drei neue unabhaengig festgelegte Trainingsseeds. Pro Arm30.000 Updates, Batch64, konstante kleine Lernrate3e-5, gleicher Optimizerstart und nachvollziehbare getrennte RNGs. Das ist ein vorgeschlagenes Pilotbudget, keine auf diese Daten bereits optimierte Einstellung. Messpunkte0/3000/10000/30000. Wenn Eltern verschiedener Teacher benutzt werden, diese Unterschiede je Seed eindeutig protokollieren und innerhalb jedes Arms exakt paaren.

| Arm | Datenverteilung pro Batch | Fragestellung |
|---|---|---|
| A |100% Original-Zweierdaten|Bringt nur mehr Offline-Training denselben Effekt?|
| B |75% Original /25% erfolgreiche eigene ZWEIER-Daten|Kontrolle fuer zusaetzliche Policy-Daten ohne Dreier-Aufgabenabdeckung|
| C |75% Original /25% erfolgreiche eigene DREIER-Daten|Neue Uebergangs-/Hoehenzustaende bei gleichem Quellengewicht|

Eine50/50-Mischung ist eine moegliche spaetere Dosisablation, nicht gleichzeitig weiterer Freiheitsgrad im ersten Hauptvergleich. Teacherpool und Elterncheckpoint-Zuordnung vor Sammlung fixieren. Die drei Parents sind die drei bisherigen unabhaengig trainierten Modelle, keine drei identischen Gewichte mit nur anders benannten Seeds. Innerhalb jedes Replikats starten A/B/C exakt gleich. Falls stattdessen ein identischer Student mit neuen Samplerseeds verwendet wird, darf dies nicht als unabhaengige Modellinitialisierung ausgegeben werden.

Der eingefrorene Teacher wird auf denselben Entwicklungsstarts bewertet. Zusaetzlich Offline-Actor-MSE des initialisierten Students gegen die Selbstdaten **vor Update1** ausweisen, getrennt nach identischem Teacher und anderen Teachern; so wird der tatsaechliche neue Lernimpuls sichtbar. Ein Gewinn bei anderer Initialisierung bzw. anderen Teacherlabels darf nicht allein der Erfolgsfilterung zugeschrieben werden. Ein spaeterer engerer Kontrollversuch kann alle ungefilterten Selbstdaten gegen erfolgsgefilterte Daten vergleichen; der erste Pilot identifiziert noch keinen isolierten Filtereffekt.

Innerhalb der neuen Daten zuerst Episode gleichwahrscheinlich, dann verfuegbare Teilphase und Frame ziehen; Originaldaten mit bisheriger Phasenbalancierung. Keine stille Uebergewichtung langer Warte-/Release-Tails oder haeufig erfolgreicher identischer Starts. Abschlussloss nur fuer definiert gelabelte Uebergaenge; physische Controllergates gesondert. Datenquellenanteile, Frame-/Episodenzahl und tatsaechliche Updates dokumentieren. Das Hinzufuegen neuer Episoden darf durch eine veraenderte Epochenlaenge keinen verdeckten Updatevorteil schaffen.

Keine synthetischen Aktionskorrekturen oder neue RL-Updates in diesen Armen. Fehlertrajektorien als Diagnosearchiv erhalten, nicht blind als gute BC-Ziele verwenden. Recovery-Labels durch einen wirklich kompetenten Experten waeren ein eigener Versuch mit anderem Informationsbudget.

## Benchmark und Abbruchkriterien

Primaer: stabiler vollstaendiger Dreierturm auf allen Starts, je Trainingsseed separat. Sekundaer: erster Stapel, untere Geometrieerhaltung ab erster Platzierung, Rueckzug/zweiter Anflug, Greifen/Lift/Zielkontakt, Gesamtdauer, C–B-Versatz. Genauigkeit nicht allein auf Erfolge reduzieren; daneben Erfolgsquote und klar definierte Fehlerstatistik berichten. Zweierleistung gegen Ausgangsmodell pruefen, um Vergessen sichtbar zu machen.

Modellwahl nur auf Closed-Loop-Entwicklung, nicht auf Offline-Loss allein. Zum Einmal-Endtest nur eingefrorene ausgewaehlte Modelle. Das Punktziel bleibt mindestens90/100 Dreiertuerme auf JEDEM der drei Trainingsseeds; Konfidenzintervalle und Seedschwankung dazu. Ein positiver Pilot braucht konsistente Verbesserung gegen budgetgleiches A und den unveraenderten Teacher, nicht nur groessere Trainingsdatenzahl. Kein Fortschritt, deutliche Zweierregression oder Konzentration auf wenige leichte Starts rechtfertigt keine blinde weitere Aggregationsrunde. Simulatorversuche, Erfolgsfilter, Trainingsupdates und gesamte Laufzeit mitzaehlen.

## Literaturabgrenzung

[Oh et al., Self-Imitation Learning, ICML2018](https://proceedings.mlr.press/v80/oh18b.html) nutzt gute eigene Erfahrungen in einem Off-policy-Actor-Critic-Verfahren. Unser vorgeschlagenes erfolgsgefiltertes BC ist keine Reproduktion dieses RL-Algorithmus; dessen Ergebnisse garantieren hier keine Verbesserung.

[Ross et al., DAgger, AISTATS2011](https://proceedings.mlr.press/v15/ross11a.html) erhebt Expertenlabels auf vom Learner besuchten Zustaenden. Eigene erfolgreiche Aktionen ohne unabhängige Expertenkorrektur sind kein DAgger. Der lokale zustandsbehaftete Experte darf nicht beliebig in einer fehlgeschlagenen Episode neu initialisiert und als korrektes Recovery-Orakel bezeichnet werden.

**Status:** Zwei-Agenten-Pruefung und Dokumentation; keine neue Rolloutsammlung, kein neuer Trainingslauf in diesem Schritt. Naechste konkrete Arbeit ist ein korrekt instrumentierter Collector samt kleinem Replay-/Datenaudit, danach der vorab festgelegte Pilot.
