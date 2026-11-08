# Nachtversuch zur Machbarkeit critic-gestützter Imitation

Der Versuch misst, wie oft tatsächlich ausgeführte Bewegungen verschiedener eingefrorener IL-Policies aus derselben Situation zu einem anderen stabilen Dreierturm-Ergebnis führen. Das Ergebnis dient der Themenwahl für eine Arbeit zu Behavior Cloning. Der Lauf erzeugt gepaarte Simulationsmessungen und führt null Optimizerupdates aus.

## Start und Zeitfenster

Vom Projektverzeichnis aus startet folgender PowerShell-Befehl den versteckten Supervisor. Vor dem Start muss der technische Smoke abgeschlossen und der Hauptlauf im Zustand `READY` sein. Die Eingangsprüfung kann einige Sekunden dauern. Für das feste Ende am Sonntag, 8. November 2026, um 12:00 Uhr in Berlin den Befehl spätestens kurz vor 01:00 Uhr aufrufen.

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\il_action_feasibility_20261107\night.py launch
```

Der Supervisor rechnet relativ zum Startzeitpunkt und hält Windows während des Laufs wach. Ein Start um 00:30 Uhr ergibt eine Breitenphase bis 05:30 Uhr, eine erste Vertiefung bis 08:30 Uhr und eine zweite bis 11:30 Uhr. In jedem Fenster sind 25 Sekunden für den Abschluss eines Workers und die Auswertung vorgesehen. Zu späte Starts werden vor dem Anlegen der Startsperre abgewiesen. Manuelles Herunterfahren beendet den Prozess.

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\il_action_feasibility_20261107\night.py status
```

Der Statusbefehl liest zwei kleine JSON-Dateien und prüft die Prozesse. Ein kontrollierter Abbruch erfolgt durch Anlegen der Datei `night_001/STOP`. Der Supervisor überwacht Worker, Fortschritt und Zeitgrenzen. Fehler, Stopps und unvollständige Messungen ergeben keine wissenschaftliche Bestätigung. Jeder vollständig gespeicherte Familienvergleich bleibt als eigene SQLite-Transaktion erhalten. Ein exklusiver Startmarker verhindert Doppelstarts und versehentliches Überschreiben.

## Versuchsplan

| Zeit ab Start | Inhalt | Datensatz |
|---|---|---|
| Stunde 0–5 | Vier Richtungen reihum, pro Richtung eine Beobachtung je Familie. Der erste Block von 60 Familien wird separat ausgewiesen. | Gemeinsame Familien für alle vier Richtungen |
| Stunde 5–8 | Ausgewählte Einzelaktion. Erneute Häufigkeitsmessung und Auswertung des nutzbaren Critic-Signals. | Neue Familien |
| Stunde 8–11 | Ausgewählter Bewegungsabschnitt. Erneute Messung und zusätzlicher Vergleich von 20 Quellaktionen mit genau einer Quellaktion. | Weitere neue Familien |

- [Einzelaktion beim Anflug](richtungen/einzelschritt_anflug.md)
- [Einzelaktion beim Greifen](richtungen/einzelschritt_greifen.md)
- [Bewegungsabschnitt beim Transport](richtungen/abschnitt_transport.md)
- [Bewegungsabschnitt bei der letzten Ablage](richtungen/abschnitt_ablage.md)

## Gepaarter Eingriff

Drei eingefrorene, aus Demonstrationen gelernte Policies bilden den Datenpool. Quelle und Referenz durchlaufen alle neun geordneten Kombinationen gleichmäßig in Blöcken von neun Startfamilien. Damit bleibt auch die erwartete Verdünnung durch identische Quelle und Referenz messbar. Die spätere Aussage gilt für diese Mischung eigener IL-Erfahrungen in der Simulation. Ihre Anteile sind eine Festlegung dieses Versuchs.

Bis zum festgelegten Zeitpunkt steuert die Quellpolicy einschließlich ihrer Phasenentscheidungen. Ab dann steuert in beiden Zweigen dieselbe Referenz die Phasenwechsel. Im Aufzeichnungszweig liefert die Quelle für ein oder höchstens 20 Frames die ausgeführten Bewegungen, danach übernimmt die Referenz vollständig. Der Vergleichszweig wiederholt die gesamte Vorgeschichte und nutzt bereits ab dem Prüfzeitpunkt auch für die Bewegung die Referenz. Die ausgewerteten Abschnitte werden frisch und zustandsabhängig erzeugt. Beim Vergleich zweier Abschnitte dürfen sich die Folgezustände ab dem ersten Eingriff unterscheiden. Ein vorzeitiges reguläres Episodenende verkürzt das Fenster.

Prüfstelle und Bewegungsfenster werden vor der Messung festgelegt. Wiederherstellung, Phase, Anfangszustand und Hash der Vorgeschichte bis zum Eingriff werden verglichen. Jede 30. Familie einschließlich der ersten erhält eine identische Kontrollwiederholung. Unveränderte Aktionsfolgen können den identischen Ausgang wiederverwenden. Prüfstelle verfehlt, identische Aktion, tatsächlich anderer Erfolg und bloßer Zeitunterschied werden getrennt gezählt. Die Sequenzerdauer und das Episodenlimit von 1000 Frames bleiben in beiden Zweigen gleich. Ein stabiler Turm benötigt 50 aufeinanderfolgende gültige Frames.

## Auswahl und Interpretation

Primärmaß ist der Anteil der eingeplanten, vollständig bearbeiteten Familien, in denen genau ein Zweig den stabilen Dreierturm erreicht. Auch nicht erreichte Prüfstellen zählen im Nenner. Die Richtung des Wechsels wird getrennt gezählt. 10 % sind eine praktische Planungsschwelle aus dem Beispiel mit 30 informativen Fällen pro 300 Familien. Sie ist kein Mindestgewinn beim Lernen.

Nach fünf Stunden wählt ein lokales Skript reproduzierbar eine Richtung pro Gruppe. Es bevorzugt die höhere untere Grenze des deskriptiven 95-%-Wilson-Intervalls der Wechselrate, bei Gleichstand die höhere Erreichbarkeit und dann die Reihenfolge in `protocol.json`. Alle Breitenmessungen bleiben sichtbar. Auch bei schwachen Signalen werden zwei Kandidaten weiter untersucht und die geringe Datenabdeckung dokumentiert. Die Kandidatenauswahl verwendet weder Q-Vorhersagen noch Vertiefungsdaten. Die Gruppen unterscheiden sich sowohl durch die Manipulationsphase als auch den zeitlichen Umfang des Eingriffs.

Primäre Bestätigung kommt aus den frischen Vertiefungsfamilien. Der Bericht weist den ersten festen 60er-Block separat aus. Zusätzliche Familien werden bis zur vorab festgelegten Zeitgrenze untersucht. Die konkrete Gesamtzahl hängt vom Durchsatz ab. Wilson-Intervalle dienen als Orientierung bei der balancierten Mischung der drei verwandten Policies. Der Lauf misst die Erträge vorgegebener Aktionsalternativen. Die Wirkung der daraus abgeleiteten Gewichte auf eine neu trainierte BC-Policy bleibt eine spätere Forschungsfrage.

Für Einzelaktionen ist die Q1-Differenz zwischen Quellaktion und Referenzaktion vor dem Eingriff definiert. Für Abschnitte wird die diskontierte Summe dieser Differenzen entlang des tatsächlich ausgeführten Abschnitts ausgewertet. Der vorgewärmte Critic lernte aus einer Mischung von Parents. Seine Eignung für eine bestimmte Referenzfortsetzung ist eine Prüfgröße. Ein Betrag bis einschließlich 0,000001 gilt als Gleichstand. Die Entscheidungsregel bevorzugt in diesem Fall die Referenz. Die zusätzliche Ein-Schritt-Ablation der zweiten Vertiefung isoliert den Beitrag der restlichen Abschnittsbewegungen.

## Ergebnisse und Reproduktion

`night_001/selection.json` hält die Auswahl samt Grundlage fest. In `breadth`, `deep1` und `deep2` entstehen eigene Berichte je untersuchter Richtung, eine Auswertung je Referenzseed und der erste feste 60er-Block. `ERGEBNIS.md` fasst die Vertiefungen zusammen. `pairs.sqlite3` enthält die einzelnen Vergleiche mit Start- und Präfixhash, Aktionen, Criticdifferenzen und gepaarten Ausgängen. `ready.json` hält den Interpreter und die Hashes der Modellgewichte, Quellen und des Protokolls fest. Die Pipeline öffnet keine historischen Endtestrollouts. Technische Smoke-Familien haben einen eigenen Seedbereich.
