# Controllervergleich: Rückzugsfreigabe

Abgeschlossen: [Ergebnisbericht](run_001/REPORT.md) und
[unabhängige Integritätsprüfung](run_001/verification.json).
Auf den20 gemeinsamen Entwicklungsstarts je Parent steigt der vollständige
Dreierturmerfolg von11/9/9 auf18/17/15 pro20. Insgesamt29/60 gegenüber50/60
Modell-Start-Kombinationen; gepaart21 Gewinne und0 Verluste. Die20 Startfamilien
sind über die drei Parents geteilt, keine60 unabhängigen Familien. Gewichte
und ursprünglicher Controllercode bleiben unverändert; die neue Variante liegt
ausschließlich in diesem separaten Experiment. Eine unabhängige Endtestbestätigung
steht aus.

Autorisierung: „Okay“ am04.11.2026 nach dem vorgeschlagenen Vergleich mit
eingefrorenen Modellen auf neuen Entwicklungsstarts. Keine Trainingsupdates,
keine alten Endtestrollouts, kein realer Roboter.

## Festgeschriebener Vergleich

- Drei unveränderte C-Parents aus dem früheren Self-Imitation-Pilot.
- Je20 neue Startzustände2026110700–2026110719; Baseline und Gate innerhalb jedes
  Parents gepaart, insgesamt120 Rollouts. Technischer Seed2026110600 ist getrennt.
- Baseline: bisheriger Sequencer, Freigabe bei gelerntem Phase0-Abschluss.
- Gate: derselbe gelernte Bewegungskopf, zusätzlich20mm vertikaler Abstand aller
  Greiferkontaktgeometrien über dem geschützten Turm, drei aufeinanderfolgende
  gültige kontaktfreie Frames und gelernter Phase0-Abschluss. Bis dahin Phase0
  fortsetzen; Anker bleibt gecacht, Phasenzeit zählt tatsächliche Aktionen.
- Boxen: genaue Welt-Z-Ausdehnung anhand ihrer Orientierung. Meshes:
  konservative Bounding-Sphären. Diese Freigabe zertifiziert nicht den gesamten
  folgenden Bewegungskorridor und verwendet privilegierte Simulatorgeometrie.
- Maximal1000 Aktionen pro Episode; nicht freigegebener Rückzug nach200 Aktionen
  zählt als Controllerfehlschlag. Gesamtlauf maximal30Minuten, keine Retries.
- Enderfolg: unveränderte strenge50-Frame-Turmmetrik. Zusatzdiagnose:
  nächste Aufnahme mit fünf nativen Griff-/30mm-Anhebeframes sowie50 weiteren
  geschützten Frames bei kontinuierlich gültigem unteren Turm seit Freigabe.

`smoke_001` prüfte bitgenaue Baseline-Parität mit dem nativen Collector,
identische gepaarte Initialzustände und Zustände/Aktionen bis zum ersten
Rückzugsframe. Die Gate-Variante konnte die Freigabe mit dem vorhandenen Kopf
erreichen; der technische Einzelversuch ist keine Wirksamkeitsmessung.
Vier Unit-Tests prüfen Bestätigungsframes, Geometrie und Ablehnungskriterien.
Im Hauptlauf wird jede Gatefreigabe anhand der gespeicherten Kriterien geprüft.
`audit_run.py` prüfte nach Abschluss alle120 Rohrollouts:60 gepaarte Starts,
52 geometrische Freigaben, Erfolgs-/Aufnahmezählung, zeitliche Verkettung,
identische Aktionen bis zur Intervention und unveränderte Quell-/Modellhashes.

Das Rohfeld `y` speichert die vorhergesagte Phasenentscheidung des Modells vor
einer möglichen Gate-Unterdrückung. Es ist kein neues Expertenlabel für den
tatsächlichen Controllerwechsel. Diese Entwicklungsrollouts werden ohne eigenes
Datenprotokoll nicht automatisch zu Trainingsdaten.

```powershell
praxis/.venv/Scripts/python.exe experiments/retreat_gate_20261104/compare.py --output experiments/retreat_gate_20261104/run_001
```

Laufstatus: `run_001/status.json`. Rohrollouts bleiben lokal unter `traces/`;
Protokoll, Quellcode-Snapshot und Einzel-/Zusammenfassungsergebnisse werden
separat gespeichert. Abgeschlossene Resultate stehen in `run_001/REPORT.md`.
Eine STOP-Datei im Laufordner beendet nur diesen Versuch an der nächsten Aktion.
Originalcode und Modellgewichte bleiben unverändert. Resultate sind
Entwicklungsdaten und keine unabhängige Endtestbestätigung.
