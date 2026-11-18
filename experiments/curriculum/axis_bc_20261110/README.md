<!-- current-bc-status:start -->
> Stand 12.11.2026: **Abgeschlossen**. Originaler B/C-Vergleich; Ausführung damals ohne spätere Zeitkorrektur. [Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.
<!-- current-bc-status:end -->

# BC mit Bewegungs-Curriculum: X → XY → XYZ

## Fragestellung und Grenze

Hilft eine strukturierte Reihenfolge bestehender Demonstrationsframes beim
Erlernen der Stapelbewegung? Verglichen werden identisch initialisierte Policies
mit exakt demselben Multiset aus Minibatches. Nur deren Reihenfolge unterscheidet
sich. Es gibt keinen Critic, keine neuen Expertenlabels und keine Onlineupdates.

Dies ist ein **Offline-Curriculum nach Bewegungsrichtung**. X-lastige Bewegung ist
nicht automatisch leicht. Es werden weder Achsen der Simulation gesperrt noch
künstliche X-only-Aufgaben oder Demonstrationen erzeugt. Die Ergebnisse gelten
zunächst für diese konkrete Reihenfolge. Ein Curriculum über Startzustände,
Zielentfernung, Kontaktschwierigkeit oder einzelne Manipulationsaufgaben wäre ein
separater Folgeversuch.

## Daten und Modell

Verwendet werden die vorhandenen 200 erfolgreichen programmierten
Zwei-Würfel-Demonstrationen mit dem bestehenden Split ganzer Trajektorien:
180 Training / 20 Validierung, 27.322 / 2.974 Frames. Beim Vorbereiten werden die
zwischengespeicherten Arrays vollständig aus dem Original rekonstruiert und auf
exakte Gleichheit geprüft. Originaldaten, Split, Quellcode und Konfiguration
werden über SHA-256 eingefroren. Vor jedem Start werden die Hashes geprüft.

Die vorhandene PhaseNet bleibt erhalten: zehn Zustandsmerkmale, sieben
Phasenköpfe, Breite 128, gelernte XYZ-/Greiferaktionen und Phasenabschluss.
Die drei Rotationsausgaben bleiben wie bisher null. Beide Arme starten für
Seeds 1/2/3 frisch mit denselben Gewichten, ohne historische Parent-Checkpoints.
Der bestehende geometrisch abgesicherte Aufgabenkoordinator bleibt identisch.
Phasenreihenfolge und Paarwahl sind vorgegeben; ein autonom gelernter Planer
wird nicht behauptet. Die Daten und Auswertung nutzen privilegierte
Simulationszustände, keine Vision.

## Curriculum und Kontrolle

Die Richtung wird aus den **unveränderten Demoaktionen** bestimmt. Bei normierten
Aktionen in [-1,1] ist die vorab festgelegte Schwelle 0,1:

| Stufe | Updates | Fokuspool | Anteil im Batch |
|---|---:|---|---:|
| X | 1–5.000 | abs(X)>0,1 und abs(Y),abs(Z)≤0,1 | 75 % |
| XY | 5.001–12.000 | max(abs(X),abs(Y))>0,1 und abs(Z)≤0,1 | 75 % |
| XYZ | 12.001–30.000 | alle Trainingsframes, einschließlich Greifen und Halten | 100 % |

In den ersten beiden Stufen kommen 25 % aus allen Trainingsphasen hinzu,
damit Greifen, Anheben und Absetzen von Anfang an vertreten sind. Innerhalb
jedes Pools wird gleichmäßig über vertretene Phasen und dann über deren Frames
gezogen. X ist Teilmenge von XY; XYZ bezeichnet den ganzen Pool und verlangt
keine gleichzeitige Bewegung entlang aller Achsen. Die 0,1-Schwelle ist eine
Aktionsschwelle, keine gemessene Wegstrecke oder Erfolgswahrscheinlichkeit.

Für jeden Seed wird der komplette Plan mit 30.000 Batches à 64 Frames vorab
erzeugt. `curriculum` arbeitet ihn geordnet ab. `mixed` verwendet eine feste
zufällige Permutation derselben Batches. Damit stimmen die Häufigkeiten jedes
Trainingsframes exakt überein. Kontrollarm und Curriculum haben dieselben
innerhalb eines Batches gemischten Beispiele. Der Kontrollarm ist eine
expositionsgleiche BC-Kontrolle und keine exakte Wiederholung eines alten
Uniform-BC-Experiments.

Stufenwechsel sind für diesen ersten Versuch **fest vorgegeben**, nicht von
einem adaptiven Erfolgsgate abhängig. Das isoliert die Reihenfolge bei exakt
gleicher Datenexposition. Ein adaptives Curriculum kann danach getrennt geprüft
werden. Die konkreten Grenzen sind Pilotentscheidungen, keine optimierten Werte.

Identische Lernregel: MSE aller vier aktiven Aktionen + 0,1 × BCE des
Phasenabschlusses für Phasen 0–5; positive BCE-Gewichte allein aus Trainingsdaten;
AdamW, LR 1e-4 mit 500 Updates Warmup, Weight Decay 1e-6, Gradient Clip 10.

## Messung

Nach 1.000 / 5.000 / 12.000 / 20.000 / 30.000 Updates: Offlinefehler und je 20
gleiche neue Entwicklungsstarts für zwei und drei Würfel auf jedem Trainingsseed
und Arm. Startzustandshashes müssen zwischen Modellen übereinstimmen. Die
Primärgröße ist der vollständige stabile Dreierturm; Zweierstapel, Greifen,
Anheben, Phasenfehler und Aktions-MSE dienen der Diagnose. `lift_seen` ist nur
eine Höhenbeobachtung, kein Nachweis eines stabilen Griffs. `first_pair_valid_seen`
ist eine Momentaufnahme, kein eigener bestätigter Stapelerfolg.

Erfolg erfordert 50 aufeinanderfolgende gültige Frames: korrekte Geometrie,
Würfelkontakte, kein Greifer-/Fingerkontakt und geringe Geschwindigkeiten gemäß
vorhandener physikalischer Prüfung. Horizonte: 500 / 1.000 Steuerschritte.

Der feste letzte Checkpoint aller sechs Modelle wird verwendet. Erst nach
vollständigem Training kann `test` alle Modelle einfrieren und je 100 andere
Starts für zwei und drei Würfel auswerten. Endtests werden nicht zur Auswahl
verwendet. Ergebnisse pro Trainingsseed sowie gepaarte Szenenergebnisse berichten;
300 Szenen sind keine 300 unabhängigen Trainingsreplikate. Keine automatische
Behauptung eines Curriculum-Gewinns aus geringerem Loss. Vergleichbare Budgets:
30.000 Optimizerupdates und 1.920.000 gezogene Frames pro Modell, etwa 70,27
Framepass-Äquivalente; dies sind keine vollständig durchlaufenen Epochen.

## Bedienung

Alle Befehle im Projektstamm. Das Setup startet standardmäßig keinen langen Lauf.

```powershell
$python = '.\praxis\.venv\Scripts\python.exe'
$script = '.\experiments\curriculum\axis_bc_20261110\train.py'
$run = '.\experiments\curriculum\axis_bc_20261110\ready_001'
& $python $script prepare --output $run
& $python $script smoke --prepared $run --output '.\experiments\curriculum\axis_bc_20261110\smoke_001' --device cuda
& $python $script run --output $run --device cuda
& $python $script status --output $run
& $python $script test --output $run --device cuda
```

Ein bereits vorhandenes `ready_001` nicht erneut vorbereiten. Für einen neuen
Versuch einen neuen Ordnernamen verwenden. `run` arbeitet im Vordergrund. Der
achtstündige Grenzwert umfasst Training und Entwicklungsrollouts gemeinsam;
ein anschließender Endtest hat ein eigenes achtstündiges Maximum. Kein
automatischer Hintergrundstart, Neustart oder Resume. Ein Betriebssystemstillstand
kann vom kooperativen Zeitlimit nicht beendet werden.

`STOP` im Laufordner beendet die Arbeit bei der nächsten Update-Runde oder dem
nächsten Simulationsframe. Alle bis dahin erreichten Modellstände werden gespeichert.
Bei normalem Betrieb werden Checkpoints mindestens alle 1.000 Updates gespeichert,
Status und neue Metriken alle 100 Updates. Status benennt Initialisierung,
Training und Evaluation getrennt. Der leichte Statusbefehl importiert keine
ML-Bibliotheken, prüft unter Windows Prozessstartzeit/PID und liest Metriken ab
dem letzten Byteoffset. Nach 15 Minuten ohne Statusänderung wird gewarnt;
eine Warnung beendet keinen Prozess. Ein unerwartet verschwundener aktiver
Prozess wird als Fehler gemeldet. Technische Läufe und unvollständige Panels
sind keine wissenschaftlichen Ergebnisse.

Technischer Smoke: Seed 99, sechs Updates pro Arm, je 20 Simulationsframes auf
zwei und drei Würfeln, strikt separater Output. Er validiert den Ausführungspfad,
keine Lernleistung. `test_curriculum.py` prüft insbesondere gleiche Datenexposition,
Reproduzierbarkeit, fehlende Pools, nichtendliche Verluste, Stopps und Splits.

`source_snapshot/`, `provenance.json`, `data_audit.json`, gespeicherte Samplepläne,
`metrics.jsonl`, Status und alle Auswertungen machen den Lauf nachvollziehbar.
Checkpoints enthalten Modell und Optimizer; die Samplepläne speichern die
vollständige Reihenfolge. Ein exakter Resume ist weder implementiert noch
behauptet. Bestehende Versuche werden nicht verändert.
