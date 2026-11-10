# Produktiver V2-Nachtlauf · 01.11.2026

Vom Nutzer ausdrücklich gestartet. Aktiver Lauf: run_001. Startbudget ab01:26:37
Berlin, Gesamtdeadline11:26:37; neue Updates enden spätestens15min vorher.
Bei100Epochen oder globalem EarlyStopping kann der Lauf früher regulär enden.
Die zehn Stunden enthalten Datengenerierung, Lernen, Validation und Endtests.

## Implementierung und Freigabe

- scene_data.py erzeugt0–5Würfel/Quader inklusive Türmen, Mischszenen und
  physisch ausgependelten kleinen Brücken.350MuJoCo-Schritte, Prüfungen auf
  Geschwindigkeit, Positionsverlust, Penetration und Roboterkontakt. Kleine
  Armstellungs-/Kameravariationen; statisch gehaltene Armstellung während des
  Auspendelns. Keine gelernte Robotermotorik.
- Alle Kameras sind160×160RGB. Kalibrierte Weltstrahlen/Kameraursprünge als
  Geometrieinput. Kameraprojektion wird gegen die tatsächlich gerenderte isolierte
  Instanzmaske geprüft. Sichtbarkeit aus vollständiger/isolierter Segmentierung;
  weder Masken noch Simulatorobjektzustände gehen in das Modell ein.
- PHYSICS_CALIBRATION_CHECK.json:352Szenen einschließlich0–5Objekten und
 32länglichen Quaderszenen, Prüfungen bestanden. Gezielt verworfene Einstürze und
  veränderte Anordnungen bleiben im Ausschlussinventar.
- preflight_001 verfehlte die Objektanzahl-Anforderung. Ursache im Entwicklungs-
  test: stark untergewichtete leere Slots begünstigten zusätzliche Detektionen.
  Bei nur5Slots ist die extreme DETR-Hintergrundgewichtung0,1 nicht erforderlich.
  Einzige daraus gewählte Lossänderung: Hintergrundgewicht1 statt0,1.
- preflight_002 bestand mit32absichtlich wiederholten kleinen Szenen:
  4,53mmZuordnungsfehler,90,625%korrekte Anzahl nach950Updates. Das ist ein
  **Überanpassungstest**, kein Generalisierungsergebnis. DiagnostikLR0,001 mit
  Absenkung, ProduktionsLR bleibt0,0003 mitWarmup/Cosine.
- Exaktes Weiterrechnen nach Restore von Modell, AdamW- und RNG-Zuständen wurde
  auf identischem nächsten Trainingsbatch geprüft (Toleranz1e-7).
- smoke_002 absolvierte komplette Datengenerierung, alle6Modelle, eine Epoche,
  Checkpoints, Loss-/Komponentenplots, transparente GT-/Vorhersage-Overlays,
  RGB-Eingabebilder und beide reservierten Testpfade regulär. Seine Testseeds
  werden im Produktionslauf nicht wiederverwendet.

## Eingefrorene Konfiguration

904.112Parameter, sechsConv/ReLU-Schichten, dreiTransformerdecoder mitGELU,
fünfObjektslots. Drei gepaarte Seeds, jeweils feste Kameras und feste+Handkamera.
EffektiveBatch32, zweiMikrobatches16. AdamW3e-4/WeightDecay1e-4, Gradientclip1.
Normierte Position/Größe mitSmooth-L1, symmetriebewusster Rotationsloss,
Detektions- und Sichtbarkeits-BCE. Matchingkosten ausPosition, Größe und
Detektionswahrscheinlichkeit; Rotation geht in den Trainingsloss ein.

12.000Trainings- und2.000Validierungsfamilien, feste disjunkte Seedfamilien,
keine Augmentationsvarianten desselben gespeicherten Aufbaus über dieSplits.
Neue Aufbauten werden vorab unabhängig generiert; Originalfotos, Kalibrierung,
Labels und ihreSHA256Hashes bleiben gespeichert. Die tatsächlichen Häufigkeiten
der Objektzahlen und Anordnungen stehen in den Datensatzmanifesten.

Bis100echteEpochen ohneZurücklegen. Alle6Modelle erhalten gleiche Beispielreihen-
folge und bezahlte Updates, Dropout-RNG proSeedpaar zusätzlich gleichgesetzt.
Wenn alleModelle15Validierungsrunden keine relevante Verbesserung zeigen, wird
global früh beendet. Es findet keine automatische Architektur-/Loss-/LR-Suche
während des produktiven Laufs statt.

Checkpointauswahl nach dem Mittel der vorhandenen vier **Anordnungsstrata**-
Validierungslosses. GanzeVal-Losses werden daneben geplottet. Eine separate
Makrogewichtung nach Sichtbarkeitsklassen ist in diesem Lauf nicht implementiert.
Trainingsloss wird über alle Trainingsbatches der Epoche aggregiert; feste
Trainingsprobe und Validation laufen imEvalmodus. Checkpointauswahl und alle
Testmetriken bleiben getrennt. Position ist ein Fehler zugeordneter Slots;
CountAccuracy undRecall≤10mm zeigen zusätzlich, ob tatsächlich erkannt wurde.

## Geometrievergleich und Frontend

Epoche0, danach jede5.Epoche und finale Bestauswahl: gleiche repräsentative
Val-Szenen plus deterministisch wechselnde Szenen, jeSeed/Kameraarm. Es werden
PNG/SVG, Eingangs-RGBs, rohe GT-/Vorhersagegeometrie undmetrische JSONs gespeichert.
Die vollständig gerenderten Panels umfassen bis16Familien, **nicht256**.
Die geplante zusätzliche256erIoU-Diagnose ist noch nicht implementiert; die
ganzeValidation wird trotzdem jedeEpoche überLoss/Zählung/Recall geprüft.
Keine Geometrieregistrierung, keine Übernahme wahrer Größen inVorhersagen.
Bestbilder sind mit ihrer tatsächlichen ausgewählten Epoche gekennzeichnet.

monitor/training-runs.json registriert den aktiven Lauf unter
vision-scene-v2-run1. Die lokale Research-Atlas-Ansicht liest Status, Gesamt-
Losskurven undGeometrieindex alle15s. Epochenauswahl, Seed/Kamera undSzene sind
für die echten Geometrieausgaben auswählbar. Die gehosteteWebsite bleibt ohne
separatenUploader ein ausdrücklich datierterSnapshot.

## Reservierte Schlussprüfung

Nach gemeinsamem6Modell-Freeze:2.000neueIID-Familien plus512längliche Quader-
Szenen. Produktionsseeds8201001/8201002, technischeSmokeseeds getrennt.
Das Quaderpanel verändert Form undbeschränkt dieAnordnung auf verstreuteObjekte.
Es ist ein Geometrieverschiebungstest, kein streng disjunkterFormklassen- oder
unbekannterTopologie-Nachweis. Einige Maß-/Aspektbereiche können sich mit den
trainierten Brücken überschneiden. Das wird nicht als reinerWürfel→Quader-
Zero-shot-Nachweis ausgegeben. Ein echtes Lego-Haus oder Steckkräfte sind kein
Bestandteil diesesVersuchs.

## Betrieb

SupervisorPID19912 undWorkerPID25256. Prozessdienststart mitBasis-Python und
denselbenvenv-site-packages. independence.json bestätigt in_job=false.
Sourcehashes wurden vorDatengenerierung geprüft. WährenddesLaufs bleiben die
eingefrorenen Trainer-/Modell-/Datengenerierungsdateien unverändert.
Best- undLatestcheckpoints, Optimizer, RNG undSamplerposition werden gesichert.
STOP_REQUESTED wird an gemeinsamenUpdategrenzen geprüft. Supervisor stoppt bei
Deadlineüberschreitung oder20minfehlendemHeartbeat; kein automatischerNeustart.
AutomatischerSystemschlaf wird solange verhindert undbeimEndefreigegeben.
