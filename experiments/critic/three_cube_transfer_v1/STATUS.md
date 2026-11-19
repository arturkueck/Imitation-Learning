# Fortschritt der Nachtläufe zum Dreierturm

Gesamtpause: nein

Bei einem Sofortstopp nach [Nachtplan](NACHTPLAN.md) `Gesamtpause: ja` setzen und Grund sowie erforderliche Nutzerentscheidung dokumentieren. Nur der Nutzer hebt diese Pause auf. Eine fehlende Trainingsfreigabe wird im Nachtplan erteilt.

| ID | Status | Datum | Verweis / Fortsetzungspunkt |
|---|---|---|---|
| N1-1 | erledigt | 19.11.2026 | [Seedinventar](used_scene_seeds.json) · 2100000000–2100099999 für N1-2 reserviert, 0 Überschneidungen. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-2 | erledigt | 19.11.2026 | [Splitmanifest](splits.json) · 7 disjunkte Bereiche für 875 geplante Familien. Schwierige Panels werden in N1-5 zugeordnet. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-3 | erledigt | 19.11.2026 | [Merkmale difficulty_v1](difficulty.py) · Transport, Turmabstand, Freiraum und Tischlage aus dem Anfangszustand in Metern. [9 bestandene Testfälle](test_difficulty.py) · [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-4 | erledigt | 19.11.2026 | 300/300 Episoden auf 100 gemeinsamen Kalibrierungsfamilien, davon 103 erfolgreich. 951,9 Episoden/h über die Worker-Laufzeit. [Rohdaten- und Abschlussprüfung](nights/NACHT_1_20261118.md#integrität) |
| N1-5 | erledigt | 19.11.2026 | [Kalibrierung](CALIBRATION.md) · [Eingefrorene Grenzen](difficulty_v1.json) · [SHA-256](difficulty_v1.sha256) · [375/375 zugeordnete Familien](difficulty_panels_v1.json), 0 Rollouts |
| N1-6 | erledigt | 19.11.2026 | [Protokollentwurf](PROTOCOL.md), Status `ZUR FREIGABE`, mit Armen, Budgets aus 951,9 Episoden/h, Critic-Akzeptanz, Bindungsstufen, Checkpoint-, Analyse- und Ausschlussregeln. Offene Nutzerentscheidungen in [§12](PROTOCOL.md#12-offene-nutzerentscheidungen). 0 Rollouts. [Prüfung](nights/NACHT_1_20261118.md#integrität) |
| N2-1 | offen | – | – |
| N2-2 | offen | – | – |
| N2-3 | offen | – | – |
| N2-4 | offen | – | – |
| N3-1 | offen | – | – |
| N3-2 | offen | – | – |
| N4-1 | offen | – | – |
| N4-2 | offen | – | – |
| N4-3 | offen | – | – |
| N4-4 | offen | – | – |
