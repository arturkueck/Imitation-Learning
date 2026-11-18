<!-- current-bc-status:start -->
> Stand 12.11.2026: **Abgeschlossen**. Feste 30k-Abschlussfunktion gegen gewöhnliche Fortsetzung; kein stabiler Vorteil. [Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.
<!-- current-bc-status:end -->

# Nachtlauf: Abschlussentscheidung und Aktionslernen getrennt prüfen

Vorbereitet am 11.11.2026; dieser Ordner startet standardmäßig kein Training.
Fragestellung: Tragen veränderte Abschlussentscheidungen zum unterschiedlichen
Online-Erfolg nach weiterem BC-Training bei? Die vorhandenen Validierungsdaten
zeigen bei **allen sechs Modellen** geringeren Aktions-MSE und Abschluss-BCE
bei 60k als bei 30k. Eine allgemeine Verschlechterung des Klassifikators ist
dadurch nicht belegt. Die folgende Intervention ist ein gezielter Hypothesentest.

## Ein gemeinsamer Lauf, maximal zehn Stunden

1. **Vorhandene Diagnose:** `prior_diagnosis.json` fasst Validierungs-MSE,
   BCE, gesamten Loss sowie TP/FP/FN bei 30k, 40k, 50k und 60k zusammen.
   Der Abschlussfehler wird auf Demonstrationszuständen gemessen, nicht als
   tatsächlicher Zeitpunkt eines Phasenwechsels im Rollout.
2. **Austauschtest ohne Training:** Für jedes der sechs Ausgangsmodelle alle
   vier Kombinationen aus Aktionsmodell 30k/60k und Abschlussfunktion 30k/60k
   auf den bestehenden 20 Dreierturm-Entwicklungsstarts auswerten. Das sind
   24 Policies und 480 Entwicklungsepisoden. Die Startzustandshashes müssen
   übereinstimmen. Insbesondere 60k-Aktionen mit 30k-Abschluss zeigen, ob ein
   bloßer Austausch der Abschlussfunktion bei unveränderten Aktionsgewichten
   das Ergebnis verändert. Spätere Zustände dürfen sich infolge des Eingriffs
   unterscheiden; eine exklusive Fehlphase ist damit noch nicht identifiziert.
3. **Historische Trajektorien:** Je Modell ein Beispiel aus vier Gruppen:
   verbessert, verschlechtert, beide erfolglos, beide erfolgreich. Auswahl ist
   reproduzierbar der kleinste Szenenseed je vorhandener Gruppe, maximal 24
   Paare bzw. 48 Rollouts. Alte 30k- und 60k-Modelle werden wiederholt und
   Anfangszustand sowie Erfolg müssen mit den gespeicherten Ergebnissen
   übereinstimmen. Bei Abweichung bleiben die Traces zur Diagnose erhalten und
   der Lauf stoppt vor dem Training. NPZ-Traces speichern Greifer- und
   Würfelpositionen, Aktionen, Phase, Abschlusswahrscheinlichkeit, Grasp,
   Kontakte/Stapelkriterien und Koordinatorereignisse. Das sind bewusst
   ausgewählte Beispiele, keine Schätzung von Fehlerhäufigkeiten. Historische
   Bestätigungsszenen sind hierfür ausdrücklich Diagnosematerial, keine neuen
   unberührten Endtests. Es werden keine neuen Trainingslabels erzeugt.
4. **Kontrollierter Trainingsvergleich:** Alle sechs 30k-Eltern mit ihren
   AdamW-Zuständen um 30k Updates auf 60k weitertrainieren. Die Abschlussfunktion
   bleibt exakt auf dem 30k-Stand. Die bisherigen gewöhnlich weitertrainierten
   60k-Modelle werden als Kontrolle wiederverwendet. Ihre gespeicherten
   Batchpläne werden vorab exakt gegen den neu erzeugten Plan geprüft.
   Keine Kontrolle muss erneut trainiert werden. Beide Bedingungen haben
   dieselben Ausgangsgewichte, Optimizerzustände, Daten, Batchreihenfolgen,
   Updates und Lernraten. Die sechs Eltern umfassen die bisherigen zwei
   Trainingsvorgeschichten mit je drei Seeds. Während dieser Fortsetzung
   erfolgt kein neues X/XY-Curriculum.
5. **Neue Bestätigung:** Feste 60k-Endpunkte, alle zwölf Kontroll- und
   Interventionsmodelle vor dem ersten Ergebnis einfrieren. Pro Modell 100
   neue gepaarte Starts für Zwei- und Dreierturm, Namespace
   2026117000–2026117099. Alte Endtests und die Austauschtests wählen weder
   Modelle noch Hyperparameter aus. Hauptmaß ist der vollständige stabile
   Dreierturm nach den unveränderten physikalischen Kriterien.

Training, Austauschtests, Wiederholungen und neue Bestätigung teilen sich ein
Maximum von zehn Stunden ab Supervisorstart, davon zwei Minuten Reserve für das
kontrollierte Beenden. Die Rechenphasen enden spätestens nach 9 Stunden 58 Minuten;
der Supervisor beendet einen verbleibenden Worker am Zehn-Stunden-Limit. Keine automatischen Neustarts. Ein unvollständiger Lauf
liefert Teilresultate und darf nicht als vollständige Bestätigung gelten.

## Was genau eingefroren wird

Die Policy hat sieben Netze für die Manipulationsphasen. In jedem Netz teilen
sich Aktionsausgaben und Abschluss-Logit die versteckten Schichten. Nur die
letzte Zeile des Abschlussausgangs zu sperren würde die Abschlussfunktion
deshalb **nicht** konstant halten.

`FixedCompletion` verwendet eine unveränderliche Kopie des gesamten 30k-Netzes
für die Abschluss-Logits. Das weitertrainierte Netz liefert die Aktionen.
Die BCE des eingefrorenen Abschlusses wird weiter als Messgröße erfasst, liefert
aber keinen Gradienten zum Aktionsmodell. Der Aktions-MSE wird unverändert
optimiert; ursprüngliche AdamW-Momente bleiben erhalten. Der Optimizer enthält
die ursprünglichen Aktionsmodellparameter, die eingefrorene Referenz nicht.

Damit werden Abschlussverhalten **und** der Einfluss des Abschlussgradienten
auf die gemeinsamen Repräsentationen verändert. Ein Vorteil allein würde diese
beiden Mechanismen nicht auseinanderhalten. Der vorgeschaltete Austauschtest
prüft ergänzend die reine Inferenzintervention bei gleichen Aktionsgewichten.
Keine Änderung von Trainingsdaten, Seeds, Architektur des ursprünglichen
Aktionsnetzes, Losskoeffizienten, Lernrate, Greiferschwelle oder Koordinator.
Zusätzlich wird eine feste Referenzkopie zur Inferenz benötigt.

## Start und Betrieb

Der vorbereitete Ordner heißt `ready_001`. Aus dem Projektstamm:

```powershell
& '.\experiments\curriculum\axis_bc_completion_10h_20261111\Start-NightRun.ps1'
```

Der Starter prüft Hashes und Startsperren. Der Supervisor läuft versteckt,
hält Windows wach und gibt die Schlafsperre danach frei. Bestehende Modelle,
Ergebnisse und Quellstände werden nicht überschrieben.

```powershell
& '.\praxis\.venv\Scripts\python.exe' '.\experiments\curriculum\axis_bc_completion_10h_20261111\night.py' status --output '.\experiments\curriculum\axis_bc_completion_10h_20261111\ready_001'
```

Der Status verwendet das vorhandene inkrementelle Monitoring ohne ML-Imports.
Prozesszugriff muss im selben Windows-Kontext wie beim Hintergrundstart erfolgen;
unbekannter Prozesszugriff ist kein behaupteter Trainingsabbruch. `STOP` im
Laufordner beendet die Arbeit bei der nächsten Update-Runde oder dem nächsten
Simulationsframe. Keine Fortsetzung eines bereits gestarteten Ordners.

## Artefakte

- `prior_diagnosis.json`: bereits vorhandene Loss- und Abschlussdiagnose.
- `diagnosis/crossover_summary.json`: vier Kombinationen je Modellvorgeschichte.
- `diagnosis/replays/report.json` und NPZ: ausgewählte gepaarte Verlaufsmessungen.
- Je Modell `offline_u*.json`: Aktions-MSE, Abschlussdiagnose, Gesamtvalidierungsloss.
- `confirmation/` und `result_summary.json`: neue gepaarte Bestätigung.
- `provenance.json`, `parents.json`, `controls.json`, Samplepläne, Checkpoints:
  eingefrorene Quellen, Eingänge und Zustände. Checkpoints speichern Aktionsmodell
  und Abschlussreferenz getrennt und erhalten deren Optimizerzustände.

Unterschiede pro Trainingsseed und Szenenpaar berichten. 100 Testszenen sind
keine 100 unabhängigen Trainingsreplikate. Die Nacht enthält keinen adaptiven
Hyperparametervergleich und keinen Critic. Eine vollständige Videopipeline wird
nicht eingeführt; die Trajektorien bilden die gezielte Fehlerdiagnose ab.
