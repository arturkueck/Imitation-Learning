# Critic vorwärmen, Actor durch RL verbessern

Nach der Gegenfaktualprüfung werden verrauschte TD-Targetaktionen für neue
relative Versuche auf dieselben Parentgrenzen wie Actor und Exploration
projiziert. Versionierung und Prüfung stehen in
[TARGET_AKTIONEN.md](TARGET_AKTIONEN.md). Bestehende Resultate bleiben historisch;
ein Lernvorteil der Korrektur ist noch nicht geprüft.

Die anschließende begrenzte Stabilitätsprüfung und der daraus vorbereitete
Onlinepilot sind in [STABILITAET.md](STABILITAET.md) beschrieben. Die neue
Aktionsbegrenzung ist eine deklarierte Methodenänderung, keine stille
Bugkorrektur des ursprünglichen A/B/C-Vergleichs.

Ein separater Nachtlauf mit Supervisor, inkrementellem Monitor und eingefrorenen
Eingaben ist in [NACHTLAUF.md](NACHTLAUF.md) beschrieben. Vorbereitung startet
den Hauptlauf nicht; der Start erfolgt später explizit über `night.py launch`.

Der erste Nachtlauf ist technisch abgeschlossen, aber alle Arme verloren ihre
Aufgabenleistung. Die Prüfung in `diagnosis_001/REPORT.md` dokumentiert starke
Actor-Drift bereits nach der ersten Runde und einen behobenen Loggingfehler.
Reproduktion ohne Training oder Rollouts:
`praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/diagnose.py --output experiments/critic/critic_warmstart_20261104/diagnosis_NEW`.
Die Korrektur protokolliert nun auch verzögerte Actorupdates samt RL-/BC-Loss;
sie ändert weder Gradienten noch Hyperparameter und repariert den Kollaps nicht.

Status: ausführbares Setup mit technischen Tests. Kein wissenschaftlicher
Actor-Critic-Vergleich gestartet, kein Wirksamkeitsnachweis. `training_enabled`
ist standardmäßig `false`. Technische Optimizerupdates zählen ausdrücklich nicht
als wissenschaftlicher Trainingslauf; deren Zahl wird im Smoke-Protokoll erfasst.

## Forschungsfrage und Arme

Alle Arme starten beim gleichen vorhandenen IL-Actor pro Parentseed1/2/3 und
verwenden denselben geometrisch geprüften Rückzugscontroller. Die Referenz für
Phasenentscheidungen bleibt eine eingefrorene Parentkopie, weil Aktions- und
Abschlussausgabe sonst über gemeinsame Schichten gekoppelt wären. XYZ und
Greiferaktion werden optimiert; Rotation bleibt wie bisher null. Kein gelernter
Sequencer oder visueller Closed Loop wird behauptet.

| Arm | Criticinitialisierung | Actor-Training |
|---|---|---|
| A | zufällig | RL, ohne direkten BC-Term |
| B | vorgewärmt | RL, ohne direkten BC-Term |
| C | exakt derselbe vorgewärmte Critic wie B | RL +0.01 BC-MSE |

A/B isoliert die Warmstart-Strategie bei gleicher Online-Update-/Versuchszahl,
aber zusätzlichem Offline-Rechenaufwand für B. B/C untersucht die direkte
Nachahmungsbindung. Alle Actors enthalten bereits IL-Vorwissen. Der Ansatz ist
kein Actor von null mit ausschließlich criticseitigem Expertenwissen.

## Wertlernen und Datenvertrag

Neue, vorab festgelegte Sammlung:120 Trainingsepisoden und40 Validierungsepisoden,
zyklisch die drei unveränderten Parents, alle Ausgänge behalten. Seeds stehen
in config.json. Alte Endtestrollouts werden nicht eingelesen. Mindestmenge:
20 erfolgreiche und fünf gescheiterte Trainingsepisoden; sonst Stop ohne Retry.
Der vollständige Manifeststatus alleine gibt das Training nicht frei:
`ready_for_training` und der gehashte Datenaudit müssen ebenfalls gültig sein.

Pro Aktion werden gespeichert: aktueller Criticzustand, ausgeführte Aktion,
Folgezustand, aktuelle/nächste Actoreingabe und Phase, Reward, Terminalflag,
beobachteter diskontierter Return. Der Critic erhält gegenwärtigen Simulatorzustand,
Objekt-/Roboterbeobachtung und Sequencer-/Gatestatus einschließlich Restzeit.
Keine zukünftigen Ereignisse werden als aktuelle Features benutzt. Verdeckte
OSC-Laufzeitzustände sind damit nicht nachweislich vollständig erfasst.
Der technische Probelauf hat95 Criticfeatures und vier Aktionsdimensionen.

Reward: ausschließlich1 beim bestätigten Gesamterfolg nach50 gültigen Frames,
sonst0. Gamma0.995. Zeitlimit1000 und Controllerfehler nach200 Rückzugsaktionen
sind echte Enden der definierten endlichen Aufgabe; dort wird nicht gebootstrapt.
Eine externe Budgetunterbrechung ist kein künstliches Episodenende und erzeugt
keine als vollständig deklarierte Trainingsepisode.

Vorwärmen:2000 MC-Return-Updates pro Criticseed bei eingefrorenem Actor. Diese
Labels bewerten die damals beobachtete Fortsetzung der sammelnden Policy;
sie sind keine automatisch korrekten Werte einer später veränderten Policy.
Normierung wird ausschließlich aus Trainingsframes bestimmt. Der vorgewärmte
Critic muss auf separaten Validierungsfamilien endlich sein und beim Return-MSE
mindestens die konstante Trainingsmittelwert-Referenz erreichen. Dieses Gate
belegt keine zuverlässige Bewertung unbekannter Aktionen.

Online: TD3-inspirierter Kern mit zwei Critics, Minimum im Target, verzögerten
Actorupdates, Targetnetzen und Aktionsglättung. Bei dem auf[0,1] beschränkten
Return werden Targets entsprechend begrenzt. A/B haben ausschließlich den
Actorloss `-Q1(s, actor(x))`; C ergänzt0.01 ursprünglichen Experten-BC-MSE.
Das ist keine Cal-QL-/AWAC-Replikation und enthält keine Garantie gegen
Extrapolationsfehler. Der Critic wird online weitertrainiert.

## Geplanter Umfang und Auswertung

Je Arm/Parent vier Runden mit fünf eigenen Episoden und500 Criticupdates,
Actorupdate alle zwei Criticupdates. Kritischer Replayanteil:50% gemeinsame
Ausgangsdaten,50% private Onlineerfahrungen des jeweiligen Arms. C nutzt für BC
ausschließlich den ursprünglichen Experten-Trainingssplit. Kein Validation-MSE
wird optimiert und keine fehlgeschlagene Aktion direkt nachgeahmt.

Entwicklungsbewertung bei Runde0/2/4 auf20 gemeinsamen Starts pro Modell.
Versuchszahl und Online-Gradientenschritte sind gleich, die tatsächlichen
Umweltinteraktionen können sich durch frühere Erfolge unterscheiden und werden
separat gezählt. Zusätzliche Offline-Warmupdates und Evaluationskosten separat
berichten. Checkpoint ist fest die letzte Runde; die reservierten50 finalen
Startfamilien werden von diesem Setup nicht automatisch ausgeführt.
Jeder CLI-Aufruf hat eine feste Obergrenze von drei Stunden und einen eigenen
STOP-Pfad. Kein automatischer Neustart. Checkpoints enthalten Optimizerzustände
und RNG-Zustand; ein automatischer Resume ist nicht implementiert.

## Benutzung

Aus dem Repositoryroot, vorhandene Python-/MuJoCo-/CUDA-Umgebung verwenden:

```powershell
praxis/.venv/Scripts/python.exe -m pytest experiments/critic/critic_warmstart_20261104/test_setup.py -q -p no:cacheprovider
praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/run.py smoke --output experiments/critic/critic_warmstart_20261104/smoke_NEW
```

Für einen später ausdrücklich gestarteten Hauptversuch eine separate Kopie von
config.json erstellen, darin `training_enabled` auf `true` setzen und dieselbe
Konfiguration unverändert für alle Phasen verwenden. Beispiel mit dem Dateinamen
`active-config.json` (diese Aktivierung wurde beim Aufbau nicht vorgenommen):

```powershell
praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/run.py prepare --execute --config experiments/critic/critic_warmstart_20261104/active-config.json --output experiments/critic/critic_warmstart_20261104/data_001
praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/run.py warmup --execute --config experiments/critic/critic_warmstart_20261104/active-config.json --data experiments/critic/critic_warmstart_20261104/data_001 --output experiments/critic/critic_warmstart_20261104/warm_001
praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/run.py train --execute --config experiments/critic/critic_warmstart_20261104/active-config.json --data experiments/critic/critic_warmstart_20261104/data_001 --warmup experiments/critic/critic_warmstart_20261104/warm_001 --output experiments/critic/critic_warmstart_20261104/run_001
```

Laufordner werden nie überschrieben. `status.json`, `provenance.json`, Daten- und
Checkpointmanifeste dokumentieren den jeweiligen Stand. Daten, Gewichte und
technische Läufe bleiben lokal. Das Frontend erhält nur eine bereinigte
Konfiguration, Protokolltext, Prüfnachweise und deren Hashes.

## Literatur und Abgrenzung

- TD3: https://arxiv.org/abs/1802.09477 — Twin Critics und verzögerte Actorupdates.
- Cal-QL: https://arxiv.org/abs/2303.05479 — motiviert kalibrierte Offline-Initialisierung;
  dessen konservativer Kalibrierungsverlust ist hier nicht implementiert.
- AWAC: https://arxiv.org/abs/2006.09359 — verwandte Offline-/Online-Verbindung,
  verwendet einen anderen, nach Advantage gewichteten Actorloss.

Critic-Wertlernen aus Demonstrationsdaten ist keine direkte Aktionsimitation.
Ein momentaner Konstruktqualitätsscore allein ist kein Q-Critic. Ob der Warmstart
und die vollständige Entfernung des BC-Terms hier helfen, bleibt offen.
