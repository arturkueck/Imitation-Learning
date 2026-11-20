# Seedzahl des Hauptvergleichs: Werkzeug für N4-2 (B-3)

**Stand 19.11.2026, 23:10 Uhr · Version `seed_count_v1` · ohne Pilotdaten erstellt**

[seed_count.py](seed_count.py) legt die Rechenregel fest, mit der N4-2 die Seedzahl des Hauptvergleichs aus dem kleinsten relevanten Effekt, der Pilotstreuung und dem Budget begründet (AGENTS.md §1, [PROTOCOL.md §10](PROTOCOL.md#10-analyse-pilot-n4-1)). Das Werkzeug rechnet nur mit übergebenen Zahlen oder mit der Ausgabe von [pilot_analysis.py](pilot_analysis.py). Es startet keine Simulation, lädt keine Modelle und führt keine Optimizerupdates aus. Panels mit Testfamilien weist es ab. Es entscheidet nichts: N4-2 begründet die Zahl, und der Nutzer gibt sie mit `MAIN_PROTOCOL.md` frei.

## Hash

| Datei | SHA-256 |
|---|---|
| [seed_count.py](seed_count.py) | `91d82152d729cf8748014d508e649785d8c0b838ea12eaf2ae2063bea37d5a3a` |
| [test_seed_count.py](test_seed_count.py) | `6de93318eb920040dfcb9038f8897c63304ad9af53bca14ce7eab5a0710f3012` |

Jede Ausgabe enthält `tool_sha256`. Liest das Werkzeug eine Pilotauswertung, hält es zusätzlich deren SHA-256 fest. Unter `experiments/**` gilt `-text`, die Bytes bleiben beim Auschecken also erhalten.

## Regel (vor Sicht auf Pilotdaten festgelegt)

| Punkt | Festlegung | Begründung |
|---|---|---|
| Einheit | unabhängiger Trainingsseed: neuer BC-Parent mit gepaarten Armen BC, AC-neu und AC-IL | AGENTS.md §1. Szenen, Checkpoints und Datenerhebungen ersetzen keine Seeds. |
| Kontrast | d_i = Erfolgsquote AC-IL − AC-neu je Seed | primärer Kontrast nach §10 |
| Planungsmodell | zweiseitiger gepaarter t-Test über die Seeds und t-Intervall des mittleren Kontrasts. Die Teststärke wird exakt über die nichtzentrale t-Verteilung berechnet. | Die Streuung der d_i enthält Seed- und Szenenunsicherheit gemeinsam. Ein reines Szenenintervall deckt neues Training nicht ab (AGENTS.md §3). |
| Effekt, α, Teststärke | δ = 0,10, α = 0,05 zweiseitig, 1 − β = 0,80 | δ aus §10. Abweichungen begründet N4-2 vorab. |
| Planungsstreuung | σ_plan = max(σ_oben, σ_Szene) | siehe unten |
| σ_oben | einseitige obere 80-%-Konfidenzgrenze der Pilot-SD: s · sqrt(df / χ²₀,₂₀;df), df = Pilotseeds − 1 | Bei 3 Pilotseeds (df = 2) ist s sehr unsicher. Der Faktor beträgt 2,117. Der Punktwert s und die Seedzahl bei s werden mitberichtet. |
| σ_Szene | sqrt(q / N): q ist der Anteil diskordanter Familien (Mittel über die Pilotparents), N die Familienzahl je Seed im Hauptvergleichspanel | Untergrenze, damit ein zufällig kleines s nicht zu wenige Seeds ergibt. Var(d̂ ∣ Seed) = (q − Δ²)/N ≤ q/N, also leicht konservativ. |
| Mindestzahl | 4 | mehr als drei Seeds, AGENTS.md §1 |
| Erforderlich | n = max(4, n_Teststärke, optional n_Präzision für eine Ziel-Halbbreite) | |
| Budget | bezahlbar = ⌊(Budget − Fixkosten) / Kosten je Seed⌋, Kosten je Seed als benannte Bestandteile in Stunden | Kosten bleiben aufgeschlüsselt |
| Budget reicht nicht | keine Empfehlung. Ausgegeben werden Teststärke, Halbbreite und kleinster nachweisbarer Effekt bei der bezahlbaren Zahl sowie „Nutzerentscheidung“ | keine stille Reduktion (AGENTS.md §1) |

Ohne scipy in der venv sind die t-, χ²- und Normalverteilung samt Quantilen sowie die nichtzentrale t-Teststärke im Skript implementiert. Die Tests prüfen sie gegen Tabellenwerte und Monte-Carlo.

## Aufruf (in N4-2)

```
praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/seed_count.py plan \
  --pilot-analysis <analysis.json> --eval-families <N je Seed> \
  --cost bc_parent=<h> --cost critic_data=<h> --cost ac_runs=<h> --cost evaluation=<h> \
  --budget-hours <h> [--fixed-hours <h>] [--target-halfwidth <w>] --out <seed_count.json>
```

Alternativ gibt man `--pilot-differences d1 d2 d3` oder eine begründete Annahme `--sd σ` an. Die Diskordanzrate kommt aus der Pilotauswertung oder aus `--discordance-rate`. `seed_count.py example` gibt die Planungstabelle unten aus.

## Planungstabelle (Beispielwerte, keine Pilotdaten)

Erzeugt mit `seed_count.py example`, δ = 0,10, α = 0,05 zweiseitig, Teststärke 0,80. Die letzte Spalte nennt die Pilot-SD aus drei Seeds, deren obere 80-%-Grenze gerade σ_plan ergibt.

| σ_plan | n Teststärke | n erforderlich (≥ 4) | Teststärke dort | 95-%-Halbbreite dort | Pilot-s mit dieser oberen Grenze (3 Seeds) |
|---:|---:|---:|---:|---:|---:|
| 0,05 | 5 | 5 | 0,909 | 0,062 | 0,024 |
| 0,08 | 8 | 8 | 0,856 | 0,067 | 0,038 |
| 0,10 | 10 | 10 | 0,803 | 0,072 | 0,047 |
| 0,12 | 14 | 14 | 0,822 | 0,069 | 0,057 |
| 0,15 | 20 | 20 | 0,807 | 0,070 | 0,071 |
| 0,20 | 34 | 34 | 0,808 | 0,070 | 0,094 |
| 0,25 | 52 | 52 | 0,808 | 0,070 | 0,118 |

Lesart: Streuen die drei Pilotkontraste mit s ≈ 0,047, ergibt die Regel 10 Seeds. Bei s ≈ 0,094 sind es schon 34. Zur Einordnung: Allein die Szenenstreuung beträgt bei q = 0,30 auf 150 Familien σ_Szene = 0,045.

## Nachweis

- `praxis/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider experiments/critic/three_cube_transfer_v1/test_seed_count.py`: **61/61 bestanden**. Zusammen mit `test_pilot_analysis.py` sind es 88/88.
- Geprüft werden:
  - Quantile der t-Verteilung (df 1–30), der Normal- und der χ²-Verteilung gegen Tabellenwerte (Toleranz 2·10⁻⁶ bzw. 2·10⁻⁵)
  - Teststärke bei d = 1, n = 10: 0,8031 wie in G*Power. Ohne Effekt ergibt sich α.
  - Teststärke gegen Monte-Carlo mit 400.000 Wiederholungen für n = 4, 5 und 8 (Abweichung ≤ 0,004)
  - n = 10 für d = 1 und n = 34 für d = 0,5, Minimalität und Monotonie
  - kleinster nachweisbarer Effekt als Umkehrung der Teststärke, Präzisionsziel
  - obere Grenze der SD (Faktor 2,117 bei df = 2) und bindende Szenenuntergrenze bei s = 0
  - Mindestzahl 4 bei sehr kleiner Streuung
  - Budget machbar, nicht ausreichend und unter der Mindestzahl, jeweils ohne stille Reduktion
  - 13 ungültige Eingaben
  - Lesen einer synthetischen `pilot_analysis_v1`-Ausgabe mit Diskordanzraten, Abweisung von Testpanels, falscher Version und inkonsistenter Diskordanztabelle
  - Kommandozeile mit byte-identischer JSON-Ausgabe bei zwei Läufen
- `seed_count.py example --json` liefert bei zwei Läufen dieselbe Ausgabe, SHA-256 `8aa87e54…ee73`.
- 0 Rollouts, 0 Optimizerupdates, keine Pilotdaten, Testfamilien geschlossen.

## Aussagegrenzen

Die Rechnung plant und weist keine Wirksamkeit nach. Aus drei Pilotseeds ist σ nur grob bestimmbar, deshalb gilt die obere Grenze. Die Pilotparents teilen Szenen, ihre Kontraste sind daher keine unabhängigen Szenenstichproben. Im Pilot wird auf 100 Validierungsfamilien gemessen. Hat der Hauptvergleich mehr Familien je Seed, enthält das Pilot-s etwas mehr Szenenstreuung, und die Planung liegt auf der sicheren Seite. Die Kosten je Seed sind noch nicht gemessen. Für neue BC-Parents, Critic-Daten, AC-Läufe und Auswertung liefern erst N3-1 und N4-4 die Zeiten. Die Auswertung des Hauptvergleichs selbst legt N4-3 in `MAIN_PROTOCOL.md` fest.
