# Größerer Aktionsspielraum vor dem Onlinepilot

Am 05.11.2026 ausdrücklich angefordert: den bislang auf ±0.02 begrenzten
Spielraum vor dem Haupttraining erhöhen. Die Begrenzung beschreibt eine
Abweichung vom zustandsabhängigen eingefrorenen IL-Actor bei normalisierten
Aktionen in [-1,1]; sie ist kein Anteil erlaubter Umweltzustände oder
physikalischer Sicherheitsabstand.

## Vorab festgelegte Prüfung

Stufen: ±0.05, ±0.10, ±0.20, entsprechend 2.5-, 5- bzw. 10-fachem bisherigem
Abweichungsbudget. Diese Faktoren bezeichnen keine Erfolgsverbesserung.
Jede Stufe beginnt neu bei denselben drei IL-Parents und warmen Critics und
verwendet dieselben festen Replay- und BC-Batchstreams wie die vorherige
Stabilitätsprüfung. Architektur des Bewegungskopfs, LR, BC0.01 und übrige
Lernparameter werden dabei nicht zusätzlich abgestimmt.

Kontrollen nach 10/50/100/500 Criticupdates auf sechs neuen geteilten
Entwicklungsfamilien 2026112400–2026112405 je Parent. Zulässig sind höchstens
ein verlorener Parent-Erfolg je Parent und höchstens einer insgesamt pro
Kontrollpunkt. Neue Erfolge heben Verluste nicht auf. Aktionen müssen endlich
und innerhalb der jeweiligen Grenze bleiben. Das alte MSE-Limit von0.01 wird
nicht zusätzlich benutzt, weil es große erlaubte Abweichungen schon per
Definition ausschließen könnte; MSE wird weiter als Messgröße protokolliert.

Bei der ersten gescheiterten Stufe endet die Erweiterung. Größere Stufen werden
dann nicht mehr geprüft. Das beweist nicht, dass jede größere Grenze scheitern
muss, sondern ist eine konservative Begrenzung dieses Versuchs. Unter den
vollständig bestandenen Stufen wird die größte gewählt, fest der500er-Checkpoint.

**Erst danach** folgt eine separate Bestätigung auf20 neuen geteilten Familien
2026112500–2026112519 je Parent, jeweils mit erneut ausgeführtem eingefrorenem
Parent. Erforderlich sind mindestens10/20 Parent-Erfolge je Seed, höchstens
zwei verlorene Parent-Erfolge je Seed und höchstens drei insgesamt.
Scheitert diese Bestätigung, wird nicht anhand dieser Ergebnisse nachträglich
eine andere Grenze gewählt. Es wird kein Hauptlauf freigegeben.

Diese Auswahl ist Entwicklungsarbeit; die Bestätigungsfamilien sind ein
getrenntes Entwicklungspanel, kein reservierter wissenschaftlicher Endtest.
Die bisherigen Endtestfamilien bleiben unangetastet.

Maximales Zeitbudget eine Stunde, STOP-Datei im Ausgabeordner, keine
automatischen Neustarts oder Resume. Vorhandene Gewichte und Daten bleiben
unverändert; alle neuen Ergebnisse erhalten einen eigenen Ordner.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/action_range.py --output experiments/critic/critic_warmstart_20261104/range_NEW
```

## Vorbereitung bei bestandener Bestätigung

`prepare_range_pilot.py` erzeugt nur nach vollständig bestandenem Gate einen
neuen Pilotordner. Der Onlinepilot verwendet den gleichen bereits technisch
geprüften Ablauf aus `new_test.py`, mit der bestätigten größeren Grenze und
entsprechend angepasstem Driftgate. Exploration wird ebenfalls auf diese Grenze
projiziert. Übrige Parameter und die noch unbenutzten Online-/Entwicklungsfamilien
des vorbereiteten Pilots bleiben erhalten. Er startet wieder bei den ursprünglichen
Actors, nicht bei anhand der Entwicklungsdaten ausgewählten Actors.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/prepare_range_pilot.py
& praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/new_test.py run --execute --output experiments/critic/critic_warmstart_20261104/pilot_002
```

Die Vorbereitung startet den Hauptlauf nicht. Eine größere Grenze garantiert
weder bessere Leistung noch nützliche Criticgradienten; sie beseitigt zunächst
eine praktische Einschränkung der bisher geprüften Variante.
