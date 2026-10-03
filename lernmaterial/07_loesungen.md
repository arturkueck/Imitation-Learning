# Lösungen und typische Denkfehler

Diese Rechnungen gehören zu den eigenen Lernbeispielen. Bei einer falschen Antwort zuerst den Unterschied zur eigenen Rechnung benennen, anschließend ohne Vorlage nochmals lösen.

## 1

Differenz `(−0.2,0.5)`; Quadratssumme `0.04+0.25=0.29`; mittlere Komponenten-MSE `0.145`; L1-Summe `0.7`. Offline werden bereitgestellte Eingaben geprüft. Eigene Aktionen können später andere Eingaben erzeugen. **Denkfehler:** Norm und quadrierte Norm oder Summe und Mittel verwechseln.

## 2

e₁=0.1,e₂=0.15,e₃=0.175; Grenzwert 0.2. Bei b=0 und diesem Start bleibt alles null; ein anderer Startfehler würde geometrisch abklingen. Es ist eine skalare Rekurrenz, kein DAgger-Theorem. **Denkfehler:** „q<1, also geht bei dauerhafter Störung alles auf null“.

## 3

Der Learner bzw. die gewählte Erhebungspolicy erzeugt den Zustand. Der Expert liefert die beabsichtigte Aktion an diesem Zustand. Alte und neue Paare werden aggregiert und gemeinsam zum Trainieren verwendet. β=0.2 bedeutet erwartete 20 Expert-Ausführungen; trotzdem sind 100 Expertlabelanfragen möglich. **Denkfehler:** Nur ausgeführte Expertbefehle könnten Labels sein.

## 4

Ausführung `−0.5+0.2=−0.3`; Label zu x=0.5 bleibt −0.5. Bei x'=0.47 wird der Expert neu gefragt. Wenn seine Regel u*=−x ist, lautet das neue Label −0.47; ohne bekannte Regel darf man es nicht erfinden. State-Jitter mit unverändertem altem Label enthält keine neu beobachtete Expertkorrektur. **Denkfehler:** Noise zum Ziel machen.

## 5

`ė_x=−e_x+2e_y`, `ė_y=e_x−e_y`. Eigenwerte `−1±√2≈0.414,−2.414`. Ohne A_xy: `[[-1,0],[1,−1]]`, beide Eigenwerte −1. Es gibt weiterhin x→y-Kopplung. **Denkfehler:** Nebendiagonale als x·y-Produkt lesen oder beide Richtungen zugleich entfernen.

## 6

(a) Jacobian=`[[-1+2y,2x],[0,−1]]`; am Ursprung −I. Bei (0.25,1) ist `ẋ=0.25`. Kein Widerspruch: lokale Aussage am Ursprung versus momentane Rate an einem anderen Punkt. In diesem speziellen Modell fällt y ab und anschließend x. Daraus folgt keine allgemeine globale Stable-BC-Garantie.

(b) `0.2+3(0+0.1)=0.5`. Bei −1 und 0 beträgt die Strafe null und der Loss 0.2. Strikte Hurwitz-Stabilität verlangt Realteile kleiner als null. **Denkfehler:** ReLU-null mit strikt-negativ verwechseln.

## 7

`(0.4+0.5·0.8)/1.5≈0.533`. Beide Vorhersagen gehören zum gleichen Zeitpunkt. Ein 16er-Chunk ist die Vorhersageform; zwei ausgeführte Aktionen sind der Feedbackabstand. Der ACT-Encoder braucht beim Training den demonstrierten Chunk; dieser ist bei der späteren autonomen Vorhersage unbekannt. Im Originaltest wird z=0 verwendet. **Denkfehler:** Vergangene Aktionen mit zukünftigen Aktionen mitteln oder z=0 für eine zufällige Normalziehung halten.

## 8

(a) `Aᵏ=0.6·0.5+0.8·1=1.1`. Ein verrauschter Zwischenwert kann außerhalb des normierten Aktionsbereichs liegen.

(b) Das gewählte Training lernt das bekannte injizierte Noise. Daraus kann der Scheduler eine saubere Aktionsfolge rekonstruieren. Denoisingzwischenwerte sind Rechenzustände; nur fertige ausgewählte Aktionen werden ausgeführt.

(c) Der optimale deterministische Wert ist 0. Erwartete MSE bei 0 ist 1, bei ständig +1 ist sie 2. Wenn links/rechts sichere Wege sind und die Mitte blockiert ist, kann 0 trotzdem unbrauchbar sein. **Denkfehler:** Minimaler Aktionsloss müsse minimalen Taskfehler bedeuten.

## 9

Spur=0.13; Faktor `2/(20·0.13)=10/13≈0.76923`. Neue Matrix etwa `[[0.030769,0.007692],[0.007692,0.069231]]`; neue Spur=0.1; `20·0.1=2`. Bei α=4 verdoppeln sich Varianzen; Standardabweichungen steigen um √2. **Denkfehler:** Varianz und typische lineare Größe gleichermaßen verdoppeln.

## 10

Aus dem Integral ergibt sich `|e_x(t)|≤0.025(1−e^{-2t})`. Grenzwert 0.025. Es ist eine Fehlergrenze mit vorgegebenen Annahmen, keine Aussage, ob die Referenz die richtige Aufgabe löst oder ein Kontakt stabil bleibt.

## 11

0.4→0.6: +20 Prozentpunkte, `(0.6−0.4)/0.4=50 %` relativ. Drei Trainingsreplikate, 120 Testrollouts; gemeinsame Starts sind keine zusätzlichen Trainingsmodelle. Best-Checkpoint-Auswahl nutzt andere Information als ein festes letztes Checkpoint und kann andere Zahlen liefern. **Denkfehler:** Alle Rollouts als unabhängige trainierte Modelle zählen.

## 12 · Eine mögliche Kurzfassung

**BC:** Es fehlen passende Aktionsregeln. Das Netz lernt Eingabe→Expertaktion auf Demos. Es braucht gute Labels und brauchbare Beobachtungen. Eigene Fehlzustände können fehlen.

**DAgger:** Der Learner besucht andere Zustände als der Expert. Dort werden neue Expertlabels gesammelt und mit alten Daten vereinigt. Man braucht Expertkompetenz auch an diesen Zuständen. Nicht jede neuronale Umsetzung erfüllt die Theorieannahmen.

**DART:** Nominale Demos zeigen kaum Korrekturen. Expertbefehle werden während der Erhebung gestört. Man braucht einen reagierenden Expert und eine geeignete Noiseverteilung. Zu starke Störung kann die Aufgabe oder die Demonstration beeinträchtigen.

**Stable-BC:** Kleine Fehler können wachsen. Ein Zusatzloss gestaltet die lokale Fehlerdynamik. Man braucht Dynamikannahmen und Ableitungen. Lokale Stabilität und Aufgabenlösung sind verschieden.

**ACT:** Einzelaktionen erfassen zeitliche Folge und Demovariation begrenzt. Transformer-CVAE und Ensembling modellieren Chunks. Man braucht passende Sequenzdaten und Zeitausrichtung. Lange alte Pläne können die Reaktion verzögern.

**Diffusion:** Mehrere sinnvolle Aktionsfolgen sollen dargestellt werden. Noise-Training und iterative Generierung modellieren ihre Verteilung. Man braucht passende Demos und Rechenzeit. Fehlende gute Verhaltensdaten werden nicht automatisch ersetzt.
