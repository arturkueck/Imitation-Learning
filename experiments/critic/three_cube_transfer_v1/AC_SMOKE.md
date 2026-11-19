# N2-3 · Technischer Actor-Critic-Smoke

**Status: läuft** (gestartet 19.11.2026, 13:12 Uhr Europe/Berlin) · technischer Smoke **ohne Wirksamkeitsaussage** · [Code](ac_smoke.py) · [Tests](test_ac_smoke.py) · [Protokoll §7](PROTOCOL.md#7-bindung-an-bc-und-constraint-kandidaten)

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

## Ergebnis

Folgt nach Abschluss des Laufs. Laufdaten: `praxis/results/critic/three_cube_transfer_v1/ac_smoke_n2_3/`. Monitor:

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/ac_smoke.py monitor
```
