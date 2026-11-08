# Stabilität vor einem neuen Actor-Critic-Test

Autorisiert am 05.11.2026: Stabilitätsprüfung übernehmen und auf einen neuen
Testlauf hinarbeiten. Bestehende Nachtlaufartefakte bleiben unverändert.

## Festgelegter Entwicklungsversuch

`stability.py` vergleicht den bisherigen warmen Arm C mit einer neuen,
explizit geänderten Variante. Die neue Variante berechnet

`a = clip(a_parent + 0.02 * tanh((a_raw - a_parent) / 0.02), -1, 1)`.

Der Parent bleibt eingefroren. Das begrenzt jede der vier Aktionskomponenten
auf eine Abweichung von höchstens 0.02 bei beliebigen Actoreingaben. Es ist
keine Kollisions- oder Erfolgsgarantie. Die eingefrorene Abschlussentscheidung
wird wie bisher separat verwendet. Der zusätzliche Parent ist eine direkte
Bindung an IL-Vorwissen; der Vergleich isoliert deshalb nicht mehr ausschließlich
Critic-Warmstart. Die bekannte Idee einer begrenzten Policyänderung wird nicht
als neue wissenschaftliche Methode ausgegeben.

Beide Arme beginnen bei denselben Originalactors und vorgewärmten Critics,
nicht bei den kollabierten Actors. Sie erhalten identische Batches aus 50 %
ursprünglichen Trainingsframes und 50 % bereits vorhandenen Onlineepisoden der
ersten Nachtlaufrunde. Dieser Replay bleibt während der Prüfung fest. BC 0.01,
Optimizer, LR, Targetglättung und übrige Lernparameter bleiben gleich.

Vorab festgelegte Kontrollen nach 10/50/100/500 Criticupdates, also
5/25/50/250 Actorupdates. Sechs neue Entwicklungsstarts 2026112000–2026112005
je Parentseed 1/2/3, gepaart mit unveränderten Parents. Aktionen werden außerdem
auf bis zu 64 Trainingsframes pro Phase geprüft. Validierung und reservierte
Endtests werden dafür nicht optimiert oder neu ausgewertet.

Abbruch je Arm/Parent bei nicht endlichen Werten, Aktions-MSE über 0.01,
maximaler Aktionsabweichung über 0.1 (Kontrolle) bzw. 0.02 (neue Variante),
oder mehr als einem verlorenen Parent-Erfolg auf den sechs Startfamilien.
Die neue Variante besteht insgesamt nur, wenn sie alle vier Updateblöcke
für alle drei Parents absolviert und je Kontrollpunkt höchstens einen der
18 Parent-Erfolge verliert. Keine Auswahl eines günstigen Zwischencheckpoints.
Die 18 Kombinationen enthalten nur sechs geteilte Startfamilien.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/stability.py --output experiments/critic_warmstart_20261104/stability_NEW
```

Protokoll und Eingangshashes werden vor den Rollouts geschrieben. `STOP` im
Ausgabeordner beendet die Prüfung kooperativ; Budget höchstens eine Stunde,
keine automatischen Wiederholungen oder Resume. Quellkopien, Metriken und
Checkpoints bleiben im eigenen Ordner.

`stability_001` scheiterte vor Trainingsupdates an einer Importnamenskollision:
der historische Controller importiert sein eigenes Modul `run`, während die
neue Prüfung den heutigen Runner zunächst ebenfalls als `run` importierte.
Der neue Runner wird jetzt unter einem eindeutigen Modulnamen geladen.
Die behobene Integration wird separat unter `stability_002` geprüft; keine
Daten oder Resultate aus dem fehlgeschlagenen Start werden als Befund genutzt.
Der ursprüngliche Nachtlauf lief als CLI und war von diesem neuen Importfehler
nicht betroffen.

## Nächster Onlinepilot

`new_test.py prepare` legt nur dann einen neuen Pilotordner an, wenn die
Stabilitätsprüfung vollständig bestanden ist. Er startet kein Training.
Der Pilot beginnt erneut bei den unveränderten Originalactors und warmen
Critics, nicht bei den auf Entwicklungsstarts geprüften Stabilitätscheckpoints.

- Drei Parentseeds, vier Runden mit fünf frischen eigenen Episoden und
  500 Criticupdates je Runde: insgesamt 60 Onlineepisoden, 6000 Criticupdates
  und 3000 Actorupdates.
- Neue Onlinefamilien 2026112200–2026112219; neue Entwicklungsfamilien
  2026112100–2026112119. Die Stabilitätsstarts werden nicht wiederverwendet.
- Entwicklungsauswertung je Parent auf 20 gepaarten Starts bei Runde 0/1/2/4:
  insgesamt 240 Auswertungsrollouts, 300 Episoden einschließlich Onlineerfahrung.
- Vorhandene Originaldaten zu 50 %, ausschließlich private neue
  Onlineerfahrung zu 50 %. Keine nachträgliche Erfolgsauswahl der Episoden.
- Das ursprüngliche XYZ-Explorationsrauschen wird ebenfalls auf den Bereich
  Parent ±0.02 projiziert. Die tatsächlichen Aktionen behalten dadurch die Grenze.
  Dies verändert die Explorationsverteilung gegenüber dem ersten Nachtlauf.
- Die Targetaktionsglättung bleibt wie in der Stabilitätsprüfung. Deren
  verrauschte Critic-Targetaktionen sind nicht durch die Grenze für tatsächlich
  ausgeführte Aktionen abgesichert. Das bleibt eine bekannte methodische Grenze.
- Nach 50 Criticupdates jeweils Driftprüfung und vollständige Actor-/RL-/BC-
  Metriken. Nach Entwicklungsauswertungen Abbruch bei mehr als zwei verlorenen
  Parent-Erfolgen je Seed oder mehr als drei insgesamt. Neue Erfolge verrechnen
  verlorene Erfolge nicht weg. Alle drei Parentbaselines müssen mindestens
  zehn der zwanzig Starts lösen, sonst wird nicht trainiert.
- Fester finaler Checkpoint Runde 4; keine Auswahl anhand der Entwicklung.
  Ein Abbruch wird als Teilversuch berichtet. Kein reservierter Endtest.
- Eigenes Stundenbudget, STOP-Datei, exklusiver Startmarker, kein automatischer
  Neustart. Der CLI-Pilot läuft im Vordergrund; es wird kein neuer Zeitplan oder
  abgekoppelter Nachtlauf eingerichtet.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/new_test.py prepare
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/new_test.py run --execute
```

Ein technischer Miniworkflow mit vier Updates und drei Rollouts kann nach
bestandener Stabilitätsprüfung mit `new_test.py smoke --output .../pilot_smoke_NEW`
ausgeführt werden. Er ist ausdrücklich kein wissenschaftlicher Pilot.

Ein bestandenes Stabilitätsgate belegt Leistungserhalt nur auf diesen kleinen
Entwicklungspanels. Wissenschaftliche Verbesserung, breite Übertragbarkeit und
Neuheit bleiben nachzuweisen. Der nächste Pilot dient zunächst der Frage, ob
der Leistungserhalt auch mit frischen eigenen Onlineerfahrungen bestehen bleibt.
