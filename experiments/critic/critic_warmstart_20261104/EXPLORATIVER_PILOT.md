# Vorbereiteter explorativer Actor-Critic-Lauf

Stand05.11.2026. Der Nutzer möchte mehr Aktionsspielraum und wissenschaftlich
relevante Erkenntnisse. Sein „Okay sounds fine“ nach Erklärung der größeren
Aktionsfreiheit wird für diese reversible Vorbereitung als Zustimmung zu
einem Versuch mit möglichen vorübergehenden Rückschritten verstanden.
Der Hauptlauf wird durch die Vorbereitung nicht gestartet.

## Geänderte Forschungsentscheidung

Der separate Lauf `pilot_002` untersucht Lernen mit größeren zulässigen
Aktionsänderungen. Er ist **kein bestandenes Stabilitätsergebnis**. Die gescheiterten
Prüfungen `range_001` und `relative_002` bleiben unverändert erhalten.
Frühe niedrige Erfolgsraten werden protokolliert, führen hier aber nicht zum
Abbruch. Ein solches Ergebnis darf später nicht als technische Fehlfunktion
oder als Anlass zum automatischen Wiederholen behandelt werden.

Weiterhin gelten Abbruch bei nicht endlichen Losses/Gradienten/Aktionen,
Ausführungsfehlern, beschädigten Eingaben, STOP oder Zeitlimit. Maximal drei
Stunden ab Start; der Supervisor beendet spätestens am05.11.2026 um15:00 Berlin.
Es kann nach einer kooperativen Wartezeit von30 Sekunden eine Beendigung der
eigenen Workerfamilie erforderlich sein. Keine automatischen Neustarts oder Resume.

## Festgelegter Umfang

- Drei ursprüngliche IL-Actors und zugehörige bereits vorgewärmte Critics;
  keine Übernahme kollabierter oder anhand von Entwicklungsresultaten
  ausgewählter Actorgewichte.
- XYZ-Grenze pro Komponente `min(0.20,0.5*abs(Parentaktion))`, Greifer0.02.
  Der tatsächliche Spielraum schrumpft nahe Parent-Ruhelagen auf null; die
  XYZ-Richtung gegenüber dem Parent bleibt erhalten. Größere Spielräume
  bedeuten keine vorausgesagte prozentuale Leistungsverbesserung.
- Vier Runden mit je fünf frischen Onlineepisoden und500 Criticupdates je Seed:
  insgesamt60 Onlineepisoden,6000 Criticupdates und3000 Actorupdates.
- Replay50 % vorhandene ursprüngliche Trainingsframes,50 % private frische
  Onlineerfahrung. Direkter Originalexperten-BC-Term0.01, sonstige Lernparameter
  unverändert. Exploration wird ebenfalls in den relativen Bereich projiziert.
- Neue Onlinefamilien2026112200–2026112219. Die sechs Tuningfamilien der beiden
  vorherigen größeren Varianten werden nicht als neue Trainingsdaten verwendet.
- Entwicklungsevaluation auf20 gemeinsamen neuen Starts2026112100–2026112119
  je Seed in Runde0/1/2/4:240 Rollouts. Insgesamt300 geplante Episoden.
- Alle20 Familien werden vorab festgelegt, über die drei Seeds geteilt und
  gepaart geprüft. Es sind nicht60 unabhängige Startfamilien.
- Unveränderte Parentbaselines müssen mindestens10/20 je Seed erreichen;
  sonst endet der Versuch vor Trainingsupdates, ohne Starts nachzusammeln.
- Fester finaler Checkpoint Runde4, keine Best-Checkpoint-Auswahl. Reservierte
  Endtestfamilien werden nicht ausgeführt.

## Vorab-Hypothese und Auswertung

Die größere Freiheit kann frühere Rückschritte verursachen. Geprüft wird,
ob frische eigene Erfahrungen den Critic ausreichend an die veränderte Policy
anpassen, sodass sich die Aufgabenleistung bis Runde4 gegenüber Runde1 erholt
und die ursprüngliche Parentleistung erreicht oder übertrifft. Das ist eine
offene Hypothese; ein erneuter Kollaps ist möglich und wird unverändert berichtet.

Primär: bestätigter vollständiger Dreierturmerfolg in fester Runde4 gegenüber
Runde0 auf gepaarten Starts, getrennt für alle drei Seeds. Sekundär: Lernverlauf
0/1/2/4, gepaarte Gewinne/Verluste, Actorabweichung, Critic-/Actor-/BC-Loss und
tatsächliche Umweltinteraktionen. Sinkender Critic-Loss allein ist kein Erfolg.
Ein mittlerer Gewinn ab fünf Prozentpunkten ist ein vorab definierter praktischer
Hinweis; er ist auf diesem Entwicklungspanel kein unabhängiger Wirksamkeits-
oder Neuheitsnachweis. Unterschiede gegenüber anderen Methoden erfordern
später einen direkten Vergleich auf denselben Startfamilien und Budgets.

Die Grenzen für gepaarte Verluste in der Konfiguration sind ausdrücklich auf
20 je Seed/60 insgesamt gesetzt, damit das bestehende Produktionslogging alle
Verluste zählt, ohne wegen schlechter Aufgabenleistung früh abzubrechen.
`performance_abort_enabled=false` dokumentiert diese neue Entscheidung.

## Betrieb

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/pilot_watch.py launch --output experiments/critic/critic_warmstart_20261104/pilot_002
& praxis/.venv/Scripts/python.exe experiments/critic/critic_warmstart_20261104/pilot_watch.py check --output experiments/critic/critic_warmstart_20261104/pilot_002
```

Der Supervisor läuft ohne sichtbares Fenster, hält Windows während des Versuchs
wach und prüft seinen Worker alle fünf Sekunden. Der inkrementelle Monitor
liest nur kleine Statusdateien und neue Workerlogzeilen. Zum Abbrechen eine
Datei `pilot_002/STOP` anlegen. Die bisherigen Routinen für einen anderen
Nachtlauf werden nicht als Beleg einer Kontrolle dieses Pilots ausgegeben.

Die Vorbereitung speichert Konfiguration, Eingangshashes und Quellkopien.
Es wurde noch kein neuer wiederkehrender Kontrollauftrag eingerichtet.
Technischer Miniworkflow: `pilot_exploratory_smoke_001`, ausdrücklich von
wissenschaftlichen Ergebnissen getrennt.
