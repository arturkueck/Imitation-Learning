# Versuchsprotokoll: Zweier-BC → Dreierturm mit IL-informiertem Critic

**Status: ZUR FREIGABE** · Entwurf N1-6 vom 19.11.2026 · Version `protocol_v1-entwurf`

Dieses Dokument ist ein Entwurf. Es gibt nichts frei und startet keine Läufe. Optimizerupdates benötigen weiterhin die Häkchen im [Nachtplan](NACHTPLAN.md#freigaben). Bis zur Freigabe durch den Nutzer kann jede Festlegung geändert werden. Nach der Freigabe sind Änderungen nur noch als neue, begründete Version möglich. Es gelten [AGENTS.md](../../../AGENTS.md), [Agend.md](../../../Agend.md) und [experiments/AGENTS.md](../../AGENTS.md).

Grundlage: Exposé [proposal.tex](../../../latex/projektarbeit_proposal/v2/proposal.tex), [Splitmanifest](splits.json), [Kalibrierung](CALIBRATION.md), eingefrorene Regel [difficulty_v1.json](difficulty_v1.json) (SHA-256 `e38af330…3945`, [Hashdatei](difficulty_v1.sha256)), [Panelzuordnung](difficulty_panels_v1.json) und der in N1-4 gemessene Durchsatz.

## 1. Methodenfrage und Hypothese

*Verbessert ein Critic, der auf den Ausgängen eigener Dreierversuche der BC-Policy vortrainiert wurde, den Dreierturm auf unbekannten Starts? Dabei gibt es keine Dreier-Demonstrationen und keine Experteneingriffe in Dreier-Situationen.*

Hypothese des Exposés: Bei gleicher Zahl eigener Onlineversuche erreicht AC-IL eine höhere Dreier-Erfolgsquote als AC-neu. Beide übertreffen BC. Der Pilot N3-1 ist der **erste wissenschaftliche Lauf** dieses Vorhabens. Er schätzt Effekt und Streuung und bestätigt die Hypothese nicht (AGENTS.md §1).

## 2. Arme

Alle Arme starten je Trainingsseed bei demselben eingefrorenen Standard-BC-Modell **A** (Seeds 1, 2, 3, fester Endpunkt nach 30.000 Updates, SHA-256-geprüft über `registry.frozen_abc_a()`). Modelle mit Dreier-Expertenkorrekturen sind ausgeschlossen.

| Arm | Actor | Critic-Initialisierung | Online-Training |
|---|---|---|---|
| **BC** | A-Parent, unverändert | – | keines |
| **AC-neu** | Kopie des A-Parents | zufällig, Initialisierungsseed `c_p` | gleiche Bindung, gleiches Budget, gleiche Interaktionsszenen |
| **AC-IL** | Kopie des A-Parents | gleicher Initialisierungsseed `c_p`, danach Vortraining auf den Critic-Daten **desselben** Parents (N2-2) | wie AC-neu |

- **Isolierte Größe:** Zwischen AC-IL und AC-neu unterscheidet sich nur das Critic-Vortraining. Actor, Bindung, Replayregel, Explorationsrauschen, Updatezahlen und Interaktionsszenen sind gleich. Beide Arme verwenden je Parent denselben RNG-Strom für Exploration und Minibatches, soweit der Ablauf identisch ist.
- **Replay (Vorschlag):** Beide AC-Arme spielen ausschließlich ihre eigene Onlineerfahrung ab. Die Critic-Daten wirken in AC-IL nur über die Initialisierung. Damit bleiben Rückmeldung und Zahl der Versuche im Onlineteil gleich. Die 300 Vortrainingsepisoden je Parent werden als Zusatzkosten von AC-IL ausgewiesen (Exposé, Schritt 3). Als Alternative könnten beide Arme die Critic-Daten im Replay erhalten. Dann prüft der Vergleich nur die Initialisierung bei gleichem Datenzugang. Die Wahl ist eine Nutzerentscheidung (§12).
- **Trainierte Teile:** XYZ und Greiferaktion des Bewegungskopfs. Rotation bleibt null. Phasen- und Abschlussentscheidungen trifft weiterhin eine eingefrorene Kopie des Parents mit unverändertem Schwellwert und unveränderter Uhrkorrektur. Sequencer, Rückzugscontroller und Platzierungsreihenfolge bleiben unverändert.
- **Zuordnung des Critics:** Ein Critic je Parent, vortrainiert nur auf den 300 Episoden dieses Parents. Die drei Parents bleiben dadurch getrennte Lernverläufe. Die drei Critic-Datensätze verwenden dieselben 300 Familien und sind deshalb keine unabhängigen Szenenstichproben.

## 3. Seeds, Szenen und Splits

| Art | Werte | Bemerkung |
|---|---|---|
| Trainingsseeds / unabhängige Parent-Initialisierungen | A 1, 2, 3 | genau drei je Arm im Pilot, kein Nachschieben |
| Critic-Initialisierung `c_p` | `c_p = 7100 + p` | in AC-neu und AC-IL desselben Parents gleich |
| Exploration und Minibatches | `r_p = 7200 + p` | in AC-neu und AC-IL desselben Parents gleich |
| Szenenseeds | [splits.json](splits.json), neue Bereiche unten | Seednummern sind Kennungen, keine Schwierigkeitsskala |

Die Splits aus N1-2 und die Panels aus N1-5 werden unverändert übernommen: Kalibrierung 100, Critic-Daten 300, Validierung regulär 100 und schwierig 50, Test regulär 150 und schwierig 75, Zweierpanel 100. Für die Onlinephase werden drei neue Bereiche aus dem unvergebenen Rest `2100003250–2100099999` vorgeschlagen. Nach der Freigabe sind sie versioniert in `splits.json` nachzutragen.

| Neuer Split | Bereich (inklusive) | Familien | Zweck |
|---|---|---:|---|
| `online_interaction` | 2100003250–2100003649 | 400 | Onlineversuche im Pilot. Aufsteigende Reihenfolge, je Lauf jede Familie genau einmal. Identisch für beide AC-Arme und alle Parents. |
| `constraint_development` | 2100003650–2100003669 | 20 | Technische Stabilitätsprüfung der Bindung in N2-3, nur gegen den eigenen Parent |
| `smoke_interaction` | 2100003670–2100003689 | 20 | Onlineversuche des technischen Smokes N2-3 |

Der Rest ab 2100003690 bleibt unvergeben. Das Panel „schwierig“ bezeichnet lange Transportwege nach `difficulty_v1` innerhalb der regulären Startverteilung. Es ist kein OOD-Panel. In der Kalibrierung war seine Erfolgsquote am niedrigsten, die Beziehung war aber nicht monoton (CALIBRATION.md). Die Testpanels bleiben bis zur einmaligen Öffnung nach `MAIN_PROTOCOL.md` geschlossen. Sie werden weder ausgerollt noch für Entscheidungen verwendet.

## 4. Aufgabe, Reward und Datenvertrag

- **Erfolg:** stabiler Dreierturm über 50 aufeinanderfolgende gültige Frames, wie in der Kalibrierung N1-4 (`calibration.py`). Horizont 1.000 Frames.
- **Reward:** 1 nur beim bestätigten Erfolg, sonst 0. γ = 0,995. Erfolg, Horizont und Rückzugs-Timeout sind echte Enden der endlichen Aufgabe, dort wird nicht gebootstrapt. Ein Halt durch Deadline oder Infrastruktur ist kein Episodenende (§9).
- **Actor-Beobachtung:** unverändert wie beim A-Parent, also privilegierter Zustand mit Phaseneingabe und Uhrkorrektur.
- **Critic-Eingabe:** privilegierter Simulatorzustand mit Würfel- und Greiferlage, Stufe, Phase und Restzeit. Beide Critic-Varianten erhalten dieselbe Eingabe. Zukünftige Ereignisse werden nicht als Merkmal verwendet.
- **Übergänge (N2-1):** Je Frame werden Szenenseed, Parent, Framenummer, Stufe, Phase, Critic-Zustand, Actor-Eingabe, ausgeführte Aktion, Parentaktion, Folgezustand, Reward, Terminalflag, Endgrund und der beobachtete diskontierte Return gespeichert. Alle Episoden bleiben erhalten, auch Fehlschläge und nicht erreichte Phasen. Dazu kommen ein Manifest mit SHA-256 und Erfolgs- und Fehlerzahlen je Parent. Die Normierung wird nur aus Critic-Datenframes bestimmt und mit dem Critic eingefroren.

## 5. Budgets aus dem gemessenen Durchsatz

N1-4 ergab 951,9 Episoden pro Stunde, also etwa 3,78 s je Dreierepisode. Gemessen wurde mit einem Worker, CPU-Inferenz und neuer Simulation je Episode. Diese Rate gilt nur für eingefrorene Rollouts. Die Kosten von Critic- und Actorupdates sowie der Zweierdurchsatz sind **noch nicht gemessen**. N2-2 und N2-3 messen sie. Die Zeitangaben unten zählen daher nur die Rolloutzeit.

| Schritt | Episoden | Rolloutzeit (geschätzt) | Updates |
|---|---:|---:|---|
| N2-1 Critic-Daten: 300 Familien × 3 Parents | 900 | ≈ 0,95 h | 0 |
| N2-2 A-Rollouts auf der Validierung (regulär 300, schwierig 150) | 450 | ≈ 0,47 h | 20.000 Critic-Updates je Parent (Vorschlag) |
| N2-3 Smoke: Parent-Baseline 60, je Stufe 6 × (20 online + 20 Entwicklung) | 60 + ≤ 3 × 240 | ≤ ≈ 0,82 h | je Lauf 500 Critic- / 250 Actorupdates |
| N3-1 Online: 2 AC-Arme × 3 Parents × 400 | 2.400 | ≈ 2,52 h | je Lauf 10.000 Critic- / 5.000 Actorupdates |
| N3-1 Zwischenprüfung Runden 1–3: 6 Modelle × 3 × 100 regulär | 1.800 | ≈ 1,89 h | 0 |
| N3-2 Endprüfung Runde 4: 6 Modelle × (100 regulär + 50 schwierig) | 900 | ≈ 0,95 h | 0 |
| N3-2 Zweierpanel: 9 Modelle × 100 | 900 Zweier | nicht gemessen, ≤ ≈ 0,95 h falls ≤ Dreierdauer | 0 |

- **Online-Budget je AC-Lauf:** 4 Runden mit je 100 Episoden auf `online_interaction`. Nach jeder Episode folgen 25 Critic-Updates, nach jedem zweiten Critic-Update ein Actorupdate. Das ergibt 2.500 Critic- und 1.250 Actorupdates je Runde, also 10.000 und 5.000 je Lauf. Beide AC-Arme erhalten dieselben Episoden- und Updatezahlen. Die tatsächlichen Frames unterscheiden sich durch früheres Ende bei Erfolg und werden getrennt gezählt.
- **Critic-Vortraining (nur AC-IL):** 20.000 Updates auf den 300 Episoden des Parents, Batch 256, Lernrate 3·10⁻⁴. Es gibt kein Early Stopping und keine Abstimmung auf der Validierung. Diese Kosten werden getrennt ausgewiesen.
- **Pilot N3-1:** etwa 4,4 h Rolloutzeit zuzüglich der Updatezeit. Passt die nach N2-3 hochgerechnete Gesamtdauer nicht in ein Nachtfenster, wird nach Runde *k* exakt angehalten und in der nächsten Nacht fortgesetzt. Das Budget wird nicht stillschweigend gekürzt. Überschreitet die Hochrechnung zwei Nächte, entscheidet der Nutzer.
- Eine Parallelisierung über mehrere Worker ist zulässig, wenn Episodenergebnisse und Trajektorienhashes nicht von der Workerzahl abhängen. N2-4 prüft das per Test.

## 6. Critic-Akzeptanzkriterien (vor den Daten festgelegt)

Die Prüfung erfolgt je Parent mit dessen vortrainiertem Critic auf den A-Rollouts dieses Parents in der Validierung. Gemessene Returns und Erfolge stammen aus diesen Rollouts.

**Phasenpunkte.** Ausgewertet werden der erste Frame der Episode und der erste Frame jeder erreichten Kombination aus Stufe und Policy-Phase nach der eingefrorenen Phasenlogik des Parents. Erreicht eine Episode einen Phasenpunkt nicht, trägt sie dort nichts bei. Jeder Punkt hat einen eigenen Nenner. Der Criticwert ist `V(s) = min(Q1, Q2)(s, a_parent(s))`.

**Phasen-Baseline.** Sie sagt je Phasenpunkt die Erfolgsquote beziehungsweise den mittleren diskontierten Return voraus. Beide Werte stammen aus den Critic-Daten desselben Parents, unter den Episoden, die den Punkt erreichen. Fehlt ein Punkt in den Critic-Daten, gilt die Gesamtquote dieses Parents.

**Bestehensregel je Parent auf der regulären Validierung.** Alle Bedingungen müssen gelten:

1. **Endlich:** alle Vorhersagen endlich.
2. **Mehr als Phase:** Für Phasenpunkte mit mindestens 10 Erfolgen und 10 Fehlschlägen wird die AUC innerhalb des Punkts gegen den späteren Erfolg berechnet. Innerhalb eines Phasenpunkts liegt die Baseline konstant bei 0,5. Der nach Anzahl gewichtete Mittelwert muss **≥ 0,60** sein. Die untere Grenze des 95-%-Bootstrapintervalls muss **> 0,50** liegen. Es müssen mindestens zwei Punkte geeignet sein, sonst ist der Critic „nicht bewertbar“ und damit nicht bestanden.
3. **Besser als Phase:** Über alle Phasenpunkte gemittelt muss der quadratische Fehler gegen den diskontierten Return beim Critic kleiner sein als bei der Phasen-Baseline. Das 95-%-Bootstrapintervall der Differenz Critic − Baseline muss vollständig unter 0 liegen.
4. **Kalibrierung:** ECE ≤ 0,10 mit 10 gleich breiten Klassen des Vorhersagewerts auf [0, 1] gegen den beobachteten diskontierten Return, über alle Phasenpunkte.

Der Bootstrap verwendet 2.000 Ziehungen über Familien mit festem Seed 7300. Die schwierige Validierung wird mit denselben Kennzahlen getrennt berichtet. Sie entscheidet nicht über das Bestehen, weil 50 Familien je Parent zu wenige geeignete Phasenpunkte erwarten lassen.

**Gesamtentscheidung.** Die Critic-Validierung ist bestanden, wenn alle drei Parent-Critics bestehen. Sonst folgt **kein Pilot**. Dann wird der Befund mit getrennten Ursachen in `CRITIC_VALIDATION.md` dokumentiert: Daten (Erfolgszahl, Phasenabdeckung), Merkmale, Ziel. Ein durchgefallener Critic wird innerhalb dieses Protokolls nicht nachjustiert. Ein neuer Versuch braucht eine neue, freigegebene Protokollversion. Das Kriterium belegt keine zuverlässige Bewertung von Aktionen außerhalb der Parentverteilung.

## 7. Bindung an BC und Constraint-Kandidaten

**Actorupdate (AWAC-artig).** Die gewichtete Regression auf Aktionen aus dem Replay ist `L = E[ w · ‖π(s) − a‖² ]` mit `w = min(exp(A(s,a)/λ), 20)` und `A = Q(s,a) − Q(s,π(s))`. Dabei ist Q das Minimum der Twin-Critics. Die Gewichte werden nicht über den Batch normiert. Das ist keine exakte AWAC-Replikation, weil der Actor deterministisch ist und eine MSE-Regression statt einer Log-Likelihood verwendet wird.

**Harte Grenze zum eingefrorenen Parent.** `a = clip(a_parent + b · tanh((a_raw − a_parent)/b), −1, 1)`, mit zustandsabhängiger Breite `b_xyz = min(δ_max, 0,5 · |a_parent,xyz|)` und `b_greifer = 0,02`. Das entspricht der Regel aus [RELATIVER_SPIELRAUM.md](../critic_warmstart_20261104/RELATIVER_SPIELRAUM.md). Zu Beginn gilt `a = a_parent` exakt, ein Eigenschaftstest prüft das. Exploration (Gauß, σ = 0,05 auf XYZ, Greifer ohne Rauschen) wird in dieselbe Grenze projiziert. Critic-Ziele verwenden die begrenzte Actoraktion **ohne** zusätzliches Zielrauschen. So fragt der Critic keine Aktionen außerhalb des Ausführungsbereichs ab. Das ist eine bekannte Änderung gegenüber dem TD3-Kern in `base/`.

**Kandidaten.** λ = 0,1 bleibt fest. `δ_max` wird in der Reihenfolge **0,05 → 0,10 → 0,20** geprüft. Die Prüfung endet bei der ersten gescheiterten Stufe. Gewählt wird die größte vollständig bestandene Stufe, und sie gilt gleich für beide AC-Arme. Ein zusätzlicher BC-Term auf Zweier-Expertendaten ist nicht vorgesehen (β = 0). Er würde eine zweite Bindung einführen, die der Smoke nicht getrennt eingrenzen kann.

**Auswahl nur nach technischer Stabilität (N2-3).** Je Stufe laufen beide Critic-Varianten mit allen drei Parents: 2 Runden mit je 10 Episoden auf `smoke_interaction` und 250 Critic-Updates je Runde. Danach folgt eine Prüfung auf `constraint_development` gegen den unveränderten Parent. Eine Stufe besteht, wenn

- alle Losses, Q-Werte, Gewichte und Aktionen endlich sind und die Q-Werte in [−0,05; 1,05] liegen,
- jede ausgeführte Aktion die Grenze einhält (0 Verletzungen),
- die effektive Stichprobengröße der Gewichte im Mittel ≥ 10 % der Batchgröße beträgt,
- je Parent höchstens 2 und insgesamt höchstens 3 Parent-Erfolge auf den 20 Entwicklungsfamilien verloren gehen. Neue Erfolge verrechnen Verluste nicht.

Erfolge von AC-neu und AC-IL werden dabei **nicht** miteinander verglichen. Scheitert schon die Stufe 0,05, wird kein Pilot vorbereitet und der Nutzer entscheidet. Der Smoke liefert keine Wirksamkeitsaussage.

## 8. Checkpointregel, Prüfpunkte und Abbruchkriterium

- **Feste Regel:** Ausgewertet wird der Checkpoint nach Runde 4, also nach dem vollen Onlinebudget. Es gibt keine Auswahl nach Validierungsergebnissen. Jede Runde speichert Gewichte, Optimizer-, RNG-, Sampler- und Replayzustand an einer Episodengrenze, damit exakt fortgesetzt werden kann.
- **Runde 0:** Die AC-Actors sind vor dem ersten Update identisch mit dem Parent. Runde 0 übernimmt daher die BC-Werte aus N2-2. Ein Determinismustest bestätigt das (§9).
- **Zwischenprüfungen:** nach den Runden 1, 2 und 3 auf `validation_normal` (100 Familien), deterministisch ohne Explorationsrauschen. Sie dienen der Lernkurve und dem Abbruch, nicht der Auswahl. Alle 500 Critic-Updates werden die Aktionsabweichung zum Parent (Mittel und Maximum auf festen 64 Critic-Datenframes je Phase), die Q-Spanne, Gewichtsstatistiken und Losses protokolliert.
- **Abbruch eines Laufs (technisch):** nicht endliche Werte, eine Grenzverletzung oder eine Ausnahme. Danach folgt die Fehlerbehebung nach AGENTS.md §5 mit höchstens einem Reparaturversuch.
- **Zusammenbruch des Actors:** Bei einer Zwischenprüfung liegt die reguläre Validierungsquote eines Laufs bei höchstens der Hälfte der Quote seines Parents auf denselben 100 Familien. Dann wird der gesamte Pilot sofort angehalten, sofern die Ursache nicht rein technisch ist. `Gesamtpause: ja` wird gesetzt, und der Nutzer entscheidet (Nachtplan). Der betroffene Lauf wird nicht wiederholt.

## 9. Ausschluss- und Behandlungsregeln

- Keine Familie, Episode, kein Parent und kein Lauf wird ausgeschlossen oder ersetzt. Alle drei Parents werden in allen drei Armen berichtet.
- Nicht erreichte Phasen, Rückzugs-Timeouts, Horizontende und Instabilitäten in der Simulation innerhalb einer Episode zählen als Misserfolg im vollständigen Nenner. Bedingte Phasenquoten erhalten eigene, benannte Nenner.
- Infrastrukturunterbrechungen sind keine Ausgänge. Dazu zählen Deadline-Halt, Prozessabbruch und Stromausfall. Die laufende Episode wird verworfen und vom letzten Checkpoint mit identischem Szenenseed und gespeichertem RNG-Zustand neu ausgeführt. Ihre Zahl wird protokolliert.
- Ein abgebrochener Lauf geht mit dem Wert seines letzten ausgewerteten Prüfpunkts ein und wird als abgebrochen gekennzeichnet. Er wird nicht wiederholt. Es werden keine Seeds nachgeschoben.
- **Determinismus:** In N3-2 wird BC auf 10 regulären Validierungsfamilien je Parent erneut ausgerollt und die Trajektorienhashes mit N2-2 verglichen. Bei einer Abweichung wird das technische Problem berichtet und BC vollständig neu ausgewertet.

## 10. Analyse (Pilot N4-1)

Ausgewertet wird nur die Validierung. Regulär, schwierig und Zweier werden getrennt und mit vollständigen Nennern berichtet, also *k*/100, *k*/50 und *k*/100 je Modell.

- **Primärer Kontrast:** Erfolgsdifferenz AC-IL − AC-neu je Parent auf `validation_normal` am festen Checkpoint. Dazu der Mittelwert über die drei Parents und die Spannweite.
- **Sekundär:** AC-neu − BC und AC-IL − BC je Parent. Dieselben Kontraste auf `validation_hard`. Erhalt der Zweierfertigkeit als Differenz AC − Parent auf dem Zweierpanel.
- **Paarung:** Je Parent werden die diskordanten Familienpaare angegeben. Das 95-%-Intervall aus dem Familienbootstrap mit Seed 7300 wird ausdrücklich als reine Szenenunsicherheit bezeichnet. Es deckt nicht die Streuung durch neues Training ab. Die drei Parents teilen die Validierungs-, Online- und Critic-Datenfamilien.
- **Effizienz:** Die Erfolgsschwelle je Parent ist Parentquote + 10 Prozentpunkte auf `validation_normal`. Gemessen werden Onlineepisoden und Frames bis zur ersten Prüfrunde über dieser Schwelle, mit einer Auflösung von 100 Episoden. Wird die Schwelle nicht erreicht, wird „> 400“ berichtet. Für AC-IL werden die Werte einmal ohne und einmal mit den 300 Vortrainingsepisoden berichtet.
- **Kosten:** Onlineepisoden, Frames, Critic- und Actorupdates, Vortrainingsepisoden und -updates, Auswertungsepisoden und Laufzeit, jeweils getrennt.
- **Kleinster relevanter Effekt (vorläufig):** 10 Prozentpunkte im primären Kontrast. N4-2 legt daraus, aus der Pilotstreuung und aus dem Budget die Seedzahl (> 3) des Hauptvergleichs fest. Drei Seeds erlauben keinen Bestätigungsschluss. Es werden keine Signifikanzaussagen als Wirksamkeitsnachweis berichtet.

## 11. Ablauf und Freigaben

| Schritt | Freigabe nötig | Inhalt |
|---|---|---|
| N2-1 | Freigabe dieses Protokolls | A-Rollouts auf den Critic-Datenfamilien (Simulation mit eingefrorenen Modellen) |
| N2-2 | Häkchen N2-2/N2-3 | Critic-Vortraining und Prüfung nach §6 |
| N2-3 | Häkchen N2-2/N2-3 | technischer Smoke und Bindungsstufen nach §7 |
| N2-4 | – | `night.py prepare`, Quellen per SHA eingefroren, Fortsetzung getestet |
| N3-1 | Häkchen N3-1 | Pilot nach §2–§9 |
| N3-2 / N4-1 | – | Validierungsauswertung und Pilotbericht nach §10 |

Lange Läufe laufen unter einem Supervisor mit wirksamer Deadline, einem inkrementellen Monitor und einem Eintrag in `monitor/training-runs.json`.

## 12. Offene Nutzerentscheidungen

1. Freigabe dieses Entwurfs oder Änderungswünsche.
2. Replayregel der AC-Arme: nur Onlinedaten (Vorschlag) oder zusätzlich die Critic-Daten in beiden Armen (§2).
3. Vorgeschlagene Kennzahlen: Updatezahlen (20.000 Vortraining, 25 Critic-Updates je Onlineepisode), λ = 0,1, die Stufen für `δ_max`, die Akzeptanzschwellen in §6, die Kollapsschwelle von 50 % und die Effizienzschwelle von +10 Prozentpunkten.
4. Versionierte Ergänzung von `splits.json` um die drei neuen Bereiche in §3.

## 13. Aussagegrenzen

Simulation mit privilegiertem Zustand. Die Platzierungsreihenfolge ist fest. Es gibt drei Parents mit geteilten Szenen. Die verborgenen OSC-Laufzeitzustände sind nicht nachweislich markovsch erfasst. Die harte Grenze verhindert Ausreißer der Actoraktionen, garantiert aber weder Kollisionsfreiheit noch Erfolg. Ein Pilotergebnis ist eine Schätzung von Effekt und Streuung und kein Wirksamkeitsnachweis.
