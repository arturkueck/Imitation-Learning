# Abbildungen B-4 · Critic N2-2 gegen IL-v2

Die Abbildungen stellen die bereits verifizierten Ergebnisse von N2-2, N2-2b, D1a und D1b nebeneinander. Sie enthalten keine neue Auswertung und keine neue Entscheidung. Maßgeblich bleiben [CRITIC_VALIDATION.md](../../CRITIC_VALIDATION.md), [CRITIC_VALIDATION_V2.md](../../CRITIC_VALIDATION_V2.md) und [ACTION_SENSITIVITY.md](../../ACTION_SENSITIVITY.md).

Der in B-4 ursprünglich vorgesehene Vergleich „Smoke v1 gegen v2“ entfällt. Smoke v2 (N2-3v2) lief nie, weil D1b nicht bestanden wurde und der Nutzer am 20.11.2026 auf [Protokoll v3](../../PROTOCOL_V3.md) gewechselt hat. Die Abbildungen zu Smoke v1 liegen unverändert unter [figures/n2-3](../n2-3/README.md).

## Aufruf

Aus dem Repository-Stamm:

```powershell
./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/b-4/plot.py
```

Matplotlib läuft im Backend `Agg`. Der Generator liest keine Dateien und startet weder Simulation noch Training. Er schreibt nur die vier PNGs in diesen Ordner. Zwei Läufe am 20.11.2026 ergaben bitgleiche PNGs.

## Quellen

Alle Werte stehen unverändert als Konstanten am Anfang von [plot.py](plot.py). Gerundet wird erst bei der Beschriftung.

- **N2-2:** CRITIC_VALIDATION.md, Abschnitt „Ergebnis (Abschluss 19.11.2026)“, beide Tabellen und „Weitere Angaben“ (Monitor-`verify`, `result_verified: true`).
- **IL-v2 (N2-2b):** CRITIC_VALIDATION_V2.md, Abschnitt „Ergebnis und Abschlussprüfung am 20.11.2026“, Tabelle und „Vortraining“ (`VERIFY OK` gegen `summary.json` `767bccfc…2e94`).
- **D1a und D1b:** ACTION_SENSITIVITY.md, die beiden Übersichtstabellen und die Tabellen je Parent und Policy-Phase für δ_max = 0,20 (beide 126/126 Gruppen nachgerechnet).

Nicht gelesen: Laufordner unter `praxis/results/`, Rohtrajektorien, Gewichte, Vorteilsarrays, Testfamilien. 0 Rollouts, 0 Optimizerupdates.

## Abbildungen

| Datei | Inhalt | Art der Aussage |
|---|---|---|
| `01_critic_guete.png` | Je Panel (regulär entscheidet, schwierig nur berichtet) und Parent: gewichtete AUC, MSE-Differenz zur Phasen-Baseline (jeweils mit 95-%-KI) und ECE, mit den Schwellen aus §6 | **Critic-Güte** (Zustandswert) |
| `02_aktionssensitivitaet.png` | Median der Frame-Std. von A (log, Schwelle 0,01), Verhältnis zur Zufallsinitialisierung (Schwelle 1,5), Frames mit eindeutiger Rangfolge k/1.344 je Stufe, dazu Streudiagramm N2-2 gegen IL-v2 je Parent und Policy-Phase bei δ_max = 0,20 | **Aktionssensitivität** |
| `03_vortraining_loss.png` | Getrennte Teilbilder: N2-2 mit letztem mittlerem Loss und Trainings-MSE, IL-v2 mit mittlerem Batch-Loss im ersten und letzten 500er-Fenster | **Loss** auf den eigenen Trainingsdaten |
| `04_technische_stabilitaet.png` | Vorhergesagte Validierungsframes mit 0 nicht endlichen Werten, Critic-Updates je Variante | **Technische Stabilität** |

SHA-256 (Stand 20.11.2026):

| Datei | SHA-256 |
|---|---|
| `plot.py` | `450edac33aa90dd1251a301fefad6a3239e8ed700ae998d5d7b167e6588c4250` |
| `01_critic_guete.png` | `f9344b19037833f2ae983e34c18f86fec885db6325e1ba7c8dfdbc56ea27da32` |
| `02_aktionssensitivitaet.png` | `7ca48fbfc3366b103298905aee85d97bbd27c62894044a37a1a73188ee94f4d5` |
| `03_vortraining_loss.png` | `25487dbde427020b0dbae6ab9fde3a6451fd2580ffca5fff09606b845d8850f3` |
| `04_technische_stabilitaet.png` | `2f5e7a43d634aa092039d597e5c51c905e62e9312bb3ab0bf47f8925c4aef725` |

## Befund in einem Satz je Abbildung

- **01:** IL-v2 hat bei allen drei Parents auf beiden Panels eine höhere Punkt-AUC, eine stärker negative MSE-Differenz und eine kleinere ECE als N2-2. Die Intervalle der beiden Critics überlappen bei allen Kennzahlen außer der AUC von Parent 3 auf dem schwierigen Panel (N2-2 [0,675; 0,865], IL-v2 [0,902; 0,991]). Dort erfüllt IL-v2 alle Bedingungen, N2-2 verfehlt Bedingung 3.
- **02:** IL-v2 ist auf denselben Driftframes nicht aktionssensitiver als N2-2, sondern etwas weniger: Median der Frame-Std. und Verhältnis zur Zufallsinitialisierung sind auf jeder Stufe kleiner, eindeutige Frames gleich (0,05) oder kleiner. Beide liegen um mehr als eine Größenordnung unter 0,01, keine der 42 Gruppen bei δ_max = 0,20 erreicht 10 · 0,001 Q.
- **03:** Beide Losses fallen auf ihren eigenen Daten. Die Werte sind wegen anderer Daten (verrauschte Returns bei IL-v2) und anders berichteter Größen nicht direkt vergleichbar.
- **04:** Beide Critics sind auf allen 347.123 Validierungsframes endlich, je 60.000 Critic-Updates.

## Aussagegrenzen

- **n = 3 Parents.** Jeder Critic gehört zu genau einem A-Parent. Die Intervalle in Abb. 01 beschreiben nur die Unsicherheit über Szenenfamilien je Parent (Bootstrap mit 2.000 Ziehungen, Seed 7300). Die Streuung über ein neues Critic-Training erfassen sie nicht. Mittelwerte über Parents sind absichtlich nicht dargestellt.
- **Kein gepaarter Test N2-2 gegen IL-v2.** Beide Critics wurden auf denselben 450 gespeicherten Rollouts geprüft, die Berichte enthalten aber keine gepaarte Differenz. Die nebeneinanderstehenden Intervalle sind kein Signifikanznachweis für einen Unterschied. Es gab keine vorab festgelegte Vergleichshypothese zwischen den beiden Critics. Die Abbildung ist berichtend.
- **Gleiche Labels.** Die Validierungslabels stammen aus denselben A-Rollouts wie in N2-2 (`dataset_sha256` `fac1e51d…e570`). Die Validierungsfamilien wurden seit N2-2 also mehrfach zur Critic-Abnahme genutzt. Die Testfamilien blieben geschlossen.
- **Abb. 02** misst nur Änderungen der Critic-Ausgabe bei alternativen Aktionen. Die Aktionen wurden nicht in der Simulation ausgeführt. Die Abbildung sagt nichts über die richtige Rangfolge der Aktionen oder den Turmerfolg. Gruppiert wird nach Policy-Phase 0–6, nicht nach den 14 Phasenpunkten aus §6.
- **Abb. 03:** Für N2-2 ist nicht dokumentiert, wie „letzter mittlerer Loss“ gemittelt wurde. Für IL-v2 ist es der mittlere Batch-Loss im letzten 500er-Fenster. Die IL-v2-Laufzeit ist im Bericht nur als „etwa 37 s je Parent“ angegeben.
- **Abb. 04** belegt Endlichkeit und Updatezahl, nichts über Güte oder Erfolg. Für IL-v2 nennt der Bericht nur die Gesamtzahl der Frames. Sie stimmt mit der Summe der N2-2-Frames je Parent und Panel überein, was der Generator per `assert` prüft.
