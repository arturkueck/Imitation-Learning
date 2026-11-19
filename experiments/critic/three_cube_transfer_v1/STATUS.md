# Fortschritt der Nachtläufe zum Dreierturm

Gesamtpause: nein

Bei einem Sofortstopp nach [Nachtplan](NACHTPLAN.md) `Gesamtpause: ja` setzen und Grund sowie erforderliche Nutzerentscheidung dokumentieren. Nur der Nutzer hebt diese Pause auf. Eine fehlende Trainingsfreigabe wird im Nachtplan erteilt.

**Pause aufgehoben (19.11.2026, 22:12 Uhr):** Der Nutzer hat nach dem gescheiterten Smoke N2-3 Plan B gewählt und [PROTOCOL_V2.md](PROTOCOL_V2.md) freigegeben. Zuerst wird ein Critic mit Aktionsvariation (IL-v2) erhoben, vortrainiert und geprüft, danach Smoke v2. N2-4 und N3-1 starten nicht vor Nacht 3. Ursprünglicher Grund der Pause (13:20 Uhr): Stufe δ_max = 0,05 hat die Q-Bereichsprüfung verfehlt, [AC_SMOKE.md](AC_SMOKE.md#ergebnis-abschluss-19112026).

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
| D1a | erledigt | 19.11.2026 | [Aktionssensitivität](ACTION_SENSITIVITY.md) · 126/126 Gruppen geprüft, 0 Optimizerupdates. Median der Streuung je Frame beim N2-2-Critic 0,000498–0,000677, je Stufe 4,83–5,13-mal so hoch wie bei der Zufallsinitialisierung. Berichtender Ausgangsbefund für D1b. |
| N2-1b | läuft | 19.11.2026 | [Datenvertrag und Lauf](CRITIC_DATA_NOISY.md#lauf) · [splits_v3.json](splits_v3.json) · seit 22:41 unter Supervisor PID 34664 (created_unix 1795124497.3361793), Worker PID 37584, Cutoff 20.11. 07:30, Deadline 09:00. Integrationsprüfung bestanden, 19/19 Tests. Monitor: `praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_data_noisy.py monitor`. Fortsetzungspunkt nach `PAUSED`: erste fehlende `episodes/NNNN.json`, `start resume` vor 07:30. Noch keine Ergebnisse. |
| N2-2b | offen | – | nach N2-1b |
| D1b | offen | – | nach N2-2b, entscheidet über Smoke v2 |
| N2-3v2 | offen | – | nach D1b, [v2 §B–§D](PROTOCOL_V2.md) |
| B-1 | erledigt | 19.11.2026 | [Pilotauswertung eingefroren](PILOT_ANALYSIS.md) · [pilot_analysis.py](pilot_analysis.py) nach v1 §10, SHA-256 `ad7d6274…18a2` ([Hashdatei](pilot_analysis.sha256)). [27/27 Tests](test_pilot_analysis.py) auf synthetischen Daten grün, Testfamilien werden vor jeder Rechnung abgewiesen. Ohne Pilotdaten, 0 Rollouts, 0 Optimizerupdates. |
| B-2 | erledigt | 19.11.2026 | [Fehlerphasen der A-Parents](FAILURE_PHASES.md) · nur N1-4 (300) und N2-1 (900), Hashes vorab geprüft. Fehlschläge nach erreichter Stufe 2: 146/197 (N1-4) und 424/575 (N2-1), alle am Horizont. Häufigste N2-1-Endpunkte: Stufe 2 Lösen 231, Stufe 2 Greifen 142, Stufe 1 Lösen 93. Außerhalb der Bindung in der Ablagegruppe 157/139 von 418 bei δ_max 0,05/0,20. [failure_phases.py](failure_phases.py), [9/9 Tests](test_failure_phases.py), 0 Rollouts, 0 Optimizerupdates, Testfamilien geschlossen. |
| B-3 | offen | – | Seedzahl-Werkzeug für N4-2 |
| B-4 | offen | – | Abbildungen, Dokumentation, Nachtbericht |
| N2-4 | offen | 19.11.2026 | Nicht vor Nacht 3 (20./21.11.2026), nach bestandenem N2-3v2 mit IL-v2. Vorher: Gesamtpause nach N2-3, aufgehoben am 19.11.2026 22:12 (Plan B). |
| N3-1 | offen | – | – |
| N3-2 | offen | – | – |
| N4-1 | offen | – | – |
| N4-2 | offen | – | – |
| N4-3 | offen | – | – |
| N4-4 | offen | – | – |
