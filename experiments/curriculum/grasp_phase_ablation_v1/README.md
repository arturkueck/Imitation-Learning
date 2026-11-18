# Einzelphasen des zweiten Greifablaufs

Status: Vorbereitung. Nur technischer Smoke-Test freigegeben; wissenschaftlichen
Lauf nicht automatisch starten. Null Optimizer-Updates, unveränderte B-Modelle.

## Forschungsfrage und vorab festgelegter Vergleich

Die gemeinsame Expertenübernahme im zweiten Greifen verbesserte bestehende
Entwicklungsszenen von 26/60 auf 45/60 Gesamterfolge (19 Gewinne, keine Verluste).
Dieser Versuch untersucht, welche einzelne Phase einen Teil dieses Effekts
erzielt. Hypothesen, keine vorweggenommenen Ergebnisse:

- Anfahren: Eine bessere Ausgangspose erleichtert den folgenden BC-Griff.
- Absenken: Ein besserer Greifansatz vor Close reduziert Fehlgriffe.
- Schließen: Die Expertenbewegung und deren feste Dauer verhindern zu frühes Lift.

| Arm | Expertenübernahme nur bei der zweiten Platzierung |
|---|---|
| control | Keine |
| approach | Phase 0: Anfahren |
| descend | Phase 1: Absenken zum Greifen |
| close | Phase 2: Schließen |
| full_grasp | Phasen 0/1/2 als historische Positivkontrolle |

Die erste Platzierung und der Rückzug bleiben immer BC samt bestehendem Guard.
Eine ausgewählte Phase beginnt im tatsächlich vom Vorgänger erzeugten Zustand.
Der unveränderte Experte berechnet sein Ziel an diesem Phasenbeginn. Er ersetzt
die vollständige Aktion XYZ/Rotation/Greifer und seine eigene Abschlussregel.
Nach dem Abschluss übernimmt BC mit frischem Phasenanker und Schrittzähler
bei der nächsten Phase. Keine Zustands-Teleportation oder erzwungenen Kontakte.
Diese Übernahme entspricht der bisherigen Sequenzlogik.

## Stichprobe, Endpunkt und Prüfungen

- Drei unveränderte B-Modelle: mixed_s1/s2/s3 bei exakt 30.000 Updates.
- Jeweils dieselben 20 Entwicklungsszenen 2026113000–2026113019.
- 60 Modell-/Szenengruppen, je fünf Arme, insgesamt 300 Episoden.
- Primär: vollständiger Dreierturm für 50 aufeinanderfolgende strenge
  Gültigkeitsframes ohne Fingerkontakt. Episodenhorizont 1000 Schritte.
- Sekundär: Griffstatus beim zweiten Lift, Erreichen der Phase, tatsächliche
  Expertenframes, Endphase, Gewinne und Verluste gegen die gepaarte Kontrolle.
- Alle 60 Gruppen bleiben im Gesamtnenner, auch wenn eine Phase nicht erreicht
  wird. Bedingte Griffquoten nennen separat die erreichten Lift-Starts.
- Gleiche Anfangszustände in allen Armen. Vor dem ersten Eingriff muss die
  gesamte Aktions-/Simulationshistorie und der Zustand am betreffenden
  Phasenbeginn mit der Kontrolle exakt übereinstimmen (SHA-256).
- BC-Kontrolle und vollständige Expertenübernahme müssen die einzelnen
  historischen Ergebnisse einschließlich Framezahl und Lift-Messung reproduzieren.
- Erfolglose Eingriffe werden weder ausgeschlossen noch nachträglich angepasst.
- Keine neuen Bestätigungsszenen oder Trainingslabels; keine Modellselektion.

Das ersetzt komplette Phasen einschließlich ihrer Dauer/Abschlussregel. Es
isoliert nicht Aktion gegenüber Phasenabschluss. Es gibt keine Paar-Arme
0+1, 0+2 und 1+2; deshalb ist dies keine vollständige faktorielle Analyse von
Wechselwirkungen. Eine einzelne wirksame Übernahme macht eine Phase zum
Ansatzpunkt, aber nicht zwingend zur alleinigen Ursache. Eine wirkungslose
Einzelübernahme schließt Wechselwirkungen mit Vorgängerphasen nicht aus.
Drei Modellseeds teilen dieselben 20 Szenen. Unterschiede werden pro Seed und
gepaart berichtet; keine Signifikanzbehauptung aus 60 unabhängigen Szenen.
Es wird kein BC-Lernfortschritt oder Curriculum-Vorteil behauptet.

## Vorbereitung und Start

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/grasp_phase_ablation_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/grasp_phase_ablation_v1/pipeline.py prepare --output praxis/results/curriculum/grasp_phase_ablation_v1/ready_001
# Erst nach Freigabe des Untersuchungslaufs:
praxis/.venv/Scripts/python.exe experiments/curriculum/grasp_phase_ablation_v1/pipeline.py run --output praxis/results/curriculum/grasp_phase_ablation_v1/ready_001
```

Der volle Lauf bleibt READY, bis er ausdrücklich gestartet wird. Erwartete
Laufzeit grob 15–20 Minuten aus dem bisherigen Episodendurchsatz, feste Obergrenze
40 Minuten einschließlich Auslaufreserve. Supervisor mit hartem Prozesslimit,
kooperativer STOP-Datei und einmaligem Start; keine automatischen Neustarts.
Der PC wird nicht heruntergefahren. Schlafverhinderung gilt nur während des Laufs.

Technischer Smoke-Test: ein Modell, drei bekannte Szenen (erfolgreicher Start,
fehlender Griff und früher Abbruch), alle fünf Arme = 15 Episoden. Nur technische
Prüfung; keine Zahlen daraus als wissenschaftliches Ergebnis verwenden.

`prepare` schreibt Plan, SHA-Provenienz, Kopien der erfassten lokalen Quellen
und installierte Paket-/Python-/Torch-/CUDA-/GPU-Versionen. Die originale
Umgebung wird dadurch nicht als installierbares Containerimage eingefroren.
Originalmodelle bleiben samt Optimizer-/RNG-Zuständen im bestehenden Katalog.
Vor/nach Ausführung werden die erfassten Eingänge geprüft. Änderungen nach
Vorbereitung benötigen eine neue versionierte Vorbereitung, kein Überschreiben.

Ergebnisse: `groups.json` mit allen Armen, `summary.json`, `REPORT.md`,
`current_group.json` für den letzten Zwischenstand und 300 `traces/*.npz`.
Trace-Schema: frame, placement, phase, retreat, expert_action,
completion_probability, sequencer_event, consecutive_valid_frames, EEF XYZ (3),
cube XYZ (9), action (7), finger contacts (3), valid prefixes (2), joint
velocities (18): insgesamt 50 Spalten. Meter, numerische Bool-Werte 0/1.

Nächste Entscheidung nach diesem Versuch: Eingangszustände der auffälligen
Phase auf Datenabdeckung prüfen, anschließend ein separates gepaartes
BC-Trainingsprotokoll festlegen. Kein automatisches Folgetraining.
