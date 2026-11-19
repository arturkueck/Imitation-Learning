# Abbildungen N2-3 · Technischer Actor-Critic-Smoke (Stufe δ_max = 0,05)

Die Abbildungen zeigen die bereits verifizierten Ergebnisse von N2-3. Sie enthalten keine neue Auswertung und keine neue Entscheidung. Maßgeblich bleibt [AC_SMOKE.md](../../AC_SMOKE.md): Stufe 0,05 ist nicht bestanden, weil alle sechs Läufe die Q-Bereichsprüfung verfehlen. Es gibt kein gewähltes δ_max, und die Nutzerentscheidung nach §7 steht aus.

## Aufruf

Aus dem Repository-Stamm:

```powershell
./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/n2-3/plot.py
```

Matplotlib läuft im Backend `Agg`. Der Generator liest keine Dateien, startet weder Simulation noch Training und schreibt nur die sechs PNGs in diesen Ordner. Die Ausgabe ist bei gleicher Umgebung reproduzierbar.

## Quellen

Die einzige Quelle ist [AC_SMOKE.md](../../AC_SMOKE.md), Abschnitt „Ergebnis (Abschluss 19.11.2026)“. Der Monitor hat diese Werte beim Abschluss gegen `summary.json` und die Checkpoint-Hashes abgeglichen (`result_verified`). Übernommen sind:

- die Lauftabelle: Q nach den Runden, Q während der Updates inkl. Init, ESS, Entwicklungserfolge k/20 samt Parent-Baseline, verlorene Familien und Online-Erfolge,
- die Tabelle „Verlauf je Runde“: Online-Erfolge je Runde, mittlerer Critic-Loss, Replay-Q, Probe-Q der Parentaktion, Drift XYZ Mittel/Max (begrenzt) und Max (unbegrenzt) sowie w_max,
- die Angaben im Fließtext: Parent-Baseline 5/4/6 von 20, 0 Grenzverletzungen, alle Werte endlich, 0 % gekappt, keine neuen Erfolge, Lesarten A und B.

Grenzen und Definitionen stammen aus [PROTOCOL.md §7](../../PROTOCOL.md#7-bindung-an-bc-und-constraint-kandidaten) und dem Abschnitt „Festlegungen der Umsetzung“ in AC_SMOKE.md. Die Drift ist laut Code (`ac_smoke.py`, Funktion `drift`) der Betrag |Δa| je XYZ-Komponente über alle Probeframes. Diese Stelle wurde nur gelesen und nicht ausgeführt.

Die Werte stehen als Konstanten am Anfang von `plot.py`, mit der Genauigkeit des Berichts und ohne weitere Rundung. Gerundet wird erst bei der Beschriftung, mit deutschem Dezimalkomma. Neu berechnet werden nur Quoten k/n mit 95-%-Wilson-Intervallen, die Summen verlorener Erfolge und die Erfüllt/Verfehlt-Matrix aus den berichteten Werten und den §7-Grenzen. Alle Neuberechnungen stimmen mit dem Bericht überein.

Nicht verwendet wurden Rohtrajektorien, Episoden- und Ergebnis-JSONs, Checkpoints und Gewichte, `ac_smoke_report.py --full` sowie Testfamilien. Der Laufordner `praxis/results/critic/three_cube_transfer_v1/ac_smoke_n2_3/` ist in diesem Worktree nicht vorhanden und wurde nicht gelesen.

## Abbildungen

| Datei | Inhalt | Art der Aussage |
|---|---|---|
| `01_actor_drift.png` | Drift gegenüber dem Parent nach Runde 0, 1 und 2. Zeilen nach Variante (AC-IL, AC-neu), Linien nach Parent. Spalten: mittlere und maximale begrenzte Abweichung sowie maximale unbegrenzte Abweichung, Grenze δ_max = 0,05 eingezeichnet | **Bindung an den Parent** (technisch) |
| `02_q_bereich.png` | Je Lauf die Q-Spanne [min; max] nach den Runden (entscheidend) und während der Updates inkl. Init (nur berichtet), zulässiger Bereich [−0,05; 1,05] | **Technische Stabilität**, entscheidendes Kriterium |
| `03_q_verlauf_runden.png` | Q-Spannen je Runde und Lauf: Probeframes mit Parentaktion (Runde 0–2) und Replay (Runde 1–2). Runde 0 ist als nicht bewertet markiert | **Technische Stabilität**, Einordnung |
| `04_stabilitaetskriterien.png` | (a) mittlere ESS gegen die Grenze 25,6, (b) w_max je Runde, (c) Erfüllt/Verfehlt-Matrix der technischen §7-Kriterien je Lauf | **Technische Stabilität** |
| `05_parent_erfolge.png` | (a) Vollständiger Erfolg auf `constraint_development`: Parent, AC-IL und AC-neu je Parent als k/20 mit Wilson-KI, (b) verlorene Parent-Erfolge nach Lesart B mit den Grenzen und Lesart A im Text, (c) Online-Erfolge je Runde k/10, ausdrücklich kein Leistungsmaß | **Aufgabenerfolg** (Erhalt) |
| `06_critic_loss.png` | Mittlerer Critic-Loss je Runde und Lauf | **Loss** |

Loss (06), technische Stabilität (02–04, Drift in 01) und Aufgabenerfolg (05) stehen bewusst in getrennten Abbildungen.

## Aussagegrenzen

- **Technischer Smoke, keine Wirksamkeitsaussage.** Nach §7 werden Erfolge von AC-IL und AC-neu nicht miteinander verglichen. Die Abbildungen ordnen die Varianten nebeneinander an, damit jeder Lauf sichtbar ist. Ein Unterschied zwischen den Varianten ist daraus nicht abzulesen. Die Testfamilien blieben geschlossen.
- **n = 3 unabhängige Parent-Initialisierungen.** Je Variante gibt es drei Läufe, also einen Lauf je Parent. AC-IL und AC-neu desselben Parents teilen Parent, RNG-Ströme und Szenen und sind daher keine unabhängigen Wiederholungen. Mittelwerte über Läufe sind absichtlich nicht dargestellt. Drift, Q, ESS, w_max und Loss haben je Lauf nur einen Wert und deshalb keine Intervalle.
- **Abb. 01:** Die Drift wird auf festen Probeframes gemessen (64 je Policy-Phase), nicht auf den ausgeführten Trajektorien. Die begrenzte Drift bleibt durch die Projektion unter δ_max. Die unbegrenzte Actorausgabe überschreitet 0,05 in AC-IL P2, AC-IL P3 und AC-neu P2. Das ist keine Grenzverletzung, weil nur die projizierte Aktion ausgeführt wird. Die unbegrenzte Drift in Runde 0 ist mit 0 eingetragen, weil der Actor vor dem ersten Update identisch mit dem Parent ist (§8, Prüfung in `ac_smoke.py`). Die Tabelle des Berichts nennt für Runde 0 nur „0 / 0“. Die Drift sagt nichts über den Aufgabenerfolg.
- **Abb. 02/03:** Die entscheidende Spanne umfasst Replay und Probeframes nach Runde 1 und 2. Probe-Q der Actoraktion ist nicht eigens gezeichnet, weil es laut Bericht höchstens 0,001 von Probe-Q der Parentaktion abweicht. Unterschreitungen gab es schon in Runde 0 (eingefrorener N2-2-Critic bzw. zufällige Initialisierung). Runde 0 entscheidet nach der eingefrorenen Regel nicht. Abb. 03 belegt nur, dass die Verletzung nicht erst durch die Updates entsteht. Eine Ursachenanalyse oder ein Vorschlag zur Protokolländerung ist das nicht.
- **Abb. 04:** ESS ist der Mittelwert über alle Actorupdates eines Laufs, Werte je Runde liegen nicht vor. Die Matrix zeigt nur die technischen Kriterien. Das vierte §7-Kriterium (verlorene Erfolge) steht in Abb. 05.
- **Abb. 05:** Die Nenner umfassen alle 20 Familien `constraint_development` (2100003650–2100003669), ohne Ausschlüsse. Parent und Läufe teilen diese Familien. Die Wilson-Intervalle beschreiben nur die Szenenunsicherheit je Quote und nicht die Unsicherheit einer gepaarten Differenz oder die Streuung über neues Training. Der Erhalt wird über die Verlustzählung nach §7 beurteilt, nicht über die Intervalle. Die 20 Familien sind Entwicklungsdaten, kein Test. Die Online-Erfolge (c) entstehen mit Explorationsrauschen auf `smoke_interaction` und sind laut Bericht kein Leistungsmaß.
- **Abb. 06:** Der Critic-Loss ist der vom Bericht genannte Rundenmittelwert auf dem eigenen Online-Replay. Ob er über beide Twin-Critics summiert oder gemittelt ist, geht aus der Quelle nicht hervor. AC-IL startet vom vortrainierten Critic, AC-neu zufällig. Die Niveaus sind deshalb kein Gütevergleich. Ein kleiner, sinkender Loss belegt weder den Q-Bereich noch einen Aufgabenerfolg.
