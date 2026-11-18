# Erster Griff und Rückzug nach dem Öffnen

Vorabprotokoll für den 18.11.2026, 20:00 Uhr Europe/Berlin. Drei bereits
vorhandene, eingefrorene Targeted-Modelllinien. Null Lernupdates. Technische
Laufzeit höchstens 75 Minuten für den Hauptlauf, mit Auslaufreserve und einer
absoluten Obergrenze vor 20 Uhr. Laufabbrüche bleiben dokumentiert.

## Erster Griff

Vergleiche die Originalpolicy, einen Timeout nach 100 Phasenschritten und
eine späte Freigabe des Phasenwechsels ab 100 Schritten bei 20 aufeinander-
folgenden Frames innerhalb von 6 mm um das bisherige Greifziel. Geometrie
und Uhr verwenden dieselben Policymerkmale und Grenzen wie im letzten
Versuch zum zweiten Griff. Die Abschlussentscheidung der Originalpolicy
behält Vorrang. Die momentane Aktion kommt stets von der Originalpolicy.
Eingriffe gelten nur beim ersten Absenken zum Griff.

- Geöffnete Fälle aus dem Nachtlauf sind alle 22 Modell-/Szenenpaare, deren
  Kontrolle beim ersten Absenken endete, plus die ersten zwei erfolgreichen
  Familien je Modelllinie in numerischer Reihenfolge außerhalb sämtlicher
  erster Griff-Fehlerfamilien. Die 28 Paare sind Diagnoseanker.
- Das normale neue Panel umfasst die ganzen Familien 2026201000..2026201015
  mit allen drei Modelllinien. Seine Auswahl ist unabhängig von den Ergebnissen.
- Ein separates prozessbezogen kritisches Panel kommt aus einer festen Suche
  über 96 neue Familien 2026202000..2026202095. Ausschließlich die unveränderte
  erste Modelllinie entscheidet bei der Suche. Ein Fall ist kritisch, wenn
  er in Phase 1 der ersten Platzierung endet und im Ablauf mindestens einmal
  die Bedingungen der späten Korrektur erfüllt. Die ersten bis zu zwölf
  solcher Familien in aufsteigender Seedreihenfolge werden mit allen drei
  Modelllinien und drei Regeln verglichen. Alle 96 Suchergebnisse werden
  berichtet, einschließlich Ausbeute und nicht gewählter Fälle. Ein
  Referenzlauf allein liefert keine Aussage über den Anteil der Effekte
  unter zufällig gezogenen Szenen. Im kritischen Panel ist die erste
  Modelllinie zugleich die Selektionsreferenz. Die beiden anderen Linien
  werden separat berichtet. Seednummern dienen nur der Reproduzierbarkeit.

Wir erfassen messbare Anfangsmerkmale in Metern, darunter Ausgangsabstand
des Greifers zum ersten Quellwürfel, geplante erste XY-Transportstrecke und
radiale XY-Position des ersten Quellwürfels. Das kritische Label ist ein
reproduzierbares Ablaufkriterium für diese Diagnose. Eine allgemeine statische
Schwierigkeitsskala braucht eine eigene Kalibrierung.

## Zweite Freigabe

Auf sechs geöffneten Freigabeankern (alle drei Fehler und drei zugeordnete
Erfolgskontrollen aus der letzten Untersuchung) sowie allen normalen neuen
Familien vergleichen wir drei Arme. Die Originalpolicy gibt den Bezug.
Die beiden Eingriffsarme verwenden dieselbe bisherige Ablagebereitschaft,
dasselbe Ablageveto und dieselben ersten 20 Aktionen mit Objektfeedback
bei geöffnetem Greifer. Die Kontrolle danach hält die Position. Der neue
Arm hebt den geöffneten Greifer einmalig um 40 mm an und hält das neue Ziel,
sobald nach den ersten 20 Aktionen in drei aufeinanderfolgenden Frames
die bisherige Ablagebereitschaft gilt, der Würfel als ungegriffen gilt
und noch ein Finger Kontakt zum Quellwürfel hat. XY-Ziel ist die Position
beim Eingriff. Translationskommandos werden auf Betrag 0,3 je Achse begrenzt.
Die Regel nutzt Kontakt-/Posemessungen aus dem Simulator.

Bei Auslösung wird der Zustand genau vor dem Rückzug gegen die Haltekontrolle
gehasht. Beide Arme beginnen bis zu diesem Zeitpunkt mit identischer
Simulations- und Aktionshistorie. Ohne Auslösung müssen die gesamten Abläufe
dieser beiden Arme identisch sein. Die früheren Kontrollabläufe, einschließlich
Veto und Objektfeedback an den sechs Freigabeankern, werden reproduziert.

## Gemeinsame Kriterien

Primär zählt der vollständige Dreierturm mit 50 aufeinanderfolgenden strengen
Gültigkeitsframes bei maximal 1000 Frames. Berichtet werden gepaarte Gewinne
und Verluste, getrennt je Panel und Modelllinie. Beim Griff zählen zusätzlich
Exposition, tatsächliche Auslösung und Verlassen der ersten Griffphase.
Beim Rückzug zählen Auslösung, Fingerkontakt und XY-Lage bis zum Episodenende.
Fehler und nie erreichte Phasen bleiben im Nenner. Normales Panel, Suchbereich
und offene Anker bleiben Entwicklungsdaten und werden für einen späteren
Blindtest vollständig gesperrt. Es werden keine weiteren Familien nachgezogen.

Technischer Vorlauf sind ein bekannter erster Griffstillstand und der frühere
Parent-3-Freigabefehler mit je drei Armen. Hauptlauf: 96 Suchläufe und 342
fest eingeplante Vergleichsepisoden, plus neun pro ausgewählter kritischer
Familie bis höchstens 546 Episoden. Der bisherige Bestätigungstest bleibt als
bereits geöffnet gekennzeichnet.

## Vorbereiteter Lernvergleich

Die zweite Stufe ist ein gepaarter BC-Vergleich der Abfragestrategien. Sie setzt
eine messbare Exposition auf neuen kritischen Familien und einen reproduzierbaren
Falltyp voraus. Als Signal für die weitere Versuchsplanung prüfen wir
Rettungen in mindestens zwei neuen kritischen Familien und keine verlorenen
Aufgaben im normalen Panel. Auf demselben Strom von Zuständen der Greifphase fragt der eine
Arm nach einer festen Zufallsauswahl an. Der andere bevorzugt beobachtbare
Widersprüche zwischen geometrischer Bereitschaft und gelernter Abschlussentscheidung.
Beide nutzen dieselbe vorab definierte Quote normaler Übergänge, dieselben
Expertenlabels, gleich viele tatsächliche Anfragen, Familien und Updates sowie
gleiche Architektur und Eingaben. Protokolliert werden auch abgebrochene
Erhebungen und Simulationsaufwand. Die Regel wird zuerst auf Entwicklungsfamilien
festgelegt und danach für neue unabhängige Trainingslinien eingefroren.
Für einen Folgeversuch wird die größere Seedzahl anhand eines vorab gesetzten
relevanten Effekts und der Streuung gepaarter Parent-Differenzen begründet.
Ganze Familien bilden disjunkte Trainings-, Validierungs- und Blindtestpanels.
