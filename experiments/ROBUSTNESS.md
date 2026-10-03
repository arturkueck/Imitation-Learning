# Automatische Robustheits-Evaluation

Das Training selbst bleibt unveraendert. Nach dem finalen Modell wird automatisch
eine separate Robustheits-Suite ausgefuehrt. Sie ist in die Square-Pipeline,
den Nachtlauf und die Trainingsskripte fuer StackFour / CubeHandover eingebunden.
Die Zwischenstand-Evaluation bleibt nominal, damit das Trainingsbudget nicht
von wiederholten umfangreichen Robustheitstests dominiert wird.

## Bedingungen (jeweils nur eine Aenderung)

| Bedingung | Tatsaechlicher Eingriff |
|---|---|
| nominal | unveraenderte Umgebung / Beobachtungen |
| action_impulse_x | an Schritt 20 +0,5 auf erste normierte X-Aktion, auf [-1,1] begrenzt; dies ist ein Steuerungsfehler, kein Kraftimpuls |
| object_push_x | 1 N Welt-X-Kraft auf ein Objekt, Schritte 20-24; bei 20 Hz 0,25 Sekunden |
| mass_150pct / mass_70pct | Objektmasse und Traegheit x1,5 bzw. x0,7 |
| friction_50pct | Gleitreibung der Objekt-Kontaktgeometrien x0,5 |
| controller_gain_80pct | OSC-Proportionalverstaerkung aller Arme x0,8, D-Verstaerkung angepasst |
| proprio_noise_5mm | unabhaengiges Gaussian-Rauschen auf beobachtete EEF-Positionen, Standardabweichung 5 mm |
| observation_delay_2steps | alle Policy-Beobachtungen um zwei Kontrollschritte verzoegert (100 ms bei 20 Hz) |
| image_dark_50pct | RGB-Policy-Eingaben x0,5; synthetischer Belichtungstest, keine physische Lichtsimulation |
| image_occlusion_25pct_width | schwarzes zentrales Quadrat, Kantenlaenge 25 % der Bildbreite (6,25 % Bildflaeche) |
| camera_shift_x_2cm | agentview-Kamera real im Simulator um 2 cm in X verschoben |

Bei Zweiarm-Aufgaben trifft der Aktionsfehler Arm 0. Beim Schubs wird nur ein
Objekt gestoert, beim Stapeln der Basiswuerfel. Masse und Reibung betreffen
alle Aufgabenobjekte. Die Policy erhaelt keine Information ueber geaenderte
physikalische Parameter. Keine neuen Demonstrationen oder Retraining je Bedingung.

## Fairer Vergleich und Metriken

Standard: 20 Episoden je Bedingung, separate Seeds 16000-16019. Alle Bedingungen
verwenden denselben Checkpoint und dieselben initialen Simulatorzustaende.
Die Suite vergleicht SHA-256 der Zustandsvektoren je Episode und bricht bei
abweichenden Anfangszustaenden ab. Statische Modellmodifikationen duerfen
den initialen Zustandsvektor nicht veraendern. Rauschgeneratoren sind separat,
damit Stoerungen nicht die Reset-Zufallsfolge beeinflussen.

Gespeichert werden Erfolgsrate mit Wilson-95%-Intervall, Return, Episodenlaenge,
Erfolgsabfall gegen nominal in Prozentpunkten, sowie:

- `sustained_success_rate`: anfangs erfolgreich und bei jedem Kontrollschritt
  waehrend zwei Sekunden Policy-Nachlauf weiterhin erfolgreich.
- `object_drop_rate`: mindestens ein Aufgabenobjekt faellt unter die Tischhoehe
  minus 5 cm, waehrend Rollout oder Nachlauf. Dies ist ein operationaler Indikator,
  kein allgemeiner Detektor fuer jedes Fallenlassen innerhalb der Tischflaeche.
- Tatsaechliche Masse, Reibung, Controllerwerte und Kameraaenderungen vor/nach
  dem Eingriff sowie konkrete Ereignisse dynamischer Stoerungen.
- Zahl der Episoden, in denen der zeitgesteuerte Eingriff tatsaechlich ausgefuehrt
  wurde. Erfolg vor Schritt 20 bedeutet, dass der Eingriff nicht mehr stattfindet.

Die Nachlaufzeit beeinflusst weder Haupt-Erfolg, Return noch Episodenlaenge.
Beim Stapeln wird dadurch die Turmstabilitaet weiter geprueft, bei Uebergaben
das weitere Halten des Wuerfels. Die bestehende Videocollage bleibt erhalten.
Je Robustheitsbedingung werden die ersten drei Episoden mit zwei Sekunden
Nachlauf aufgezeichnet. Belichtung und Verdeckung werden auf die Policy-Eingaben
angewandt; die Collage zeigt die Szene, nicht diese synthetische Sensorkorruption.

## Dateien und manuelle Ausfuehrung

Automatische Ausgabe: `<experiment>/robustness/<algorithm>/SUMMARY.json`,
`SUMMARY.csv`, `RESULTS.md`, `status.json`, individuelle Episoden-JSONs und Videos.
Jede Bedingung hat ein eigenes Log; Fehler beenden die Suite und die Pipeline.
Vorhandene Suite-Ergebnisse werden nicht ueberschrieben.

```powershell
& .\praxis\.venv\Scripts\python.exe .\experiments\square\scripts\robustness_suite.py .\experiments\square_overnight\bc_rnn\final.pth bc_rnn --output-root .\experiments\square_robustness --episodes 20
```

Fuer die beiden neuen Tasks verwendet der Trainer automatisch Horizont 1000.
CLI-Parameter `--episodes`, `--seed`, `--horizon` und `--video-episodes` ermoeglichen
ein anderes Rechenbudget. Die Parameter der Bedingungen stehen zentral in
`experiments/square/scripts/robustness.py` und werden in jedem Ergebnis gespeichert.

Die Kurztests mit wenigen Schritten unter `robustness_smoke` / `robustness_verified`
pruefen nur die Technik. Sie sind keine aussagekraeftigen Robustheitsresultate.
Dieser Testumfang deckt ausgewaehlte Stoerungen ab, nicht jede Modellungenauigkeit
und nicht automatisch die Sicherheit am realen Roboter.
