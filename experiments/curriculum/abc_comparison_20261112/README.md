<!-- current-bc-status:start -->
> Stand 12.11.2026: **Vorbereitet**. Nur A wird neu trainiert; B/C-30k-Gewichte vorhanden. Einheitliche Zeitbehandlung, frische Tests noch offen. [Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.
<!-- current-bc-status:end -->

# A/B/C: vorhandene Zweier-Demonstrationen für Dreiertürme nutzen

Status: Vorbereitung, kein neuer wissenschaftlicher Trainingslauf gestartet.

| Arm | Daten/Sampling | Welche Frage? |
|---|---|---|
| A | Vollständiger Trainingspool ab Update 1; gleichmäßige Phasenauswahl, dann Frame innerhalb der Phase | Phasenausgewogenes Standard-BC als Referenz |
| B | Genau das Batch-Multiset von C, global durchmischte Batchreihenfolge | Effekt anderer Datenexposition gegenüber A |
| C | Dasselbe Batch-Multiset wie B, geordnet X → XY → XYZ | Effekt der Reihenfolge gegenüber B |

B gegen C isoliert die Reihenfolge, A gegen B die Exposition/Gewichtung und A
gegen C den Gesamtnutzen dieses Curriculums. A ist ausdrücklich phasenausgewogen,
nicht gleichverteilt über sämtliche Frames unabhängig von deren Phase.

## Gleiche Bedingungen

PhaseNet mit Breite 128, 10 Zustandsmerkmalen, sieben Phasenköpfen und vier
aktiven Aktionen. Drei Seeds 1/2/3, je 30.000 Updates, Batch 64, AdamW LR 1e-4,
500 Updates Warmup, Weight Decay 1e-6, Clip 10, Aktions-MSE + 0,1 gewichtete
Abschluss-BCE. Alle Arme verwenden dieselben ursprünglichen 180 Trainings- und
20 Validierungstrajektorien mit 27.322 / 2.974 Frames. Keine neuen Labels,
kein Critic und kein RL. Bilder werden nicht verwendet.

Vorbereitung prüft Konfiguration, Ausgangsgewichte, Checkpointstatus und
identische B/C-Datenexposition. B und C werden aus den ursprünglichen festen
30k-Checkpoints wiederverwendet. **Nur die drei A-Modelle werden neu trainiert.**
Ihre Anfangsgewichte stammen aus den exakt geprüften B/C-Initialisierungen.
Es werden weder die späteren 60k-Modelle noch eingefrorene Abschlussvarianten
als B/C ausgegeben. Der Modellkatalog dokumentiert Herkunft und SHA-256.

## Auswertung und Zeitproblem

Alle Arme verwenden dieselbe vorab festgelegte Begrenzung des Zeitmerkmals
in Phase 6 der zweiten Platzierung auf 17 Schritte. Die physikalische Zeit,
der tatsächliche Phasenzähler und die Erfolgsbedingung bleiben unverändert.
Dadurch wird der bekannte Ausführungsfehler nicht mit dem Curriculum verglichen.

Während A trainiert: Aktions-MSE, Abschluss-BCE und Entwicklung auf je 20
gleichen Zwei-/Dreierturm-Starts bei 1k/5k/12k/20k/30k. B/C-Kurven dürfen nicht
als neue korrigierte Entwicklungskurven erfunden werden; deren Zwischengewichte
sind nicht vollständig archiviert. Die neue Hauptauswertung vergleicht feste
30k-Endpunkte, keine Auswahl nach Entwicklungs- oder Testerfolg.

Nach vollständigem A-Training werden **alle neun A/B/C-Modelle eingefroren**, bevor
eine neue Bestätigungsszene geöffnet wird. Pro Modell 100 neue Dreierturm-Starts
2026121000–2026121099 und 40 Zweierturm-Starts 2026121200–2026121239. Für jedes
Panel müssen Initialzustandshashes über alle Arme und Trainingsseeds gleich
sein. Hauptmaß: vollständiger stabiler Dreierturm mit 50 strengen gültigen
Frames, nicht bloß Anheben oder kurzzeitiges Stapeln. Der vorgegebene
Aufgabenkoordinator bleibt erhalten; autonome Paarplanung wird nicht behauptet.

Ergebnisse pro Trainingsseed berichten. 100 Szenen sind keine 100 unabhängigen
Trainingsreplikate. Die vorhandenen 60k-Zeitkorrektur-Ergebnisse sind ein anderer
Vergleich und dürfen nicht als Ergebnis dieses noch vorbereiteten A/B/C-Laufs
erscheinen. Zusätzliche Dreier-/Recovery-Demos wären eine weitere Datenstudie.

## Start und Ablage

```powershell
& '.\experiments\curriculum\abc_comparison_20261112\Start-ABC.ps1'
```

Dieser Befehl startet erst auf ausdrücklichen Aufruf. Ausgabe liegt unter
`praxis/results/curriculum/abc_comparison_20261112/ready_001`. Der Supervisor
läuft versteckt, hält Windows wach und begrenzt den gesamten Lauf inklusive
Auswertung auf zehn Stunden; zwei Minuten Reserve liegen innerhalb dieses
Limits. Er beendet nur den Lauf, fährt den PC nicht herunter und startet nach
Fehlern nicht automatisch neu.

Status: `train.py status --output <run>`. Eine Datei `STOP` im Laufordner wird
bei Updates und Simulationsframes berücksichtigt. Teilresultate bleiben als
solche gekennzeichnet. Der technische Smoke hat einen eigenen Ordner und
öffnet ausschließlich technische Szenen, keine frischen Bestätigungsstarts.

## Später weitertrainieren

`A_seed*/latest.pth` wird atomar mindestens alle 1.000 Updates gespeichert.
Er enthält Modell, vollständigen AdamW-Zustand, globale Updatezahl, Plan,
Sampleplanpfad und SHA-256, nächsten Batchindex sowie Python-/NumPy-/Torch-/CUDA-RNG.
`sampling/` enthält die komplette vorab fixierte Reihenfolge. Die festen
Endpunkte unter `confirmation/` enthalten ebenfalls den vollen Trainingszustand.

`restore_training_checkpoint(path, device)` lädt Modell und AdamW vollständig.
Der identische nächste CPU-Schritt nach Speichern/Laden wird getestet. Ein
exakter CUDA-Resume über andere Software-/GPU-Versionen wird nicht versprochen.
Für eine Fortsetzung einen neuen Laufplan und Ausgabeordner anlegen, Updatezahl
und Sampling bewusst fortsetzen; keinen archivierten Endpunkt überschreiben.
B/C- und 60k-Varianten sind zusätzlich in `experiments/curriculum/models.json`
und `praxis/results/models/bc_curriculum/` mit ihren Zuständen registriert.
