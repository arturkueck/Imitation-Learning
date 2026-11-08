# Vorbereiteter IL-Actor-Critic-Nachtlauf

Vorbereitung vom 04.11.2026. Der Hauptlauf wird durch die Vorbereitung nicht
gestartet. `night_001/config.json` aktiviert ausschließlich die separate,
vorbereitete Ausführung; die allgemeine `config.json` bleibt deaktiviert.

## Festgelegter Umfang

- Drei unveränderte IL-Parents, drei Arme: A zufälliger Critic + RL;
  B vorgewärmter Critic + RL; C identischer Warmstart + RL und 0.01 BC.
- 120 neue Trainings- und 40 Validierungsepisoden. Mindestens 20 erfolgreiche
  und fünf gescheiterte Trainingsepisoden; andernfalls Abbruch ohne Nachsammlung.
- Je Criticseed 2000 Vorwärmupdates. Alle drei Critics müssen das festgelegte
  Validierungsgate bestehen; andernfalls kein Online-Training.
- Je Arm/Parent vier Runden mit fünf Onlineepisoden und 500 Criticupdates,
  Actorupdate alle zwei Schritte. Insgesamt 180 Onlineepisoden und 18000
  Online-Criticupdates, zusätzlich 6000 Offline-Criticupdates.
- Entwicklungsauswertung in Runde 0/2/4 mit je 20 gemeinsamen Starts:
  540 Rollouts. Insgesamt 880 geplante Episoden einschließlich Sammlung.
  Die 50 reservierten Endtestfamilien werden nicht verwendet.
- Alle bisherigen Seeds, Datenaufteilungen, Rewards, Lossfunktionen und
  Hyperparameter bleiben erhalten. Statusausgaben wurden für Sammlung,
  Onlineupdates und Entwicklungsauswertung ergänzt.

## Start und Kontrolle

Die folgenden Befehle aus dem Repositoryroot ausführen. Ein Start ist eine
explizite spätere Aktion; kein Zeitplan und keine Automation wurden eingerichtet.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/night.py launch
```

Der Supervisor führt `prepare`, `warmup` und `train` nacheinander in getrennten
Prozessen aus. Er läuft ohne sichtbares Fenster, verhindert währenddessen
Windows-Leerlaufstandby und gibt diese Anforderung beim Ende wieder frei.
Je Phase gelten unverändert maximal drei Stunden; insgesamt höchstens neun
Stunden zuzüglich bis zu 40 Sekunden zum Beenden eines Workers. Dies ist eine
Obergrenze, keine Laufzeitprognose. Energiesparen durch Deckelschließen,
Benutzeraktion, Neustart oder Stromausfall wird dadurch nicht verhindert.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/monitor.py
```

Der Routinecheck liest nur kleine Statusdateien und neue Workerlogzeilen.
Der Supervisor prüft seinen eigenen Worker alle fünf Sekunden. Ein fehlender
Heartbeat wird als Fehler erkannt, zehn Minuten ohne sichtbaren Fortschritt
als Warnung. `monitor/state.json` speichert Offset, Fortschritt und letzte
erfolgreiche Prüfung. Es wird keine zusätzliche Modellinstanz geladen.

Gezielter Abbruch:

```powershell
New-Item -ItemType File -Path experiments/critic_warmstart_20261104/night_001/STOP
```

Der Supervisor überträgt STOP an den aktuellen Worker. Nach 30 Sekunden ohne
Beendigung stoppt er nur seinen Worker einschließlich dessen Kindprozessen.
Es gibt weder automatische Wiederholungen noch Resume. Bereits geschriebene
Ergebnisse und Checkpoints bleiben erhalten. Ein fehlgeschlagener Lauf wird
nicht als vollständiger Vergleich gewertet.

## Nachweise und Ergebnisse

`night_001/protocol.json` enthält die exakten Befehle, Konfiguration, Ressourcen,
Hashwerte der Quelltexte, Ausgangsgewichte und ursprünglichen Trainingsarrays
sowie den technischen Smoke-Nachweis. Eingaben werden vor dem Start und jedem
Phasenwechsel erneut geprüft. Änderungen erfordern eine neue Vorbereitung in
einem neuen Ordner. Vorhandene Laufordner werden nicht überschrieben.

- `night_001/supervisor.json`: Prozessstatus, Phase, Heartbeat und Fehler.
- `night_001/worker.log`: Ausgaben der drei Phasen.
- `night_001/data/data_audit.json`: Datengate und getrennte Startfamilien.
- `night_001/warm/validation.json`: Critic-Validierung je Seed.
- `night_001/train/history.json`: Trainingsmetriken.
- `night_001/train/development.json`: Entwicklungsergebnisse aller Arme.
- `night_001/train/frozen_final.json`: neun feste finale Checkpoints samt Hashes.

Rohdaten und Gewichte bleiben lokal ignoriert. Der technische Probelauf
`smoke_night_001` gehört nicht zu wissenschaftlichen Ergebnissen. Ein positiver
Probelauf belegt Ausführbarkeit, keinen Lernvorteil.
