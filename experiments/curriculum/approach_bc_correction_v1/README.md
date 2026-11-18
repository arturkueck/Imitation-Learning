# BC-Korrekturtraining: zweites Anfahren

Status: Vorbereitung; kein wissenschaftlicher Trainingslauf gestartet.
Vorbereitung umfasst Code, Protokoll, abgesonderten technischen Smoke-Test und
einen READY-Lauf. Neue wissenschaftliche Korrekturdaten werden erst beim Start
des vollständigen Laufs erzeugt, danach trainiert und bewertet.

## Hypothese und Abgrenzung

Allein die Expertenübernahme beim zweiten Anfahren erhöhte bisher den
Dreierturm-Erfolg auf vorhandenen Entwicklungsszenen von 26/60 auf 45/60.
Hier wird geprüft, ob BC aus Expertenkorrekturen dieser Phase lernen kann
und ob Aktions- oder Abschlusslernen den Nutzen trägt. Kein Critic und keine
Curriculum-Reihenfolge. Eine geordnete Datenpräsentation kommt erst in einer
späteren getrennten Untersuchung hinzu.

## Neue Daten ohne Übernahme von Testfällen

Die drei unveränderten B-Modelle bei 30k Updates erzeugen jeweils ihre eigene
erste Platzierung und den bestehenden Rückzug. Beim tatsächlichen Beginn des
zweiten Anfahrens übernimmt der vorhandene Experte nur Phase 0. Seine Aktionen
XYZ/Greifer und der Phasenabschluss sind die BC-Labels. Eingabevertrag wie bisher:
zehn Merkmale, Phasenanker am Beginn, echte Schrittzahl. Keine Teleportation,
kein binäres Erfolgsrating als Aktionslabel. Korrekturen sind reine Simulation.

- Training: 40 neue Anfangsszenen, Seeds 2026151000–2026151039.
- Validierung: 10 neue Anfangsszenen, Seeds 2026152000–2026152009.
- Jeder Start wird von allen drei Ausgangscontrollern ausgeführt: 150
  Sammelversuche. Alle akzeptierten Trainingskorrekturen werden gemeinsam
  genutzt, damit die Modellseeds denselben Datenpool sehen.
- Ganze Anfangsszenen bleiben mit allen Controller-Ausführungen und Frames
  in genau einem Split. Validierung wird nicht als Trainingsquelle verwendet.
- Erreicht ein Controller das zweite Anfahren nicht oder läuft die
  Expertenphase ins Zeitlimit, wird das protokolliert. Keine stille
  Wiederholung und kein Ersatzstart. Bei leerem Split/fehlenden positiven
  Abschlusslabels Abbruch statt Training mit ungeeigneten Daten.
- Fortschritte auf solchen Expertenfortsetzungen garantieren keine Abdeckung
  später von der trainierten Policy erzeugter Zustände. Kein iteratives DAgger.

Diese Daten enthalten nun Zustände nach der ersten Ablage und dem Rückzug.
Sie enthalten weiterhin keinen neu gelernten Rückzug oder lange Open-Phase.

## Kontrolliertes Lernen und fünf Ausführungsvarianten

Die Phase-0-MLP besitzt gemeinsam genutzte versteckte Gewichte für Aktion und
Abschluss. Nur die letzte Ausgabezeile einzufrieren würde das andere Verhalten
nicht konstant halten. Deshalb werden zwei getrennte Kopien des unveränderten
B-Modells als Diagnosekomponenten verwendet. Eine wird nur mit Aktions-MSE,
die andere nur mit Abschluss-BCE trainiert. Bei der Ausführung wird jeweils nur
die untersuchte Phase-0-Ausgabe übernommen; alle anderen Ausgaben stammen aus B.
Keine zusätzliche Schicht, keine Verwendung des Abschlusswerts als Critic.

| Ausführung | Phase-0-Aktion | Phase-0-Abschluss |
|---|---|---|
| baseline | ursprüngliches B | ursprüngliches B |
| replay | weitertrainierte Replay-Aktionskopie | weitertrainierte Replay-Abschlusskopie |
| action | Korrektur-Aktionskopie | ursprüngliches B |
| completion | ursprüngliches B | Korrektur-Abschlusskopie |
| combined | Korrektur-Aktionskopie | Korrektur-Abschlusskopie |

Jede Kopie startet aus exakt demselben Modell und vollständigem AdamW-Zustand
ihres B-Vorfahren. Nur die Gewichte der gesamten Phase-0-MLP werden freigegeben;
Phase 1–6 bleiben bitgleich. Versteckte Schichten und Ausgangsschicht der
Phase-0-Kopie werden trainiert, nicht nur eine letzte Schicht.

Pro Modellseed werden vier Komponenten trainiert: Replay-Aktion, Replay-Abschluss,
Korrektur-Aktion, Korrektur-Abschluss. Je 5.000 zusätzliche Updates; insgesamt
12 Komponenten / 60.000 Komponentenupdates. Die kombinierte Ausführung nutzt
exakt die separat trainierten Komponenten und erhält keine zusätzlichen Updates.
Das ist ein kontrolliertes zusammengesetztes Diagnosesystem; eine spätere
Verdichtung zu einer einzigen gemeinsamen MLP ist nicht Teil dieses Versuchs.

Batchgröße 64. Korrekturkomponenten: 32 ursprüngliche Phase-0-Expertenframes und
32 neue Korrekturframes. Replaykomponenten: 64 ursprüngliche Phase-0-Frames.
Die ersten 32 Replay-Indizes sind zwischen beiden Quellen gleich. Aktion und
Abschluss verwenden jeweils denselben vorab erzeugten Samplingplan. Zufällige
Frameauswahl, keine nachträglich angepasste Schwierigkeit oder Reihenfolge.

Loss der Aktionskopie: mittlerer Fehler der vier aktiven Aktionswerte.
Loss der Abschlusskopie: 0,1 × BCE mit ausschließlich aus Trainingslabels
ermitteltem positivem Gewicht (gedeckelt bei 50). Alte und neue Quelle werden
jeweils mit 0,5 gewichtet; Replay analog mit zwei alten Hälften. Die
Positivgewichte werden pro Quelle festgelegt und mit den Daten dokumentiert.
LR 1e-4, AdamW-Decay 1e-6, Gradientengrenze 10 aus dem bestehenden B-Vertrag.
Kein erneutes Warmup; der geladene Optimizer befindet sich bereits bei 30k.

Alle Ausführungen nutzen die bestehende 0,8-Abschlussschwelle und die finale
Release-Clock-Korrektur. Phase 0 wird auch beim ersten Anfahren und im Rückzug
verwendet. Deshalb aktiviert ein expliziter Ausführungskontext die neuen
Komponenten ausschließlich bei Platzierung 2, Phase 0, außerhalb des Rückzugs.
Erstes Anfahren und Rückzug verwenden weiterhin exakt B. Der Kontext kommt aus
dem bestehenden Sequencer; er ist kein zusätzlich gelerntes Zustandsmerkmal.
Ein geladenes Composite verwendet standardmäßig B, bis dieser Kontext gesetzt
wird. Zum Ausführen daher `evaluate_episode` oder denselben Kontext-Gate nutzen.
Eine spätere globale Änderung des gemeinsamen Phase-0-Kopfs ist nicht geprüft.

## Endpunkt und Vergleichbarkeit

Fester Endpunkt Update 5.000. Keine Auswahl des besten Checkpoints anhand
von Validierungs-, Entwicklungs- oder Bestätigungsszenen; keine Anpassung
von Schwellen, Loss oder Daten nach deren Ergebnissen.

- Validierung: Aktionsfehler und Abschluss-BCE auf separaten Korrekturszenen.
- Entwicklung: bekannte 20 Szenen 2026113000–2026113019, fünf Ausführungen je
  Modell. Nicht als unabhängige frische Bestätigung interpretieren.
- Bestätigung: 50 neue Szenen 2026153000–2026153049 mit vorab festgelegten
  Einstellungen und fester Updatezahl. Keine Auswahl anhand dieses Panels.
- Primär: vollständiger Dreierturm über 50 strenge Gültigkeitsframes.
  Episodenhorizont 1000. Pro Modell gleiche Startzustände für alle fünf Varianten.
- Gewinne/Verluste gegen baseline und replay getrennt auswerten, Ergebnisse
  je Modellseed ausweisen. Szenen sind über Modellseeds geteilt.

Die Netzwerke werden pro Modell trainiert und dann mit fixiertem Endpunkt
bewertet; das Programm passt nach geöffneten Ergebnissen keine anderen
Modelle oder Einstellungen an. Die Komponenten sind dann für diesen Modellseed
eingefroren. Bestätigungsstarts nicht in eine spätere Optimierungsrunde übernehmen.

## Ablage, Wiederherstellung und Laufgrenzen

```powershell
praxis/.venv/Scripts/python.exe experiments/curriculum/approach_bc_correction_v1/pipeline.py prepare --output praxis/results/curriculum/approach_bc_correction_v1/ready_001
# Nur nach Freigabe des vollständigen Laufs:
praxis/.venv/Scripts/python.exe experiments/curriculum/approach_bc_correction_v1/pipeline.py run --output praxis/results/curriculum/approach_bc_correction_v1/ready_001
```

Grobe Planung: 1–2 Stunden einschließlich Datensammlung und 1.050 vollständigen
Bewertungen; harte Obergrenze drei Stunden. Bei Zeitlimit bleiben Zwischenstände
erhalten; kein automatischer Neustart und keine Änderung des Versuchsbudgets.
Kein Herunterfahren; Schlafverhinderung wird nach Laufende freigegeben.

Laufordner: Plan, Provenienz, Quellenkopien, Paket-/GPU-Umgebung,
`collection_attempts.json`, `corrections_train/validation.npz` mit Familien-IDs,
Datasetmanifest, vorab gespeicherte Samplingpläne, Komponentenordner mit
`latest.pth`, Loss-/Validierungswerten, Kompositionskarten und vollständige
Rolloutresultate. Originalmodelle und Daten werden nicht überschrieben.

Checkpoint enthält sämtliche Gewichte, AdamW-Zustand, nächsten Batchindex,
Trainingsplan, Daten-/Samplerhashes und Python-/NumPy-/Torch-/CUDA-RNG.
`restore_branch(path, device)` lädt und prüft diese Zustände. `fit_branch(...,
resume=path)` kann einen unvollständigen Komponentenlauf mit dem gespeicherten
Samplingplan weiterführen. Gesamtpipeline wird nicht automatisch fortgesetzt;
neue Budgets/Samplingpläne benötigen eine neue versionierte Festlegung.
Phasen 1–6 werden nach jedem Komponentenlauf gegen B bitweise verglichen.

Technischer Smoke-Test: getrennte technische Szenen, ein Modell, vier Updates
je Komponente, fünf Ausführungen auf zwei bekannten technischen Prüfszenen.
Kein wissenschaftliches Ergebnis, keine neue Bestätigung. Der volle Lauf bleibt READY.
