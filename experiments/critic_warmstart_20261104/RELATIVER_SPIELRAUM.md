# Zustandsabhängiger größerer Aktionsspielraum

Diese einzelne Alternative wurde nach dem gescheiterten konstanten ±0.05-Test
explizit als neue Methode festgelegt. Sie ist kein nachträglich geändertes
Erfolgskriterium des ersten Versuchs und kein Nachweis methodischer Neuheit.

## Regel

Für jede XYZ-Komponente wird aus der eingefrorenen Parentaktion berechnet:

`width_xyz = min(0.20, 0.5 * abs(a_parent_xyz))`

Der trainierbare Bewegungskopf liefert wie bisher `a_raw`. Ausgeführt wird

`a = clip(a_parent + width * tanh((a_raw-a_parent)/width), -1, 1)`.

Für `width=0` bleibt die Ausgabe exakt bei der Parentaktion. Der Greifer behält
die feste Breite0.02. So sind größere Änderungen während kräftiger Bewegung
möglich, ohne nahe an einer Parent-Ruhelage eine konstante Zusatzaktion zu
erzwingen. XYZ-Komponenten behalten ihre Richtung und können im nicht
absolut begrenzten Bereich um höchstens50 % ihres Parentbetrags verändert
werden. Unterschiedliche Anpassungen der Achsen können die Trajektorie ändern;
eine Umkehr einer einzelnen XYZ-Komponente gegenüber dem Parent ist ausgeschlossen.

Die Obergrenze0.20 entspricht dem Zehnfachen der bisherigen maximalen
Aktionsabweichung, aber gilt nicht in jeder Situation. Sie bedeutet weder
zehnfachen Erfolg noch freie Aktionswahl. Das Verfahren kann vorhandene
Fehlrichtungen des Parents nicht direkt umkehren. Signalerhalt und kleine
Änderungen nahe Ruhelagen sind keine Kollisions- oder Stabilitätsgarantie.

Exploration wird im nächsten Pilot in denselben zustandsabhängigen Bereich
projiziert. Die bisherige TD3-Targetglättung ist unverändert und kann weiterhin
Aktionen außerhalb dieses Ausführungsbereichs abfragen; Critic-Extrapolation
ist deshalb nicht grundsätzlich gelöst.

## Vorab festgelegte Prüfung

- Unveränderte IL-Actors und warme Critics für drei Parentseeds.
- Gleicher fester Replay und gleiche BC-Batchstreams wie zuvor; keine zusätzliche
  Abstimmung von LR, BC-Stärke oder Trainingsdaten.
- 10/50/100/500 Criticupdates, feste finale Auswahl500.
- Neue Entwicklungsfamilien2026112800–2026112805; sechs geteilte Familien,
  18 Modell-Start-Kombinationen. Je Kontrolle höchstens ein verlorener
  Parent-Erfolg je Seed und höchstens einer insgesamt.
- Maximaler Aktionsbetrag der Änderung0.20, Greifer0.02; konkrete Grenzen werden
  durch die Policy implementiert und mit Eigenschaftstests geprüft.
- Erst bei bestandenem Gate separate Bestätigung auf20 weiteren geteilten
  Familien2026112900–2026112919. Die unveränderten Parents werden dort ebenfalls
  erneut ausgeführt. Mindestens10/20 Baseline-Erfolge je Seed, höchstens zwei
  verlorene Erfolge je Seed und höchstens drei insgesamt. Keine Verrechnung
  verlorener mit neu gewonnenen Erfolgen.
- Keine andere Konfiguration nach einem Bestätigungsfehlschlag auswählen.
  Keine reservierten Endtests; diese Panels bleiben Entwicklungsdaten.
- Gesamtbudget einschließlich Bestätigung eine Stunde, STOP-Datei,
  kein automatischer Neustart und kein automatischer Hauptlauf.

`relative_range.py check` benutzt den bestehenden, getesteten Stabilitätsablauf
mit dieser ausdrücklich eingesetzten Policyregel. Der Onlinepfad setzt die
gleiche Regel sowohl beim Actor als auch bei Exploration ein. Die ersten
eigentlichen Online-Lernupdates des größeren Pilots stehen noch aus.

Der Integrationsstart `relative_001` wurde während der Baselineprüfung vor
Optimizerupdates gezielt per STOP beendet, um die Bestätigungsdiagnostik auf
tatsächlich gemessene Driftwerte des geladenen finalen Critics umzustellen.
Er liefert keine wissenschaftlichen Resultate. Der vollständige Versuch liegt
separat unter `relative_002`; der vorherige Start bleibt erhalten.

## Befehle

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/relative_range.py check --output experiments/critic_warmstart_20261104/relative_NEW
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/relative_range.py prepare --study experiments/critic_warmstart_20261104/relative_002 --output experiments/critic_warmstart_20261104/pilot_002
& praxis/.venv/Scripts/python.exe experiments/critic_warmstart_20261104/relative_range.py run --execute --output experiments/critic_warmstart_20261104/pilot_002
```

Die Vorbereitung funktioniert nur nach vollständig bestandener Bestätigung.
Der neue Pilot beginnt wieder bei den Originalactors und warmen Critics, nicht
bei den anhand der Entwicklungsresultate geprüften Actors. Seine vorgesehenen
Online- und Entwicklungsfamilien2026112200–2026112219 bzw.2026112100–2026112119
bleiben von dieser Abstimmung unbenutzt. Bestehende Versuchsergebnisse werden
nicht überschrieben.
