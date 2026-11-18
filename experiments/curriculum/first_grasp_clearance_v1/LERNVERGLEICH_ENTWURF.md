# Lernvergleich für den Abschluss des ersten Greifens

Versuchsentwurf auf Basis des abgeschlossenen Simulatorvergleichs vom
18.11.2026. Primäre Frage ist, ob die Auswahl der Zustände, an denen wir
eine Expertenentscheidung abfragen, bei gleichem Abfragebudget den
vollständigen Stapelerfolg verbessert.

Die späte Bereitschaftsregel rettete 14 der 24 kritisch gesichteten
Modell-/Szenenpaare gegenüber der Originalpolicy. Die bekannte Schwäche
ist damit auf weiteren Familien sichtbar. Gegenüber dem reinen Timeout
kommt ihr Netto-Vorteil im kritischen Panel vollständig von der für
die Sichtung verwendeten Modelllinie. Bei den zwei anderen Linien
erreichen beide 12/16. Der Timeout gehört deshalb in die Referenzgruppe.

## Erhebung

Für jede unabhängige Modelllinie sammeln wir eine feste Zahl vollständiger
Rollouts mit derselben eingefrorenen Ausgangspolicy beider Arme. Am
ersten Absenken werden Zustandsmerkmale, Abschlusswahrscheinlichkeit und
Phasenuhr aufgezeichnet. Ein Fenster beginnt mit dem ersten Erreichen
einer vorab definierten Bedingung. Zeitlich benachbarte Frames aus
demselben Fenster werden gemeinsam behandelt. So entstehen aus einem
langen Stillstand keine hunderte unabhängigen Trainingsbeispiele.

| Arm | Auswahl der zusätzlichen Expertenabfragen |
|---|---|
| BC mit gleichmäßig gezogenen Fenstern | Zufallsstichprobe aus den vorab definierten geeigneten Fenstern der ersten Griffphase. |
| BC mit gezielter Auswahl | Mehr Abfragen in Fenstern mit anhaltender geometrischer Bereitschaft, in denen die Policy den Übergang weiterhin zurückhält. |
| Regelbasierte Referenzen | Eingefrorener Ausgangspunkt, einfacher Timeout und späte Bereitschaft als drei Auswertungsreferenzen. |

Beide Lernarme erhalten dieselbe Quote normaler Übergänge. Diese umfasst
reguläre Abschlüsse und Zustände, an denen der Experte zurecht noch wartet.
Das Abfragebudget zählt tatsächliche Auskünfte über den Phasenabschluss,
einschließlich angefragter, später verworfener Labels. Der Stichprobenplan
gleicht die Anzahl vertretener Szenenfamilien, Labelbudget, Batchgröße und
Updates an. Die Auswahl kennt die Expertenantwort vor der Anfrage nicht.
Gemeinsam genutzte Labels werden bei jedem Arm transparent als Teil seines
Abfragebudgets gezählt. Phasen, die eine Episode verfehlt, und erfolglose
Erhebungen werden mitgezählt. Zeit und Simulationsschritte werden separat
berichtet.

Die Expertin oder der Experte entscheidet für jeden Zustand, ob
der Roboter das Absenken beenden und den Greifer schließen soll.
Der Auswahlindikator allein vergibt kein Trainingslabel. Vor
Trainingsstart wird auf Kalibrierungsfamilien geprüft, ob die vorhandene
Expertenregel die Frage auch in Lernerzuständen konsistent beantwortet.

## Training und Bewertung

Für den Primärvergleich haben beide Arme dieselben Startgewichte je Paar,
denselben Beobachtungsvektor und dieselbe Modellarchitektur. Die Aktion
wird aus dem ursprünglichen Modell übernommen. Eine separate Kopie
liefert die gelernte Abschlussentscheidung ausschließlich beim ersten
Absenken. So bleibt der Vergleich auf den Abschlusskopf und die
Datenauswahl begrenzt. Der Rückzug bleibt ein eigener Eingriff.

Die normale Verteilung und die Verteilung kritischer Situationen werden
vorab beschrieben. Messbare Merkmale sind der Abstand zwischen Greifer
und Quellwürfel zum Start, dessen Position im Arbeitsraum und die
geplante erste Transportstrecke. Ihre Beziehung zu Griffstillständen
wird auf gesonderten Kalibrierungsfamilien geprüft. Falls die Merkmale
unzureichend trennen, wird der kritische Paneltyp über einen vorher
festgelegten und vom Trainingsvergleich unabhängigen Referenzlauf
definiert. Dann gilt das Ergebnis für diese bedingte Stichprobe.
Alle bereits gesehenen Familien, einschließlich der 96 Sichtungsszenen,
bleiben aus dem Blindtest ausgeschlossen.

Ganze Szenenfamilien werden vorab vollständig den Rollen Training,
Validierung und Blindtest zugeordnet. Die Liste der unabhängigen
Trainingsinitialisierungen wird vorab für alle Arme gepaart festgelegt.
Die Zahl der Trainingsseeds liegt über drei. Sie wird für einen
praktisch relevanten Gewinn, etwa fünf Prozentpunkte, anhand der
Streuung gepaarter Unterschiede und der verfügbaren Rechenzeit geplant.
Die Streuung der drei geerbten Modelllinien aus der aktuellen
Diagnose wird nicht als verlässliche Schätzung der Trainingsstreuung
verwendet. Das tatsächliche Budget und die Seedzahl werden im
Lernprotokoll vor der ersten Auswertung fixiert.

Primär zählt der Dreierturm über 50 gültige Frames im vollen Nenner
des normalen Blindtestpanels. Der kritische Blindtest, Griffphase
verlassen, Auslösung, gewonnene und verlorene Aufgaben sowie Aufwand pro
Erfolg sind ergänzende Ergebnisse. Für gepaarte Unterschiede werden
Szenenfamilien und Trainingslinien als getrennte Quellen der Streuung
behandelt. Die finale Auswertung erfolgt mit eingefrorener Checkpoint-
und Auswahlregel.
