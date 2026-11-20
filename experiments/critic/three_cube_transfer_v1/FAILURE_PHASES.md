# B-2 · Fehlerphasen der A-Parents

Stand 19.11.2026, Nacht 2 · Aufgabe B-2 aus dem [Nachtplan](NACHTPLAN.md#aufgabenstapel-nacht-2-1920112026-protocol_v2-plan-b) · berichtend, keine Entscheidung.

Diese Auswertung verwendet nur bereits erhobene Daten der unveränderten A-Parents: N1-4 (`calibration`, 100 Familien × 3 Parents) und N2-1 (`critic_data`, 300 Familien × 3 Parents). Dafür gab es 0 Rollouts und 0 Optimizerupdates. Validierungs- und Testfamilien wurden nicht berührt. Das Skript weist jede Szene außerhalb dieser beiden Splits vor der Rechnung ab. Code: [failure_phases.py](failure_phases.py) · Tests: [test_failure_phases.py](test_failure_phases.py) · Ergebnisdatei: [failure_phases.json](failure_phases.json)

## Datengrundlage und Grenzen

- **N1-4** speichert nur Episodenzusammenfassungen: Ausgang, Endgrund, erreichte zweite Platzierung und längste gültige Turmfolge. Endphase und Korrekturabstand sind dort **nicht erhoben**. Für N1-4 werden deshalb nur Stufe und Ausgang berichtet.
- **N2-1** speichert je Frame Stufe, Policy-Phase, Rückzug, privilegierten Zustand und Parentaktion ([Datenvertrag](CRITIC_DATA.md)). Endphase und Korrektur stammen nur aus N2-1.
- Die drei Parents teilen jeweils dieselben Familien. Gepoolte Zahlen sind deshalb keine unabhängigen Wiederholungen.

## Operationalisierung (vor der Auswertung festgelegt)

- **Endpunkt** eines Fehlschlags: Stufe, Policy-Phase und Rückzug im letzten Frame. Phasen: 0 Anfahren, 1 Absenken zum Greifen, 2 Schließen, 3 Anheben, 4 Transport, 5 Ablegen, 6 Lösen. Die Phasen 0–3 sind auf den zu tragenden Würfel verankert, 4–6 auf die Basis (`core.DevicePolicy`).
- **Endsegment:** der längste Schluss der Episode mit unverändertem Endpunkt.
- **Nötige Korrektur** (horizontal, Zustand nach der letzten Aktion): In den Phasen 0–3 ist das der Versatz vom Greifer zum zu tragenden Würfel. In den Phasen 4–6 ist es der Versatz vom zu tragenden Würfel zur Basis, gekürzt um die Gültigkeitstoleranz von 9 mm aus `prefix_valid`. Für den Rückzug ist keine Korrektur definiert. Vertikale Fehler, Kontakt, Greiferzustand und Geschwindigkeit gehen nicht in die Korrektur ein.
- **Reichweite unter der Bindung** (v1 §7, `b = min(δ_max, 0,5·|a_parent|)`): je Achse `R = 0,05 m · Σ b` über das Endsegment. 0,05 m je Aktionseinheit ist `output_max` des OSC-Reglers. **Quote** `q = max_Achse |e| / R`. „Innerhalb“ heißt q ≤ 1, „außerhalb“ q > 1, „keine nötig“ e = 0. Geprüft wurden die Stufen δ_max ∈ {0,05; 0,10; 0,20}.
- **Ruheanteil:** Anteil der Endsegmentframes, in denen bei δ_max = 0,20 beide horizontalen Breiten unter 0,01 liegen, also unter 0,5 mm Sollwertverschiebung je Schritt.

**Aussagegrenze der Quote.** R summiert zusätzlich kommandierbare Sollwertverschiebungen. Reglerdynamik, Kontakte und die Rückwirkung einer früheren Korrektur auf den weiteren Verlauf sind nicht modelliert. q ≤ 1 heißt deshalb nur, dass die Korrektur in idealisierter Kinematik nicht durch die Bindung ausgeschlossen ist. Ob ein Critic sie findet, sagt q nicht. Die Korrektur wird am Episodenende gemessen, also nach dem Hängenbleiben, nicht beim Eintritt in die Phase.

**Nach der ersten Ausgabe ergänzt, Definitionen unverändert:** Aufschlüsselung der Quoten je Endpunkt, das Merkmal „getragener Würfel auf dem Tisch“ und die Gegenprobe „Basis intakt beim Eintritt in Stufe 2“. Anlass war, dass „über 0,05 m“ auch einen auf der Basis liegenden Würfel erfasst und die Basis am Ende häufig nicht mehr gültig war.

## Ergebnisse

**Ausgänge je Parent** (Fehlschläge nach erreichter Stufe; „Turm kurz gültig“ = mindestens ein gültiger Dreierframe, aber keine 50 in Folge):

| Daten | Parent | Erfolge | Fehlschläge | davon Stufe 1 | davon Stufe 2 | Turm kurz gültig | Endgrund Horizont |
|---|---|---:|---:|---:|---:|---:|---:|
| N1-4 | 1 | 40/100 | 60/100 | 14/60 | 46/60 | 0/60 | 60/60 |
| N1-4 | 2 | 30/100 | 70/100 | 18/70 | 52/70 | 0/70 | 70/70 |
| N1-4 | 3 | 33/100 | 67/100 | 19/67 | 48/67 | 0/67 | 67/67 |
| N1-4 | gesamt | 103/300 | 197/300 | 51/197 | 146/197 | 0/197 | 197/197 |
| N2-1 | 1 | 125/300 | 175/300 | 40/175 | 135/175 | 2/175 | 175/175 |
| N2-1 | 2 | 92/300 | 208/300 | 48/208 | 160/208 | 2/208 | 208/208 |
| N2-1 | 3 | 108/300 | 192/300 | 63/192 | 129/192 | 3/192 | 192/192 |
| N2-1 | gesamt | 325/900 | 575/900 | 151/575 | 424/575 | 7/575 | 575/575 |

Familien nach Zahl scheiternder Parents (0/1/2/3): N1-4 27/8/6/59 von 100, N2-1 78/33/25/164 von 300.

**Endpunkte der 575 N2-1-Fehlschläge.** Die Spalten ab „über 0,05 m“ beschreiben den Endzustand. Der getragene Würfel ist bei Stufe 1 B und bei Stufe 2 C.

| Stufe | Phase | P1 | P2 | P3 | gesamt | Endsegment, Frames Median [Q1; Q3] | Ruheanteil Median | Korrektur in mm Median [Q1; Q3] | über 0,05 m | auf Tisch | auf Basis | Basis intakt Ende | Basis intakt beim Eintritt in Stufe 2 |
|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 1 Absenken | 0 | 10 | 5 | 15 | 981 [980; 982] | 0,78 | 3,5 [3,2; 5,4] | 0/15 | 15/15 | 0/15 | 15/15 | – |
| 1 | 4 Transport | 4 | 8 | 30 | 42 | 910 [901; 913] | 0,93 | 1,1 [0,0; 4,1] | 42/42 | 0/42 | 0/42 | 42/42 | – |
| 1 | 5 Ablegen | 0 | 1 | 0 | 1 | 909 | 0,01 | 59,4 | 0/1 | 1/1 | 0/1 | 1/1 | – |
| 1 | 6 Lösen | 36 | 29 | 28 | 93 | 868 [857; 873] | 0,12 | 35,3 [32,5; 40,2] | 2/93 | 88/93 | 0/93 | 93/93 | – |
| 2 | 1 Absenken | 29 | 50 | 63 | 142 | 841 [838; 844] | 0,73 | 20,4 [12,9; 25,7] | 0/142 | 142/142 | 0/142 | 51/142 | 142/142 |
| 2 | 4 Transport | 17 | 9 | 21 | 47 | 757 [748; 786] | 0,90 | 11,1 [0,0; 155,8] | 26/47 | 21/47 | 0/47 | 39/47 | 47/47 |
| 2 | 5 Ablegen | 0 | 4 | 0 | 4 | 722 [722; 733] | 0,00 | 55,4 [54,8; 108,2] | 0/4 | 4/4 | 0/4 | 1/4 | 4/4 |
| 2 | 6 Lösen | 89 | 97 | 45 | 231 | 740 [726; 750] | 0,98 | 72,4 [3,2; 191,1] | 93/231 | 138/231 | 29/231 | 153/231 | 231/231 |

Kein Fehlschlag endet im Rückzug oder in den Phasen 0, 2 und 3. Alle 575 laufen bis zum Horizont. Das Endsegment umfasst im Median 722–981 der höchstens 1.000 Frames. Die Fehlschläge sind also überwiegend ein langes Verharren in einer Phase. Die geometrische Gegenprobe bestätigt die Basis beim Eintritt in Stufe 2 in 424/424 Fällen. Am Ende ist sie nur noch in 244/424 Stufe-2-Fehlschlägen intakt (51/142, 39/47, 1/4 und 153/231).

**Korrektur gegen die Bindung, je Gruppe und Parent** (keine nötig / innerhalb / außerhalb):

| Gruppe | δ_max | P1 | P2 | P3 | gesamt |
|---|---|---|---|---|---|
| Greifen (Phasen 0–3) | 0,05 | 0 / 29 / 0 | 0 / 60 / 0 | 0 / 68 / 0 | 0 / 157 / 0 |
| Greifen (Phasen 0–3) | 0,10 | 0 / 29 / 0 | 0 / 60 / 0 | 0 / 68 / 0 | 0 / 157 / 0 |
| Greifen (Phasen 0–3) | 0,20 | 0 / 29 / 0 | 0 / 60 / 0 | 0 / 68 / 0 | 0 / 157 / 0 |
| Ablage (Phasen 4–6) | 0,05 | 4 / 70 / 72 | 20 / 68 / 60 | 38 / 61 / 25 | 62 / 199 / 157 |
| Ablage (Phasen 4–6) | 0,10 | 4 / 72 / 70 | 20 / 69 / 59 | 38 / 62 / 24 | 62 / 203 / 153 |
| Ablage (Phasen 4–6) | 0,20 | 4 / 77 / 65 | 20 / 72 / 56 | 38 / 68 / 18 | 62 / 217 / 139 |

Je Endpunkt (gesamt, δ_max 0,05 / 0,10 / 0,20 als keine/innerhalb/außerhalb): In Stufe 2, Phase 4 verschiebt sich die Verteilung von 13/16/18 über 13/20/14 zu 13/34/0. In Stufe 2, Phase 6 bleibt sie bei allen Stufen 29/64/138, in Stufe 2, Phase 5 bei 0/3/1. Alle übrigen Endpunkte liegen bei jeder Stufe vollständig innerhalb oder brauchen keine Korrektur (Stufe 1, Phase 4: 20/22/0).

Kennzahlen der Gruppen: Bei Greifen beträgt die Korrektur im Median 19,7 mm [6,2; 25,0], der Ruheanteil 0,74 und die mittlere Breite bei δ_max = 0,20 im Median 0,13 mm je Schritt. Bei Ablage beträgt die Korrektur im Median 35,4 mm [3,3; 143,3], höchstens 320 mm, der Ruheanteil 0,98 und die Breite 0,020 mm je Schritt. Keine Quote war unendlich.

## Befund (berichtend)

1. **Wo die A-Parents scheitern.** In beiden Datensätzen scheitert die Mehrheit nach erreichter zweiter Platzierung: in N1-4 bei 146/197 und in N2-1 bei 424/575 Fehlschlägen. Die drei häufigsten Endpunkte in N2-1 sind Stufe 2 · Lösen (231), Stufe 2 · Absenken zum Greifen von C (142) und Stufe 1 · Lösen (93). In Stufe 1 · Lösen liegt B in 88/93 Fällen neben A auf dem Tisch, im Median 35 mm außerhalb der Toleranz. Parent 3 verharrt auffällig oft in Stufe 1 · Transport (30/42).
2. **Basis.** Bei 180 der 424 Stufe-2-Fehlschläge ist das Paar A–B am Ende nicht mehr gültig, obwohl es beim Eintritt in Stufe 2 in allen 424 gültig war. Wann es gestört wurde, misst diese Auswertung nicht.
3. **Abstand zur Bindung.** Die Korrekturen beim Greifen sind über das lange Endsegment kumulativ bei jeder Stufe erreichbar (157/157). Der Parent ruht dort aber im Median in 74 % der Frames. In der Ablagegruppe liegen 139–157 von 418 Fehlschlägen außerhalb der Bindung. Eine größere Stufe δ_max ändert daran wenig (0,05 → 0,20: 157 → 139). In Stufe 2 · Lösen ändert sie nichts (138/231 bei jeder Stufe). Dort ruht der Parent fast vollständig (Ruheanteil 0,98). Die Breite wird dann durch `0,5·|a_parent|` begrenzt, nicht durch δ_max.

Diese Zahlen beschreiben die eingefrorenen Parents auf bereits geöffneten Familien. Sie sind keine Wirksamkeitsaussage über AC-Arme und werden nicht zur Wahl von δ_max, τ oder anderen Protokollgrößen verwendet. Die Stufenwahl bleibt nach Protokoll v2 §B–§D an technische Stabilität gebunden.

## Nachweis und Reproduktion

```powershell
& praxis/.venv/Scripts/python.exe -m pytest -q experiments/critic/three_cube_transfer_v1/test_failure_phases.py
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/failure_phases.py run
```

- 9/9 Tests auf synthetischen Daten grün. Sie prüfen die Splitsperre, das Endsegment, beide Korrekturdefinitionen, die Reichweite unter der Bindung, Quoten und Kategorien, Endzustandsmerkmale, eine Episode von Anfang bis Ende und vollständige Nenner.
- Eingaben vor der Rechnung geprüft: N1-4 `raw_sha256` `c8888112bac1b9ce403bd4070aeaca38c878ab61bc5f9ebef9a7a1838bdcf573` gegen `summary.json`, Erfolgszahl 103 bestätigt. N2-1: Hash jeder der 900 `.npz` gegen ihre Metadatei, `dataset_sha256` `9f0aeaaff68734ffa2bd2a14bc91bd32c3c92db5fc255af1029a580daff9a2ba` gegen `summary.json` und [CRITIC_DATA.md](CRITIC_DATA.md).
- SHA-256 `failure_phases.py` `003154a8030bf0796e77c2c05f375bf4694dc84a289c97532e2db97123d85e33` (auch in der Ergebnisdatei). SHA-256 `failure_phases.json` `e57ccb7a4bc9083c5001de9b5d4cf5b7097944ef33c62fd419ddfab625034298`, bei zwei Läufen identisch. Laufzeit etwa 3 s, Exitcode 0.
