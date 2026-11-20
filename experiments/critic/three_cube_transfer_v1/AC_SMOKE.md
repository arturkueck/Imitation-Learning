# N2-3 · Technischer Actor-Critic-Smoke

**Status: abgeschlossen, Stufe 0,05 nicht bestanden. Keine Stufe gewählt, Nutzerentscheidung nach §7 nötig** (Lauf 19.11.2026, 13:12–13:18 Uhr Europe/Berlin) · technischer Smoke **ohne Wirksamkeitsaussage** · [Ergebnis](#ergebnis-abschluss-19112026) · [Code](ac_smoke.py) · [Auswertung, nur lesend](ac_smoke_report.py) · [Tests](test_ac_smoke.py) · [Protokoll §7](PROTOCOL.md#7-bindung-an-bc-und-constraint-kandidaten)

Der Smoke prüft nach PROTOCOL.md §7 die AWAC-artige Bindung an den eingefrorenen A-Parent in den Stufen δ_max = 0,05 → 0,10 → 0,20 (λ = 0,1). Er grenzt die Stufe nur über technische Stabilität ein. Erfolge von AC-neu und AC-IL werden nicht miteinander verglichen. Die Testfamilien bleiben geschlossen.

## Ablauf

1. **Parent-Baseline:** die drei unveränderten A-Parents auf den 20 Familien `constraint_development` (2100003650–2100003669). Das ergibt 60 Episoden mit 0 Updates und demselben Episodenpfad wie N2-1 (`critic_data.episode`).
2. **Je Stufe sechs Läufe:** AC-neu und AC-IL, jeweils mit den Parents 1, 2 und 3. Ein Lauf umfasst 2 Runden mit je 10 Episoden auf `smoke_interaction` (2100003670–2100003689, aufsteigend, Runde 1 die ersten zehn). Nach jeder Episode folgen 25 Critic-Updates, nach jedem zweiten Critic-Update ein Actorupdate. Das ergibt 500 Critic- und 250 Actorupdates je Lauf. Danach folgen 20 deterministische Episoden ohne Rauschen auf `constraint_development`.
3. **Stufenbewertung** nach §7. Die Prüfung endet bei der ersten gescheiterten Stufe. Gewählt wird die größte vollständig bestandene Stufe.

## Festlegungen der Umsetzung innerhalb von §7

Diese Punkte legt das Protokoll nicht im Einzelnen fest. Sie wurden vor dem Start in `config.json` eingefroren und ändern weder Arme noch Seeds, Splits, Budgets, Erfolgsdefinition, Reward oder Beobachtung.

- **Begrenzte Aktion:** `a = clip(a_p + b·tanh((a_raw + ε − a_p)/b), −1, 1)` mit `b_xyz = min(δ_max, 0,5·|a_p,xyz|)` und `b_Greifer = 0,02`. Das Explorationsrauschen ε (σ = 0,05 auf XYZ, 0 am Greifer) wird vor derselben Projektion addiert. Bei `b = 0` gilt exakt `a = a_p`. Geprüft wird jede ausgeführte Aktion mit einer Toleranz von 10⁻⁶ für Rundungsfehler.
- **Phasen und Abschluss:** Den Abschluss-Logit liefert der eingefrorene Parent. Sequencer, Rückzug und Uhrkorrektur bleiben unverändert (`critic_data.episode`).
- **Critic:** AC-IL startet vom eingefrorenen N2-2-Critic desselben Parents, geprüft per SHA-256. AC-neu verwendet `torch.manual_seed(7100 + p)` und dieselben Normierungspuffer. Damit ist er bitgleich mit dem N2-2-Critic vor dessen erstem Vortrainingsupdate (Test). Beide Varianten starten mit frischen AdamW-Optimierern.
- **Ziele und Updates:** Das TD-Ziel lautet `r + γ(1−t)·min Q_ziel(s', π_ziel,begrenzt(s'))`, ohne Zielrauschen und wie in `base/core.py` auf [0, 1] geklemmt. Terminal sind Erfolg, Horizont und Rückzugs-Timeout. Für den Actor gilt `mean(w·‖π_begrenzt(s) − a‖²)` mit `w = min(exp((Q(s,a) − Q(s,π(s)))/λ), 20)` und ohne Batchnormierung. Die Zielnetze werden nach jedem Actorupdate per Polyak aktualisiert (τ = 0,005). Batch 256, Lernraten 3·10⁻⁵ (Actor) und 3·10⁻⁴ (Critic), Weight Decay 10⁻⁶ und Gradientenclip 10 stammen unverändert aus `base/config.json`.
- **Replay:** nur die eigene Onlineerfahrung des Laufs.
- **RNG:** `SeedSequence(7200 + p).spawn(2)` liefert die Ströme für Exploration und Minibatches, in AC-neu und AC-IL desselben Parents gleich. Die Szenen werden wie in N2-1 geseedet.
- **Drift:** Gemessen wird nach Runde 0, 1 und 2 auf festen 64 Critic-Datenframes je Policy-Phase des Parents (Auswahl mit Seed 7400 + p). Berichtet werden mittlere und maximale Abweichung der begrenzten und der unbegrenzten Actoraktion vom Parent.
- **Q-Bereich [−0,05; 1,05] (entscheidend):** Critic-Ausgaben nach jeder Runde auf dem gesamten Replay (ausgeführte Aktionen) und auf den Probeframes (Parent- und Actoraktion). Zusätzlich wird der Bereich während der Updates berichtet. Er schließt die zufällige Initialisierung von AC-neu ein.
- **Effektive Stichprobengröße:** `(Σw)²/Σw²` je Actorupdate, gemittelt über alle Actorupdates eines Laufs (Mittel der beiden Runden). Grenze: ≥ 25,6, also 10 % von 256.
- **Verlorene Parent-Erfolge:** Eine Familie gilt als verloren, wenn der Parent dort Erfolg hatte und der Lauf nicht. Neue Erfolge werden nicht verrechnet. Entscheidend ist die konservative Lesart B: je Parent über beide Varianten höchstens 2, alle sechs Läufe zusammen höchstens 3. Lesart A (je Variante: je Parent ≤ 2, Summe ≤ 3) wird mitberichtet. Weichen beide Lesarten in der Entscheidung voneinander ab, wird das als Nutzerentscheidung markiert.
- **Parallelisierung und Fortsetzung:** Die sechs Läufe einer Stufe laufen als getrennte Prozesse mit festen Seeds und je 2 Torch-Threads. Ihr Ergebnis hängt nicht von der Prozesszahl ab. Fortgesetzt wird jeweils ab einem vollständigen Lauf. Ein unterbrochener Lauf wird nach `discarded/` verschoben (nicht gelöscht), gezählt und deterministisch neu ausgeführt (§9).

## Prüfung vor dem Start

[9/9 Tests](test_ac_smoke.py) bestanden in der Projekt-venv, Exitcode 0. Geprüft wurden Projektion und Nullbreite, die exakte Gleichheit mit dem Parent vor dem ersten Update, die Grenze unter Rauschen, bitgleich deterministische Updates mit Zählung, die AC-neu-Initialisierung gleich N2-2, die Replay-Maskierung, die Stufenregeln einschließlich beider Lesarten, die disjunkten Splits ohne Testfamilien und der Dashboardeintrag. Eine technische Integrationsprüfung lief auf der bereits geöffneten Kalibrierungsfamilie 2100000000 mit Parent 1, ohne Rauschen und mit 0 Updates. Der Ausführungspfad mit begrenztem Actor reproduzierte den Trajektorienhash, die Framezahl und den Ausgang aus N1-4 exakt. Die Drift auf den Probeframes war 0.

## Laufstatus

Der Lauf startete um 13:12 Uhr unter Supervisor PID 11684 (Erstellungszeit Unix 1795090328.5802815) und Worker PID 26712 (1795090328.8061771). Der Cutoff liegt bei 14:30 Uhr, die harte Deadline bei 14:45 Uhr. Um 13:14 Uhr meldete der Monitor `OK`: Parent-Baseline 3/3 abgeschlossen, Stufe 0,05 mit sechs aktiven Läufen bei je 125/500 Critic-Updates, keine Fehlerzeilen.

Um 13:20 Uhr meldete der Monitor `COMPLETE` ohne Fehlerzeilen. Supervisor (PID 11684) und Worker (PID 26712) stimmen in PID und Erstellungszeit mit dem Start überein, sind beendet und stehen auf `COMPLETE`, der Worker-Exitcode war 0. Der Worker endete um 13:17:44 Uhr nach 335 s, weit vor Cutoff und Deadline. Es gab keine Pause, keinen verworfenen Teilstand und keine Wiederholung. Beim Abschluss prüfte der Monitor einmalig die SHA-256-Werte aller sechs Checkpoints, berechnete die Stufenbewertung aus den Laufergebnissen neu und glich die Ergebnishashes mit `summary.json` ab. Alles stimmte überein (`result_verified`). Nach dem Lauf bestanden erneut 9/9 Tests, Exitcode 0.

## Ergebnis (Abschluss 19.11.2026)

**Die Stufe δ_max = 0,05 ist nicht bestanden. Damit endet die Prüfung nach §7, und die Stufen 0,10 und 0,20 wurden nicht ausgeführt.** Es gibt keine bestandene Stufe und kein gewähltes δ_max (`chosen_delta_max: null`, `pilot_prerequisite: false`). Nach §7 wird kein Pilot vorbereitet, der Nutzer entscheidet. Die beiden Lesarten der Verlustregel stimmen überein, eine Nutzerentscheidung ist dafür nicht nötig.

**Grund:** Alle sechs Läufe verfehlen die entscheidende Prüfung des Q-Bereichs [−0,05; 1,05]. Alle anderen Bedingungen sind in allen Läufen erfüllt: Alle Werte sind endlich, 0 Grenzverletzungen, ESS im Mittel 255,8–256,0 von 256 (Grenze 25,6), 2 verlorene Parent-Erfolge (Grenze 3).

| Lauf | Q nach Runden [min; max] | Q in Updates inkl. Init | ESS | Entwicklung k/20 (Parent) | verloren | neu | Online k/20 | Drift XYZ Mittel / Max nach Runde 2 |
|---|---|---|---|---|---|---|---|---|
| AC-IL P1 | [−0,153; 1,006] | [−0,464; 1,100] | 255,9 | 5 (5) | – | – | 8 | 0,0037 / 0,0276 |
| AC-IL P2 | [−0,163; 1,013] | [−0,284; 1,323] | 255,8 | 3 (4) | 2100003658 | – | 8 | 0,0041 / 0,0373 |
| AC-IL P3 | [−0,173; 1,016] | [−0,223; 1,059] | 255,9 | 6 (6) | – | – | 7 | 0,0032 / 0,0396 |
| AC-neu P1 | [−0,082; 0,173] | [−0,127; 0,161] | 256,0 | 5 (5) | – | – | 8 | 0,0033 / 0,0352 |
| AC-neu P2 | [−0,058; 0,055] | [−0,094; 0,122] | 256,0 | 3 (4) | 2100003658 | – | 9 | 0,0043 / 0,0408 |
| AC-neu P3 | [−0,203; 0,068] | [−0,102; 0,131] | 256,0 | 6 (6) | – | – | 7 | 0,0033 / 0,0297 |

Die Parent-Baseline auf `constraint_development` ergab 5/20, 4/20 und 6/20. Verlorene Parent-Erfolge nach Lesart B: Parent 1 0, Parent 2 2 (dieselbe Familie in beiden Varianten), Parent 3 0, zusammen 2. Lesart B besteht, Lesart A besteht für beide Varianten. Neue Erfolge gab es keine. Erfolge von AC-neu und AC-IL werden nach §7 nicht verglichen.

**Verlauf je Runde** (Runde 0 vor dem ersten Update, Q-Spannen als [min; max]):

| Lauf | Runde | Online-Erfolge | Critic-Loss (Mittel) | Replay-Q | Probe-Q Parentaktion | Drift XYZ Mittel / Max (unbegrenzt) | w_max |
|---|---|---|---|---|---|---|---|
| AC-IL P1 | 0 | – | – | – | [−0,084; 0,873] | 0 / 0 | – |
| | 1 | 5/10 | 0,00124 | [−0,125; 1,006] | [−0,125; 0,823] | 0,0035 / 0,0302 (0,0392) | 1,27 |
| | 2 | 3/10 | 0,00067 | [−0,153; 1,005] | [−0,106; 0,837] | 0,0037 / 0,0276 (0,0330) | 1,30 |
| AC-IL P2 | 0 | – | – | – | [−0,123; 0,954] | 0 / 0 | – |
| | 1 | 5/10 | 0,00119 | [−0,095; 1,013] | [−0,162; 0,886] | 0,0037 / 0,0403 (0,0896) | 1,54 |
| | 2 | 3/10 | 0,00054 | [−0,080; 1,013] | [−0,139; 0,860] | 0,0041 / 0,0373 (0,0636) | 1,55 |
| AC-IL P3 | 0 | – | – | – | [−0,091; 0,902] | 0 / 0 | – |
| | 1 | 5/10 | 0,00094 | [−0,049; 1,016] | [−0,173; 0,876] | 0,0038 / 0,0307 (0,0389) | 1,34 |
| | 2 | 2/10 | 0,00048 | [−0,071; 1,007] | [−0,145; 0,899] | 0,0032 / 0,0396 (0,0544) | 1,29 |
| AC-neu P1 | 0 | – | – | – | [−0,200; 0,122] | 0 / 0 | – |
| | 1 | 5/10 | 0,00202 | [−0,031; 0,085] | [−0,082; 0,173] | 0,0031 / 0,0287 (0,0360) | 1,01 |
| | 2 | 3/10 | 0,00174 | [−0,032; 0,080] | [−0,026; 0,107] | 0,0033 / 0,0352 (0,0438) | 1,01 |
| AC-neu P2 | 0 | – | – | – | [−0,214; 0,097] | 0 / 0 | – |
| | 1 | 5/10 | 0,00191 | [−0,018; 0,038] | [−0,058; 0,051] | 0,0043 / 0,0361 (0,0693) | 1,01 |
| | 2 | 4/10 | 0,00145 | [−0,014; 0,053] | [−0,034; 0,055] | 0,0043 / 0,0408 (0,0597) | 1,01 |
| AC-neu P3 | 0 | – | – | – | [−0,235; 0,068] | 0 / 0 | – |
| | 1 | 5/10 | 0,00169 | [−0,028; 0,039] | [−0,203; 0,068] | 0,0032 / 0,0257 (0,0293) | 1,01 |
| | 2 | 2/10 | 0,00132 | [−0,020; 0,040] | [−0,150; 0,035] | 0,0033 / 0,0297 (0,0363) | 1,01 |

Die Probe-Q-Werte an der begrenzten Actoraktion weichen höchstens um 0,001 von denen an der Parentaktion ab. Die Onlineerfolge entstehen mit Explorationsrauschen auf `smoke_interaction` und sind kein Leistungsmaß.

**Technische Beobachtungen zur Einordnung** (sie entscheiden nicht und ändern die Bewertung nicht):

- Werte unter −0,05 lagen schon **vor dem ersten Update** vor. Das betrifft die eingefrorenen N2-2-Critics (Probe-Minimum −0,084, −0,123 und −0,091) ebenso wie die zufällige Initialisierung von AC-neu (−0,200, −0,214 und −0,235). Runde 0 geht nach der eingefrorenen Regel nicht in die Bewertung ein. Die Verletzung entsteht also nicht erst durch Divergenz in den Updates. Die Critic-Losses sind klein und sinken, das Maximum nach den Runden liegt bei höchstens 1,016.
- Nur auf dem Replay betrachtet bleiben die drei AC-neu-Läufe im Bereich ([−0,032; 0,085], [−0,018; 0,053] und [−0,028; 0,040]). Die AC-IL-Läufe liegen auch dort darunter (−0,153, −0,095 und −0,071). Die eingefrorene, entscheidende Prüfung umfasst Replay und Probeframes.
- Die AWAC-Gewichte sind praktisch gleichförmig: w_max 1,01–1,55, 0 % gekappt, ESS ≈ 256. Bei λ = 0,1 sind die gemessenen Vorteile zu klein, um die Regression nennenswert zu gewichten. Das Actorupdate wirkt hier also nahezu wie eine ungewichtete Regression auf die eigenen ausgeführten Aktionen.
- Die begrenzte Drift bleibt mit höchstens 0,041 unter δ_max = 0,05. Die unbegrenzte Actorausgabe weicht um bis zu 0,090 ab.

**Kosten:** 6 Läufe mit zusammen 3.000 Critic- und 1.500 Actorupdates, 120 Online-, 120 Entwicklungs- und 60 Baseline-Episoden. Die Updates dauerten im Mittel 4,3 s je Lauf (500 Critic- und 250 Actorupdates, 2 Torch-Threads, sechs Läufe parallel), die Rollouts 101–110 s je Lauf. Worker-Laufzeit 335 s.

**Für die Nutzerentscheidung offen:** Nach §7 entscheidet der Nutzer, wie es nach dem Scheitern von Stufe 0,05 weitergeht. Jede Fortsetzung zum Pilot würde eine Protokollentscheidung verlangen, etwa zur Definition oder Grenze der Q-Bereichsprüfung, zur Ausgangsskala der Critics oder zu λ. Der Agent hat dazu nichts geändert und nichts wiederholt. N2-4 und N3-1 bleiben bis dahin gesperrt.

### Nachweise

- Laufdaten: `praxis/results/critic/three_cube_transfer_v1/ac_smoke_n2_3/` (`summary.json`, `stages/stage_0.05.json`, `runs/d0.05_<variante>_p<p>/result.json` mit `checkpoint.pt`, `baseline/parent_<p>/result.json`)
- `config_sha256` d96d09ea2ce4b68782d113c8324a70ad4a466dbfcf08ada345903b692f65a5a4
- SHA-256 der Laufergebnisse: il_p1 `43c95cb4…bde4372d`, il_p2 `99c82c64…ce01911f`, il_p3 `85b51968…24033ae2`, neu_p1 `dc797401…cd67b80e`, neu_p2 `2996fbbc…86967a81`, neu_p3 `ea2b19a4…64ab0c47`, vollständig in `summary.json`
- Ausgabe der Tabellen, nur lesend: `ac_smoke_report.py` (alle Rohwerte mit `--full`)

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/ac_smoke.py monitor
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/ac_smoke_report.py
```
