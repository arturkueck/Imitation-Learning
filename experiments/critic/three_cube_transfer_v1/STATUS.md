# Fortschritt der Nachtläufe zum Dreierturm

Gesamtpause: ja

Bei einem Sofortstopp nach [Nachtplan](NACHTPLAN.md) `Gesamtpause: ja` setzen und Grund sowie erforderliche Nutzerentscheidung dokumentieren. Nur der Nutzer hebt diese Pause auf. Eine fehlende Trainingsfreigabe wird im Nachtplan erteilt.

**Grund der Pause (19.11.2026, 13:20 Uhr):** Im technischen Smoke N2-3 hat schon die Stufe δ_max = 0,05 nicht bestanden. Alle sechs Läufe verfehlen die Q-Bereichsprüfung [−0,05; 1,05]. Nach [PROTOCOL.md §7](PROTOCOL.md#7-bindung-an-bc-und-constraint-kandidaten) wird dann kein Pilot vorbereitet, und der Nutzer entscheidet. Jede Fortsetzung zu N2-4 und N3-1 würde eine Protokollentscheidung verlangen. **Erforderliche Nutzerentscheidung:** wie nach dem Scheitern von Stufe 0,05 weiterverfahren wird. [Ergebnis und technische Einordnung](AC_SMOKE.md#ergebnis-abschluss-19112026)

| ID | Status | Datum | Verweis / Fortsetzungspunkt |
|---|---|---|---|
| N1-1 | erledigt | 19.11.2026 | [Seedinventar](used_scene_seeds.json) · 2100000000–2100099999 für N1-2 reserviert, 0 Überschneidungen. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-2 | erledigt | 19.11.2026 | [Splitmanifest](splits.json) · 7 disjunkte Bereiche für 875 geplante Familien. Schwierige Panels werden in N1-5 zugeordnet. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-3 | erledigt | 19.11.2026 | [Merkmale difficulty_v1](difficulty.py) · Transport, Turmabstand, Freiraum und Tischlage aus dem Anfangszustand in Metern. [9 bestandene Testfälle](test_difficulty.py) · [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-4 | erledigt | 19.11.2026 | 300/300 Episoden auf 100 gemeinsamen Kalibrierungsfamilien, davon 103 erfolgreich. 951,9 Episoden/h über die Worker-Laufzeit. [Rohdaten- und Abschlussprüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-5 | erledigt | 19.11.2026 | [Kalibrierung](CALIBRATION.md) · [Eingefrorene Grenzen](difficulty_v1.json) · [SHA-256](difficulty_v1.sha256) · [375/375 zugeordnete Familien](difficulty_panels_v1.json), 0 Rollouts |
| N1-6 | erledigt | 19.11.2026 | [Pilotprotokoll](PROTOCOL.md), am 19.11.2026 für Claude freigegeben. [Versionierte Zusatzsplits](splits_v2.json). |
| N2-1 | erledigt | 19.11.2026 | [Datensatz, Manifest und Hash](CRITIC_DATA.md#ergebnis-abschluss-19112026) · 900/900 Episoden auf 300 `critic_data`-Familien, 325 Erfolge und 575 Fehlschläge (Parent 1/2/3: 125/92/108 von je 300), 0 Optimizerupdates. Monitor `COMPLETE` mit Abgleich gegen `summary.json`. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N2-2 | erledigt | 19.11.2026 | [CRITIC_VALIDATION.md: Kriterien nach §6 erfüllt](CRITIC_VALIDATION.md#ergebnis-abschluss-19112026) · Alle drei Critics bestehen auf `validation_normal` (gewichtete AUC 0,853 / 0,886 / 0,817, MSE-Differenz zur Phasen-Baseline mit Intervall < 0, ECE 0,040 / 0,033 / 0,039). 450/450 A-Rollouts, A-Erfolge regulär 41/100, 29/100, 29/100 und schwierig 23/50, 19/50, 16/50. 60.000 Critic-Updates, 0 Updates in den Rollouts. Monitor `COMPLETE` mit Neuberechnung gegen `summary.json`. Testfamilien geschlossen. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N2-3 | erledigt | 19.11.2026 | [Smoke-Bericht: Stufe 0,05 nicht bestanden, keine Stufe gewählt](AC_SMOKE.md#ergebnis-abschluss-19112026) · Alle sechs Läufe verfehlen den Q-Bereich [−0,05; 1,05]. Endlichkeit, 0 Grenzverletzungen, ESS ≈ 256 und 2 verlorene Parent-Erfolge (Grenze 3) sind erfüllt, beide Lesarten stimmen überein. Drift- und Erfolgsverlauf je Runde stehen im Bericht. 3.000 Critic- und 1.500 Actorupdates. Monitor `COMPLETE` mit Neuberechnung gegen `summary.json`. Nach §7 kein Pilot, der Nutzer entscheidet (Gesamtpause). Ohne Wirksamkeitsaussage, Testfamilien geschlossen. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N2-4 | offen | – | – |
| N3-1 | offen | – | – |
| N3-2 | offen | – | – |
| N4-1 | offen | – | – |
| N4-2 | offen | – | – |
| N4-3 | offen | – | – |
| N4-4 | offen | – | – |
