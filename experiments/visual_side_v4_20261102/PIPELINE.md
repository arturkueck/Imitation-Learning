# V4: Pipeline für gepaarte Seitenansichten

Stand: 03.11.2026. Aktuelle Vorbereitung: `prepared_004`. Noch kein V4-Training gestartet und keine V4-Gewichte erzeugt. Frühere `prepared_001/002/003` bleiben als Entwicklungsartefakte erhalten; ihre Quellcode-Siegel entsprechen früheren Implementierungen.

## Umgesetzter Versuch

Zunächst wird die Wahrnehmung trainiert, die zusätzliche seitliche Handkamerabilder verarbeiten soll. A und B starten pro Seed aus exakt demselben eingefrorenen V3-M2-Checkpoint; je drei Seeds ergeben sechs Modelle. A erhält die bisherigen Blickrichtungen, B die geprüften Seitenansichten. Beide sehen dieselben Szenen, dieselbe Datenreihenfolge, dieselbe maximale Zahl zusätzlicher Bilder und gleich viele Optimierungsschritte. Nicht erreichbare Ansichten werden nicht durch erfundene Bilder ersetzt. Ein Kontext enthält zwei feste Kameras und höchstens drei tatsächlich verfügbare Handkamerabilder.

Das Modell hat 904.112 Parameter: sechs Conv-Lagen mit ReLU, einen Transformer-Decoder mit drei Lagen, Breite 128, vier Attention-Heads und GELU sowie fünf Objekt-Slots mit je 16 Rohwerten. Architektur und Startgewichte bleiben im A/B-Vergleich gleich. Trainiert wird mit AdamW, Lernrate 0,0001, Weight Decay 0,0001, effektivem Batch 32, Microbatch 4, zwei gepaarten Kontexten, FP32, Gradient-Clipping 1 und drei Warmup-Epochen. Maximal zehn Epochen, gemeinsames Early Stopping. Loss: Objektexistenz + 5 × Position + Größe + 0,5 × symmetriebewusste Rotation + 0,25 × Sichtbarkeit.

Vorher-/Nachher-Kontexte verwenden dieselbe beobachtbare Zielobjektmenge. So wird ein neu sichtbar gewordenes Objekt nicht als zusätzliche Strafe nur für die spätere Aufnahme gezählt. Sichtbarkeit und Modelleingaben bleiben auf den jeweiligen Kontext beschränkt. Zukünftige RGB-Bilder, Simulatorpositionen und Kandidatenergebnisse gelangen nicht in die Modelleingabe.

## Datenherkunft und unveränderliche Splits

`prepared_004/history.sqlite` ist ein versiegelter historischer Herkunftsindex mit 105.069 Familien und 326 reservierten Seed-Namensräumen. Er enthält auch frühere Entwicklungs-/Prüfdaten. Mehrfachrollen aus älteren Versuchen werden konservativ gesperrt; die Zahl solcher Einträge ist kein Nachweis für einen früheren Train-Test-Leak.

| Rolle | Neue Familien | Seed |
|---|---:|---:|
| Wahrnehmungstraining | 18.000 | 94834001 |
| Modellvalidierung | 2.000 | 94834002 |
| Aufnahmebedarf-Training, reserviert | 4.000 | 94834003 |
| Aufnahmebedarf-Validierung, reserviert | 1.000 | 94834004 |
| Kalibrierung, reserviert | 1.000 | 94834005 |
| IID-Endtest, gesperrt | 2.000 | 94834006 |
| Kamera-Endtest, gesperrt | 1.000 | 94834007 |
| Geometrie-Endtest, gesperrt | 1.000 | 94834008 |

Hinzu kommen **6.000 fest ausgewählte alte V3-Trainingsfamilien**, also 25 % Replay unter den 24.000 Trainingsfamilien. Alle 12.000 alten V3-Trainingsfamilien wurden auf ausschließlich historische Trainingsrollen geprüft. Keine alte Validierungs-, Test-, Kalibrierungs- oder Entwicklungsfamilie wird als Replay zugelassen. Alte Datensätze bleiben schreibgeschützt gelesen und werden nicht neu aufgeteilt. Eine Familien-ID bleibt über alle Bilder, Kameraposen und Fortsetzungen hinweg in derselben Rolle.

Neben Seed/Familien-ID prüft die Pipeline Fingerprints des Ausgangs-RGB und der Objektgeometrie, unabhängig von Slot-Reihenfolge und Würfelsymmetrien. Damit scheitert auch das bloße Umbenennen einer alten Szene. Die unabhängige Prüfung vor dem Training berücksichtigt aktuelle Entwicklungsszenen erneut. Ein gemeinsames transaktionales Register unter `monitor/vision-data-claims.sqlite` verhindert zudem Konflikte zwischen neuen, gleichzeitig vorbereiteten Läufen. Dieses Register aufbewahren. Die V1-Bildarchive ohne Familienfelder sind über ihre dokumentierten Seed-/Indexbereiche geschützt; vollständige Inhalts-Fingerprints gelten für die familienhaltigen V2/V3-/Pilotdaten. V1 ist kein Gewichts-Vorfahre dieses Modells.

Neue Kamera-Endtestansichten liegen in einem räumlich abgegrenzten Bereich mit Sicherheitsabstand, der in den tatsächlichen V2/V3-Trainingskamerapositionen nicht vorkommt. Andere neue Splits schließen diesen Bereich aus. Der Geometrie-Endtest verwendet längere/schmalere Quader außerhalb der neuen Trainingsbereiche. Das ist kein Nachweis für beliebige unbekannte Objektformen.

## Kamerabilder und Sicherheit

Datenerzeugung nutzt die 26 Routen aus `guidance_002`, gerichtetes Nachzentrieren und kollisionsgeprüfte vollständige Wege einschließlich Greifer/Kamera. Wunsch-, Plan- und Ist-Pose, verfügbare und abgelehnte Aufnahmen werden getrennt gespeichert. Jede Familie beginnt mit zurückgesetztem Simulatorzustand. Referenzgeometrie aus der Simulation wird zur Kollisionsprüfung benutzt. Rein visuelles Freiraum-Erkennen und reale Sicherheitsgarantien sind damit nicht gelöst. Keine reale Roboterbewegung wird ausgeführt.

## Auswahl, Berichte und spätere Phasen

Checkpointwahl und A/B-Auswahl verwenden nur neue Modellvalidierung: gemeinsame Ausgangs-, alte und seitliche Blickkontexte. Die Pipeline schreibt tatsächliche Train-/Validation-/feste Train-Probe-Losses, Komponenten, Positionsfehler, Zählgenauigkeit und Recall. Epoche 0 hat keinen erfundenen Trainingsloss. Alle fünf Epochen und für die besten Checkpoints entstehen 3D-Vergleiche: Cyan = Simulator, Orange = erste Schätzung, Grün = Schätzung nach Zusatzbildern. Zusätzlich werden interaktive Szenen-JSONs und zugehörige Kameraeingaben gespeichert.

Der Seitenansicht-Gate verlangt B als Gewinner auf dem gemeinsamen Validierungsloss, mindestens 10 % geringeren Seitenansicht-Fehler als A, höchstens 1 mm Verschlechterung auf alten Ansichten und bessere Seitenansicht-Ergebnisse in mindestens zwei der drei Seeds. Scheitert er, ist die nachfolgende Aufnahmebedarf-Phase blockiert. Endtests entscheiden weder Checkpointwahl noch Fortsetzung.

**Dieser Implementierungsschritt umfasst die gepaarte Wahrnehmungsphase.** Datenrollen und Sperren für Aufnahmebedarf/Blicknutzen/Kalibrierung sind vorbereitet. Deren Trainer und der geschlossene aktive Folgeversuch sind eine getrennte Anschlussphase; hier wird keine fertige lernende Aufnahmeentscheidung behauptet. Endtest-Bildgenerierung benötigt zusätzlich einen eingefrorenen Gesamtansatz (`final_policy_freeze.json`).

## Bedienung

Alle Befehle aus dem Repository-Root, PowerShell. Prüfen ohne Training:

```powershell
praxis/.venv/Scripts/python.exe experiments/visual_side_v4_20261102/pipeline.py verify --run prepared_004 --deep
praxis/.venv/Scripts/python.exe experiments/visual_side_v4_20261102/pipeline.py monitor --run prepared_004
```

Erst **nach gesonderter Trainingsfreigabe und festgelegtem Stundenbudget** starten; `H` durch dieses Budget ersetzen:

```powershell
praxis/.venv/Scripts/python.exe experiments/visual_side_v4_20261102/pipeline.py start --run prepared_004 --start-training --hours H
```

Das Budget umfasst Datenerzeugung, Prüfungen, Training und Validierung. `STOP_REQUESTED` im Run-Ordner stoppt kontrolliert; Wiederaufnahme verwendet `start --run prepared_004 --start-training --resume` ohne neues `--hours`. Die Deadline bleibt unverändert. Checkpoints enthalten alle sechs Optimizer, Teilgradienten, RNG-Zustände und den Daten-Cursor. OS-Sperren verhindern parallele Schreiber; fehlende Sandbox-Prozesssicht löst keinen automatischen Neustart aus. Quellcode-, Daten- oder Startgewichtänderungen verletzen das Siegel und blockieren den Lauf. Neue wissenschaftliche Varianten erhalten eine neue Vorbereitung.

`monitor/training-runs.json` registriert diese Vorbereitung lokal. Online-Veröffentlichung ist nicht Teil dieses Schritts. Ergebnisse und Plots werden erst nach tatsächlichem Training befüllt.

## Laufzeit

Die vollständige Datenerzeugung mit acht vorgesehenen Kamera-Slots, Routenprüfung und adaptivem Nachzentrieren ist erheblich aufwendiger als der frühere Kamerapilot. Dessen Sekunden-pro-Szene-Wert darf nicht für diesen Lauf übernommen werden. Der kleine Entwicklungstest liefert eine erste Messung, keine belastbare Gesamtlaufzeit für 20.000 neue Familien. Eine Zusage für zehn oder sechzehn Stunden wäre vor dem Start nicht belegt. Die festgelegten wissenschaftlichen Parameter werden dafür nicht stillschweigend reduziert.

## Parallele Datenerzeugung

Die CLI verwendet standardmäßig vier Windows-spawn-Worker (--workers 4, begrenzt auf 1–4). Jeder Prozess besitzt Simulator und eingefrorenes Ensemble; jeder bekommt feste Indizes worker_id, worker_id + workers, .... Pro Worker läuft ein Torch-CPU-Thread. Familien-ID, Seed, Split und Kameraprüfungen bleiben unverändert. Der Kamerabank-Cache wird unter exklusiver Sperre initialisiert. Datensatzindex und Siegel schreibt nur der Koordinator nach erfolgreichem Abschluss aller Worker und Hashprüfung. Ein Workerfehler setzt eine Abbruchmarkierung für die übrigen Worker; Teilresultate bleiben erhalten.
