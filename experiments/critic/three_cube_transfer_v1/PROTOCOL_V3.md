# Versuchsprotokoll v3: Critic-gefilterte Selbstimitation zum Dreierturm

**Status: FREIGEGEBEN** · Nutzerfreigabe vom 20.11.2026, 11:14 Uhr (einschließlich S-3/S-4) · Version protocol_v3 · Nutzerentscheidung vom 20.11.2026, 11:10 Uhr: Wechsel zu Critic-gefilterter Selbstimitation

Ersetzt für die weitere Arbeit den Actor-Critic-Pfad aus [PROTOCOL.md](PROTOCOL.md) (v1) und [PROTOCOL_V2.md](PROTOCOL_V2.md) (v2). Deren Ergebnisse bleiben gültig und werden nicht verändert. Es gelten [AGENTS.md](../../../AGENTS.md), [Agend.md](../../../Agend.md), [AGENTEN_ORCHESTRIERUNG.md](../../../AGENTEN_ORCHESTRIERUNG.md) und [experiments/AGENTS.md](../../AGENTS.md).

## 0. Anlass

- **Der Critic bewertet Zustände gut.** IL-v2 besteht §6 bei allen drei Parents, mit regulärer AUC von 0,885, 0,916 und 0,882 ([CRITIC_VALIDATION_V2.md](CRITIC_VALIDATION_V2.md)).
- **Aktionen innerhalb der Bindung unterscheidet er kaum.** In D1b liegt der Median der Streuung des Vorteils bei höchstens 0,000589, gefordert waren 0,01 ([ACTION_SENSITIVITY.md](ACTION_SENSITIVITY.md#d1b--entscheidung-für-il-v2)). Ein Actorupdate über Vorteile hätte damit kaum Signal.
- **Die Fehler liegen dort, wo kleine Korrekturen wenig ausrichten.** Die meisten Fehlschläge enden in Stufe 2 beim Greifen oder Lösen. 139 von 418 Fehlschlägen in der Ablagegruppe liegen selbst bei δ_max = 0,20 außerhalb der Bindung ([FAILURE_PHASES.md](FAILURE_PHASES.md)).

v3 nutzt den Critic deshalb für das, was er nachweislich kann: ganze Abschnitte eigener Dreierversuche nach ihrer Erfolgsaussicht auswählen. Die Auswahl dient als Trainingsdaten für BC. Der Actor erhält keine Critic-Gradienten.

**Vorbefunde, die gegen große Effekte sprechen:**

- **SI-001:** Eigene erfolgreiche Dreiertrajektorien brachten einen kleinen positiven Pilotbefund (62/58/49 % gegen Replay 55/51/49 %). Gemessen wurde mit der später korrigierten Metrik.
- **SI-004:** Regelbasiert ausgewählte Abschnitte aus Fehlversuchen halfen nicht (Parent 90/150, Arme 88–93/150).

v3 unterscheidet sich von SI-004 durch die Auswahl über einen validierten Critic statt einer festen Regel und durch die aktuelle 50-Frame-Erfolgsdefinition. Ein großer Effekt wird nicht erwartet. Der Pilot schätzt Effekt und Streuung.

## 1. Methodenfrage und Hypothesen

*Verbessert BC, das auf eigenen Dreierversuchen nachtrainiert wird, deren Abschnitte ein auf eigenen Versuchen vortrainierter Critic auswählt, den Dreierturm stärker als Nachtraining nur auf erfolgreichen eigenen Versuchen? Dabei gibt es keine Dreier-Demonstrationen und keine Experteneingriffe.*

- **SI-005a (Hauptkontrast):** SI-K erreicht auf `validation_normal` eine höhere Dreier-Erfolgsquote als SI-E.
- **SI-005b:** SI-E erreicht eine höhere Quote als unverändertes BC. Das wiederholt SI-001 unter der aktuellen Metrik.
- **Nebenbedingung:** Auf dem Zweierpanel fällt keiner der Arme um mehr als 10 Prozentpunkte unter seinen BC-Parent. Das wird nur berichtet und entscheidet nicht.

Der Pilot ist der erste wissenschaftliche Lauf dieser Fragestellung. Er hat genau drei Seeds, die drei A-Parents, und bestätigt nichts (AGENTS.md §1).

## 2. Arme

| Arm | Start | Nachtrainingsdaten | Updates |
|---|---|---|---|
| **BC** | A-Parent p, unverändert | – | 0 |
| **SI-E** | Kopie von A-Parent p | 50 % Zweier-Demonstrationen der A-Rezeptur, 50 % **erfolgreiche** eigene Episoden aus dem Pool von Parent p | 5.000 |
| **SI-K** | Kopie von A-Parent p | 50 % Zweier-Demonstrationen, 50 % erfolgreiche eigene Episoden **und** nach §4 Critic-ausgewählte Präfixe gescheiterter Episoden aus demselben Pool | 5.000 |

- **Isolierte Größe:** Zwischen SI-K und SI-E unterscheidet sich nur die Auswahl aus demselben Pool. Startgewichte, Zweieranteil, Updatezahl, Batch, Lernrate, Optimizer und Minibatch-RNG sind gleich.
- **Rezeptur des Nachtrainings:** wie die A-Rezeptur aus `experiments/curriculum/registry.py`, also gleiche Verlustfunktion, Batch, Lernrate und Beobachtung. Neu ist nur der Datenmix. Abweichungen der Umsetzung werden vor dem Start in `config.json` eingefroren und begründet.
- **Checkpoint:** fest nach 5.000 Updates, keine Auswahl.
- **Seeds:** Minibatches `7700 + p`, in beiden SI-Armen gleich.

## 3. Datenpool (S-1, keine Optimizerupdates)

- **Familien:** `online_interaction` (2100003250–2100003649, 400 Familien). Sie sind bisher unbenutzt, weil der AC-Pilot nicht lief. Damit sind die Poolfamilien disjunkt zu den Critic-Daten von IL-v2 (N2-1, N2-1b). Die Auswahl ist also nicht zirkulär.
- **Policy:** A-Parents mit Explorationsrauschen wie N2-1b (σ = 0,05 auf XYZ, projiziert in δ_max = 0,20, Greifer ohne Rauschen, RNG `7800 + p`). Das ergibt erfolgreiche und gescheiterte Versuche in ausreichender Zahl (N2-1b: 382/900 Erfolge).
- **Umfang:** 400 Familien × 3 Parents = 1.200 Episoden, alle Ausgänge behalten. Geschätzt 1,3–1,6 h.
- **Datenvertrag:** wie N2-1b. Zusätzlich speichert der Lauf den IL-v2-Wert `V_t = min(Q1, Q2)(s_t, a_t)` je Frame und die Phasengrenzen nach der Phasenlogik des Parents.

## 4. Critic-Auswahl für SI-K (vor den Daten festgelegt)

Für jede **gescheiterte** Episode von Parent p mit dem IL-v2-Critic dieses Parents:

1. **Phasen-Baseline** `b(k)`: Erfolgsquote je Phasenpunkt k aus N2-1 und N2-1b desselben Parents, wie in §6 von v1.
2. **Kandidaten** sind die Frames `t_k`, an denen ein Phasenpunkt k erreicht und abgeschlossen ist.
3. **Schnittpunkt** `t*` ist der späteste Kandidat mit `V(t_k) − b(k) ≥ 0,10`.
4. **Präfix:** Gibt es ein `t*`, geht der Präfix `[0, t*]` in die Daten ein, sonst nichts aus dieser Episode.

Erfolgreiche Episoden gehen in SI-E und SI-K vollständig ein. Die Auswahl ist deterministisch und wird mit Hash eingefroren, bevor ein Update läuft.

**Begründung:** Der Critic soll die Abschnitte eines Fehlversuchs finden, nach denen der Erfolg noch deutlich über dem Durchschnitt der erreichten Phase lag. Ab dort ist der Versuch vermutlich erst später gescheitert. Die Marge 0,10 liegt bei etwa 2,5-mal dem mittleren Kalibrierungsfehler (ECE ≤ 0,028) und damit über dem Kalibrierungsrauschen.

**Gate S-2 (vor dem Training):** SI-K muss je Parent mindestens 10 % mehr Selbstframes enthalten als SI-E. Außerdem müssen die Präfixe aus mindestens 10 verschiedenen Familien stammen. Sonst unterscheiden sich die Arme zu wenig, und es gibt kein Training: Gesamtpause, der Nutzer entscheidet. Das ist die Lehre aus SI-004, wo nur drei Familien geeignet waren.

## 5. Ablauf, Budgets und Aufgaben

| ID | Aufgabe | Updates | Abhängig von | Fertig, wenn |
|---|---|---|---|---|
| S-0 | Auswertung vorab einfrieren: `pilot_analysis.py` (B-1) auf die Arme BC, SI-E und SI-K übertragen oder unverändert nutzen, mit Tests, SHA im Protokoll | 0 | – | Skript und Tests, ohne Daten |
| S-1 | Datenpool nach §3 | 0 | – | 1.200/1.200 Episoden, Manifest, Hash, Erfolgszahlen je Parent |
| S-2 | Auswahl nach §4 und Gate | 0 | S-1 | `SELECTION.md` mit Frame- und Familienzahlen je Arm und Parent, Gate bestanden oder nicht |
| S-3 | Technischer Smoke: 200 Updates je Arm für Parent 1, endliche Losses, Aktionsabweichung zum Parent auf festen Frames | 400 | S-2 bestanden | Smoke-Bericht, ausdrücklich ohne Wirksamkeitsaussage |
| S-4 | Pilot-Nachtraining: 2 Arme × 3 Parents × 5.000 Updates | 30.000 | S-3 | sechs eingefrorene Checkpoints mit SHA |
| S-5 | Validierung: sechs SI-Modelle auf `validation_normal` (100) und `validation_hard` (50), alle neun Modelle auf dem Zweierpanel (100). BC-Werte auf der Validierung aus N2-2 mit Determinismusprüfung auf 10 Familien je Parent | 0 | S-4 | Rohpaare je Parent und Szene im Vertrag aus S-0 |
| S-6 | Pilotbericht, Abbildungen, Videos nach Orchestrierung §7 | 0 | S-5 | `SI_PILOT_REPORT.md` |

**Geschätzte Laufzeit:** S-1 etwa 1,5 h, S-3 und S-4 zusammen unter 1 h. S-5 umfasst 900 Dreier- und 900 Zweierepisoden, etwa 1,5–2 h. Das passt in eine Nacht. Reicht die Zeit nicht, wird nach v1 §9 exakt angehalten und fortgesetzt.

**Abbruch:** nicht endliche Losses oder eine Ausnahme, dann höchstens ein Reparaturversuch nach AGENTS.md §5. Fällt ein SI-Modell im Smoke S-3 auf den festen Frames um mehr als 0,10 im Mittel von der Parentaktion ab, wird angehalten und der Nutzer entscheidet.

## 6. Splits und Testfamilien

- **Validierung:** `validation_normal` und `validation_hard` wurden in N2-2 und N2-2b mit A-Rollouts zur Critic-Abnahme verwendet. Die SI-Auswahl verwendet sie nicht. Für die Modellbewertung im Pilot bleiben sie zulässig. Das wird im Bericht genannt.
- **Zweierpanel:** wird erstmals ausgerollt.
- **Test:** Testfamilien bleiben geschlossen. Sie werden erst mit einem eigenen Hauptprotokoll einmalig geöffnet.

## 7. Analyse (S-6)

- **Primär:** SI-K − SI-E auf `validation_normal` je Parent als gepaarte Differenz über dieselben 100 Szenen, mit Bootstrap-Intervall über Szenen. Dazu der Mittelwert über die drei Parents, ausdrücklich als Schätzung bei drei Seeds.
- **Sekundär:** SI-E − BC, getrennt auf `validation_hard`. Dazu die Zweier-Erfolgsquote je Arm, die Datenmengen je Arm und die Kosten (Rollout- und Updatezeit).
- Vollständige Nenner. Normale und schwierige Validierung werden nicht zusammengefasst.
- **Seedzahl für einen Hauptvergleich:** mit `seed_count.py` (B-3) aus kleinstem relevantem Effekt (+5 Prozentpunkte), Pilotstreuung und Budget.

## 8. Freigaben

| Schritt | Freigabe |
|---|---|
| S-0, S-1, S-2, S-5, S-6 | keine Optimizerupdates, nach Freigabe dieses Protokolls zulässig |
| S-3, S-4 | neues Häkchen „S-3/S-4“ im NACHTPLAN durch den Nutzer |

Nach der Freigabe trägt die Planungssitzung S-0 bis S-6 in `tasks.json`, NACHTPLAN und `STATUS.md` ein und hebt die Gesamtpause auf. Die AC-Aufgaben N2-3v2, N2-4 und N3-1 bis N4-4 werden in `STATUS.md` auf „blockiert (ersetzt durch v3)“ gesetzt und nicht gelöscht. B-4 bleibt als Dokumentationsaufgabe bestehen.

## 9. Aussagegrenzen

Simulation mit privilegiertem Zustand. Drei Parents mit geteilten Szenen. Die Poolrollouts enthalten Explorationsrauschen. Die Selbstdaten zeigen also eine verrauschte Verhaltenspolicy und nicht exakt die Policy des Parents. Der Critic wählt nach geschätzter Erfolgsaussicht aus. Er belegt nicht, dass die gewählten Abschnitte richtig ausgeführt wurden. Ein Pilotergebnis ist eine Schätzung von Effekt und Streuung und kein Wirksamkeitsnachweis.
