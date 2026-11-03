# Vision V4: Seitenansichten und kontrollierte Aktualisierung

Status: **Entwurf, nicht implementiert oder gestartet.** Datum: 02.11.2026.
Dieser Plan startet weder Datenerzeugung noch Training, Agenten oder Automation.
Keine Übernahme der abgelaufenen V3-Deadline. Ein neuer Lauf benötigt ein eigenes autorisiertes Budget.

## Ausgangspunkt und Hypothesen

V3 M2 wurde bereits mit zwei festen und 0–3 Handansichten sowie kalibrierten Weltstrahlen trainiert. Es ist kein ausschließlich auf drei feste Bilder trainiertes Modell. Die vorgesehenen Kandidatenbänder betrugen 1–22 cm Versatz. Die neuen Seiten-Diagnosen erreichen 32,8/48,6 cm und 17,1/15,9° Blickhöhe über dem Ziel. In einer Szene steigt der Satzfehler von 12,43 auf 51,75/18,23 mm-äq. Das ist ein Hinweis auf fehlende Abdeckung, kein Ursachennachweis.

V3 erzielte nur 1,61% hilfreiche gültige Request-Trainingskandidaten; seine kalibrierte aktive Policy wurde deaktiviert. Ein neues sinkendes Head-Loss genügt deshalb nicht als Erfolgskriterium.

H1: Gezielte Seitenansichten verbessern die Fähigkeit, solche Bilder zu verarbeiten.
H2: Gepaarte Kontexte zeigen, wann ein zusätzliches Bild hilft oder schadet.
H3: Getrennte Blickwahl und Übernahmeentscheidung erzielen messbaren Nutzen bei begrenzter Schadensquote und tatsächlichen Requests.
Jede Hypothese wird separat ausgewertet; ein besseres Ergebnis kann nicht vorausgesetzt werden.

## 1. Daten und Kamerabewegungen

Nur Simulation, zunächst statische Szenen und Quaderrepräsentation. 0–5 Objekte, Würfel und unterschiedlich proportionierte Quader; verstreut, gemischt, Türme, Wände/Brücken. Für nichtleere Szenen Zielanteile 25/25/35/15%, nur geometrisch mögliche Kombinationen; tatsächliche Verteilungen ausweisen. Leerszenen 5%, übrige Anzahlen gleich häufig. Proportionen, Farben, Licht, Hintergründe und Verdeckung variieren. Lange/dünne Quader werden jetzt ausdrücklich Teil der Trainingsdomäne; bisherige V3-Geometrie-Endtests sind damit historische Diagnosen, kein neuer Blindtest.

Pro Familie: zwei feste Kameras, anfängliche Handansicht, bis zu sechs gespeicherte erreichbare Kandidaten aus folgenden Familien:

| Familie | Geometrischer Wunsch |
| --- | --- |
| Naher Kontrollblick | kleiner Versatz wie V3, ähnliche Richtung |
| Rechts | Kamera roboterrechts vom Fokus, auf Fokus nach links ausrichten |
| Links | Kamera roboterlinks vom Fokus, auf Fokus nach rechts ausrichten |
| Basis | Kamera zur Basis versetzen, von dort zum Fokus ausrichten |
| Erhöht/diagonal | alternative Höhe und diagonale Sicht |
| Schwieriger Kontrollblick | geprüft erreichbarer, aber verdeckter/unscharfer/redundanter Blick |

Seitenwünsche: 20–50 cm Versatz zur Ausgangskamera als Abdeckungsziel, Blickhöhe 10–35° über Zielhorizontalen. Basiswünsche bis 40°. Dies sind Suchbereiche, keine erzwungenen Posen oder Quoten für nicht erreichbare Ziele. Tatsächlich erreichte Verteilungen, Abweisungen und Korrelationen nach Richtung/Objektanzahl/Anordnung veröffentlichen. Keine Ersatzfahrt mit anderem Winkel unter dem ursprünglichen Label. Basisfamilie bleibt als blocked erhalten, falls keine zulässige Pose gefunden wird.

Fokus aus aktueller Vorhersage/Unsicherheit und beobachtbarem Arbeitsbereich; keine echte Objektpose zur Laufzeit-Blickwahl. Ein separater als oracle markierter Diagnosegenerator darf GT-Zentren benutzen, aber dessen Ansichten dürfen keine Evidenz für eine ausführbare aktive Policy liefern. Primärdaten verwenden den nicht-orakulären Generator. Kandidaten werden mit der eingefrorenen V3-Referenz erzeugt, damit A/B dieselben Daten erhalten; zusätzliche adaptive Kandidaten erst nach Variantenwahl in separaten Request-Familien.

Für jede Aufnahme tatsächliches RGB, Intrinsik und erreichte Kameraextrinsik speichern. MuJoCo −Z beim Export explizit in den gemeinsamen optischen Frame umrechnen. Projektionstests mit bekannten Weltpunkten sowie Vorwärtskinematik prüfen den Vertrag. Wunsch-, Plan- und Ist-Pose bleiben getrennt. Arme dürfen feste Kameras verdecken: zeitgleiche neue feste Bilder und eine Kontrollauswertung ohne neues Handbild trennen diesen Effekt vom Nutzen der Handkamera.

Bildmängel (Verdeckung, Anschnitt, Bewegungsunschärfe, Über-/Unterbelichtung) bleiben erhalten. Kamera-/Farbaugs synchron zum Kalibrierungsvertrag; geometrische Bildtransformationen verändern auch Intrinsik/Strahlen. Ein eigener Kalibrierungsfehler-Stresstest nutzt absichtlich gestörte geschätzte Extrinsik, getrennt von der nominal exakt kalibrierten Simulationsauswertung.

## 2. Splits, Größen und Kontrollen

Neue Seed-Namensräume, familienweise Trennung vor Bildern/Kameraposen; Manifest und Hashes vor Trainingsstart einfrieren. Alle Ansichten, Augmentationen und Präfixe einer Szene bleiben im selben Split. Die zwei bereits betrachteten Seitenbeispiele bleiben ausschließlich Regression/Illustration.

Geplante Obergrenzen, vorab durch Speicher-/Laufzeitpilot zu bestätigen:

| Zweck | Neue Familien |
| --- | ---: |
| Wahrnehmung train | 18.000 |
| Wahrnehmung validation | 2.000 |
| Request-/Übernahmeköpfe train | 4.000 |
| Köpfe validation | 1.000 |
| Schwellenkalibrierung | 1.000 |
| Blindtest IID | 2.000 |
| Blindtest neue Kameraregionen | 1.000 |
| Blindtest neue Quaderproportionen/Anordnungen | 1.000 |

Trainingsmischung Wahrnehmung: 75% neue Szenenfamilien, 25% ausschließlich bisherige V3-Trainingsfamilien als Replay gegen Vergessen. Die 18.000 neuen Familien und Replay werden identisch zwischen A/B verwendet; A sieht pro Familie nur den bisherigen Blickbereich, B zusätzlich Seiten-/Basis-/Diagonalbilder. Keine V3-Validation-/Kalibrierungs-/Endtestfamilien als Replay. Gleiche Updates, Startgewichte und Batch-/Seedreihenfolge; nicht nur gleiche Epochenzahl.

Drei gepaarte Modellseeds 1/2/3. A und B starten jeweils vom zugehörigen eingefrorenen V3-M2-Best-Checkpoint. Kein Neuinitialisieren des Backbones.

* A: kontrolliertes Weitertraining mit bisheriger Kameraverteilung.
* B: gleiche Architektur und Lernregeln, erweiterte Blickverteilung.
* Referenz: unverändertes V3 M2, null Updates.

Kamera-Holdout sind getrennte räumlich/winkelmäßig definierte Regionen mit Puffer, nicht nur andere Raster-IDs. Größen-Holdout durch disjunkte vorab definierte Proportionsbereiche; Zufallsseeds allein genügen nicht. Exakte Grenzen erst nach Machbarkeitspilot festlegen, vor Haupttraining einfrieren. Bessere Seitenleistung bei unveränderter Architektur stützt H1. Eine größere Architektur ist eine spätere, eigenständige Studie.

## 3. Modell und Trainingsalgorithmus

Wahrnehmung bleibt zunächst **904.112 Parameter**, maximal fünf Objekt-Slots. Eingabe B×V×3×160×160, V=2–5 (zwei feste, bis zu drei Handbilder). Pro Ansicht 20×20 Strahlen mit sechs Werten: Weltstrahlrichtung plus Kameraursprung. Nicht vorhandene Bilder und Tokens maskieren.

* CNN: sechs 3×3-Convs, Kanäle 32/32/64/64/128/128; drei Downsampling-Schritte, ReLU nach jeder Conv.
* Features: 400 Tokens je Ansicht, Dimension 128; lineare Strahlenprojektion 6→128 und drei Kamera-Rollenembeddings.
* Decoder: drei Transformer-Decoderblöcke, vier Attention-Heads, Feedforward 128→256→128, GELU, Dropout 0,1 und LayerNorm.
* Fünf lernbare Objektqueries; Ausgabekopf 128→128→16 mit GELU. Pro Slot Detektion, Position(3), Größe(3), Rotation(6), Sichtbarkeit(3).

Es gibt daher keine einzelne sinnvolle Zahl aller „Neuronen“; Kanäle, Tokenbreite, Slots und Parameterzahl werden getrennt angegeben. Dies ist 3D-Quaderrekonstruktion, kein freies Objektmesh und noch keine Lego-Montagefähigkeit.

AdamW, effektive Batchgröße 32 (Microbatch nach Pilot, Gradient Accumulation), LR 1e−4, Weight Decay 1e−4, Gradient Clipping 1,0, FP32 als Referenz. Drei Warmup-Epochen, Cosine-Abfall bis zum vorab eingefrorenen Updatebudget. Maximal 40 neue effektive Epochen, Early-Stopping-Patience 8 für das Seedmittel des balancierten Validation-Loss; A/B bleiben für den Hauptvergleich auf einem gemeinsamen maximalen Updatebudget. Zusätzlich Val-best je Seed ausweisen. Epochen beziehen sich auf tatsächlich gezogene Beispiele einschließlich Replay, nicht auf 18.000 allein. Exakte Batch-/Samplerposition, RNG, Scheduler und Optimizer für Resume speichern.

Unveränderte V3-Objektzuordnung und Loss-Komponenten: Detektion×1, Position×5, Größe×1, symmetriebewusste Rotation×0,5, Sichtbarkeit×0,25. Vor Start vorhandene Implementierungsdefinitionen und Einheiten im Manifest sichern. Kein zusätzliches Monotonie-Loss, das jedes neue Bild zwangsläufig als hilfreich behandelt.

Pro Szene Kontexte mit null/einem/zwei Zusatzbildern trainieren. Innerhalb eines Minibatches gepaarte Präfixe bilden und deren normalen Rekonstruktionsloss mitteln; die effektive Batchgröße zählt Szenen, die beiden Kontexte sind keine unabhängigen Familien. Handbildreihenfolge variieren, Bildanzahl und Verfügbarkeitsmasken variieren. Targets sind innerhalb eines Vergleichspaars identisch; Sichtbarkeitsrollen werden pro Kontext separat bestimmt. Für Vor-/Nachbewertungen zusätzlich die schon anfangs sichtbaren und erst neu sichtbaren GT-Objekte getrennt ausweisen. Verdeckte Objekte dürfen den scheinbaren Nutzen nicht durch einen wechselnden Nenner erzeugen.

## 4. Zwei getrennte Entscheidungen nach eingefrorener Wahrnehmung

Erst A/B nach Wahrnehmungsvalidation wählen, anschließend deren drei Checkpoints hashen/einfrieren und Köpfe auf neuen Request-Familien trainieren. Keine laufend wandernden Gewinnlabels.

**Vor der Fahrt:** bestehende Need-/Gain-/Helpful-Köpfe mit neu berechneten Labels neu trainieren. Inputs nur bisher aufgenommene Bilder/Schätzungen, aktuelle Unsicherheit, geplante relative Kamerapose und bekannte Roboterkinematik. Keine künftigen Kandidaten-RGBs, echten Objektgeometrien, GT-Verdeckung oder aus Zukunftsbildern abgeleiteten Merkmale. Nur geometrisch zugelassene Kandidaten rangieren; blockierte Kandidaten erhalten kein erfundenes Wahrnehmungsgewinnlabel.

**Nach der Aufnahme:** neuer kleiner Übernahmekopf, geplant 32→64→32→3 mit GELU, **4.291 Parameter** (vor Implementierung nachzählen). 32 vorab festgelegte beobachtbare Merkmale aus Vor-/Nach-Ensemble, Objektanzahl/Zuordnung, Positions-/Größen-/Rotationsänderung, Bildqualität, tatsächlicher relativer Pose und Abweichung von Plan zu Ist. Zuordnung ohne GT zur Laufzeit. Drei Outputs: erwarteter Gewinn, Wahrscheinlichkeit eines Gewinns ≥2 mm-äq., Wahrscheinlichkeit einer Verschlechterung >2 mm-äq. Merkmalsliste und Normalisierung im Pilot einfrieren; kein GT-Satzfehler als Input. Ganze Szene übernehmen oder bisherigen Zustand beibehalten; kein ungeprüftes objektweises Zusammenmischen kollidierender Hypothesen.

Loss Übernahmekopf: SmoothL1 auf Gewinn/20 mm plus je BCEWithLogits für hilfreich/schädlich, Gewichte 1/1/1. AdamW LR 3e−4, Batch 256, Weight Decay 1e−4, maximal 30 Epochen, Patience 5, drei Seeds. Gleiches vorab festgelegtes Optimizerprotokoll für Request-Köpfe. Natürliche Positivquote ausweisen; im Training höchstens 50% schwierige Zustände zusätzlich samplen, ursprüngliche Verteilung und Importance-Gewichte dokumentieren. Validation/Kalibrierung/Blindtest behalten natürliche Häufigkeiten. Keine Genauigkeit aus künstlich balancierten Daten als Produktionswert berichten.

GT darf Gewinnlabels liefern, nicht Kopfinputs. Ein GT-Orakel ist ausschließlich separate Obergrenzenanalyse. Wenn selbst die beste erlaubte Zusatzansicht kaum hilft, zunächst Wahrnehmung/Daten verbessern und keine erfolgreiche aktive Blickwahl behaupten.

## 5. Kalibrierung und vorab festgelegte Erfolgskriterien

Schwellen nur auf separaten Kalibrierungsfamilien wählen, erst danach Blindtests einmalig auswerten. Keine Änderung aufgrund alter V3-Endtests als neue Blindtest-Evidenz ausgeben. Für jede Quote Familien-/Aufnahmenenner und 95%-Intervalle ausweisen; familienweises Bootstrap, drei Seeds einzeln und Mittel/Streuung.

1. B vs A: im Seiten-Validation-Stratum mindestens 10% geringerer Satzfehler im Seedmittel und in mindestens 2/3 Seeds bessere Werte. Auf ursprünglichen Ansichten höchstens 1 mm-äq. mittlere Regression; Recall/Missing/Extra daneben, damit Zuordnung schlechte Erkennung nicht versteckt. Dies sind vorgeschlagene Akzeptanzschwellen, keine vorhergesagten Resultate.
2. Aktiver Betrieb gegen keine Zusatzaufnahme, zufälligen sicheren Blick und geometrischen Seitenblick: positiver mittlerer Nettofehlergewinn, familienweises 95%-Intervall ohne Null. Anzahl Bilder, Bewegungslänge/-zeit und blockierte Versuche separat berichten; keine frei erfundene Umrechnung von Bewegungszeit in mm.
3. Kalibrierung benötigt mindestens 100 tatsächliche Übernahmen; obere 95%-Wilson-Grenze des Anteils schädlicher Übernahmen (>2 mm-äq.) ≤5%. Zusätzlich jede Verschlechterung (>0) und deren Schwere ausweisen. Auf Blindtests gleiche Schwellen einfrieren und dieselben Werte prüfen. Kleine Teilgruppen bleiben explizit unentschieden. Bei Nenner 0 gibt es keinen Erfolgsnachweis. Das Gesamtintervall belegt keine Sicherheit pro Objekt oder Kamerafamilie.
4. Request-Coverage und Need-Recall berichten. Eine Policy ohne Requests besteht nicht. Scheitert ein Gate, bleibt automatische Aktualisierung deaktiviert; bisherige Schätzung und Nichtwissen sichtbar erhalten.

## 6. Arm und Freiraum: unabhängiger Gate, kein Wahrnehmungs-Loss

Wunschpose → IK/Gelenkgrenzen → Selbst-/Umweltkollision → ganzer Weg samt Greifer, Kamera und Halterung → tatsächliche Pose und Blickfeld → Aufnahme → Übernahmeprüfung. Bei jeder Ablehnung blockiert protokollieren. Zwei Zusatzbilder maximal, dann unsicher zurückmelden. Ein großer Umweg ist kein eigenes Optimierungsziel; gesucht wird ein informativer Seitenblick auf einem zugelassenen Weg.

Simulatorreferenz darf Offline-Daten und ausdrücklich bezeichnete Diagnosefahrten prüfen. Visueller Freiraum ist ein anderer Nachweis: unbeobachtete Bereiche bleiben unknown, keine Fahrt hindurch. Vor einem visuellen Erkundungsschritt muss bereits der vollständige Schritt in verifiziertem Freiraum liegen. Kann die Anfangsarmhülle mit den vorhandenen Kameras nicht freigegeben werden, kein Start; zunächst feste Kameraabdeckung/Startbereich verbessern. Das Training ersetzt dieses Problem nicht. Keine Realroboterbewegung und keine visuelle Kollisionsgarantie aus Simulationsresultaten ableiten.

## 7. Auswertung, Frontend und Budget vor Start

Alle fünf Epochen sowie Start/Best/Final: dieselben 16 Validation-Familien, alle drei Seeds, Cyan=GT/Orange=Präfix/Grün=neue Schätzung, tatsächlicher Kameraweg/Blickachsen, Inputbilder und Poseprotokoll. Abgelehnte neue Schätzungen trotzdem als „nicht übernommen“ zeigen, angenommener Zustand separat markieren. Keine nachträgliche geometrische Ausrichtung. Gute und schlechte Fälle in vorab gewählter Liste statt Best-Case-Galerie. GIFs für alle erreichbaren Blickfamilien und für blockierte Wünsche eine Erklärung statt fingierter Fahrt.

Plots: Train-/Validation-/feste Train-Probe-Loss, Komponenten, Seiten-/Original-Strata, Lernrate, Vorher-/Nachherfehler je Familie, Helpful/Harmful-PR-Kurven, Zuverlässigkeit der Wahrscheinlichkeiten, Coverage/Nutzen/Schaden über Schwellen und Anzahl Zusatzbilder. Kein reines Gesamt-Loss als Nachweis für Aufnahmequalität. Testplots erst nach Modell-/Schwellenfreeze.

Vor Hauptlauf: Datenerzeugungs-/Speicherpilot mit 200 neuen Familien; alle Ansichtsrichtungen einschließlich blockierter Basis dokumentieren, tatsächliche Parameterzahl, drei echte Optimizerupdates und exakten Teil-Epochen-Resume prüfen. Laufzeit pro Datenfamilie, Peak-RAM/VRAM, Array-/Checkpointgröße und Zeit pro A/B-Update messen. Mit gepaarten Präfixen ist V3-Zeit pro Update keine verlässliche V4-Prognose.

Danach Gesamtzeit für Datenerzeugung + 2 Varianten × 3 Seeds + Köpfe + Kalibrierung + Blindtests + Renderberichte kalkulieren und ein festes Budget vorschlagen. Keine Zusage „10 Stunden reichen“ vor diesem Benchmark. Falls Budget zu klein: vorab gemeinsamen Updateumfang reduzieren oder zunächst nur Wahrnehmung A/B durchführen; niemals still Seeds streichen oder Endauswertung auslassen. Noch kein Pilotstart durch diesen Plan.

Routine-Monitoring deterministisch mit persistentem Logoffset; maximal alle zwei Stunden Agentenprüfung und nur bei Fortschrittsstörung/Fehler/Abschluss berichten. Eine neue Deadline gilt nur für einen später ausdrücklich gestarteten Lauf; Prozessregistrierung, STOP_REQUESTED, atomare Checkpoints und ein technischer Reparaturversuch erst nach bewiesenem Prozessende. Keine automatische wissenschaftliche Parameteränderung.

## Verwendete lokale Evidenz

* `../visual_active_v3_20261101/run_001/config.json`
* `../visual_active_v3_20261101/run_001/source/experiments/visual_active_v3_20261101/model_v3.py`
* `../visual_active_v3_20261101/run_001/FOLLOWUP_REVIEW.md`
* `../active_view_20261101/SIDE_VIEWS.md`

Offene Umsetzung: V4-Datengenerator/-splits, gepaarter Trainer, Übernahmekopf, Kalibrierung, registrierter Frontend-Entwurf und Pilot. Diese Datei beschreibt die Konzeption, nicht fertige Trainingssoftware.

## Pilotnachtrag, 02.11.2026

Der 200-Familien-Pilot ist unter `pilot_002/REPORT.md` dokumentiert. Der explorative Per-Szene-Planer (`pilot_001`) wurde nach 32 Familien wegen hoher Datenerzeugungskosten kontrolliert beendet; sämtliche Artefakte sind erhalten. Keine Produktionsgewichte geändert, kein Haupttraining gestartet.

Die schnellere Referenz-Kamerabank prüft statische/Selbstkollisionen einmal und Objekte jeder neuen Szene separat durch konservative analytische Swept-AABBs. Ein statischer Geometriefingerprint verhindert die Wiederverwendung bei geänderten Vertragsdaten. Trainingserzeugung darf den Fokus innerhalb des kalibrierten Blickfelds statt exakt im Zentrum abbilden; die tatsächliche Winkelabweichung wird mitgeloggt. Dies ersetzt nicht den getrennten Nachweis einer zur Wunschpose gerichteten aktiven Fahrt.

47/200 Zusatzwünsche aufgenommen; Abdeckung links und Basis noch unzureichend. **Vor Haupttraining Bank erweitern**, ohne freie/erreichbare Räume vorzutäuschen. Nächster Abdeckungspilot: mindestens 20 gültige rechte/linke/erhöhte Ansichten je 40 zugeordneten Wünschen; Basis kann explizit blockiert bleiben. Keine nachträgliche Änderung dieses Gates anhand von Endtests. Auch vollständige Kopf-/Split-/Frontendimplementierung und ein Updatebudget fehlen noch.

Als erste gepaarte Studie zehn effektive Epochen A/B mit je drei Seeds planen. Vierzig Epochen sind ein ursprüngliches Maximum, keine Laufzeitzusage. Die Budgetabschätzung im Pilotbericht enthält gemessene Optimizerzeit und klar markierte Datenhochrechnungen; Validation/Köpfe/Endauswertung sind zusätzlich zu budgetieren. Die zwei kleinen Numerikmessungen sind technische Prüfungen, keine V4-Modellfreigabe.

## Kameraführung nachgebessert, 03.11.2026

`guidance_002` prüft dieselben 200 Entwicklungsfamilien. 147 statt 47 zulässige Ansichten: rechts 28/40, links 24/40, Basis 27/40, erhöht 37/40 und schwierige Kontrollansichten 31/40. 26 zertifizierte Kamerafahrten, feinere konservative Hüllen mit unveränderten Abständen und separate Zielnachführung am Aufnahmepunkt. Maximale geplante optische Zielabweichung 2,954°. Das zuvor definierte reine Abdeckungsgate ist damit bestanden; tatsächliche Erfassungen werden zusätzlich in capture_audit.json protokolliert.

Zwei Entwicklungsfehler sind separat erhalten: erneutes physikalisches Settling war kein identischer Szenen-Replay; beim Fortsetzen wurden geladene NumPy-Wege addiert statt verkettet. Die native Kontaktprüfung stoppte den zweiten Fehler. Unveränderliche Objektzustände, explizite Wegverkettung und Regressionstests sichern den korrigierten Lauf ab. Ungültige Resume-Ergebnisse aus guidance_001 gehen nicht in guidance_002 ein; nur 138 bereits validierte, auf Anfangs-/Endpunkte geprüfte ursprüngliche Datensätze wurden übernommen. Für alle erfolgreichen Ansichten folgt eine unabhängige tatsächliche Bilderfassung mit erneuter Nachführungsprüfung in der exakt gespeicherten Szene.

Kein Modelltraining oder neue Produktionspolicy. Die Prüfung verwendet ausdrücklich Simulatorreferenz und ist kein visueller Freiraumnachweis. Nächste Trainingsvorbereitung kann auf dieser Führung aufbauen; A/B-Haupttrainer, getrennte Kopftrainings und feste Holdouts/Budgets benötigen weiterhin Umsetzung und Trainingsfreigabe.
