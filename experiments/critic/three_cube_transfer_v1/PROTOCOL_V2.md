# Versuchsprotokoll v2: Änderungen nach dem gescheiterten Smoke N2-3

**Status: FREIGEGEBEN** · Nutzerentscheidung vom 19.11.2026, 22:12 Uhr (Plan B: Critic zuerst verbessern) · Version protocol_v2 · ersetzt nur die unten genannten Abschnitte von [PROTOCOL.md](PROTOCOL.md) (protocol_v1)

Alles, was hier nicht geändert wird, gilt unverändert aus protocol_v1: Methodenfrage, Arme, Parents, Seeds, Splits, Reward, Beobachtung, Online-Budget, Critic-Akzeptanz (§6), Checkpoint- und Abbruchregeln (§8), Ausschlussregeln (§9), Analyse (§10). Die Ergebnisse von N1-1 bis N2-2 bleiben gültig. Die N2-2-Critics bleiben als Referenz erhalten. Für den Arm AC-IL wird nach §E ein neuer Critic (IL-v2) vortrainiert und validiert. Testfamilien bleiben geschlossen.

## 0. Anlass und Befund

Der Smoke N2-3 ([AC_SMOKE.md](AC_SMOKE.md#ergebnis-abschluss-19112026)) ist an Stufe δ_max = 0,05 gescheitert. Alle sechs Läufe verfehlen die Q-Bereichsprüfung [−0,05; 1,05]. Alle anderen Prüfungen sind bestanden. Die Auswertung zeigt zwei getrennte Probleme:

1. **Die Q-Bereichsprüfung misst keine Instabilität.** Werte unter −0,05 lagen schon vor dem ersten Update vor, bei den eingefrorenen N2-2-Critics (Probe-Minimum −0,084 / −0,123 / −0,091) und bei der zufälligen Initialisierung (−0,200 / −0,214 / −0,235). Die TD-Ziele sind auf [0, 1] geklemmt, die Critic-Losses sind klein und sinken, das Maximum nach den Runden liegt bei höchstens 1,016. Die Prüfung erfasst damit die unbeschränkte lineare Ausgabe an selten gesehenen Zuständen, keine Divergenz.
2. **Der Critic steuert den Actor praktisch nicht.** An der begrenzten Actoraktion weicht Q höchstens um 0,001 vom Wert an der Parentaktion ab. Mit λ = 0,1 ergibt das Gewichte von etwa exp(0,01) ≈ 1 (w_max 1,01–1,55, ESS ≈ 256 von 256). Das Actorupdate ist damit nahezu eine ungewichtete Regression auf die eigenen verrauschten Aktionen. Ein Pilot unter v1 würde AC-neu und AC-IL deshalb kaum unterscheiden können, unabhängig von der Hypothese.

Ursache für (2), soweit belegbar: Das Vortraining in N2-2 regressiert den Return nur an der **Parentaktion** (`Learner.warm`). Die N2-1-Daten enthalten kein Explorationsrauschen ([CRITIC_DATA.md](CRITIC_DATA.md)). Der vortrainierte Critic hat deshalb nie gelernt, wie sich Q mit der Aktion ändert. Seine Aktionsabhängigkeit stammt aus der Initialisierung. Ob das so ist, prüft D1 (§A) ohne Training.

**Transparenz:** Diese Änderungen entstehen nach Sicht auf die Smoke-Daten. Deshalb zählt kein Ergebnis aus Smoke v1 für v2. Smoke v2 läuft vollständig neu, und die neuen Schwellen werden unten aus technischen Überlegungen begründet, nicht aus dem Bestehen der v1-Läufe.

## A. Neu: Diagnose D1 „Aktionssensitivität“ (vor Smoke v2, keine Optimizerupdates)

**Frage:** Hängt Q innerhalb des Ausführungsbereichs messbar von der Aktion ab, und trägt das Vortraining dazu etwas bei?

- **Frames:** die festen Driftframes aus N2-3 (64 Critic-Datenframes je Policy-Phase und Parent, Auswahlseed 7400 + p). Keine Validierungs- oder Testframes.
- **Aktionen:** je Frame K = 32 Aktionen gleichverteilt im begrenzten Bereich um die Parentaktion, für jede Stufe δ_max ∈ {0,05; 0,10; 0,20} (Breite `b_xyz = min(δ_max, 0,5·|a_parent,xyz|)`, Greifer ±0,02). Seed 7500 + p.
- **Critics:** N2-2-Critic (AC-IL-Start) und zufällig initialisierter Critic mit `c_p = 7100 + p` (AC-neu-Start).
- **Kennzahlen je Parent, Phase, Stufe, Variante:** Vorteil `A = Q(s,a) − Q(s,a_parent)` mit Q = Minimum der Twin-Critics. Berichtet werden Standardabweichung, 90-%-Quantil von |A| und der Anteil der Frames, in denen das beste Aktionsmuster eindeutig ist (|A_max − A_2.| > 10⁻³).
- **Rechenaufwand:** nur Vorwärtsdurchläufe, unter einer Minute.

**Rolle von D1 in v2:** D1 läuft zweimal. **D1a** auf dem N2-2-Critic ist nur berichtend und belegt den Ausgangsbefund. **D1b** auf dem neuen Critic IL-v2 (§E) entscheidet:

| Befund D1b | Folge |
|---|---|
| Median-Std(A) des IL-v2-Critics ≥ 0,01 auf mindestens einer Stufe **und** mindestens 1,5-mal die Median-Std der zufälligen Initialisierung | Smoke v2 nach §B–§D mit IL-v2 als AC-IL-Critic |
| eine der beiden Bedingungen verfehlt | Kein Smoke v2. Befund dokumentieren, Gesamtpause, der Nutzer entscheidet. |

Die Schwelle 0,01 ist eine Größenordnung über dem in N2-3 gemessenen Unterschied (≤ 0,001) und entspricht einem Prozentpunkt geschätzter Erfolgswahrscheinlichkeit.

## B. Änderung von §7: Gewichtung des Actorupdates

**v1:** `w = min(exp(A/λ), 20)` mit λ = 0,1, ohne Normierung.

**v2:** Die Vorteile werden je Batch standardisiert:

`z = (A − mean_batch(A)) / (std_batch(A) + 10⁻⁶)`, `w = min(exp(z/τ), 20)` mit **τ = 1**, fest für beide AC-Arme und alle Stufen.

**Begründung:** Die Gewichtung hängt so nicht mehr von der absoluten Q-Skala ab, die sich zwischen AC-neu und AC-IL systematisch unterscheidet (v1: AC-neu-Spanne etwa 0,1, AC-IL etwa 1,1). Beide Arme bekommen dieselbe Regel, ohne dass λ aus Erfolgsdaten gewählt wird. Für normalverteilte Vorteile ergibt τ = 1 eine erwartete effektive Stichprobengröße von exp(−1/τ²) ≈ 37 % des Batches. Das liegt im Bereich, in dem die Gewichte unterscheiden, ohne auf wenige Beispiele zu kollabieren. τ wird nicht nachjustiert.

**Bekanntes Risiko:** Bei sehr kleinen Vorteilen verstärkt die Standardisierung Rauschen des Critics. Deshalb ist D1 (§A) Voraussetzung, und die Prüfung „ESS ≥ 10 %“ aus v1 bleibt bestehen. Die Gewichtsstatistik je Runde (Mittel, Maximum, Anteil gekappt, ESS) wird berichtet.

Die harte Grenze zum Parent, die Stufenfolge 0,05 → 0,10 → 0,20, die Abbruchregel bei der ersten gescheiterten Stufe und die Wahl der größten bestandenen Stufe bleiben aus v1.

## C. Änderung von §7: Stabilitätsprüfung statt fester Q-Bereich

Die v1-Bedingung „Q-Werte in [−0,05; 1,05]“ wird ersetzt durch eine Divergenzprüfung. Alle anderen Bestehensbedingungen bleiben (endlich, 0 Grenzverletzungen, ESS ≥ 10 %, höchstens 2 verlorene Parent-Erfolge je Parent und 3 insgesamt in der konservativen Lesart B).

Eine Stufe besteht die Q-Prüfung, wenn für jeden Lauf nach jeder Runde, auf Replay und Probeframes zusammen, gilt:

1. **Keine Ausreißer:** alle Q-Werte liegen in [−0,25; 1,25].
2. **Kein Wegdriften:** höchstens 5 % der Q-Werte liegen außerhalb von [−0,05; 1,05].
3. **Keine Verschlechterung:** Der Anteil außerhalb von [−0,05; 1,05] steigt gegenüber Runde 0 (vor dem ersten Update) um höchstens 5 Prozentpunkte.

**Begründung:** Werte deutlich außerhalb des Rewardbereichs (± 0,25) zeigen eine echte Fehlschätzung. Einzelne leicht negative Werte einer linearen Ausgabe an selten gesehenen Zuständen tun das nicht, solange sie nicht zunehmen. Bedingung 3 trennt Divergenz durch Updates vom Ausgangszustand, den v1 mitbewertet hat.

Die Q-Spanne während der Updates wird weiter berichtet, entscheidet aber nicht.

**Verworfene Alternative:** Ein Sigmoid-Ausgang würde Q strukturell auf (0, 1) begrenzen, verlangt aber ein neues Vortraining und eine neue Validierung nach §6 für alle drei Critics. Die bestandenen N2-2-Critics blieben dann nicht erhalten. Kann bei einer späteren Version gewählt werden.

## D. Smoke v2 (ersetzt N2-3 für v2)

- Ablauf, Familien (`smoke_interaction`, `constraint_development`), Seeds, Updatezahlen und Parallelisierung wie N2-3. Die Familien sind technische Familien und werden bewusst wiederverwendet, damit v1 und v2 vergleichbar berichtet werden können.
- Neu: Entwicklungsprüfung gegen den Parent **auch nach Runde 1**, nicht nur am Ende. Das ist nur berichtend und entscheidet nicht. Anlass: In v1 fielen die Onlineerfolge in allen sechs Läufen von 5/10 in Runde 1 auf 2–4/10 in Runde 2. Bei n = 10 mit Explorationsrauschen ist das kein Befund, ähnelt aber der Actor-Drift aus `critic_warmstart_20261104/diagnosis_001`.
- Zusätzlich je Runde berichtet: Std(A) im Replay je Variante und der Anteil der Actorupdates, deren Richtung von der ungewichteten Regression abweicht (Kosinus < 0,99). Das zeigt, ob der Critic jetzt tatsächlich steuert.
- Budget: höchstens 3 Stufen × (6 × 40 Episoden + 6 × 20 Zusatzepisoden) + 60 Baseline, etwa 15–20 min Laufzeit.
- Smoke v2 bleibt rein technisch, ohne Wirksamkeitsaussage, und vergleicht keine Erfolge von AC-neu und AC-IL.

Scheitert schon Stufe 0,05 auch unter v2, wird kein Pilot vorbereitet. Gesamtpause, und der Nutzer entscheidet.

## E. Neu: Critic IL-v2 mit Aktionsvariation (N2-1b, N2-2b)

**Anlass:** Der N2-2-Critic hat nur Parentaktionen gesehen (§0). Ein Vorteil `Q(s,a) − Q(s,π(s))` kann aus einem reinen Zustandswert nicht entstehen. Damit AC-IL die Hypothese AC-003 im gemeinten Sinn prüft, braucht das Vortraining Daten mit Aktionsvariation.

**N2-1b, Datenerhebung (keine Optimizerupdates):**

- **Familien:** neuer Split `critic_data_noisy`, 300 Familien `2100003690–2100003989`, versioniert in `splits_v3.json`. Der Rest ab 2100003990 bleibt unvergeben.
- **Policy:** die drei A-Parents, unverändert. Auf XYZ wird Gaußrauschen σ = 0,05 addiert und in die Grenze der **weitesten** Stufe δ_max = 0,20 projiziert (Regel aus §7), damit die Daten alle Stufen abdecken. Greifer ohne Rauschen. RNG-Seed 7600 + p. Abschlusslogit, Sequencer, Rückzug und Uhrkorrektur wie in N2-1.
- **Umfang:** 300 Familien × 3 Parents = 900 Episoden, alle Ausgänge behalten. Geschätzt 1,0–1,3 h Rolloutzeit.
- **Datenvertrag:** wie N2-1, zusätzlich je Frame Parentaktion, ausgeführte (verrauschte, begrenzte) Aktion und Rauschwert. Manifest mit SHA-256 und Erfolgs- und Fehlerzahlen je Parent.

**N2-2b, Vortraining und Validierung von IL-v2:**

- **Daten je Parent:** N2-1 (300 Episoden, Parentaktionen) und N2-1b (300 Episoden, verrauschte Aktionen) desselben Parents. Normierung aus beiden zusammen, mit dem Critic eingefroren.
- **Ziel und Budget:** unverändert `Learner.warm` (Monte-Carlo-Regression des beobachteten diskontierten Returns an der **ausgeführten** Aktion), 20.000 Updates, Batch 256, Lernrate 3·10⁻⁴, Initialisierungsseed `c_p = 7100 + p`, Minibatches `r_p = 7200 + p`. Kein Early Stopping.
- **Validierung:** Kriterien §6 aus protocol_v1 unverändert, auf den **gespeicherten** N2-2-Validierungsrollouts der A-Parents (keine neuen Rollouts, keine Testfamilien). Fällt IL-v2 durch, kein Smoke v2, Gesamtpause.
- **Danach D1b** nach §A.

**Bekannte Grenze:** Der Return nach einer verrauschten Aktion stammt von einer verrauschten Fortsetzung, nicht vom Parent. Q ist daher die Bewertung der verrauschten Verhaltenspolicy. Das wird im Bericht genannt.

**Pilot:** AC-IL verwendet im Pilot IL-v2. AC-neu bleibt unverändert. Der N2-2-Critic wird im Pilot nicht verwendet.

## F. Ablauf und Freigaben

| Schritt | Freigabe | Inhalt |
|---|---|---|
| Freigabe v2, Gesamtpause aufgehoben | Nutzer, 19.11.2026 22:12 (Plan B) | dieses Dokument |
| D1a | keine (nur Vorwärtsdurchläufe) | §A auf N2-2-Critic, berichtend |
| N2-1b | erteilt (Plan B) | §E Datenerhebung, `CRITIC_DATA_NOISY.md` |
| N2-2b | erteilt (Plan B) | §E Vortraining und Validierung IL-v2, `CRITIC_VALIDATION_V2.md` |
| D1b | keine | §A auf IL-v2, entscheidend, `ACTION_SENSITIVITY.md` |
| N2-3v2 | erteilt (Häkchen N2-2/N2-3, gilt für v2) | §B–§D mit IL-v2, `AC_SMOKE_V2.md` |
| N2-4, N3-1 … | wie v1 | **nicht vor Nacht 3 (20./21.11.2026)**, mit IL-v2 und der in Smoke v2 gewählten Stufe |

In `STATUS.md` werden ergänzt: `D1a`, `N2-1b`, `N2-2b`, `D1b`, `N2-3v2` sowie die Begleitaufgaben aus dem Nachtplan. N2-3 bleibt als „erledigt, nicht bestanden“ stehen.

## G. Aussagegrenzen (ergänzend zu v1 §13)

Die Standardisierung der Vorteile ist eine bekannte Abweichung von AWAC und wird im Pilotbericht genannt. Die Schwellen in §C sind nach Sicht der v1-Daten festgelegt. Smoke v2 ist dadurch eine technische Prüfung, keine unabhängige Bestätigung der Bindung.
