<!-- current-bc-status:start -->
> Stand 12.11.2026: **Abgeschlossen**. Auswertung unveränderter 60k-Gewichte: 60 zusätzliche gepaarte Dreiertürme, keine Verluste; null Trainingsupdates. [Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.
<!-- current-bc-status:end -->

# BC-Pipeline mit begrenztem Zeitmerkmal: unabhängige Bestätigung

Diese getrennte Versuchsversion prüft die im Diagnoseversuch gefundene
Zeitextrapolation der letzten Freigabephase auf **frischen Szenen**. Die sechs
vorhandenen gewöhnlich weitertrainierten 60k-BC-Modelle werden mit und ohne
Eingangsbegrenzung verglichen. Die bestehenden Experimente bleiben unverändert.

## Warum zunächst keine neuen BC-Updates?

Das Zeitmerkmal in Phase 6 reicht in den vorhandenen Trainingsdaten höchstens
bis 0,85, entsprechend 17 Schritten. Die neue Begrenzung verändert daher keinen
dieser Trainingsframes. Der Fehler tritt auf, wenn die gelernte Policy bei der
Ausführung länger in dieser Phase bleibt. Ein neues Training mit denselben
Frames würde die fehlenden längeren Verläufe nicht hinzufügen.

Der erste Pipeline-Schritt ist deshalb die Validierung der korrigierten
**Ausführung** einer BC-Policy mit festen Gewichten. `optimizer_updates` ist
explizit null; versehentliche Trainingsupdates werden im Protokoll abgewiesen.
Ein späterer Trainingsversuch mit längeren Demonstrationen wäre eine separate
Daten- und Versuchsversion. Er wird hier nicht stillschweigend begonnen.

## Festgelegter Vergleich

- Alle sechs 60k-Modelle: zwei Trainingsvorgeschichten, je Seeds 1/2/3.
- Vor jeder frischen Messung sind alle Modelle kopiert und über SHA-256
  eingefroren; vorhandene Checkpoints werden nicht überschrieben.
- Pro Modell **100 neue Dreierturm-Starts**, Seeds 2026119000–2026119099.
  Jede Szene wird einmal unverändert und einmal mit Zeitbegrenzung ausgeführt.
  Das sind 600 Paare bzw. 1.200 primäre Episoden.
- Pro Modell **20 zusätzliche Zweierturm-Starts**, Seeds 2026119200–2026119219.
  Hier ist die Intervention unerreichbar. Beide Ausführungen müssen bitgenau
  dieselben Trajektorien und Ergebnisse erzeugen: 120 Paare / 240 Episoden.
- Ausschließlich das Zeitmerkmal in Phase 6 der **zweiten Platzierung** wird
  beim aus den Trainingsdaten abgeleiteten Maximum begrenzt. Der tatsächliche
  Phasenzähler, Simulationszeit, Aktionen des Netzes, Phasenentscheidungen,
  Aufgabenkoordinator und alle Erfolgskriterien werden nicht ersetzt.
- Das strenge Kriterium bleibt bei **50 aufeinanderfolgenden gültigen Frames**;
  Horizonte bleiben 500 / 1.000 Steuerschritte. Kontakt-, Geometrie-, Grasp-
  und Geschwindigkeitskriterien entsprechen den bisherigen Versuchen.
- Identische Anfangszustände und bitgenau gleiche Vorgeschichte bis zur ersten
  veränderten Eingabe werden für jedes Paar geprüft. Eine Abweichung beendet
  den Versuch mit Fehler statt scheinbar gepaarte Ergebnisse zu melden.

Die bisherigen Diagnosebeispiele werden nicht zur neuen Erfolgsrate gezählt.
Der technische Smoke verwendet explizit die bekannte Szene 2026115004 und
einen getrennten technischen Zweierturm-Start. Er öffnet keine neuen
Bestätigungsstarts.

## Ergebnisse und vorab festgelegte Beurteilung

`result_summary.json` zeigt Erfolgszahlen, gepaarte Gewinne/Verluste und
Unterschiede je Modell. Zusätzliche Größen sind längste stabile Zeit,
erneuter Fingerkontakt in der letzten Freigabephase und Zahl der veränderten
Zeiteingaben. Die Mittelwerte der drei Trainingsseeds werden getrennt nach
Trainingsvorgeschichte ausgewiesen.

Ein Ergebnis wird nur als **Kandidat zur weiteren Prüfung** markiert, wenn:

1. alle Messungen vollständig sind und alle Zweierturm-Kontrollen identisch;
2. beide Trainingsvorgeschichten im Mittel mindestens 5 Prozentpunkte gewinnen;
3. kein einzelnes Modell mehr als 5 Prozentpunkte verliert.

Diese Schwellen sind praktische, vor der frischen Messung fixierte Kriterien,
keine statistischen Signifikanztests. 100 Szenen ersetzen keine unabhängigen
Trainingsreplikate. Die Pipeline wählt keine besten Seeds, verändert keine
Grenzwerte anhand der Ergebnisse und aktiviert keine Policy automatisch.
Unvollständige Resultate erhalten niemals eine Freigabeempfehlung.

## Start

Der vorbereitete Ordner ist `ready_001`; Vorbereitung und Smoke starten keinen
langen Lauf. Im Projektstamm:

```powershell
& '.\experiments\curriculum\axis_bc_clock_validation_20261112\Start-Pipeline.ps1'
```

Maximal zehn Stunden ab Supervisorbeginn **einschließlich** Speichern und
Beenden. Die letzte Zweiminutenreserve liegt innerhalb des Limits. Der
Rechenprozess erhält die Grenze von 9 Stunden 58 Minuten; spätestens am
Zehn-Stunden-Limit beendet der Supervisor einen verbliebenen Worker.
Ein vollständiger Vergleich kann deutlich früher enden. Keine automatischen
Neustarts, keine Wiederaufnahme eines bereits gestarteten Ausgabeordners.

Der Prozess läuft versteckt und verhindert währenddessen Windows-Schlaf.
Am Ende wird nur diese Sperre aufgehoben. **Der PC wird nicht heruntergefahren.**

Status ohne ML-Imports:

```powershell
& '.\praxis\.venv\Scripts\python.exe' '.\experiments\curriculum\axis_bc_clock_validation_20261112\pipeline.py' status --output '.\experiments\curriculum\axis_bc_clock_validation_20261112\ready_001'
```

Der leichte Monitor liest Status und Prozessidentität statt Trajektorien.
Für die Prozessprüfung ist derselbe Windows-Kontext wie beim Start nötig.
`STOP` im Laufordner wird bei jedem Simulationsframe berücksichtigt. Bereits
vollständige Paare sind atomar gespeichert; ein halb bearbeitetes Paar wird
nicht als vollständiges Vergleichspaar gezählt.

## Dateien

- `policy.py`: wiederverwendbarer Eingangsadapter ohne neue Schichten oder Gewichte.
- `clock_contract.json`: Phase, Platzierung, aus Training abgeleitete Grenze.
- `frozen/`, `models.json`, `provenance.json`: alle fixierten Eingänge.
- `*_count*.json`, `events.jsonl`: abgeschlossene Paare und Einzelresultate.
- `traces/`, `trace_layout.json`: vollständige Trajektorie der jeweils ersten
  vorab festgelegten Szene pro Modell und Aufgabe, mit Spaltenbeschreibung.
- `partial_summary.json`, `result_summary.json`: getrennte Teil-/Endauswertung.
- `status.json`, `supervisor_status.json`, `monitor_state.json`: Betriebsstatus.

Automatische Tests prüfen die Intervention, den unveränderten realen Zähler,
Paarung, negative Kontrollen, getrennte Szenen, Reviewkriterien und das harte
Zeitbudget. Der Smoke prüft echte Modellinferenz und beide Aufgaben auf der GPU.
