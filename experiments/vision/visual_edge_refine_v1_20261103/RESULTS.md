# Technischer Entwicklungsversuch: eingerichtet und geprüft

Aktueller vollständiger Lauf: `smoke_003`,03.11.2026. Neue Entwicklungsfamilien95343001/0–3; getrennt von Training, Modellvalidierung und Endtests. Sechs Tests bestanden. Vier Familien bearbeitet, drei tatsächliche Bildfolgen mit je40 Bildern aufgenommen. Eine Familie blieb ohne vorhandene zulässige Seitenroute und wurde ausdrücklich als blockiert gespeichert. Kein neues neuronales Training; B-Startgewichte unverändert.

## Ergebnisse der kleinen Funktionsprüfung

Szenenfehler in mm-äquivalent, inklusive Objektzählfehler und Eckengeometrie. Keine Roboter-Platziergenauigkeit und kein unabhängiger Endtest.

| Familie / Index | Angelegte Tracks | Triangulierte Punkte | Übernommene Objektkorrekturen | Erste Schätzung | Neuronales Endbild | Ungefilterte Geometrie | Übernommene Geometrie |
|---|---:|---:|---:|---:|---:|---:|---:|
|0|82|0|0|15,795|28,157|15,795|15,795|
|1|61|18|1|2,090|2,989|1,751|1,586|
|2|–|–|0|–|–|–|–|
|3|102|27|3|5,080|4,917|4,011|4,011|

Familie2: keine vorhandene geprüfte Seitenroute verfügbar, daher keine Bildfolge und kein Eintrag in den Mittelwerten. Familie0: Tracks reichen nicht für triangulierte Punkte mit genügend Parallaxe und Reprojektionsqualität; Anfangsschätzung bleibt erhalten. Familie1: ein Kandidat wurde wegen ausgeschöpftem Optimierungsbudget abgelehnt, obwohl der Bildfehler sank; ein anderer bestand den Gate. Dadurch kann das übernommene Ergebnis besser als der ungefilterte Kandidat sein. Familie3: drei Änderungen angenommen. In diesen drei auswertbaren Szenen verschlechterte die Übernahme keine Szene; dies ist wegen der winzigen Entwicklungsstichprobe **kein allgemeiner Qualitätsnachweis**.

Der RGB-Gate liest keine GT-Objektpositionen. Die Simulatorgeometrie wird erst nach Abschluss aller Kandidaten und Übernahmeentscheidungen zur Auswertung und Darstellung genutzt. Die vorhandene Referenz-Kollisionsprüfung wird nur zur Aufnahme über bestehende Routen weiterverwendet; sie wurde nicht erweitert.

## Verifikation

- Sechs Tests: metrische Projektion/Rückprojektion/Triangulation, fehlende Parallaxe, synthetische geometrische Verbesserung, Nichtverwendung reservierter RGBs im Fit/Tracking, Ablehnung ohne Evidenz, Routenendpunkte und Dictionary-Schnittstelle der echten Modellarchitektur.
- Originales eingefrorenes B-Ensemble zusätzlich auf gespeicherten echten Simulatorbildern vorwärts geprüft; keine Optimizer-Updates.
- Alle drei B-Checkpointhashes und die Quellcode-/Konfigurationssiegel geprüft.
- Sämtliche34 in `smoke_003/artifacts.json` registrierten Dateien per SHA-256 geprüft.
- Alle vier Familien im gemeinsamen Entwicklungsregister verifiziert; ihre IDs bleiben für späteres Training gesperrt.
- Sämtliche gespeicherten 2D-Trackingbeobachtungen liegen in den Anpassungsframes und außerhalb der reservierten Prüf-RGBs.
- Sequenzkontaktbogen und dreifarbige 3D-Überlagerung visuell geprüft. Die GIFs zeigen tatsächliche Kameraaufnahmen der interpolierten Simulationsroute, keine erfundene Bewegung.

## Ansehen

Eine Szene mit erfolgreicher Korrektur:

- `smoke_003/development/scene_0001/tracking.gif`
- `smoke_003/development/scene_0001/comparison.png`
- `smoke_003/development/scene_0003/tracking.gif`
- `smoke_003/development/scene_0003/comparison.png`

Alle Vergleiche: `smoke_003/comparison.png`; Rohresultate und Ablehnungen: `smoke_003/results.json`. Cyan in den 3D-Plots=Simulator, Orange=erste Schätzung, Grün=übernommene Geometrie. Cyan im Kamera-GIF bezeichnet dagegen verfolgte Bildpunkte. Reservierte Prüf-Frames enthalten absichtlich keine Anpassungs-Tracks.

Die beiden technischen Fehlstarts sind unter smoke_001/FAILURE.md und smoke_002/FAILURE.md dokumentiert; ihre Artefakte wurden erhalten. README.md beschreibt Eingaben, Grenzen, CLI und Wiederholung in neuen Ausgabeordnern. Nächster wissenschaftlicher Schritt wäre ein größerer, vorab festgelegter Entwicklungsvergleich mit Erfassung der Verschlechterungsquote; weder Training noch Website-Veröffentlichung wurden hier gestartet.
