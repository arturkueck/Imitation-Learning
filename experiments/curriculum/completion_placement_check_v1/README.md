# Abschlussentscheidungen und Ablage vor der Freigabe

Vorabprotokoll vom 18.11.2026. Autorisiert ist eine begrenzte Diagnose mit
eingefrorenen Modellen, **kein Training**. Urspruengliche Quellen bleiben
unveraendert. Optimizerupdates: null. Keine automatische Wiederholung.

## Fragen und feste Auswahl

1. Bleibt der gelernte Abschluss beim Absenken zum Griff trotz erreichter
   Expertenbedingung aus? Hilft ein isolierter Austausch des Abschlusses?
2. Erfolgt der Eintritt in die Freigabe ohne passende Ablagegeometrie,
   Kontakt oder Beruhigung? Sind Bewegung oder Abschluss der vorherigen
   Phase 5 wirksame Ursachen? Schadet ein zusaetzliches Veto guten Ablaeufen?

18 vorher nicht zugewiesene Anfangsszenen 2026193000..2026193017, jeweils mit
den drei vorhandenen sammlungsfremden Targeted-Kompositionen. Keine Auswahl
anhand von Erfolgen oder Geometrie. Das sind 18 Familien und drei geerbte
Initialisierungen, nicht 54 unabhaengige Trainingswiederholungen. Alle Familien
sind ab diesem Lauf geoeffnete Kalibrierung und bleiben von spaeteren
Train-/Validierungs-/Blindtestpanels getrennt. Seedkennung ist keine Schwierigkeit.

Zusaetzlich die sechs bereits untersuchten erfolglosen Freigabefaelle aus
residual_phase_diagnosis_v1: derselbe kleinste Fehlerseed je Parent/Platzierung,
aber Eingriff jetzt ausschliesslich in der **vorherigen Phase 5** derselben
Platzierung. Diese bekannten Faelle separat berichten, nicht zur frischen
Kalibrierung hinzurechnen. Kontrollarme muessen ihre Archivresultate exakt
reproduzieren. Keine nachtraegliche Fallauswahl.

Vor Ausfuehrung: Konfliktpruefung neuer Kennungen gegen vorhandene Konfigurationen
und Plaene im Curriculum-Bereich und Experiments. Initialzustandshashes gegen
alle archivierten Nachtstartzustaende pruefen. Gleiche neue Szene ueber Parents
muss denselben Initialzustand haben. Keine Behauptung ueber nicht protokollierte
historische Starts. Technischer Smoke hat eigene Szene 2026194000 und einen
bekannten Phase-5-Fall; seine Daten gehen nicht in die Hauptauswertung ein.

## Sechs Arme, keine neuen Gewichte

| Arm | Eingriff ausserhalb des Rueckzugs |
|---|---|
| control | Unveraendertes eingefrorenes Modell |
| grasp_completion | Nur Phase 1: vorhandene Experten-Abschlussregel, BC-Bewegung |
| place_action | Nur Phase 5: Expertenbewegung, BC-Abschluss |
| place_completion | Nur Phase 5: Experten-Abschlussregel, BC-Bewegung |
| place_both | Nur Phase 5: beides vom vorhandenen Experten |
| place_guard | Nur Phase 5: BC-Abschluss benoetigt zusaetzlich definierte Ablagebereitschaft |

In den neuen Familien gelten Eingriffe fuer beide Platzierungen. Bekannte
Freigabefaelle erhalten nur die fuenf control/place-Arme, nur in ihrer
betroffenen Platzierung. Vor dem ersten moeglichen Eingriff muessen Zustand
und gesamte Historie zwischen den Armen identisch sein. Nicht erreichte
Kontexte bleiben im Nenner und muessen unveraenderte Trajektorien haben.

Der vorhandene StackExpert wird pro Eintritt in Phase 1/5 am wirklichen
Zustand initialisiert; sein Phasenziel bleibt nach Fertigmeldung festgehalten.
Es ist eine Vergleichsregel, kein unfehlbarer Oracle. Completion-only ersetzt
die aktuelle Aktion nicht. Seine spaeteren Aktionen aendern sich durch den
Phasenwechsel. Kombinationen koennen Wechselwirkungen haben.

Das Guard ist ein **Machbarkeitsversuch**, keine validierte Sicherheitsregel:
XY <= 9 mm, Hoehendifferenz 40 +/- 8 mm, Wuerfelkontakt, Quellwuerfelgeschwindigkeit
<= 0,03 m/s und <= 0,3 rad/s, gueltiger unterer Turm; alles in drei
aufeinanderfolgenden Vor-Aktions-Zustaenden, mindestens fuenf Phase-5-Aktionen.
Geometrie-/Geschwindigkeitsgrenzen stammen aus dem bestehenden Erfolgskriterium;
sie werden nicht an neuen Ergebnissen angepasst. Beim noch gehaltenen
Quellwuerfel wird **nicht** Kontaktfreiheit zum Greifer verlangt. Das Veto kann
Stillstand verstaerken, wenn die unveraenderte Bewegung die Bedingung verfehlt.
Es erzeugt keinen Abschluss, wenn der BC-Klassifikator unter 0,8 bleibt.

Alle anderen Phasen, 0,8-Schwelle, Clock-Korrektur, Retreat-Guard, 1000-Frame-
Horizont sowie physikalische 10-Frame-Zwischen-/50-Frame-Gesamterfolgskriterien
bleiben unveraendert. Phase 6 hat keinen verwendeten gelernten Abschluss.

## Endpunkte, Merkmale und Grenzen

- Primaer diagnostisch: gepaarte Gewinne und Verluste vollstaendiger Aufgaben,
  jeden Arm, Parent und Panel getrennt. Keine Fallentfernung, kein Nachschieben.
- Sekundaer: Phase-1-Expertenbereitschaft ohne Fortschritt; Phase-5-Austritt
  mit/ohne vorab definierte Bereitschaft, Kontakt, Geometrie, Geschwindigkeiten;
  erreichte Phasen und Guard-Blockierungen. Eintritt und Austritt getrennt.
- Feste Anfangsmerkmale in Metern: EEF-Abstand zu beiden Quellwuerfeln,
  zwei XY-Transportstrecken, kleinster XY-Mittenabstand der Wuerfel. Speichern
  fuer eine spaetere Schwierigkeitseichung; noch keine validierte Skala und
  keine nachtraegliche Umbenennung guenstiger Szenen in leicht/schwer.
- Null Optimizerupdates, Parameterhashes vor/nachher, unveraenderte Quellen.
  Neue Gewichte, Trainingslabels oder eine automatische Uebernahme des Guards
  sind kein Ergebnis dieses Auftrags.

Festes Budget: 54 neue Modell-/Szenenpaare mit sechs Armen plus sechs bekannte
Paare mit fuenf Armen = **354 Episoden**. Maximal 45 Minuten mit Auslaufreserve,
kein automatischer Neustart. Auswahlumfang begrenzt eine Ursachenpruefung;
kein Powernachweis fuer eine allgemeine Erfolgssteigerung. Drei vorhandene
Parents sind keine Ausnahmegenehmigung fuer ein neues Drei-Seed-Training.

Technischer Smoke: eine getrennte Szene mit allen drei Parents/sechs Armen,
plus bekannter zweiter Freigabefall Parent 3/2026189042 mit fuenf Armen:
23 Episoden, maximal zehn Minuten. Nur technische Pruefung. Eine STOP-Datei
im jeweiligen Laufordner beendet den eigenen Worker.

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/completion_placement_check_v1 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/completion_placement_check_v1/pipeline.py prepare --smoke --output praxis/results/curriculum/completion_placement_check_v1/smoke_001
praxis/.venv/Scripts/python.exe experiments/curriculum/completion_placement_check_v1/pipeline.py run --output praxis/results/curriculum/completion_placement_check_v1/smoke_001
praxis/.venv/Scripts/python.exe experiments/curriculum/completion_placement_check_v1/pipeline.py prepare --output praxis/results/curriculum/completion_placement_check_v1/run_001
praxis/.venv/Scripts/python.exe experiments/curriculum/completion_placement_check_v1/pipeline.py run --output praxis/results/curriculum/completion_placement_check_v1/run_001
```
