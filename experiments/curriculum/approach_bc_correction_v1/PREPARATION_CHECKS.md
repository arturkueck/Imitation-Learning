# Technische Freigabe der Vorbereitung

Status: wissenschaftlicher Lauf nicht gestartet. Der vollständige Plan bleibt
READY. Der Nutzerauftrag umfasst Vorbereitung, nicht dessen Ausführung.

## Geprüfter endgültiger Stand

- Drei Unit-Tests bestanden: Szenenfamilien-Überschneidung wird abgelehnt;
  nur Phase-0-Parameter sind trainierbar; Aktions-/Abschlusskomposition ersetzt
  nur das ausgewählte Verhalten. Ohne aktivierten Ausführungskontext bleibt B.
- `smoke_004`: COMPLETE. Sechs technische Sammelversuche aus getrennten
  technischen Train-/Validierungsfamilien; vier Komponenten mit je vier
  Updates; zehn vollständige Rollouts über fünf Ausführungsvarianten.
- Der neue Auswerter reproduziert den bekannten B-Kontrollausgang einschließlich
  Framezahl, Anfangszustand, Endphase und Rückzugsstatus.
- Phase 1–6 bleiben nach jedem Komponentenlauf bitgleich zum B-Vorfahren.
- Alle erfassten Provenienzeingänge wurden vor und nach dem Smoke-Lauf geprüft.
- Supervisor beendet und Schlafverhinderung freigegeben. Kein PC-Shutdown.
- `resume_check_001/verification.json`: alle vier Komponenten vom Checkpoint
  nach Update 2 mit demselben Samplingplan bis Update 4 fortgesetzt. Gewichte
  UND vollständiger Optimizerzustand stimmen bitgenau mit der ursprünglichen
  ununterbrochenen Ausführung überein. Nächster Batchindex ebenfalls identisch.
- Train-/Validierungsfamilien sind disjunkt; positive Abschlusslabels vorhanden.

## Aufbewahrte Entwicklungsstände

`smoke_001` und `smoke_003` sind abgeschlossene technische Zwischenstände.
`smoke_002` wurde vorbereitet, aber nicht ausgeführt. Sie werden nicht mit
Forschungsergebnissen vermischt. Während der Vorbereitung wurden versionierte
Zwischencheckpoints, gepaarte Berichte und die Beschränkung der neuen
Komponenten auf den zweiten Anfahrkontext ergänzt. `smoke_004` prüft diesen
endgültigen Ausführungspfad. Keine wissenschaftlichen Resultate behauptet.

## Wiederholung

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/approach_bc_correction_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/approach_bc_correction_v1/verify_smoke.py --output praxis/results/curriculum/approach_bc_correction_v1/smoke_004 --verification-output praxis/results/curriculum/approach_bc_correction_v1/resume_check_NEU
```

Neue Prüfverzeichnisse verwenden. Keine alten Smoke-Checkpoints überschreiben.
Ein späteres Ändern von Code/Plan erfordert eine neue versionierte Vorbereitung;
die Hashprüfung verhindert das stille Verwenden geänderter Eingänge.
