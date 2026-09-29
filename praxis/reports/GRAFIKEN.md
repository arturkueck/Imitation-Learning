# Grafiken zu Plan A

Die Abbildungen wurden aus den drei JSON-Zusammenfassungen in diesem Ordner
mit [`plot_results.py`](../src/plot_results.py) erzeugt. PNG ist für die
Vorschau, PDF für Dokumente und Druck gedacht.

## Gemessene Ergebnisse

1. [Erfolg bei 20 und 100 Epochen (PNG)](figures/01_gemessene_lernkurven.png) ·
   [PDF](figures/01_gemessene_lernkurven.pdf): voller Trainingssplit, drei
   Bedingungen. Die Linien verbinden nur zwei Messzeitpunkte; die hellen
   vertikalen Balken zeigen die Spannweite über drei Trainings-Seeds. Das sind
   keine Konfidenzintervalle. Die 20- und 100-Epochen-Policies stammen aus
   getrennten Trainingsläufen mit denselben Seed-Nummern.
2. [Alle Bedingungen und Datensplits nach 100 Epochen (PNG)](figures/02_gemessene_bedingungen.png) ·
   [PDF](figures/02_gemessene_bedingungen.pdf): BC und Erweiterung auf den
   gleichen Rollout-Starts innerhalb jedes Splits. Zwischen den Splits wurden
   andere Rollout-Seeds verwendet; die Splitwerte sind daher nicht paarweise
   vergleichbar.

## Hypothetische Trends

[Drei Szenarien bis 300 Epochen (PNG)](figures/03_hypothetische_trends.png) ·
[PDF](figures/03_hypothetische_trends.pdf). Die durchgezogenen Abschnitte
zeigen die nominal gemessenen 20- und 100-Epochen-Werte des vollen Splits.
Grau hinterlegte und gestrichelte Abschnitte sind **hypothetische Szenarien**.
Ihre Endpunkte sind frei gewählt und weder Schätzwerte noch statistische
Konfidenzgrenzen:

| Szenario | Hypothese | Illustrativer Wert bei 300 Epochen (BC / Erweiterung) | Prüfung |
| --- | --- | --- | --- |
| A: BC holt auf | Mehr Training schließt die Lücke weitgehend | 95 % / 98 % | Beide Policies mit identischem Budget bis 300 Epochen trainieren und neu evaluieren |
| B: Abstand bleibt | Die lokale Korrekturreaktion bringt einen dauerhaften Vorteil | 80 % / 95 % | Zusätzliche Checkpoints, Seeds und Störungen prüfen |
| C: Zusatzverlust schadet später | Fortgesetzte Regularisierung verschlechtert die spätere Policy | 90 % / 85 % | Späte Checkpoints und Aktionsfehler mit `λ=0` vergleichen |

Mit nur zwei Trainingszeitpunkten lässt sich keine belastbare Kurvenform oder
Wahrscheinlichkeit für eines dieser Szenarien bestimmen. Die hohen Lift-Werte
erzeugen zudem einen Deckeneffekt. Eine echte Prognose würde weitere
Checkpoints, unabhängige Trainings-Seeds und idealerweise einen zweiten Task
brauchen.

## Reproduktion

```powershell
$env:MPLCONFIGDIR=(Join-Path (Resolve-Path 'praxis').Path '.cache/matplotlib')
& 'praxis/.venv/Scripts/python.exe' praxis/src/plot_results.py
```
