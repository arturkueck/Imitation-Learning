# Neuer Trainingsentwurf: räumliche Szenenwahrnehmung mit 0–5 Objekten

Stand: 01.11.2026. **Entwurf, kein gestarteter Trainingslauf.** Nutzerauftrag:
altes Training abbrechen und einen besseren Versuch entwerfen. Das spätere Ziel
ist ein visuell vorgegebenes kleines Lego-Haus. Dieser Versuch schafft dafür
einen Wahrnehmungsbaustein, keine Greif-/Montagepolicy.

## 1. Abbruch des alten Versuchs

Der Nutzer brach visual_overnight_20261101/run_003 ausdrücklich ab. Worker10380
wurde nach Befehlszeilenprüfung beendet. Supervisor15488 endete am01.11.2026
um00:33:43 Berlin und gab seine Schlafsperre frei. user_stop.json und
status_before_user_stop.json dokumentieren den Abbruch; status.json kennzeichnet
den Lauf als cancelled_by_user. Keine Quader-Endtests wurden gestartet. Alle
Renderdaten, Losskurven, Best-/Latest-Checkpoints bleiben unverändert erhalten.
Die letzte vollständige Validierungsrunde war Zyklus249 bzw.24.900 Updates pro
Modell (aus curves.json geprüft, STOP_SUMMARY.json). Teilupdates danach
sind kein vollständiger weiterer Vergleich. Der alte Versuch ist eine enge
Zwei-Objekt-Referenz, keine Baseline für die neue Mehr-Objekt-Aufgabe.

## 2. Präzise Forschungsfrage

Kann ein kompaktes Modell aus kalibrierten RGB-Ansichten die **beobachtbaren**
Objekte einer Szene lokalisieren und ihre Abmessungen und Orientierung schätzen,
wenn Anzahl, Farbe, Stapelhöhe und Verdeckung wechseln? Verbessert eine
Handkamera bei gleichem Modell die Präzision bzw. zusätzliche Sichtabdeckung?

Erste Objektklasse: starre Würfel und Quader. Keine exakten CAD-Modelle als
Modelleingabe und keine Anpassung an spätere reale Einzelobjekte. Der Simulator
liefert Trainingslabels; das Modell erhält nur RGB und Kamerakalibrierung.
Die geschätzten Quader sind eine begrenzte Formrepräsentation, kein Nachweis
für beliebige unbekannte Formen, Lego-Noppen, Steckverbindungen oder Material.

## 3. Daten statt bloß mehr Optimizerupdates

Geplanter Hauptdatensatz: 12.000 Trainingsfamilien, 2.000 Validierungsfamilien,
mindestens2.000 reservierte Testfamilien. Diese Zahlen sind ein Ziel nach
Geschwindigkeitsprobe; keine ungemessene Zusicherung, alles passe in10Stunden.
Wenn die Datenerzeugung zu langsam ist, wird das gemeinsame Budget vor dem
Produktionsstart symmetrisch reduziert und eingefroren, nicht nach Testbefunden.

Eine Familie umfasst denselben physischen Aufbau und alle seine Kameraansichten,
Armstellungen und Augmentierungen. Familien dürfen niemals auf train/val/test
verteilt werden. Objektmaße, Supportgraph, Farbpalette und Startzustand werden
zusätzlich gehasht. Reine neue RNG-Seeds ersetzen keine kontrollierten Splits.

### Objektanzahl und Formen

- 5% leere Szenen gegen erfundene Detektionen.
- Je19% Szenen mit1,2,3,4 oder5 Objekten.
- Unter vorhandenen Objekten etwa50% Würfel,50% Quader. Maße zunächst25–70mm,
  Quader-Aspektverhältnisse bis2. Farben zufällig, ausdrücklich mehrfach dieselbe
  Farbe in einer Szene. Keine feste Zuordnung Rot=Slot1/Grün=Slot2.
- Eine reine Würfel→Quader-Aussage erfordert später einen eigenen Würfel-only-
  Trainingsarm. Das Hauptmodell trainiert Quader bereits mit; dessen neue Quader
  sind Größen-/Formvarianten innerhalb bzw. außerhalb der trainierten Verteilung.

### Anordnungen innerhalb der nichtleeren Szenen

| Anteil | Szene | Was damit gelernt werden soll |
|---:|---|---|
| 35% | Einzelobjekte/verstreute Objekte, unterschiedliche Abstände | Grundlokalisierung, Zählung, Hintergrund |
| 30% | Mischung aus freien Objekten und Zweier-/Dreierstapeln | Teilaufbauten, Höhen, benachbarte Bauteile |
| 25% | Türme mit2–5 Objekten | hohe Objektmittelpunkte, verdeckte Unterteile |
| 10% | stabile kleine Wände, versetzte Reihen, einfache Brücken | mehrere Träger und gegenseitige Verdeckung |

Nicht jede Kombination passt zu jeder Objektanzahl. Szenen werden aus einer
vorab festgelegten zulässigen Kombinationstabelle gezogen; finale Häufigkeiten
werden tatsächlich gemessen. Das Haus selbst ist noch kein Trainingsziel.

**Physikalische Validität:** Aufbauten in der Simulation setzen und auspendeln
lassen; Kontakt, Überlappung, Geschwindigkeit und Stabilität prüfen. Keine
schwebenden Würfel oder ineinanderteleportierten Quader als normale Stapel.
Geplante Brücken nur akzeptieren, wenn tatsächliche Kontakte und Stabilität
bestätigt sind. Verworfene Szenen und ihre Gründe bleiben im Dateninventar.
Erfolg der statischen Szene beweist keine ausführbare Roboter-Baufolge.

### Verdeckung

Sichtbarkeit pro Objekt/Kamera aus Instanzmasken und isolierter Referenzansicht
berechnen. Masken/Tiefen dienen nur Labels und Audit, nicht als Eingabe.
Entwicklungsberichte nach frei sichtbar (>75%), mäßig (25–75%), stark (5–25%)
und nahezu unsichtbar (<5%) aufschlüsseln. Sichtbarkeit wird nicht mit
Wahrscheinlichkeit einer korrekten Pose gleichgesetzt.

Pose-/Größen-/Orientierungsverluste nur für ein Objekt mit >=5% Sichtbarkeit in
mindestens einer **verfügbaren** Kamera. Komplett verdeckte Objekte sind in diesem
statischen Versuch keine rekonstruierbare Pflichtausgabe. Die Detektionsausgabe
bedeutet 'aus den verfügbaren Ansichten beobachtbares Objekt', nicht 'physisch
garantiert vorhandenes Objekt'. Unbeobachtbare Instanzen werden gesondert gezählt.
Wenn die dritte Kamera ein vorher unsichtbares Objekt sichtbar macht, ändert
sich die erreichbare Abdeckung berechtigt; dies muss von Präzision auf den
gemeinsam sichtbaren Objekten getrennt werden. Kein Training zum Erraten
vollständig unsichtbarer Mittelpunkte und kein Vertrauen in unkalibrierte Scores.

### Kameras und Variation

Zwei feste schräge Kameras plus Handgelenkkamera. Dreifach-RGB160×160. Zunächst
gleiche physische Szenen für beide Kameraarme. Feste Kameras mit kleinen
kalibrierten Posevariationen, Licht/Hintergrund/Farben getrennt randomisiert.
Handkamera aus mehreren kollisionsfreien Armstellungen; keine trainierte aktive
Kamerapolicy. Sichtfeld und Verdeckungen protokollieren.

Intrinsik und Weltpose jeder Kamera sind bekannte Kalibrierungsinformationen.
Bei der Handkamera kommt die Weltpose aus Hand-Auge-Kalibrierung und gemessenen
Robotergelenken. Dies sind keine versteckten Objektpositionen. Ohne korrekte
Kalibrierung gibt es keine garantierte metrische Weltkoordinate. Kleine
Kalibrierungsfehler werden in einem getrennten Robustheitstest untersucht.

## 4. Modell – konkret dimensionierter Vorschlag

Architekturprototyp: model_prototype.py. **904.112 Parameter**, davon287.008 im
CNN. Prototyp untrainiert, keine fertige Trainingspipeline.

Eingaben:

- Bilder B×3×3×160×160.
- Kalibrierte Strahlen B×3×20×20×6: Weltstrahlrichtung3 + Kameraursprung3.
  Ursprung vor Training relativ zum Arbeitsraum und auf dieselbe Meterskala
  normieren. Genaue Strahlberechnung anhand getesteter Renderer-Konventionen.
- Kameraverfügbarkeitsmaske B×3.

Gemeinsamer CNN für alle Ansichten:

| Stufe | Operation | Ausgabe pro Kamera |
|---|---|---|
| Block1 | Conv3→32,3×3,stride2 + ReLU; Conv32→32,3×3 + ReLU | 32×80×80 |
| Block2 | Conv32→64,3×3,stride2 + ReLU; Conv64→64,3×3 + ReLU | 64×40×40 |
| Block3 | Conv64→128,3×3,stride2 + ReLU; Conv128→128,3×3 + ReLU | 128×20×20 |

Die räumliche Struktur bleibt erhalten:1.200 Bildtokens mit128 Merkmalen statt
globalem Durchschnitt. Strahlprojektion Linear6→128 und Kameraembedding3×128
ergänzen die Geometrie. Fünf lernbare Objektqueries (5×128) lesen diese Tokens
über drei Transformer-Decoderblöcke: Dimension128, vier Attentionköpfe,
Feedforward128→256→128, GELU, Dropout0,1, LayerNorm. Kein großer vortrainierter
Backbone; Größe bewusst unter1Mio Parametern.

Gemeinsamer Ausgabekopf Linear128→128 + GELU + Linear128→16 je Query:

- 1 Detektionslogit (Sigmoid bei Inferenz).
- 3 Positionswerte relativ zum Arbeitsraum (linear).
- 3 Größenwerte (Softplus und metrische Skalierung im späteren Postprocessing).
- 6 Werte für eine kontinuierliche Rotationsrepräsentation, anschließend
  orthonormalisieren; dies sind nicht6Eulerwinkel.
- 3 Sichtbarkeitslogits, je Kamera; bei nicht verfügbarer Kamera nicht bewerten.

Nicht benötigte Slots lernen 'keine Detektion'. Die Slotreihenfolge hat keine
Objektidentität; sie wird mit bipartitem Matching zugeordnet. Das ist das
Set-Prediction-Prinzip aus DETR, keine Behauptung einer DETR-Reproduktion.
Aus dem Geometrieoutput kann später ein Supportgraph abgeleitet werden; dafür
ist zunächst kein zusätzlicher unvalidierter Relationskopf nötig.

## 5. Verluste und Optimierung

Hungarian Matching zwischen vorhersagbaren GT-Objekten und fünf Slots. Matching
anhand Detektionskosten und normierten Positions-/Größen-/Rotationsfehlern,
ausdrücklich nicht nach Farbe oder einem festen Simulatorobjektindex.

Startkonfiguration nach getrennten Normalisierungstests:

`L = 1*L_detection + 5*L_position + 1*L_size + 0.5*L_rotation + 0.25*L_visibility`

- Detection: BCEWithLogits, leere Slots Gewicht0,1; Recall/False Positives
  kontrollieren, damit Leergewicht nicht systematisch Unterzählung begünstigt.
- Position/Größe: Smooth-L1 nach metrischer Normierung auf0,1m; beta0,1 im
  normierten Raum entspricht10mm Übergang. Nicht Winkel und Meter unskaliert addieren.
- Rotation: geodätischer SO(3)-Fehler, **Minimum über physikalisch äquivalente
  Boxsymmetrien**. Für Würfel sind mehrere Orientierungen gleichwertig; für
  Quader gilt eine andere Symmetriegruppe. Größen-/Rotationskonvention gemeinsam
  festlegen und an gedrehten Testboxen prüfen.
- Visibility: BCE auf pro-Kamera-Sichtbarkeitsklassen; Klassen anhand gemessener
  Sichtfraktion, nicht vermeintlicher physikalischer Unsicherheit. Detektions-
  und Sichtbarkeitsscores werden erst nach Kalibrierungsprüfung als Konfidenz genutzt.

Lossgewichte sind ein vorab definierter Startpunkt, noch nicht validierte Optima.
Gesamtloss **und jede Komponente** werden geplottet, damit ein kleiner
Gesamtwert keinen schlechten Zähl-/Positionskopf verdeckt.

AdamW, LR3e-4, WeightDecay1e-4, Gradientclip1. Effektive Batchgröße32; geplante
Mikrobatch16 mit2 Akkumulationsschritten, vor Start auf12GB GPU messen. Gleiche
Mikrobatches und Updatezahl zwischen den Kameraarmen. Drei gepaarte Seeds
bleiben: sechs Modelle, nicht drei Szenen. Mehr Seeds haben zunächst geringere
Priorität als neue Szenen und Sichtabdeckung.

Bis100 echte Epochen ohne Zurücklegen. Mit12.000 Familien und Batch32 sind
375Updates/Epoche, maximal37.500Updates/Modell. Lernrate fünf Epochen warmup,
danach vorab festgelegter Cosineverlauf. Ein Epochen-/Zeitbudgetkonflikt beendet
beide Arme eines Seeds nur am gemeinsamen Updatepunkt. Kein Weitertrainieren
eines Arms, um eine schönere Kurve zu erhalten.

Bestcheckpoint nach über Sichtbarkeits-/Anordnungsstrata ausgewogenem Val-Loss.
Early Stopping pro Seedpaar erst, wenn BEIDE Arme15Epochen keine relative
Verbesserung von mindestens0,5% ihres bisherigen Bestwertes mehr erreichen.
Kameravergleich verwendet gleiche bezahlte Updates; bestgewählte Updates
zusätzlich ausweisen. Konkrete Scheduler-/Stoppingparameter vor Produktion einfrieren.

## 6. Validation, Test und Plots

Alle fünf Objektzahlen, alle Anordnungen und Sichtbarkeitsgruppen müssen in
Validierung vorkommen. Train/Val unterscheiden sich in Szenenfamilien. Ein
zusätzliches festes Trainingspanel über alle Strata ist ausschließlich Diagnose.

Nach jeder Epoche: gesamter Trainingsloss (über die echten Trainingsbatches
aggregiert), gesamte Validation im Evalmodus, identisches Trainingspanel im
Evalmodus, Losskomponenten, Lernrate, Gradienten und Laufzeit. So bleiben
Dropout-Effekte von Generalisierungslücken unterscheidbar. PNG/SVG/JSON/CSV.

Berichte pro Seed/Kamera und pro Objektzahl, Stapelhöhe und Sichtbarkeit:

- Precision/Recall und korrekte Objektanzahl auf beobachtbaren Instanzen.
- Mittelpunktfehler XY/Z/3D, Median und P90; Anteile innerhalb5mm/10mm.
- Winkelabweichung unter Symmetrien und Größenfehler.
- End-to-End Recall: Objekt korrekt detektiert UND innerhalb10mm. Fehler nicht
  durch Auslassen schwieriger Objekte aus dem Nenner entfernen.
- Gemeinsame Sichtbarkeit beider Kameraarme für fairen Präzisionsvergleich;
  zusätzliche Abdeckung durch Handkamera separat.
- Kalibrierungs-/Sichtbarkeitsstress mit explizitem 'nicht beobachtbar'.

Neue reservierte Tests, vor Training festgelegt:

1. Neue Szenen innerhalb der trainierten Verteilung.
2. Neue Quader-Aspektverhältnisse2–3 und zurückgehaltene Maßkombinationen.
3. Zurückgehaltene Anordnungstopologien und besonders starke Verdeckungen.
4. Kleine neue Kameraposen, Licht-/Hintergrundänderungen und Kalibrierungsfehler.

Nicht jede Randbedingung gleichzeitig verändern: getrennte Panels ermöglichen
eine Diagnose. Erst alle Modelle auswählen/einfrieren, dann einmalig testen.
Vorherige Quader-Testbilder oder Testmetriken nicht für neue Modellwahl verwenden.

### 6.1 Regelmäßiger 3D-Abgleich und transparente Überlagerung

Explizite Nutzeranforderung: alle paar Epochen die aus den Fotos vorhergesagte
3D-Szene mit der wirklichen Simulationsszene vergleichen und neue Bilder erzeugen.

Vorgabe: **bei Epoche0, danach alle5Epochen**, zusätzlich am letzten vollständigen
Checkpoint und für den ausgewählten Bestcheckpoint. Für alle sechs Modelle
dieselben zwölf festen repräsentativen Validierungsfamilien (leer,1–5Objekte,
frei/gestapelt/verdeckt) und vier vorab deterministisch rotierende Val-Familien.
Keine nachträgliche Auswahl nur schöner Ergebnisse, keine reservierten Endtests
als regelmäßige Trainingsdiagnose. Kameraverfügbarkeit/Objektbeobachtbarkeit pro
Arm berücksichtigen. Panel-IDs vor Training einfrieren.

Pro Szene speichern:

- Tatsächliche drei RGB-Eingangsbilder, verwendete Kameras und Kalibrierung.
- Simulationsgeometrie: echte Mittelpunkte, volle Kantenlängen, Orientierung.
- Vorhergesagte Geometrie aus dem **unveränderten** Modelloutput nach regulärem
  Postprocessing: eigene Positionen, Größen und Orientierungen. Keine Übernahme
  echter Maße, keine nachträgliche Registrierung oder Ausrichtung an GT.
- Überlagerungsbild in schräger Ansicht, Draufsicht und Seitenansicht: Simulation
  **Cyan**, Vorhersage **Orange**, jeweils Alpha0,30. Gleiche Achsen, metrisch
  gleich skalierte Dimensionen, identische Ansichten/Grenzen über alle Epochen.
- Fehlende/zusätzliche Detektionen rot umrandet und beschriftet; nicht aus der
  Grafik entfernen. Physisch vorhandene, aus verfügbaren Kameras vollständig
  unbeobachtbare Objekte als HIDDEN markieren; nicht als normales MISS bestrafen.
- JSON mit Objektzuordnung und Metriken. Schwarze Verbindung zwischen zugeordneten
  Mittelpunkten zeigt die Verschiebung. Epochennummer, Seed, Kameramodus und
  Checkpointhash müssen für echte Ausgaben auf/bei der Grafik stehen.

Das neue Modell rekonstruiert zunächst eine **parametrische Szene aus Quadern**,
kein beliebig detailliertes Mesh. Der Vergleich prüft damit genau die gelernte
Repräsentation. Fotos der Rendererdiagnose werden nicht wieder als Trainingseingabe
eingespeist. Transparenz dient Sichtbarkeit, nicht physikalischer Materialschätzung.

Zusätzlich zu Position/Größe/Orientierung: orientierte3D-IoU (Schnittvolumen durch
Vereinigungsvolumen,1=deckungsgleich), mittlerer Fehler optimal zugeordneter acht
Boxecken in mm. IoU nicht nur auf erfolgreichen Detektionen mitteln: Missing/Extra
separat berichten; ein ausdrücklich benannter 'scene_iou_score' ist Summe
zugeordneter IoUs geteilt durch größere Objektanzahl und **keine** echte
Vereinigungsvolumen-IoU der Gesamtszene. Große Fehlverschiebungen dürfen nicht
durch zentrierte Formvergleiche verborgen werden.

Positionsbasierte Hungarian-Zuordnung ohne GT-Identitäts-/Farbleak, metrisches
Gate vorab0,10m, unzugeordnete Objekte sichtbar. Geometrie-Metriken mindestens
auf festem ausgewogenem Val-Panel von256Familien alle5Epochen; Visualisierungen
auf den16oben beschriebenen Szenen. Ganze Val-Losses/Detektionsmetriken weiterhin
jede Epoche. Panelzahlen und Renderzeit in den10h-Benchmark aufnehmen.

Implementierung: compare_geometry.py berechnet orientierte Boxüberschneidung
über Halbraumschnitt und konvexe Hülle (numerische Gleitkommagenauigkeit),
symmetriebewussten Winkel, Positions-/Größen-/Eckenfehler sowie Missing/Extra.
Es erzeugt PNG, SVG, scene.json und metrics.json. Analytische Tests prüfen
identische Boxen, halbe Überlappung (IoU1/3), getrennte Boxen und symmetrische
90°Würfelrotation. Die beiden teiltransparenten Farben sind bereits umgesetzt.
overlay_demo ist ausdrücklich eine **Illustration mit künstlichen Fehlern**,
keine Simulationserhebung oder trainierte Vorhersage.

Noch zu integrieren: Epochencallback, Export echter Modellvorhersagen/Simulator-
labels, feste Panels und input-RGB-Kontaktbogen. Der bisherige Prototyp ist
untrainiert; deshalb gibt es noch keinen echten V2-Geometrievergleich.

## 7. Begrenztes Nachtbudget und Startbedingungen

Ungefähres Ziel bleibt zehn Stunden **Gesamtwandzeit**, nicht garantierte zehn
GPU-Optimierungsstunden. Kein neuer Lauf wird durch dieses Dokument gestartet.

1. Maximal45min technische Vorbereitung/Benchmark:320kleine Szenen mit allen
   Objektzahlen/Szenentypen; Rendering, Kalibrierung, Sichtlabels und Physik prüfen.
   Auf32einfachen beobachtbaren Szenen muss das Modell bewusst überfitten können
   (z.B. hoher Detektionsrecall und wenige mm Positionsfehler). Kein Erfolg:
   zuerst Pipeline/Matching prüfen, keinen langen Lauf starten.
2. Geplant bis2h Sammlung/Validierung des eingefrorenen Datensatzes. Gemessener
   Durchsatz bestimmt vor Produktion, ob12k/2k plus Endtests passen. Alle sechs
   Trainingsläufe kurz benchmarken und einen Budgetplan speichern.
3. Restliches Budget bis9h: gepaarte Modelle trainieren, begrenzte Epochen,
   EarlyStopping, Best-/Latestcheckpoints inklusive Optimizer, Scheduler und
   CPU/CUDA-/Sampler-RNG. Datenfamilien und Samplerposition exakt fortsetzbar.
4. Bis1h Reserve für gemeinsamen Freeze, Endtests, Plots und Bericht. Bei
   unvollständigem Budget keine Tests als bestanden ausgeben. Gegebenenfalls
   weniger vollständige Seeds transparent berichten, nicht fehlende Replikate erfinden.

Akzeptanzkriterien vor Start: keine Split-Leaks, stimmige Projektion/Reprojektion,
physisch gültige Szenen, kein Farbindex-Leak, keine Labels als Eingabe,
Maskierung ausgeschalteter Kamera wirksam, Symmetrien korrekt, endliche
Gradienten, Checkpoint-Resume auf identischem nächsten Batch nachgewiesen,
realistische gemessene10h-Kosten.

Nachtbetrieb: Windows-Prozessdienst/Basis-Python ohne Codex-Jobbindung,
Supervisor, Schlafsperre, Deadline, endlicher Reparaturversuch, kein automatischer
Methodenwechsel. **Graceful stop marker** bei jedem gepaarten Update prüfen,
letzten gemeinsamen Zustand sichern und sauber beenden; kein PID-Abschuss als
normaler Steuerweg. Monitorzustand mit Logoffset/Updates und bekannten Fehlern.

## 8. Was danach zum Lego-Haus noch fehlt

Die fertige Zielanordnung muss ebenfalls visuell erfasst und mit dem aktuellen
Zustand verknüpft werden. Gleiche Bauteile brauchen geometrisches Matching,
keine angenommene Farbidentität. Danach Baufolge, Greif-/Ablageposen,
Kollisionsvermeidung und visuelle Korrekturen. Steckkräfte, Noppenausrichtung und
Präzision echter Legomontage werden von diesem Boxdatensatz nicht gelernt.
Das erfordert einen eigenen Aktions-/Kontaktversuch und später reale Prüfung.

## Quellen und Implementierungsstand

- DETR / Set Prediction und bipartites Matching:
  https://arxiv.org/abs/2005.12872
- BOP / Sichtbarkeit und symmetriebewusste Posebewertung:
  https://bop.felk.cvut.cz/challenges/bop-challenge-2023/

model_prototype.py implementiert nur die vorgeschlagene Netzarchitektur.
Forward-Test mit variierender Kameraverfügbarkeit bestand; ein gezielter Test
zeigte, dass das Verändern einer maskierten Kamera die Ausgabe nicht beeinflusst.
compare_geometry.py ergänzt einen analytisch geprüften Geometrievergleich und
transparente Diagnoseansichten; die Trainingsanbindung ist noch offen.
Datengenerator, Matching-Loss, Posepostprocessing, Trainer und Budgetbenchmark
sind für diesen Entwurf **noch nicht implementiert**. Keine erfundenen neuen
Trainings- oder Transferergebnisse.
