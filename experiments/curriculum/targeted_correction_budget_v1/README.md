# Nachtlauf: Herkunft zusätzlicher BC-Korrekturen

Vorbereitung für den 17./18.11.2026. Ein wissenschaftlicher Start ist separat.
Absolute Deadline: **18.11.2026, 09:00 Europe/Berlin**. Der Worker beendet
seine Arbeit spätestens um 08:58; der Supervisor erzwingt das Ende seines
eigenen Prozessbaums. Keine Neustarts, Budgetverlängerungen oder Abschaltung
des PCs. Ein abgeschlossener Lauf endet auch vor der Deadline.

## Forschungsfrage und Hypothese

Verbessert die Herkunft neuer Expertenlabels aus tatsächlich durch BC
erreichten Zuständen den stabilen Dreierturm-Erfolg gegenüber zusätzlichen
Expertenbeispielen derselben Phase aus gewöhnlichen Expertenabläufen?

**Hypothese:** Bei gleicher Zahl neu verwendeter Labels, identischen Updates
und gleicher Ausführung profitieren BC-Modelle stärker von Korrekturen nach
einem BC-Präfix als von neuen Beispielen nach einem Experten-Präfix.
Ein Null- oder Negativbefund grenzt den Nutzen gezielter Erhebung ein.
Es wird kein bestimmter morgiger Erfolgswert vorausgesetzt.

| Arm | Zusätzliche Trainingsdaten | Ausführung beim zweiten Anfahren |
|---|---|---|
| baseline | keine zusätzlichen Updates | ursprüngliches B |
| replay | bisherige Phase-0-Daten | fortgesetzte Aktion + Abschluss |
| standard | neue Phase-0-Labels nach Experten-Präfix | neue Aktion + Abschluss |
| targeted | neue Phase-0-Labels nach BC-Präfix | neue Aktion + Abschluss |

Primärer Vergleich: **targeted gegen standard**. Targeted gegen Replay
prüft zusätzlichen Nutzen gegenüber Weitertraining. Beide neuen Datenarme
gegen Replay zeigen den Nutzen zusätzlicher Daten im jeweiligen Kontext.
Dies ist weder ein Reihenfolge-Curriculum noch Critic-Training.

## Gepaarte Datenerhebung und gleiches Labelbudget

Drei vorab festgelegte, disjunkte Erhebungsblöcke enthalten jeweils 120
Trainings- und 30 Validierungsszenen. Ein BC-Ausgangsmodell pro Familie wird
vorab zyklisch aus den drei B-Seeds zugeteilt. Alle Trainingsmodelle erhalten
anschließend denselben gepoolten Datensatz des jeweiligen Blocks.

Für jede Szene werden zwei echte Abläufe mit identischem Anfangszustand
erzeugt. Targeted benutzt B bis zum zweiten Anfahren, dann den unveränderten
Experten für Phase 0. Standard benutzt denselben Experten bereits im Präfix
bis zu genau dieser Phase und danach dieselbe Expertenregel. Keine
Teleportation, zusätzliche Störung oder Übernahme eines Teststarts.

Nur gemeinsam geeignete Szenen werden in beide neuen Datenarme aufgenommen.
Fehlt das zweite Anfahren oder endet eine Expertenphase nicht rechtzeitig,
wird die Familie für beide Arme verworfen und protokolliert. Keine
Ersatzstarts. Mindestabdeckung: 60 Trainings-/15 Validierungsfamilien je
Block, sonst wissenschaftlicher Abbruch statt Nachsammeln.

Pro Paar werden min(32, Länge beider Phasen) unterschiedliche Frames jeder
Phase verwendet: immer das terminale Abschlusslabel und deterministisch
gleichmäßig verteilte nichtterminale Frames. Damit stimmen die Zahl neuer
Trainingslabels, die Familiengewichte im Sampler und die Abschlusslabelquote
zwischen Standard und Targeted exakt überein. Derselbe neue Batchindex
bezeichnet dieselbe Familie und dieselbe relative Auswahlposition.

**Das ist ein gleiches Budget verwendeter Lernlabels, kein behauptetes gleiches
Erhebungsbudget.** Vollständige Phasen werden zur Ausführung abgefragt; der
Experten-Präfix benötigt weitere Expertenaufrufe. Alle erzeugten Labels,
Expertenaufrufe und Erhebungszeiten werden separat berichtet. Der Vergleich
gilt zunächst für BC-erreichbare Familien und diese festgelegte Frameauswahl.

## Lernen und Ausführung

Alle drei unveränderten B-30k-Ausgangsmodelle werden in allen drei Datenblöcken
untersucht. Je Quelle werden eine Aktions- und eine Abschlusskopie mit jeweils
5.000 Updates trainiert: 54 Komponenten / 270.000 Komponentenupdates.
Architektur, vollständiger AdamW-Ausgangszustand, LR 1e-4, Decay 1e-6,
Gradientengrenze 10 und Abschluss-BCE-Koeffizient 0,1 bleiben wie zuvor.
Es werden dieselben bereits geprüften Trainings- und Kompositionsfunktionen
des abgeschlossenen Korrekturversuchs importiert, nicht verändert.

Jeder Batch enthält 32 identische alte Beispiele und 32 zusätzliche Beispiele;
Replay nutzt in der zweiten Hälfte ebenfalls alte Beispiele. Standard und
Targeted verwenden exakt dieselben Zufallsindizes in ihren gepaarten Arrays.
Die datenabhängigen positiven BCE-Gewichte sind durch die gepaarten
Labelzahlen zwischen diesen beiden Armen identisch. Nur Phase 0 wird
trainiert; Phasen 1–6 müssen bitgleich zu B bleiben.

Alle drei fortgesetzten Arme verwenden dieselbe Zusammensetzung aus zwei
Kopien, ausschließlich bei Platzierung 2 / Phase 0 / außerhalb des Rückzugs.
Sonst bleibt B. Guard, Clock-Korrektur und 0,8-Abschlussschwelle bleiben gleich.
Die Methode benötigt privilegierte Simulatorzustände und den bestehenden
Sequencer. Eine einzelne gemeinsame MLP oder autonome Phasenplanung wird
nicht behauptet. Dieses Experiment isoliert keine Aktion/Abschluss-Interaktion.

## Endpunkte und Auswertung

Alle 54 Komponenten werden vor dem ersten neuen Bestätigungstest vollständig
eingefroren. Fester Endpunkt Update 5.000; Loss und Validierung dienen der
Diagnose, nicht der Checkpoint-Auswahl. Kein Nachtrainieren nach Testeinsicht.

- Entwicklung: dieselben bereits geöffneten 20 Szenen, separat berichten.
- Bestätigung: 100 neue, gemeinsame Szenen über alle Modelle und Datenblöcke.
- Primär: vollständiger Dreierturm über 50 strenge Gültigkeitsframes ohne
  Fingerkontakt, maximal 1.000 Schritte. Alle Starts bleiben im Erfolgsnenner.
- Pro Datenblock und Modellseed: Erfolgsrate und gepaarte Gewinne/Verluste
  Targeted gegen Standard sowie gegen Replay/B.
- Beschreibendes praktisches Kriterium: im Mittel mindestens +5 Prozentpunkte
  gegenüber Standard und positive Richtung in allen drei Datenblöcken.
  Das ist kein Signifikanztest und keine allgemeine Robustheitsgarantie.
- Drei Modellseeds und drei Datenblöcke sind getrennte Variationsquellen.
  900 Targeted-Modell/Daten/Szenenpaare teilen **100** Bestätigungsszenen;
  weder 900 unabhängige Szenen noch neun unabhängige Modellinitialisierungen.
- Baseline-Episoden werden pro Modell/Szene einmal ausgeführt und in den
  Datenblocktabellen wiederverwendet; nicht als neue Replikate zählen.

Der Lauf schreibt Split-/Budgetaudits, Rohphasen und Auswahlindizes,
Samplingpläne, volle Checkpoints/Optimizer/RNG, Quellen-Hashes,
Paket-/GPU-Umgebung, Offlinewerte, Einzelepisoden, Paarvergleiche und
Abbildungen. Bestätigungsszenen gelten nach Ausführung als geöffnet.
Keine Veröffentlichung und kein Überschreiben bisheriger Ergebnisse.

## Befehle

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/targeted_correction_budget_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/targeted_correction_budget_v1/pipeline.py prepare --output praxis/results/curriculum/targeted_correction_budget_v1/night_20261117
# Vollständigen wissenschaftlichen Lauf erst nach Startauftrag:
powershell -NoProfile -File experiments/curriculum/targeted_correction_budget_v1/start.ps1
# Kurze inkrementelle Kontrolle:
praxis/.venv/Scripts/python.exe experiments/curriculum/targeted_correction_budget_v1/monitor.py --output praxis/results/curriculum/targeted_correction_budget_v1/night_20261117
```

Technischer Smoke: `prepare --smoke` in einem separaten Ordner, danach `run`.
Nur ein Parent, ein Datenblock, vier Updates je Komponente und bekannte
technische Auswertungsszenen. Wissenschaftliche Bestätigung bleibt geschlossen.
Voraussichtlich einige Stunden für den Vollversuch; diese Planung wird nach
dem Smoke gemessen konkretisiert. Bei Zeitablauf bleiben Teilresultate erhalten,
werden als unvollständig berichtet und nicht durch kürzere Endpunkte ersetzt.
