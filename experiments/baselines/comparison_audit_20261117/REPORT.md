# Baselineprüfung · 17.11.2026

## Befund

Für kontrollierte BC-/Curriculum-Fragen sind reproduzierbare interne
Baselines vorhanden. Eine qualifizierte, von zufälligen Gewichten aus
ausschließlich mit RL gelernte Dreierturm-Baseline wurde im geprüften
Bestand nicht gefunden. Die vorhandenen Actor-Critic-Arme beginnen mit
BC-Actors und ersetzen diese Referenz nicht.

Die Prüfung ist unabhängig vom aktiven Nachtlauf. Keine seiner Quellen,
Konfigurationen, Daten, Checkpoints oder Monitoringregeln wurden verändert.
Kein Simulator, Training oder GPU-Modell wurde für diese Prüfung gestartet.

## Was tatsächlich geprüft wurde

`audit.py` prüft ohne Torch-/Simulatorimport den abgeschlossenen
`praxis/results/curriculum/abc_comparison_20261112/ready_001`:

- Worker und Supervisor COMPLETE, wissenschaftlicher Lauf, feste 30k-Endpunkte.
- Alle neun erhaltenen Endcheckpoints stimmen mit ihren eingefrorenen SHA-256 überein.
- 1.260 Einzelresultate stimmen mit Panel- und Gesamtsummen überein.
- Pro Panel stimmen Szenenbereiche und Anfangszustandshashes zwischen allen
  Armen und Modellseeds überein; verschiedene Szenen-IDs besitzen verschiedene
  physikalische Anfangszustände.
- Alle Erfolgsflags entsprechen mindestens 50 gültigen Frames.
- Der gespeicherte B/C-Audit bestätigt gleiche Initialisierung und gleiches
  Batch-Multiset für jeden Seed. Der gelesene Samplingcode trennt Exposition
  und Reihenfolge entsprechend.

Ergebnis und gehashte Eingänge: [evidence.json](evidence.json).
Reproduktion: `praxis/.venv/Scripts/python.exe experiments/baselines/comparison_audit_20261117/audit.py`.
Das ist eine aktuelle Artefakt-/Konsistenzprüfung, keine neue Auswertung im Simulator
und kein vollständiger Beweis aller historischen Ausführungsschritte.

## Vorhandene Baselines

Erfolge je 100 gemeinsame neue Dreierturm-Starts, getrennt nach Trainingsseed:

| Arm | Tatsächliche Definition | Seed 1 | Seed 2 | Seed 3 |
|---|---|---:|---:|---:|
| A | Phasenausgewogenes Standard-BC, voller Datenpool ab Beginn | 40 | 28 | 26 |
| B | BC mit exakt den C-Minibatches, global durchmischt | 48 | 56 | 50 |
| C | BC mit geordneter X→XY→XYZ-Präsentation | 52 | 42 | 46 |

Alle verwenden ursprüngliche Zweier-Demonstrationen, dieselbe PhaseNet,
dasselbe Budget, identische Clock-Korrektur und denselben Ausführungsrahmen.
A ist phasenausgewogen, nicht frameuniform über den gesamten Datensatz.
B/C beginnen frisch mit denselben Initialgewichten; sie sind keine
Fortsetzung eines mit zusätzlichen Korrekturen verbesserten Modells.

- **A gegen B:** veränderte Datenexposition/Samplinggewichtung.
- **B gegen C:** Reihenfolge bei identischem Batch-Multiset.
- **A gegen C:** Gesamtwirkung dieses konkreten Curriculumprogramms.

B ist in allen drei Seeds besser als A. C übertrifft B nur in einem Seed.
Ein konsistenter Nutzen dieser geordneten Präsentation ist nicht belegt.
Das ist kein Nachweis gegen Curriculum Learning allgemein. Die Achsenheuristik
ist eine operationalisierte Reihenfolge, keine validierte Skala der Aufgabenschwierigkeit.

Die 100 Starts werden über neun Modelle geteilt; das sind weder 900 unabhängige
Szenen noch neun unabhängige Initialisierungen pro Methode. Die Werte gehören
zu diesem Panel und dürfen nicht als direkte Rangliste neben die früheren
50-Szenen-Korrekturergebnisse oder den neuen Nachtlauf gestellt werden.

**Bewertung:** brauchbare, erhaltene und nachvollziehbare interne Referenzen;
kein Nachweis optimaler Hyperparameter, vollständiger Ausoptimierung oder
einer starken allgemeinen State-of-the-Art-Baseline. Ein guter Kontrollarm
muss nicht selbst gewinnen. B verhindert insbesondere, dass ein Gewinn durch
andere Datenhäufigkeiten irrtümlich der Reihenfolge zugeschrieben wird.

## Warum „nur Curriculum Learning“ präzisiert werden muss

Curriculum beschreibt die Präsentation von Trainingsbeispielen oder Aufgaben,
benötigt aber einen zugrunde liegenden Lerner. Hier ist das **BC + Curriculum**.
Die vorhandene Definition entspricht einer veränderlichen Trainingsverteilung,
wie sie [Bengio et al. (2009)](https://icml.cc/2009/papers/119.pdf) beschreiben.

Für unsere IL-Methodenfrage ist die kompakte Vergleichsgruppe sinnvoll:

1. BC ohne zeitliches Curriculum als Hauptreferenz.
2. BC + Curriculum ohne zusätzliche Korrekturkomponente als Methodenvergleich.
3. RL von zufälliger Initialisierung als zusätzliche Systemreferenz.

Die expositionsgleiche B-Kontrolle bleibt beim Curriculumvergleich nötig.
Wenn beide gewünschten neuen Ansätze ohne Demonstrationen gemeint sind,
ist die passende Alternative **SAC gegen SAC + Curriculum**. Das untersucht
Curriculum innerhalb von RL und ersetzt den kontrollierten BC-Vergleich nicht.
Ein Programm „zwei Würfel, danach drei“ ändert auch die Aufgabenexposition;
für eine isolierte Aussage zur Reihenfolge wäre eine Kontrolle mit denselben
geplanten Aufgabenstarts in gemischter Reihenfolge zusätzlich erforderlich.
Die dadurch tatsächlich erzeugten RL-Transitionen müssen nicht identisch sein.

## Stand einer echten RL-Referenz

Die untersuchte Familie `experiments/critic/critic_warmstart_20261104` lädt
vorhandene BC-Parents. `Learner` kopiert diesen Actor und bewahrt seine
gelernte Abschlussausgabe als Referenz. Das gilt auch für den Arm ohne
direkten BC-Lossterm. Er ist deshalb **RL-Finetuning eines IL-Actors**.
Der historische Kollaps auf 0/60 ist kein Ergebnis einer RL-von-null-Baseline
und belegt keine allgemeine Unfähigkeit von RL zum Stapeln.

Im aktuellen `praxis/.venv` sind Stable-Baselines3, Gymnasium, Gym, SB3-Contrib
und RL-Games nicht installiert; robosuite 1.5.1 und Torch sind vorhanden.
In den geprüften Baseline-/Critic-/Praxis-Einstiegen wurde kein fertiger
SAC-/PPO-von-null-Vergleich gefunden. Eine Paketinstallation allein würde
weder Implementierung noch trainierte Referenz ersetzen. Die aktive Umgebung
wurde nicht verändert.

**Vorschlag für den späteren RL-Aufbau: SAC mit einer etablierten Implementierung.**
SAC ist ein passender Kandidat für kontinuierliche Aktionen, kein garantierter
Gewinner für diese Aufgabe: [Originalarbeit](https://proceedings.mlr.press/v80/haarnoja18b.html),
[SB3-SAC-Dokumentation](https://stable-baselines3.readthedocs.io/en/master/modules/sac.html).
Auch robosuite verwendet SAC in seinem offiziellen, historischen
[Benchmark](https://robosuite.ai/docs/algorithms/benchmarking.html); dessen
Resultate sind keine Messwerte für unseren angepassten Dreierturm.

Für die Bezeichnung „nur RL“ müssen Actor und Critic zufällig beginnen,
Replay ausschließlich aus eigenen Interaktionen stammen und Demonstrationen,
BC-Loss, BC-Initialisierung sowie BC-gelernte Abschluss-/Rückzugskomponenten
ausgeschlossen sein. Ein fester physikalischer Controller oder offengelegter
Aufgabenkoordinator kann Teil des Rahmens bleiben; sein Beitrag muss dann
für alle verglichenen Systeme klar dokumentiert werden.

## Konkrete Hürden vor einem fairen RL-Training

1. **Erfolg und Reward:** Die lokale `StackFour`-/`StackThree`-Implementierung
   belohnt nativ `stable_steps >= int(0.5 * control_freq)`. Bei den verwendeten
   20 Hz sind das 10 Frames. Unser Haupttest fordert 50 Frames und zusätzlich
   keinen Greifer-/Fingerkontakt. Die native Prüfung verbietet lediglich
   einen erkannten Griff. Native Reward-/Erfolgsflags sind daher keine
   austauschbaren Auswertungsziele. Das muss ein separater RL-Adapter auflösen.
2. **Exploration:** Der lokale Reward ist binär. Das Überschreiben von
   `reward()` implementiert keine dichte Formung, auch nicht durch bloßes
   Setzen von `reward_shaping=True`. Ein vorab festgelegter, unveränderlicher
   Shapingreward wäre weiterhin RL; seine Zusatzannahmen und Kosten müssten
   offengelegt werden. Ein kurzer erfolgloser Sparse-Reward-Lauf wäre allein
   keine überzeugend starke Referenz.
3. **Ausführungsrahmen:** Aktuell gibt es sieben Phasenköpfe, vorgegebene
   Phasen-/Paarreihenfolge, gelernte Abschlüsse, einen Rückzugs-Guard, begrenzte
   Release-Clock und fest null gesetzte Rotation. Ein SAC-Actor darf nicht
   heimlich den gelernten BC-Abschluss weiterverwenden. Ein flacher RL-Actor
   ohne diese Struktur prüft dagegen ein anderes Gesamtsystem. Vor Aufbau
   muss deshalb feststehen, ob wir Lernregeln unter gemeinsamem Rahmen oder
   vollständige Systeme vergleichen.
4. **Beobachtung und API:** Die bisherigen zehn Actorfeatures enthalten
   relativ zum Phasenanker verschobene EEF-Position, Quaternion, Greiferzustand
   und Phasenzeit; die Phase wählt den Kopf. Ein RL-Markovzustand kann weitere
   Informationen benötigen. Informationszugang, Aktionsabbildung, Normierung,
   Terminierung versus externe Trunkierung und Zeitlimitbehandlung sind vor
   dem Training technisch zu validieren. Größere RL-Beobachtungen sind als
   Unterschied auszuweisen, nicht als isolierter Lernregelvergleich auszugeben.
5. **Kein willkürlich schwaches Budget:** BC-Updates sind nicht mit RL-
   Umweltaktionen gleichzusetzen. Eigene Umweltinteraktionen, Expertlabels,
   Gradientenupdates, Evaluation, Tuning und Rechenzeit getrennt berichten.
   Ein separater einfacher RL-Funktionstest kann die Pipeline prüfen; dessen
   Gewichte dürfen nicht in die Dreierturm-Referenz übernommen werden, wenn
   diese ausdrücklich ohne Curriculum beginnen soll.

Diese Anforderungen stimmen mit den Hinweisen zur separaten Evaluation,
Wrapperkontrolle und Implementierungsprüfung in den
[offiziellen SB3-Empfehlungen](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html)
überein. Die lokale Erfolgskriterium-Differenz stammt aus unserer Codeprüfung,
nicht aus einer Behauptung über Standard-robosuite.

## Empfohlene nächste Entscheidung

Die vorhandenen A/B/C-Modelle als feste interne Referenzen erhalten. Für den
aktuellen Methodenbeitrag insbesondere B und einen budgetgleichen
Weitertrainingsarm verwenden; neue Korrekturdaten und mehr Rechenaufwand
nicht dem Curriculum zuschreiben. Eine neue allgemeine Vergleichsrunde
verwendet gemeinsame frische, vorher geschlossene Teststarts und mindestens
drei Trainingsseeds pro Methode, mit Ergebnisdarstellung je Seed.

Eine reine SAC-Baseline als getrenntes Vorhaben mit festem Zustands-/Aktions-
und Rewardvertrag, technischer Validierung und vorab festgelegtem Budget
aufbauen. Falls Curriculum als zweiter demonstrationsfreier Ansatz gewünscht
ist, denselben SAC-Kern mit präregistriertem Curriculum ergänzen. Falls es um
IL geht, BC + Curriculum beibehalten und bei Bedarf ein tatsächlich begründetes
Schwierigkeitscurriculum gesondert entwickeln. Keine neue Trainingsfreigabe
oder Änderung des laufenden Versuchs folgt aus dieser Bestandsprüfung.
