# Direkte Prüfung der Critic-Aktionsbewertung

Autorisiert am05.11.2026 nach dem explorativen Trainingslauf. Diese Prüfung
verändert keine Modellgewichte und führt keine Optimizerupdates aus.

## Frage

Ordnet der Critic auf identischen Ausgangszuständen bessere und schlechtere
Aktionen passend zu ihren tatsächlichen Folgen ein? Ein kleiner Return-MSE
auf beobachteten Daten beantwortet diese Frage nicht. Untersucht werden die
vorgewärmten Critics und die finalen Critics des Pilots, jeweils für alle drei
Parentseeds. Die Daten werden nicht als neuer Trainingssatz verwendet.

## Festgelegte Zustände und Aktionen

Zwei neue geteilte Entwicklungsstartfamilien2026113000/2026113001. Sowohl
Originalpolicy als auch finale Policy erzeugen eigene Zustandskontexte.
Probezeitpunkte sind festgelegt: Stage1/Phase0/Schritt5,
Stage1/Phase4/Schritt5 und Stage2/Phase0/Schritt5. Nicht erreichte Probes
werden protokolliert und nicht durch günstigere Starts ersetzt.

Verglichen werden die aktuelle Aktion, die Bewegung des jeweils anderen
Actors auf derselben Eingabe, eine XYZ-Änderung der Länge0.1 entlang des
passenden Q1-Gradienten, die entgegengesetzte Änderung, umgekehrte XYZ-Aktion
und geöffneter Greifer. Alle Aktionen bleiben in [-1,1]. Umkehr und Öffnen
sind separate Stresskontrollen, keine durch den Critic trainierten Aktionen.
Gleiche Aktionen werden nur einmal simuliert; Aliasnamen bleiben im Rohprotokoll.

**Jeder Eingriff betrifft exakt eine Aktion.** Danach folgt unverändert die
Policy des jeweiligen Kontextes mit dem bisherigen Sequencer. Dies erhält den
Bezug zur Bedeutung eines Q-Werts. Eine zehn Frames lange erzwungene
Fehlhandlung wäre kein fairer Test desselben Ein-Aktions-Q-Werts.

Die gesamte Vorgeschichte wird in einer frisch erzeugten Umgebung wiederholt.
Simulatorzustand, Controllerausgaben, Solver-Warmstart, Criticfeatures und
Policyvorschläge müssen bis zum Eingriff bitgenau dieselben Hashes erzeugen.
Es werden nicht nur sichtbare Objektpositionen zurückgesetzt. Der technische
Smoke wiederholt zusätzlich die unveränderte Aktion und verlangt denselben
Erfolg, Endframe und Abbruchgrund.

## Gemessener Wert

Gemessen wird der tatsächlich erreichte diskontierte Return ab dem Eingriff:
`gamma ** (Erfolgsframe - Eingriffsframe)` bei bestätigtem Gesamterfolg,
andernfalls0. Gamma0.995, unverändertes absolutes Episodenlimit1000 Aktionen.
Präfixaktionen erhalten keine zusätzliche Zeit am Ende. Neben dem Return werden
Erfolg, Endframe, letzte Phase/Stage und Abbruchgrund gespeichert.

Q1 ist primär, weil der bisherige Actorloss Q1 optimiert. Q2 und Minimum werden
ebenfalls gespeichert. Auswertung innerhalb desselben Zustands: korrekte und
falsche Reihenfolgen, identische Ausgänge, tatsächliche Folgen der Q1-Gradient-
Empfehlung und Regret gegenüber der besten konkret geprüften Aktion.
Identische Aktionsvektoren werden für paarweise Statistiken zusammengeführt.
Unveränderte Ausgänge gelten nicht als falsche Bewertung.

## Grenzen der Aussage

- Ein einzelner kleiner Eingriff kann bei sparsem Reward ohne messbaren Effekt
  bleiben. Dann ist der Test für diese Reihenfolge nicht informativ.
- Warmup-Labels stammen aus einem Pool mehrerer Parents. Sie beschreiben nicht
  nachweislich exakt jede hier separat fortgesetzte Parentpolicy.
- Der finale Critic wurde mit verrauschten TD-Targetaktionen trainiert;
  untersucht wird die im Einsatz verwendete deterministische Fortsetzung.
  Ein Fehler kann damit auch eine Ziel-/Ausführungsdiskrepanz zeigen.
- Original- und finale Policy erreichen unterschiedliche Zustände. Das primäre
  Urteil ist jeweils die Aktionsreihenfolge für den passenden Policykontext.
  Unterschiede der beiden Critics sind nicht automatisch ein isolierter
  kausaler Effekt des Vorwärmens.
- Mehrere Probezeitpunkte, Aktionen und Parentseeds aus zwei geteilten
  Startfamilien liefern keine große unabhängige Stichprobe. Keine p-Werte oder
  allgemeine Genauigkeitsbehauptung daraus ableiten.
- Selbst nachgewiesene Fehlbewertungen isolieren nicht sämtliche Ursachen des
  gesamten Policy-Leistungsrückgangs.

Maximal90 Minuten, STOP-Datei, keine automatischen Wiederholungen. Reservierte
Endtests und alte Endtestrollouts werden nicht eingelesen.

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/critic_action_audit.py --output experiments/critic_warmstart_20261104/critic_audit_NEW
```

Rohdaten: `counterfactuals.json`; Vorgaben: `protocol.json`; Prozess:
`status.json`; Abschlussintegrität: `verification.json`. Die erste Summary
führt Variantenamen auf. Die berichtete paarweise Auswertung wird auf
unterschiedliche Aktionsvektoren reduziert, damit Aliasnamen keine zusätzliche
Evidenz vortäuschen.
