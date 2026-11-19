# Abbildungen N2-2 · Critic-Vortraining und Critic-Validierung

Die Abbildungen zeigen die bereits verifizierten Ergebnisse von N2-2. Sie enthalten keine neue Auswertung und keine neue Entscheidung. Maßgeblich bleibt [CRITIC_VALIDATION.md](../../CRITIC_VALIDATION.md).

## Aufruf

Aus dem Repository-Stamm:

```powershell
./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/n2-2/plot.py
```

Matplotlib läuft im Backend `Agg`. Der Generator liest keine Dateien, startet keine Simulation und kein Training und schreibt nur die vier PNGs in diesen Ordner.

## Quellen

Die einzige Quelle ist [CRITIC_VALIDATION.md](../../CRITIC_VALIDATION.md), Abschnitt „Ergebnis (Abschluss 19.11.2026)“. Diese Werte hat `critic_validation.py monitor` mit einem einmaligen `verify` gegen `summary.json` abgeglichen (`result_verified: true`). Übernommen sind:

- beide Tabellen (`validation_normal`, `validation_hard`) mit A-Erfolgen, geeigneten Punkten, AUC [95-%-KI], MSE von Critic und Phasen-Baseline, Differenz [95-%-KI] und ECE,
- aus „Weitere Angaben“: Endlichkeit und Frameanzahlen, Phasenpunkt-Einträge, Endgründe sowie Vortrainingskosten, letzter mittlerer Loss und Trainings-MSE.

Die Werte stehen als Konstanten am Anfang von `plot.py`, ohne weitere Rundung, also mit der Genauigkeit des Berichts. Gerundet wird erst bei der Beschriftung, mit deutschem Dezimalkomma. Neu berechnet werden nur Erfolgsquoten (k/n) und deren 95-%-Wilson-Intervalle aus den berichteten Zählungen.

Nicht verwendet: Rohtrajektorien, Episoden-JSONs, Critic-Gewichte, `critics/parent_p.json`, Testfamilien. Der Laufordner unter `praxis/results/` war für diese Arbeit nicht zugänglich und wurde nicht gelesen.

## Abbildungen

| Datei | Inhalt | Art der Aussage |
|---|---|---|
| `01_vortraining_loss.png` | Je Parent der letzte mittlere Trainingsloss und die MSE auf den eigenen Trainingsdaten (Return²), dazu die Laufzeit von 20.000 Updates | **Loss** auf Trainingsdaten |
| `02_critic_validierung.png` | Zeilen `validation_normal` (entscheidet) und `validation_hard` (entscheidet nicht). Spalten: gewichtete AUC [95-%-KI] mit den Schwellen 0,60 und 0,50 sowie geeigneten Punkten k/14, MSE von Critic und Phasen-Baseline, MSE-Differenz [95-%-KI] mit Nulllinie, ECE mit Schwelle 0,10 | **Critic-Güte** nach §6 |
| `03_bc_aufgabenerfolg.png` | Vollständiger Erfolg im Dreierturm der unveränderten A-Parents, k/n je Panel mit 95-%-Wilson-KI | **Aufgabenerfolg** (BC) |
| `04_technische_stabilitaet.png` | Geprüfte Frames je Parent und Panel, jeweils 0 nicht endliche Criticwerte, dazu die Phasenpunkt-Einträge | **Technische Stabilität** |

Loss, Critic-Güte, Aufgabenerfolg und technische Stabilität stehen bewusst in getrennten Abbildungen.

## Aussagegrenzen

- **n = 3 Parents.** Jeder Critic gehört zu genau einem A-Parent (Critic-Seeds 7101–7103). Alle Intervalle beschreiben die Unsicherheit über Szenenfamilien je Parent: in Abb. 02 per Perzentil-Bootstrap mit 2.000 Ziehungen und Seed 7300, in Abb. 03 per Wilson. Die Streuung über ein neues Training erfassen sie nicht. Mittelwerte über Parents sind absichtlich nicht dargestellt.
- **Abb. 01 zeigt nur Endwerte, keine Losskurve.** Die Kurven liegen in den Critic-Metadaten im Laufordner und wurden hier nicht verwendet. Trainingsloss und Trainings-MSE gelten für die eigenen N2-1-Daten und sagen nichts über Validierung, Generalisierung oder Aufgabenerfolg. Der Bericht weist „letzten mittleren Loss“ und „MSE auf den eigenen Trainingsdaten“ als zwei getrennte Größen aus. Sie stehen deshalb in getrennten Teilbildern und sind nicht direkt vergleichbar. Wie der Loss genau gemittelt wird, ist in der Quelle nicht angegeben.
- **Abb. 02:** Nach §6 entscheidet nur `validation_normal`, und dort bestehen alle drei Critics. Auf `validation_hard` verfehlt Parent 3 Bedingung 3, das Differenzintervall schließt die 0 ein. Zudem waren dort nur 12 von 14 Punkten geeignet. Das hat keinen Einfluss auf die Entscheidung. Die Critic-Güte am Phasenpunkt sagt nichts darüber aus, ob ein Actor-Critic-Training den Aufgabenerfolg verbessert.
- **Abb. 03:** Die Nenner umfassen alle Familien des Panels, ohne Ausschlüsse: 100 auf `validation_normal`, 50 auf `validation_hard`. Alle Fehlschläge endeten am Horizont. Es sind Validierungsergebnisse und kein Test, die Testfamilien blieben geschlossen. Dieselben Rollouts liefern die Labels für Abb. 02, die beiden Abbildungen sind also nicht unabhängig. Dass das schwierige Panel keine niedrigere Erfolgsquote hat, deckt sich mit der nicht monotonen Kalibrierung aus N1-5. Ein Schwierigkeitseffekt lässt sich daraus nicht ableiten.
- **Abb. 04** belegt nur die Endlichkeit (Bedingung 4) und die technische Vollständigkeit. Über Güte oder Erfolg sagt sie nichts.
