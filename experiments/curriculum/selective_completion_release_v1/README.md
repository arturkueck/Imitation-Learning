# Selektiver Abschluss und Freigabedynamik

Vorabprotokoll, 18.11.2026. Nutzerfreigabe: weitere Ursachenuntersuchung.
**Keine Optimizerupdates, keine neuen Gewichte, kein neues Training.**
Alle Eingriffe betreffen ausschliesslich die zweite Platzierung ausserhalb
des Rueckzugs. Vorhandene Quellen werden nicht veraendert.

## Drei getrennte Fragen

1. Kann eine spaete Abschlusskorrektur bekannte Griffstillstaende beheben,
   ohne rechtzeitig erfolgende gelernte Abschluesse zu ersetzen?
2. Wie wirken Ablageveto und anschliessende Freigabebewegung zusammen?
3. Was unterscheidet eine Regel mit Greiferzustand von einer Regel mit
   zusaetzlichem aktuellem Objektfeedback? Dies ist eine Controllerdiagnose,
   kein Nachweis, dass ein neu trainiertes Modell mit mehr Merkmalen besser wird.

## Auswahl und Umfang vor Ausfuehrung

**Neue Kalibrierung:** 12 nicht vorher zugewiesene Szenenfamilien
2026195000..2026195011, keine Auswahl nach Geometrie oder Erfolg. Jede mit
drei geerbten eingefrorenen Targeted-Kompositionen und acht Armen:
36 Modell-/Szenenpaare, 288 Episoden. Alle bleiben anschliessend geoeffnete
Kalibrierung, getrennt von spaeteren Train-/Validation-/Blindtestfamilien.

**Geoeffnete Griffanker:** alle sechs Kontrollfaelle des letzten Laufs, die
in zweiter Phase 1 endeten, plus alle vier erfolgreichen Kontrollen, die
durch den dortigen pauschalen Griffabschluss verloren gingen. Drei Arme
pro Paar: 30 Episoden. Selektionsgrund und Herkunft explizit speichern.

**Geoeffnete Freigabeanker:** die drei bekannten zweiten Freigabefehler
aus residual_phase_diagnosis_v1 und deren drei urspruenglich zugeordnete
erfolgreiche Kontrollen. Sechs Arme: 36 Episoden. Bekannte Fehler und
Erfolgskontrollen getrennt berichten, nicht zur neuen Kalibrierung addieren.

Insgesamt **354 Episoden in 52 Fallgruppen**. Feste Fallzahl begrenzt
eine Ursachenpruefung; keine Teststaerke fuer eine allgemeine Verbesserung.
Drei wiederverwendete Parents sind keine neuen Trainingswiederholungen.
Keine Faelle nachschieben, ausschliessen oder bei Fehlschlag ersetzen.

Vorher Konfliktpruefung der Szenenkennungen gegen vorhandene Experiment-
und Curriculumplaene. Initialzustandshashes gegen Nachtlauf und letzten
Kalibrierungslauf pruefen. Neue Familien ueber Parents gepaart. Kein Anspruch,
unprotokollierte historische Starts vollstaendig ausschliessen zu koennen.

## Griff: Geometrie gegen reinen Timeout

- control: bestehende BC-Aktion und Abschlussregel.
- grasp_timeout: Wenn BC in zweiter Phase 1 nach 100 bereits verstrichenen
  Phasenaktionen noch nicht abschliesst, nach der aktuellen BC-Aktion fortschalten.
- grasp_ready: Derselbe spaete Eingriff nur nach 20 aufeinanderfolgenden
  Bereitschaftsframes: EEF-Abstand zum gespeicherten Phasenanker plus
  (0,0,3 mm) < 6 mm. Vorhandene BC-Abschluesse immer respektieren.

100 Schritte stammen vom vorhandenen Cap der Eingabeuhr; 20 Frames aus
der bisherigen Definition anhaltender Bereitschaft. Keine Anpassung an neue
Ausgaenge. Die Bereitschaft wird ausschliesslich aus den vorhandenen zehn
Policymerkmalen berechnet. Eine externe Hysterese fuegt einen Zaehler hinzu;
das ist keine unveraenderte Feedforward-Klassifikation und kein neuer Sensor.
Die aktuellen Aktionen bleiben BC. In anderen Phasen greift keine dieser
Regeln ein. Nicht bereit am Timeout wird im Timeout-Arm bewusst als Kontrast
zugelassen; Fehlschlaege gehoeren zum Ergebnis.

## Freigabe: 2 x 3 faktorieller Vergleich

| Ablageveto | Bestehende Freigabe | EEF halten und oeffnen | Objekt-XY-Feedback und oeffnen |
|---|---|---|---|
| aus | control | release_hold | release_feedback |
| an | guarded_bc | guarded_hold | guarded_feedback |

Das Veto ist exakt die vorher gepruefte Phase-5-Regel, einschliesslich
Geometrie, Kontakt, Geschwindigkeiten, drei stabilen Frames und Mindestdauer.
Es erzeugt keinen Abschluss, wenn der BC-Klassifikator keinen verlangt.

Beide neuen Phase-6-Regeln oeffnen mit -1, halten die Rotation fest und
verwenden denselben begrenzten P-Regler (Gain 0,6, Skalierung 0,05 m):

- EEF halten: EEF an der beim Freigabeeintritt gemessenen Position halten.
- Objektfeedback: In den ersten 20 Phase-6-Aktionen horizontale Bewegung
  aus aktueller Differenz Zielwuerfel minus Quellwuerfel; EEF-Hoehe beim
  Freigabeeintritt halten. Danach aktuelle EEF-XY-Position einmal festhalten
  und bis zum Ende halten; die Hoehenreferenz bleibt diejenige beim Eintritt.
  Der Zeitraum folgt der vorhandenen
  Experten-Freigabedauer und wird nicht nach Ergebnis angepasst.

Objektfeedback nutzt privilegierte Simulatorpositionen. Die Algorithmen
unterscheiden sich in ihrer Feedbackreferenz; ein Vorteil waere ein Befund
fuer diese Controllerintervention, keine reine Featureablation eines sonst
identischen trainierten Modells. Alle Original-BC-Vorhersagen werden weiter
gemessen. Originalsequencer, Rueckzugsregeln, die finale Clock-Korrektur,
0,8-Schwelle, 1000 Frames und 50 strenge Erfolgsframes bleiben gleich.
Insbesondere wird kein gelernter Phase-6-Abschluss vorgetaeuscht.

## Gueltigkeitspruefung und Endpunkte

- Alle geoeffneten Kontrollarme muessen ihre archivierten Resultate exakt
  reproduzieren. Neue Kontrollen sind keine nachtraeglich gewaehlten Checkpoints.
- Identischer Anfangszustand und Verlauf bis zum ersten tatsaechlichen
  Eingriff; dessen Historien-/Zustandshash gegen die Kontrolle am selben
  Frame vergleichen. Ohne tatsaechlichen Eingriff identische Gesamttrajektorie.
- Zusaetzlich gleicher Phase-6-Eingang zwischen Freigaberegeln innerhalb
  desselben Veto-Arms. Vorherige erste Platzierung unveraendert.
- Primaer diagnostisch: vollstaendige Aufgabenerfolge, gepaarte Gewinne und
  Verluste, jeden Parent und Panel/Selektionsgrund separat, voller Nenner.
- Faktorielle Effekte: Bewegungsregel bei gleichem Veto, Veto bei gleicher
  Bewegungsregel, deskriptive Differenz der Unterschiede. Nicht erreichte
  Kontexte bleiben im Nenner; Exposition getrennt ausweisen.
- Sekundaer: lokale Phasenfortschritte, Zeitpunkt und Bereitschaft spaeter
  Griffabschluesse, Freigabeeintritt, XY-Drift danach, Kontakt, Dynamik,
  gueltige Frames und Erfolgskontrollverluste.
- Null Updates und unveraenderte Parameter-/Quellhashes nachweisen.

## Beobachtungspruefung ohne Training

Auf den neuen **Kontrolltrajektorien**, getrennt je Parent, Platzierung und
Phase 5/6: hoechstens 20 gleichmaessig verteilte Frames pro Phasenkontext.
Nur verschiedene Anfangsfamilien vergleichen. Exakte Gleichheit der zehn
tatsaechlichen Policymerkmale und zusaetzlich vorab definierte Naehe:
EEF-Komponenten <= 1 mm, Quaternionkomponenten <= 0,01, Greifergelenke
<= 0,5 mm, Eingabeuhr <= ein Schritt. Die Einheiten werden aus dem
normalisierten tatsaechlichen Eingabevektor rekonstruiert.

Zaehlen, ob sich bei aehnlichen Eingaben die aktuelle XY-Abweichung um
mindestens 5 mm unterscheidet und die feste Ablagebereitschaft verschieden
ist. Keine Schwellenoptimierung. Naehe ist keine exakte Gleichheit und
beweist keine informationstheoretische Unloesbarkeit. Auch verschiedene
Ausgaenge beweisen allein keinen Nutzen neuer Merkmale. Objektfeedback-
Intervention und diese deskriptive Beobachtungspruefung getrennt berichten.

Anfangsmerkmale: EEF-Quellabstaende und alle drei XY-Abstaende zwischen
Wuerfelmitten in Metern, keine als validiert ausgegebene Schwierigkeitsskala.
Die Seednummer ist keine Schwierigkeit. Keine Testdaten zur Kalibrierung.

## Begrenzung und technische Pruefung

Maximal 45 Minuten inklusive Auslaufreserve, kein automatischer Neustart.
Eine STOP-Datei im eigenen Laufverzeichnis beendet den Worker. Quellen und
Checkpoints werden nicht ueberschrieben, PC wird nicht heruntergefahren.

Technischer Smoke: die drei geoeffneten Griffstillstaende der Szene
2026193009 (je drei Arme) und Parent-3-Freigabefehler plus zugeordnete
Erfolgskontrolle (je sechs Arme): **21 Episoden**, maximal zehn Minuten.
Technische Daten werden nicht als zusaetzliche Hauptreplikation gezaehlt.

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/selective_completion_release_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/selective_completion_release_v1/pipeline.py prepare --smoke --output praxis/results/curriculum/selective_completion_release_v1/smoke_001
praxis/.venv/Scripts/python.exe experiments/curriculum/selective_completion_release_v1/pipeline.py run --output praxis/results/curriculum/selective_completion_release_v1/smoke_001
praxis/.venv/Scripts/python.exe experiments/curriculum/selective_completion_release_v1/pipeline.py prepare --output praxis/results/curriculum/selective_completion_release_v1/run_001
praxis/.venv/Scripts/python.exe experiments/curriculum/selective_completion_release_v1/pipeline.py run --output praxis/results/curriculum/selective_completion_release_v1/run_001
```
