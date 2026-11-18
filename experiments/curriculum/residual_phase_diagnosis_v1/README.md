# Restfehler: Bewegung und Phasenabschluss getrennt prüfen

Begrenzte Fortsetzung des vom Nutzer akzeptierten Diagnoseplans vom 18.11.2026.
**Keine Optimizerupdates, kein neues Training, keine neuen Blindtestszenen.**
Die drei bestehenden Modelllinien werden ausschließlich eingefroren verwendet.
Dies ersetzt keine später erforderlichen unabhängigen Trainingswiederholungen.

## Frage und Auswahl vor Ausführung

Der abgeschlossene Haupttest hat für Targeted 91 erfolglose Modell-/Szenenpaare:
43 vor der korrigierten Phase, sieben zwischen deren Beginn und zweitem Lift,
41 nach zweitem Lift mit erkanntem Griff. Endphasen sind Hinweise, keine Ursachen.

Aus ausschließlich bereits geöffneten Targeted-Haupttestfällen wird je
nichtleerer Parent/Platzierung/Endphase-Gruppe der kleinste erfolglose Szenenseed
ausgewählt. Für jede Gruppe kommt der kleinste noch nicht verwendete erfolgreiche
Seed desselben Parents hinzu. Erfolgreiche Kontrollen sind voneinander und von
allen ausgewählten Fehlerseeds verschieden. Sie sind nicht geometrisch gematcht;
der eigentliche kausale Vergleich liegt zwischen den Armen derselben Szene.
Keine Auswahl anhand der erst jetzt entstehenden Eingriffsergebnisse.

Es gibt 17 nichtleere Fehlergruppen in Phase 1/4/6. Daraus entstehen 34
Fallgruppen, jeweils Fehler plus erfolgreicher Vergleichsfall, mit insgesamt
**112 Episoden**. Mehrfach verwendete Szenen über Parents sind keine unabhängigen
Replikate. Die Gruppen sind Ablauf-/Fehlerklassen, keine validierte Skala von
Szenenschwierigkeit. Es werden keine neuen Trainingsfamilien oder Splits angelegt.

## Interventionen

| Zielphase | control | action | completion | both |
|---|---|---|---|---|
| 1: Absenken zum Griff | unverändert | Expertenbewegung, BC-Abschluss | BC-Bewegung, Expertenabschluss | beides Experte |
| 4: Transport | unverändert | Expertenbewegung, BC-Abschluss | BC-Bewegung, Expertenabschluss | beides Experte |
| 6: Freigeben/Halten | unverändert | Expertenbewegung bei unveränderter physikalischer Stabilitätsprüfung | nicht anwendbar | nicht anwendbar |

Ein Eingriff gilt nur in der gewählten Platzierung und Phase außerhalb des
Rückzugs. Der vollständige Ablauf beginnt im ursprünglichen Anfangszustand;
keine Teleportation und keine erzwungenen Kontakte. Alle anderen Phasen,
Sequencer, Retreat-Guard, 0,8-Abschlussschwelle, finale Clock-Korrektur und
strenge Erfolgskriterien bleiben wie im Nachtlauf. Danach läuft wieder dieselbe
eingefrorene Targeted-Komposition.

Der Experte ist der unveränderte vorhandene StackExpert, am tatsächlichen
Phaseneintritt initialisiert. Für den Action-only-Arm wird sein Ziel derselben
Phase festgehalten; nach eigener Fertigmeldung darf er nicht versehentlich
Aktionen der nächsten Phase ausführen. BC entscheidet weiter über den Übergang.
Completion-only verändert keine aktuelle Bewegung, aber die Übergangsentscheidung;
spätere Bewegungen können sich dadurch selbstverständlich ändern.

**Phase 6 hat keinen verwendeten gelernten Abschluss.** Ein Completion-only-
Arm wäre dort wirkungslos und wird daher nicht als Ursachenprüfung ausgegeben.
Die physikalischen 10 gültigen Frames vor erstem Rückzug beziehungsweise 50
Frames für vollständigen Dreierturm bleiben unverändert; der Experte ersetzt
hier ausschließlich die Bewegung einschließlich Greiferkommando.

## Gültigkeitsprüfungen und Endpunkte

- Kontrollarme müssen die archivierten Einzelresultate reproduzieren:
  Anfangszustand, Erfolg, Framezahl, Endphase/-platzierung, Rückzugs-Timeout,
  zweiter Lift, aktive Korrekturframes und erster Turm.
- Bis zum Eingriff müssen vollständige Aktions-/Simulationshistorie und
  Zustand am Zieleintritt zwischen sämtlichen Armen bytegleich sein.
- Ein nicht erreichter Zielkontext bleibt im Nenner. Ohne Exposition darf der
  Arm nicht von der Kontrolle abweichen. Keine fehlgeschlagenen Eingriffe entfernen.
- Primär diagnostisch: Gewinne und Verluste im vollständigen Aufgabenerfolg
  gegenüber der eigenen Kontrolle, einzeln nach Phase, Platzierung, Parent und
  Fehler-/Erfolgskontrolle. Keine neue allgemeine Erfolgsquote aus der Auswahl.
- Sekundär: erreichte Phase, Eingriffsframes, BC-/Expert-Abschlussabweichungen,
  Griff am zweiten Lift, Kontaktsignale, Geometrie, Geschwindigkeiten, Zeitmerkmale
  und Phasenereignisse. Traces und vollständige Fallausgänge bleiben lokal.
- Alle Modellparameter sind eingefroren; Parameter- und Datei-Hashes werden
  geprüft. Kein Checkpoint wird ersetzt oder nach Ergebnis ausgewählt.

Action-only-Nutzen deutet auf einen wirksamen Bewegungsanteil, Completion-only-
Nutzen auf einen wirksamen Übergangsanteil im jeweiligen Kontext hin. Nur
gemeinsamer Nutzen lässt Wechselwirkungen zu. Ein wirkungsloser Experteneingriff
beweist weder irreparablen Zustand noch eine funktionierende Phase: Zielregel,
Vorgeschichte und weitere Phasen begrenzen seine Aussage.

## Begrenzung und technische Prüfung

Harte Obergrenze 30 Minuten inklusive Auslaufreserve; keine automatischen
Neustarts oder zusätzlichen Fälle. Kein PC-Shutdown. Technischer Smoke:
drei vorab genannte Fehlergruppen, alle drei Parents, beide Platzierungen
und alle drei Phasen; Fehler- plus Erfolgskontrollen, **20 Episoden**, höchstens
zehn Minuten. Technische Ergebnisse zählen nicht zur vollständigen Diagnose.

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/residual_phase_diagnosis_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/residual_phase_diagnosis_v1/pipeline.py prepare --output praxis/results/curriculum/residual_phase_diagnosis_v1/run_001
praxis/.venv/Scripts/python.exe experiments/curriculum/residual_phase_diagnosis_v1/pipeline.py run --output praxis/results/curriculum/residual_phase_diagnosis_v1/run_001
```

Eine STOP-Datei im eigenen Laufordner beendet die Diagnose. Unvollständige
Gruppen bleiben als solche erhalten, keine Verkürzung des Plans nach Einsicht.
Keine neuen Gewichte, Trainingslabels zur automatischen Übernahme oder Freigabe
eines nachfolgenden Trainings. Schwierigkeitsskala und künftiger Hauptvergleich
benötigen eigene Vorbereitung gemäß AGENTS.md.
