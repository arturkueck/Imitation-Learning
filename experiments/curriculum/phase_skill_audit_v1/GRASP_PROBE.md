# Zweiter Greifprozess: Ursachenprüfung

Freigabe: 13.11.2026, Nutzerauftrag Nachtlauf bis heute 08:00 Uhr Berlin.
Ausgeführt wird der zuletzt vorbereitete kontrollierte Eingriff ohne Training.
Kein anschließendes Lernexperiment wird automatisch gestartet.

Drei unveränderte B-Modelle bei 30.000 Updates, 20 bestehende
Entwicklungsszenen, zwei gepaarte Bedingungen: 120 Episoden. Kontrolle bleibt
BC; Eingriff ersetzt nur Approach, Grasp-Descend und Close der zweiten
Platzierung durch den vorhandenen Experten. Danach wieder BC bei Lift.
Erfasst werden Griffstatus am Lift-Beginn, gesamte Aufgabenerfüllung für 50
stabile Frames sowie Gewinne und Verluste pro Modell/Startzustand.

Paare müssen bis zum Eingriff dieselbe vollständige Aktions-/Simulationshistorie
haben. Die Kontrolle muss den vorangegangenen Diagnoseausgang reproduzieren.
Horizon 1000; bestehender Retreat-Guard und finale Release-Clock bleiben aktiv.
Ungeeignete oder erfolglose Eingriffe werden mitgezählt, nicht ausgesondert.

Supervision: höchstens 20 Minuten einschließlich Auslaufreserve und in jedem
Fall vor 08:00 Uhr. Kooperativer Abbruch plus Prozess-Watchdog. Schlaf wird nur
während des Laufs verhindert und anschließend wieder zugelassen. Kein
Herunterfahren, kein Neustart bei Fehlern. Modelle bleiben unverändert und
behalten Optimizer-/RNG-Zustände in den bestehenden Modellbundles.

Technischer Probelauf smoke_001 scheiterte vor Simulationsbeginn an einer
Python-Modulnamenkollision `audit`. Der Import erhielt einen eigenen Namen.
smoke_002 schloss das gepaarte Szenario erfolgreich einschließlich identischer
Vorgeschichte und Reproduktion der Kontrolle ab. Beide sind technische Läufe
und werden aus den wissenschaftlichen Ergebnissen ausgeschlossen.

```powershell
praxis/.venv/Scripts/python.exe experiments/curriculum/phase_skill_audit_v1/grasp_probe.py --output praxis/results/curriculum/second_grasp_probe_v1/night_001 --until 2026-11-13T08:00:00+01:00
praxis/.venv/Scripts/python.exe experiments/curriculum/phase_skill_audit_v1/grasp_probe.py --status --output praxis/results/curriculum/second_grasp_probe_v1/night_001
```

Statusprüfung liest Prozessidentität, kompakten Fortschritt und ausschließlich
neue Logeinträge. `STOP` im Laufverzeichnis beendet den Worker kooperativ.
Plan, Provenienz, Ergebnispaare, Zusammenfassung und Bericht liegen im neuen
Ergebnisverzeichnis; frühere Befunde werden nicht überschrieben.

Trace je Frame, 50 Spalten: frame, placement, phase, retreat, expert_action,
completion_probability, sequencer_event, consecutive_valid_frames, EEF XYZ (3),
cube XYZ (9), action (7), finger contacts (3), strict-valid prefixes (2), cube
joint velocities (18). Numerische Bool-Werte 0/1, Längen in Metern.
