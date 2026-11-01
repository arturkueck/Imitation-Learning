# Visueller Würfel-zu-Quader-Pilot

Dieser begrenzte Vorversuch misst Objektlokalisierung, nicht Greif- oder Stapelerfolg.
Autorisierung: Vergleich feste Kameras / feste Kameras plus Handkamera; Training
auf Würfeln, Prüfung auf anderen rechteckigen Objekten.

- Zwei farblich unterscheidbare Objekte auf dem Tisch, zufällige Positionen und
  Drehungen um die Hochachse. Farbbindung dient nur der eindeutigen Zuordnung.
- Training: 512 Szenen mit Würfeln (Kantenlänge 30–60 mm).
- Entwicklung: 128 neue Würfelszenen; ausschließlich diese wählen Checkpoints.
- Einmaliger Endtest: 128 neue Würfelszenen und 128 Quaderszenen mit
  Kantenlängen 30–70 mm und längster/kürzester Kante mindestens 1,5.
- Identische Szenen und Aufnahmen für beide Arme: zwei feste Kameras oder
  dieselben Kameras plus Handgelenkkamera. Im Kontrollarm wird die dritte
  Ansicht maskiert; Architektur, Parameterzahl und Batchreihenfolge sind gleich.
- Zwei gepaarte Modellseeds, jeweils maximal 600 Updates, Batch 32.
- Ein fester Armzustand; keine aktive Kamerabewegung. Ergebnis gilt nur für
  diese Konfiguration, nicht für beliebige Armstellungen oder Verdeckungen.
- Eingabe: RGB-Bilder. Ausgabe: Weltkoordinaten beider Objektmittelpunkte.
  Keine Simulatorpositionen, Geometrieparameter oder Segmentierung als Eingaben.
- Hauptmetrik: euklidischer Mittelpunktfehler in mm, zusätzlich XY-Fehler,
  90%-Quantil und Anteil innerhalb 10 mm. Z-Fehler separat: bei Würfeln hängt
  Z systematisch von der Kantenlänge ab, bei Quadern nicht; dies ist Teil des
  Verteilungssprungs und kein isolierter Kameratest.
- Kameras bleiben kalibriert und unverändert. Farben, Hintergrund und Licht
  werden in diesem ersten technischen Pilot nicht unabhängig getestet.
- Statische Renderdaten: Geometrien werden vor dem Rendern verändert; es findet
  keine Physiksimulation dieser Szenen statt. Daher keine Aussagen über Masse,
  Kontakte, Stabilität, Bewegungsausführung oder Sim-to-Real-Transfer.

Quader-Testdaten werden weder zur Checkpointwahl noch zum Finetuning benutzt.
Ein Quader-Vorteil oder Scheitern ist hier nur ein erster Befund. Für belastbare
Übertragbarkeit folgen getrennte Formfamilien, mehr Seeds, variierende Armposen,
neue Farben sowie ein geschlossener Greif-/Stapeltest mit Zielvorlagen.
