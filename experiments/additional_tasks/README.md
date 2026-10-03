# Zusaetzliche Aufgaben: StackFour und CubeHandover

Automatische Robustheitspruefung ist vor dem naechsten Training eingebunden:
Nach der nominalen finalen Evaluation prueft `run_training.py` zusaetzlich
elf einzelne Stoer-/Modellbedingungen plus Normalfall (je 20 gepaarte Episoden).
Parameter, Metriken und Pfade: `experiments/ROBUSTNESS.md`.

Beide Aufgaben sind als projektlokale robosuite-Umgebungen implementiert,
registriert und mit MuJoCo, Kamerabeobachtungen und derselben Vierer-Collage
getestet. Implementierung: `praxis/src/task_extensions/environments.py`.
Keine Aenderungen an upstream robosuite.

## StackFour

Vier gleich grosse Wuerfel (4 cm Kantenlaenge), zufaellig auf dem Tisch.
Ziel: roter A unten, darueber gruen B, blau C, gelb D. Alle drei Kontakte
muessen vorhanden sein, die Hoehen und seitliche Ausrichtung passen,
kein Wuerfel darf vom Greifer gehalten werden. Der fertige Turm muss
mindestens 0,5 Sekunden stabil sein. Ein Panda, Aktionsdimension 7.

Der Test konstruiert einen Turm ausschliesslich fuer die Pruefung des
Erfolgskriteriums und entfernt danach den obersten Wuerfel. Dies ist kein
Demonstrationsdatensatz und kein Policy-Ergebnis.

Ein zustandsbasierter skriptgesteuerter Kandidat fuer Demonstrationen ist
`task_extensions.stack_expert:make_expert`. Er benutzt Simulatorpositionen;
die trainierbaren Policies sehen RGB und Propriozeption. Im ersten Test war
eine von zwei Trajektorien erfolgreich. Fuer Training ist dieser Test zu klein;
die Collector-Datei wird daher ausdruecklich nicht als fertiger Datensatz benutzt.

## CubeHandover

Zwei gegenueberstehende Panda-Arme, Wuerfel mit 5 cm Kantenlaenge.
Der Wuerfel beginnt auf dem Tisch nahe Arm 0. Erfolg erfordert nachgewiesenes
Greifen durch Arm 0 und danach mindestens 0,5 Sekunden ausschliessliches
Greifen durch Arm 1, angehoben ueber den Tisch. Aktionsdimension 14,
Propriozeption beider Arme. Ein geeigneter Demonstrator muss noch erstellt
oder ein kompatibler Datensatz gesammelt werden; es wird nicht stillschweigend
die Hammer-Standardaufgabe eingesetzt.

## Vorbereitung und Training

`prepare_tasks.py` erstellt Metadaten, Szenenbilder und je Task gespeicherte
BC-/BC-RNN-/BC-Transformer-Configs (1000 Epochen, Seed 1, Batch 16).
`scene_preview.mp4` zeigt nur die untrainierte Umgebung mit offenen Greifern.
Es ist kein Video einer gelernten Aufgabenloesung.

Demonstrationen sammeln, z.B. den Stack-Kandidaten ausgiebig pruefen:

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\additional_tasks\collect_demonstrations.py --task stack_four --expert task_extensions.stack_expert:make_expert --demos 200 --attempts 600
```

Der Collector nimmt ausschliesslich erfolgreiche echte Simulationsrollouts
auf, inklusive RGB, Propriozeption, Aktionen, Zustaenden, XML und Rewards.
Er schreibt einen deterministischen 90/10-Split auf Demonstrationsebene und
einen detaillierten Collection-Report. Bestehende Datensaetze werden nicht
ueberschrieben; `--output` erlaubt separate Testdateien.
Fuer CubeHandover akzeptiert derselbe Collector `--expert module:function`.
Die Funktion erhaelt das Environment und liefert einen aufrufbaren Experten
`expert(observation) -> action` mit 14 Aktionswerten.

Erst nach erfolgreicher Datensammlung (mindestens 100, vorzugsweise 200 Demos):

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\additional_tasks\run_training.py --task stack_four
```

Der Trainer prueft Collection-Report, Trajektorienzahl, Split, Bild-/State-Keys
und Aktionsdimension vor jedem Trainingslauf. Ohne passende Daten bricht er
mit einer klaren Fehlermeldung ab. Er startet keinen sinnlosen Lauf mit Square-Daten.
Der Befehl laeuft im Vordergrund; ein neuer detached Nachtlauf fuer beide Aufgaben
folgt erst nach Validierung der Demonstrationen.

## Videos

Identische 2x2-Collage: bisherige agentview, vorne, rechts, diagonal oben
aus groesserer Entfernung. Nach dem Messende laufen die Policies standardmaessig
noch zwei Sekunden weiter; der Nachlauf wird nicht in Return, Erfolg oder
Episodenlaenge eingerechnet. `success_after_video_tail` zeigt getrennt, ob
die Aufgabe am Ende des Nachlaufs weiterhin erfolgreich ist.
Bestehende Aufnahmen werden nicht nachtraeglich als laengere Rollouts ausgegeben.

Stand: Umgebungen und Configs getestet; noch keine trainierten Modelle fuer
diese beiden Aufgaben, keine wissenschaftlichen Ergebnisse.

Hintergrund: [robosuite Standardaufgaben](https://robosuite.ai/docs/_sources/modules/environments.html)
haben Zwei-Wuerfel-Stack und Hammer-Uebergabe;
[MimicGen](https://mimicgen.github.io/) bietet Stack und Stack Three.
Diese sind keine fertigen Datensaetze fuer die hier gewuenschten exakten Varianten.
