# Bericht 1: Vierstundenblock und Zwischenanalyse

23.10.2026. Block1 ist technisch erfolgreich beendet. 210.000 / 207.000 / 207.000 Updates fuer Seeds1/2/3. Gemessene Blocklaufzeit 14.348,7s, davon insgesamt 4.454,6s (74,2min) Optimierung ueber alle drei Seeds; die uebrige Zeit entfiel vorwiegend auf Evaluation. Die letzten Seeds haben wegen der festen Deadline weniger Updates. Die letzte Dreierbewertung von Seed1 war mit8/10 Episoden unvollstaendig und wird nicht zur Auswahl verwendet.

## Beobachteter Fortschritt

| Seed | Gespeicherter bester Checkpoint | Zweier-Entwicklung | Dreier-Entwicklung | Letzte vollstaendige Dreierbewertung |
|---|---:|---:|---:|---:|
|1|204.000 Updates, Runde68|10/10|4/10|4/10 bei207.000|
|2|165.000 Updates, Runde55|10/10|7/10|5/10 bei207.000|
|3|96.000 Updates, Runde32|10/10|5/10|3/10 bei207.000|

Erste erfolgreiche Dreiertuerme wurden bei allen drei Seeds bereits bei6.000 Updates gemessen. Das ist ein echter Fortschritt gegenueber der bisherigen durchgehend erfolglosen Komposition. Allerdings sind die dargestellten Hoechstwerte auf wiederholt verwendeten zehn Entwicklungsstarts ausgewaehlt; kein unabhängiger Generalisierungsnachweis. Das90%-Ziel ist nicht erreicht. Die reservierten84000er Teststarts wurden noch nicht verwendet.

Die spaetesten Gewichte sind nicht generell besser als fruehere: Seed2 faellt von7/10 auf5/10, Seed3 von5/10 auf3/10. Weiteres Offline-Training allein verbessert daher den Task nicht monoton. Bei allen Seeds sind Validierungs-Aktionsfehler klein, trotzdem bleiben erhebliche Closed-Loop-Fehler. Gegen Ende bestehen weiterhin falsche/fruehe Phasenabschluesse, etwa27 False Positives fuer Phase5 bei Seed3. Der Offline-Abschlussklassifikator ist somit nicht fehlerfrei.

## Vertiefte Auswertung der gespeicherten Bewegungen

Alle30 Dreier-Zeitreihen der drei ausgewaehlten Checkpoints wurden gelesen. Die14 Fehlschlaege erreichen alle das zweite Paar und enden in Phase6. Das bedeutet jedoch nicht, dass der Fehler erst in Phase6 entsteht. Die untere A/B-Geometrie verliert bei11 der14 Fehlschlaege erstmals waehrend Phase0 des zweiten Paars ihre Toleranz, bei2 in Phase1, bei1 in Phase2. Definition: A/B lateral >9mm oder vertikaler Abstand ausserhalb40±8mm. Ein einmaliger Toleranzverlust ist kein zwingend irreversibler Zusammenbruch und allein kein Kontaktkraftbeweis.

Viele Endzustaende zeigen B auf dem Tisch und C auf B: Die Policy stapelt das zweite Paar, nachdem der untere Turm beschaedigt wurde. Andere Faelle halten alle Hoehen ungefaehr ein, verfehlen jedoch Geometrie/Kontakt/Stabilitaet. Die wichtigste aktuell belegte Fehlermarke ist deshalb die Erhaltung des unteren Stapels waehrend des Beginns der naechsten Fertigkeit. Siehe block1_trace_diagnosis.json fuer jeden Einzelfall.

Die neue Phasendarstellung entkoppelt das Greifen von der Zielhoehe. Sie loest aber das fehlende Rueckzugssegment nicht: Nach dem Loslassen beginnt der naechste offene Anflug seitlich aus unmittelbarer Naehe des Turms. Die Zeitreihen begruenden die Hypothese einer ungeeigneten Uebergangsbahn. Ohne zusaetzliche Kraft-/Kontaktanalyse ist die genaue Kollision oder Ursache nicht abschliessend bewiesen.

## Entscheidung fuer Block2

Die gelernte offene Anflugphase0 wird vor dem Paarwechsel einmal ueber dem gerade platzierten Wuerfel wiederverwendet. Dabei wird dessen Position als Quellanker gesetzt; dieselbe gelernte Phase0 erzeugt alleXYZ-/Greiferaktionen und ihren gelernten Abschluss. Danach beginnt Phase0 fuer den naechsten Wuerfel. Das ist eine explizite zusaetzliche Orchestrierungsregel und Wiederverwendung eines gelernten Kopfes, keine aus den Demos gelernte Reihenfolge und kein neu demonstrierter Rueckzug. Es gibt keine vorgegebenenXYZ-Expertenkommandos und keine neuen Aktionslabels.

Technische Vorpruefung mit Seed2/best auf63000 und63001: beide Episoden vollstaendig; Paarwechsel wird erreicht, aber0/2 Erfolge. Die Aenderung ist also nicht vorab als Verbesserung bestaetigt. Sie wird im zweiten Trainingsblock mit allen drei Seeds und wiederholten identischen Entwicklungsstarts untersucht. Diese ersten beiden Diagnosefaelle sind keine unabhaengigen Testdaten.

Fortsetzung von den drei gespeicherten best.pth, Optimizerzustand wiederhergestellt, Lernrate3e-5 statt1e-4, sonst gleiche Daten/Architektur/Loss/Sampling und Abschlussgrenze0,8. Zwei Faktoren aendern sich: kleinerer Lernschritt und Orchestrierung. Ein Unterschied kann deshalb ohne nachtraegliche gepaarte Ausfuehrung derselben Gewichte mit/ohne Rueckzug nicht einem Faktor allein zugeschrieben werden. Diese Ausfuehrungsablation ist fuer die Abschlussanalyse vorgesehen. Die Modellwahl bleibt an Entwicklung gebunden, der Endtest folgt erst nach der Wahl.

## Zeit- und Verfahrensgrenzen

Die erste Agentenanalyse fand erst um12:50 Berliner Zeit statt, etwa31min nach Ende von Block1. Zuvor eingegangene Heartbeats belegen ohne entsprechende Werkzeugpruefung keine Agentkontrolle. Die alten Checks werden nicht nachtraeglich erfunden. Der zweite Block startet dadurch spaeter und kann innerhalb der unveraenderten Deadline nicht mehr volle3–4h erhalten. Seine genaue Laufzeit wird im zweiten Bericht ausgewiesen. Gesamtende bleibt16:19:19, zweites Training endet spaetestens15:49:19, damit Zeit fuer Abschlussanalyse bleibt.

Die Methode verwendet feste Teilphasen- und Paarreihenfolge sowie privilegierte Simulatorzustaende und physische Abschlussgates. Ergebnisse belegen gegebenenfalls zusammengesetzte gelernte Bewegungen mit dieser Struktur, keine autonome Planungsfaehigkeit. Rotation ist wegen identischer Null-Trainingslabels fest null. Die bisherige Direct-Baseline hat andere Architektur, Sampling, Aktionshorizonte und Inputs; keine isolierte Kausalaussage aus dem historischen Vergleich. Ein geringerer Epochenbedarf bis90% kann erst bei tatsaechlichem Erreichen und separater Bestaetigung behauptet werden.
