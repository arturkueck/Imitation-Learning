# Datensatzbericht: neue Self-Imitation-Daten

800 feste Sammelversuche abgeschlossen. Alle erfolgreichen und fehlgeschlagenen Episoden sind archiviert; fuer BC sind nur erfolgreiche Episoden vorgesehen. Keine alten Endtestrollouts wurden in diesen Datensatz kopiert.

| Aufgabe / Split | Versuche | Erfolgreiche Episoden | Akzeptierte Frames |
|---|---:|---:|---:|
| stack2_train | 300 | 286 | 53438 |
| stack2_valid | 100 | 99 | 18869 |
| stack3_train | 300 | 154 | 51423 |
| stack3_valid | 100 | 56 | 18497 |

## Auswahl pro Teacher

| Aufgabe / Split | Teacher | Versuche | Erfolge |
|---|---:|---:|---:|
| stack2_train | 1 | 100 | 96 |
| stack2_train | 2 | 100 | 96 |
| stack2_train | 3 | 100 | 94 |
| stack2_valid | 1 | 34 | 33 |
| stack2_valid | 2 | 33 | 33 |
| stack2_valid | 3 | 33 | 33 |
| stack3_train | 1 | 100 | 43 |
| stack3_train | 2 | 100 | 53 |
| stack3_train | 3 | 100 | 58 |
| stack3_valid | 1 | 34 | 22 |
| stack3_valid | 2 | 33 | 21 |
| stack3_valid | 3 | 33 | 13 |

Unabhaengige Nachpruefung: 339727 Frames aller800 Episoden auf endliche Werte geprueft. Zehn Modelleingaben aus Prae-Aktionsbeobachtung, Anker und Phasenschritten nachgerechnet. Exakte Verkettung post_obs[t]=pre_obs[t+1] nachgewiesen. Gespeicherte Phasen-Pseudolabels passen zur Teacherentscheidung; sie werden nicht fuer den Abschlussloss verwendet. Erfolg aus50 aufeinanderfolgenden valid-Frames neu berechnet. Keine identischen Initialzustand-Hashes zwischen Train und Valid innerhalb derselben Aufgabe.

Die Teacherzuweisung erfolgte zyklisch vor dem Versuchsausgang. Die ersten300 Versuche pro Aufgabe bilden Training, die weiteren100 Validierung. Unterschiede zwischen den Erfolgsquoten zeigen Selektionsbias; ein erfolgreicher Endzustand garantiert keine optimale oder durchgehend kollisionsfreie Bahn. Phasen-/Controllerstruktur und privilegierte Simulatorzustaende bleiben Teil der Methode.

Bei Zweier-Versuch121063 stoppte die erste Aktionsnachrechnung: batched CUDA-Inferenz wich um2,503395e-6 von der tatsaechlichen Einzelbild-Inferenz ab. Wiederholung mit exakt demselben Einzelbildpfad liefert0,0 Abweichung. Nach Reparatur wurde exakte Gleichheit statt einer groesseren Toleranz geprueft; absichtlich korrumpierte Aktion wurde im Negativtest abgewiesen. Die ersten63 Episoden wurden erhalten und vor Fortsetzung nochmals geprueft. Dokumentation in repair_001/.

Trainingsarme: AOriginal; B75%Original+25%eigeneZweier; C75%Original+25%eigeneDreier. Neue Daten beeinflussen den Actor-MSE, Abschlussloss bleibt an die Originalexpertendaten gebunden. Validierung ist nicht Training. Ergebnisse stehen nach Laufende in RESULTS.md; dieser Bericht behauptet keinen Trainingsvorteil.

Maschinenlesbare Nachweise: dataset_manifest.json, dataset_audit.json, datasets/stack*/manifest.json und die NPZ-Dateien samt Modell-XML. Der neue Datensatz enthaelt Drei-Wuerfel-Episoden; die anschliessenden Ergebnisse sind keine reine Zero-shot-Generalisation ausschliesslich aus Zwei-Wuerfel-Trainingsdaten.