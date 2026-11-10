# Eingefrorene Entwicklungs-Evaluation mit100 neuen Szenen

Freigegeben am03.11.2026. Kein neues Training und keine Endtestauswertung. Das B-Ensemble, die Aufnahme-/Übernahmeregeln, Tracking, Geometrieoptimierung und zentrierte Kameraführung bleiben gegenüber `active_smoke_002` unverändert. Ihre kritischen Quellcodehashes werden vor dem Start verglichen. Zusätzlicher Code orchestriert unabhängige Worker, sammelt Vergleichsaufnahmen und wertet erst danach die Ergebnisse aus.

## Festgelegter Vergleich

100 vorab zugeordnete neue Entwicklungsfamilien, deterministische Seed-/Indexzuordnung, vorhandene natürliche Verteilung von0–5 Objekten, Anordnungen und dünnen/langen Quadern. Keine Auswahl nach späterem Erkennungserfolg. Historische IDs und RGB-/Geometriefingerprints sperren Überschneidungen; das gemeinsame Register schützt auch parallele neue Läufe. Historische Splits werden ausschließlich für diesen Schutz indexiert, nicht als Inferenz-/Evaluationsbeispiele oder Endtest zur Auswahl verwendet.

Für dieselbe Szene werden erste Schätzung, geometrische Anpassung nach einer Seite, nach beiden Seiten und die adaptive Regel verglichen. Soweit erreichbar, werden beide Seiten tatsächlich aufgenommen, **auch wenn die adaptive Regel früher aufgehört hätte**. Solche Bilder sind als reine Vergleichsaufnahmen markiert; die frühere Regel erhält sie nicht. Ein anfängliches Überspringen kann durch später erfasste Vergleichsbilder nicht nachträglich eskalieren. Für eine Entscheidung nach der ersten Seite sind nur die erste tatsächlich aufgenommene Seite und ihre Bildqualität verfügbar. Fehlende Erkennungen und unerreichbare Richtungen bleiben im Ergebnis.

Vergleich bei nicht verfügbaren Seiten: letzte verfügbare Zwischenlösung, andernfalls erste Schätzung. Diese betriebliche Fallback-Auswertung wird für alle100 Szenen gezeigt. Zusätzlich gibt es einen gepaarten Vergleich ausschließlich der Szenen mit beiden tatsächlich verfügbaren Seiten; dessen Nenner wird separat angegeben. Leere/nichtleere Szenen und Objektzahl/Anordnung/Geometrie werden getrennt ausgewiesen. Die neuronale Fusion der tatsächlich aufgenommenen Endbilder ist ein zusätzlicher Kontrollwert. Sie erhält nur die bisherigen maximal drei Handbilder; Geometrie verwendet dagegen die Hinweg-Bildfolgen. Das ist kein Vergleich zweier Architekturen mit identischer Bildanzahl.

## Primäre Fragen und feste Definitionen

- Durchschnitt, Median und95. Perzentil des Szenenfehlers, einschließlich FP/FN und Eckengeometrie. Kein reiner Positions- oder Platzierfehler.
- Jede Verschlechterung über1e-6 mm-äquivalent sowie materielle Verschlechterung um **mehr als1 mm-äquivalent** gegenüber dem Anfang.
- Gewinn/Schaden der zweiten Seite gegenüber der ersten, mit eigenem Verfügbarkeitsnenner.
- Adaptive Seitenwahl und Fälle, die trotz geometrischer Unterstützung schlechter als die Anfangsschätzung sind.
- Trackingabbrüche, qualifizierte/triangulierte Punkte, zu geringe Unterstützung, Optimierungsabbrüche und Ablehnungsgründe.
- Übernommene schädliche Kandidaten beziehungsweise verworfene nützliche Kandidaten. Diese Objekt-Diagnose verwendet eine feste Zuordnung der ursprünglichen Erkennungen zum GT und einen unbeschnittenen Positionsfehler +0,25×Eck-RMSE. Sie ist vom Szenenfehler zu unterscheiden. Nicht zugeordnete Erkennungen bleiben im Szenenmaß enthalten, aber außerhalb des Nenners dieser lokalen Update-Diagnose.

Die GT-Messung geschieht erst nach Abschluss der Aufnahme-/Übernahmeentscheidungen. Keine Schwellenanpassung anhand dieses Laufs und keine automatische Anschluss-Trainingsentscheidung. Die Szenen sind Entwicklungsmaterial und bleiben für späteres Request-Training sowie Endtests gesperrt.

## Ausführung und Artefakte

Vier Windows-spawn-Worker besitzen je einen eigenen Simulator und die drei unveränderten B-Modelle. Feste Indexaufteilung modulo4, begrenzte CPU-Threads und gemeinsames transaktionales Familienregister. Ein Koordinator schreibt Laufstatus und Gesamtbericht. Fehler erhalten Teildaten und stoppen den Lauf; kein automatischer Neustart und keine wissenschaftliche Parameteränderung.

**Tatsächliche Laufzeitanpassung:** Vier Worker überschritten auf diesem Rechner die Windows-/CUDA-Speichergrenze. Nach nachgewiesenem Prozessende erfolgte genau ein dokumentierter technischer Wiederaufnahmeversuch mit zwei Workern (Indexaufteilung modulo2). Die100 Familien-IDs, Modelle und Regeln bleiben dieselben. Vier erhaltene Anfangssamples wurden einschließlich aller Arrays exakt gegen die erneute Erzeugung geprüft. Fehler und Ursprungsdaten bleiben unter `benchmark_001/attempt_001_failed` erhalten; Details in `benchmark_001/TECHNICAL_REPAIR.md` und `attempt_002_runtime.json`. Für neue lokale Läufe hier zwei Worker verwenden.

```powershell
praxis/.venv/Scripts/python.exe experiments/vision/visual_edge_refine_v1_20261103/run_active.py --run benchmark_001 --benchmark --scenes 100 --frames 28 --workers 4
```

Es gibt zuerst eine getrennte Vier-Szenen-Vorprüfung mit zwei Workern. Diese zählt nicht zu den100 Hauptszenen. GIF-/3D-Ausgaben sind für die vorab festgelegten ersten sechs Hauptszenen vorgesehen; alle Rohbildfolgen und Zwischenstände bleiben für spätere Fehleranalyse gespeichert. Bestehende Ausgabeordner werden nicht überschrieben.

Ergebnisse: `summary.json`, `scenes.csv`, `object_updates.json`, `benchmark.png` und `REPORT.md`. `evaluation_config.json`/Siegel dokumentieren vorab Varianten, Schwellen und Familien. `artifacts.json` versiegelt die gespeicherten Szenendaten; `worker_N.log` und `worker_N_status.json` halten Prozessfortschritt fest. Die vollständige Auswertung verifiziert Modell-/Quellcodehashes und die Trennung von Anpassungs- und Prüfaufnahmen.
