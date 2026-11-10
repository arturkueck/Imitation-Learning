# Qualitätsbewertung von Schritt A

01.11.2026. Implementierung und Auswertung abgeschlossen. **Kein Training gestartet.** 0 Optimizer-Updates und 0 neue neuronale Modellaufrufe. Bestehende Vorhersagen, Checkpoints und frühere Ergebnisse wurden beibehalten. Der Vergleich dauerte etwa zwei Minuten auf der CPU.

## Urteil

Die Reprojektion und Sichtbarkeitsbehandlung funktionieren als Diagnoseinfrastruktur. Die hier untersuchte einfache RGB-Heuristik bringt jedoch **keinen nachgewiesenen Qualitätsgewinn** gegenüber der vorhandenen Seed-Streuung. Sie wird deshalb nicht als neue Freigabe- oder Aufnahmeregel aktiviert.

Das ist ein Ergebnis über diese konkrete Heuristik auf vorhandenen Validierungsszenen. Es belegt nicht, dass Bildkonsistenz mit besseren Masken oder Bildreferenzen grundsätzlich nutzlos wäre.

## Vergleich bei gleichem Budget

Auf der zurückgehaltenen Hälfte der bestehenden Validierung werden jeweils 10 % der Vorhersagegruppen zurückgestellt. Fehler bedeutet mehr als 10 mm Positionsabweichung oder falsches Zusatzobjekt. Die Kombination wurde ausschließlich auf der anderen Hälfte ausgewählt: für beide Kameravarianten 75 % Positionsstreuung und 25 % Bildsignal, jeweils auf kalibrierten Perzentilrängen.

| Kameras | Verfahren | Erkannte Fehler | Anteil aller Fehler erkannt | Fehler unter beibehaltenen Gruppen |
| --- | --- | ---: | ---: | ---: |
| Fest + Hand | Seed-Streuung | 126 / 219 | 57,53 % | 3,61 % |
| Fest + Hand | Bildkonsistenz | 99 / 219 | 45,21 % | 4,66 % |
| Fest + Hand | Ausgewählte Kombination | 119 / 219 | 54,34 % | 3,88 % |
| Zwei feste | Seed-Streuung | 130 / 243 | 53,50 % | 4,42 % |
| Zwei feste | Bildkonsistenz | 119 / 243 | 48,97 % | 4,85 % |
| Zwei feste | Ausgewählte Kombination | 124 / 243 | 51,03 % | 4,65 % |

Bei Fest + Handkamera werden mit der Kombination sieben Fehler weniger gefunden als mit Seed-Streuung. Die Differenz des erkannten Fehleranteils beträgt -3,20 Prozentpunkte; gepaartes Szenen-Bootstrap-95%-Intervall: -7,95 bis +1,05 Prozentpunkte. Bei zwei festen Kameras: -2,47 Punkte, Intervall -6,67 bis +2,00. Ein Vorteil ist damit nicht belegt. Bei 20 % Budget ist die Kombination für Fest + Hand in dieser Auswertung sogar klar schwächer: -6,85 Punkte, Intervall -12,20 bis -1,72.

Die früher berichteten Werte aus `uncertainty_001` nutzten eine feste kalibrierte Schwelle mit rund 5,2 % Zurückstellung bei Fest + Hand. Die Werte dieser Tabelle nutzen exakt 10 % Budget. Die unterschiedlichen Zahlen dürfen nicht als Änderung am Vision-Modell gelesen werden.

## Türme und gemeinsame Fehler

Bei einem separat innerhalb der Turmgruppe auf 10 % begrenzten Budget findet Fest + Handkamera:

| Verfahren | Erkannte Turmfehler | Fehler unter beibehaltenen Turmvorhersagen |
| --- | ---: | ---: |
| Seed-Streuung | 28 / 87 = 32,18 % | 9,92 % |
| Bildkonsistenz | 16 / 87 = 18,39 % | 11,93 % |
| Ausgewählte Kombination | 27 / 87 = 31,03 % | 10,08 % |

Auch bei tatsächlich stärker verdeckten Objekten (maximale Sollsichtbarkeit unter 80 %) ist die Kombination bei gleichem 10%-Budget schwächer: 17 statt 21 von 43 Fehlern erkannt. Sichtbarkeitslabels dienen ausschließlich der Auswertung, nicht der Bildbewertung.

Der besonders relevante Teil mit drei zustimmenden Seeds, höchstens 3 mm Streuung und trotzdem fehlerhafter Position/Zusatzdetektion umfasst 19 Gruppen bei Fest + Hand. Beim globalen 10%-Budget markieren weder Seed-Streuung, Bildheuristik noch Kombination eine dieser 19 Gruppen. Für zwei feste Kameras erfasst die Kombination ebenfalls keine der 18 entsprechenden Gruppen. Das ursprüngliche Problem gemeinsamer Fehlvorstellungen bleibt somit offen.

## Prüfung der Ursache

Die aus den gespeicherten Kamerastrahlen rekonstruierte Projektion hat maximal 0,0000103 Pixel Restfehler auf deren Kalibrierungsgitter. Synthetische Tests bestätigen korrekte Reprojektion und Verdeckung durch näher liegende Boxen. Dies prüft die interne Kalibrierung, nicht die Genauigkeit zukünftiger realer Kameras.

Die gezielte Sichtprüfung zeigt einen konkreten Schwachpunkt: Helle beziehungsweise überstrahlte Objektflächen können wie der helle Tisch aussehen. Die Hintergrundheuristik bestraft dann sogar korrekt projizierte Geometrie. Die nachgelagerte, ausdrücklich mit Sollgeometrie durchgeführte Beispielprüfung dokumentiert dies in `oracle_example_audit.json`; ihre Ergebnisse fließen nicht in Rankings oder Rezeptwahl ein.

Beispiel Szene 441: Die wirklich richtige Box wird in der Handansicht auf 94,96 % ihrer sichtbaren Pixel fälschlich als Hintergrundwiderspruch bewertet. Über alle Ansichten liegt ihr Bildscore bei 0,482; die falsche Vorhersage bekommt 0,504. Diese beiden Werte sind für eine zuverlässige Unterscheidung zu ähnlich. Bei ausgewählten unnötigen Warnungen tritt derselbe Effekt auf. Aus den bewusst ausgewählten Beispielen wird keine Häufigkeit für den gesamten Datensatz abgeleitet.

Zusätzlich liegen viele Objekte in den festen Ansichten nur wenige Pixel groß vor. Eine Verschiebung im Millimeterbereich muss dort keine deutlich veränderte Kontur erzeugen. Bei Verdeckungen können die sichtbaren Konturen trotz falscher Höhe ähnlich bleiben. Diese Mechanismen sind plausible Grenzen; ihre jeweiligen Anteile am Gesamtfehler wurden nicht kausal getrennt.

## Was als Nächstes sinnvoll wäre

Zunächst die Bildbelege verbessern: kalibrierte leere Referenzaufnahmen beziehungsweise belastbarere Vordergrundmasken, bekannte Robotermasken aus tatsächlich gespeicherten Gelenkständen und robustere Behandlung überstrahlter/grauer Flächen. Das wäre eine gezielte Erweiterung von A, weiterhin ohne Training der vorhandenen Vision-Modelle.

Anschließend eine neue, getrennte Diagnose-Kalibrierung und Prüfung mit ausreichenden Turm-/Verdeckungsszenen vorsehen. Die jetzige zurückgehaltene Hälfte nicht zur wiederholten Optimierung derselben Heuristik verwenden. Ein verbessertes Verfahren müsste bei gleichem Budget mehr gemeinsame Fehler erkennen; außerdem sollten Größe und Orientierung als zusätzliche Qualitätsziele bewertet werden, da das bisherige primäre Fehlerkriterium nur Position und Zusatzdetektionen umfasst.

Einfach die jetzige Bildheuristik stärker zu gewichten ist durch diese Ergebnisse nicht gerechtfertigt. Die Handkamera bleibt ein möglicher Weg zu zusätzlicher Information, setzt aber sowohl verifizierbaren Bewegungsraum als auch eine nachweislich nützliche Auswertung der neuen Perspektive voraus.

## Artefakte

- `fixed_wrist_comparison.png` und `fixed_comparison.png`: alle Vergleichskurven.
- `qualitative_examples.png`: zusätzliche Treffer, übersehene Fehler und unnötige Warnungen mit Soll-/Vorhersageüberlagerung.
- `results.json`: sämtliche Haupt- und Teilgruppenmetriken mit Provenienz.
- `METHOD.md`: Verfahren, Grenzen und Reproduktion.
- `oracle_example_audit.json` und `audit_examples.py`: klar getrennte nachträgliche Ursachendiagnose.

15 Tests bestanden. Keine unabhängige Schlussprüfung: Die bestehenden Validierungsdaten wurden zuvor zur Checkpoint-Auswahl genutzt. Keine Hardwarefreigabe und keine Änderung der Kollisionsprüfung.
