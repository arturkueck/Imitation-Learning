# Übungen ohne Unterlagen

Nimm Papier oder eine leere Textdatei. Rechne zuerst selbst. Wenn du festhängst, nutze nur den Hinweis, nicht sofort die Lösung. Die acht Kernfragen reichen für die erste Sitzung.

## 1 · Einen BC-Loss lesen

Expertaktionen: `(1,−1)`. Modellaktionen: `(0.8,−0.5)`. Berechne (a) Summe der quadrierten Komponentenfehler, (b) mittleren Komponenten-MSE, (c) L1-Summe. Erkläre, weshalb ein niedriger Wert noch keinen erfolgreichen Rollout beweist.

Hinweis: Erst Differenz bilden, dann quadrieren; b teilt durch zwei.

## 2 · Fehler weitertragen

`e_{t+1}=0.5e_t+0.1`, `e₀=0`. Berechne e₁,e₂,e₃ und den Grenzwert. Was ändert sich, wenn b=0 ist? Ist dies das DAgger-T²-Theorem?

Hinweis: Beim Grenzwert gilt `e=0.5e+0.1`.

## 3 · DAgger in drei Sätzen

Die Lernpolicy besucht einen neuen Greiferzustand. Beschreibe getrennt: Wer hat den Zustand erzeugt? Wer liefert das Label? Was passiert mit alten Daten? Bei β=0.2: Wie oft wird der Expert im Erwartungswert bei 100 Befehlen ausgeführt, und wie viele Labelanfragen sind trotzdem möglich?

Hinweis: Ausführen und annotieren sind verschieden.

## 4 · DART-Labels

In einem Zustand x=0.5 liefert der Expert u*=−0.5. Die Störung ist +0.2. Welcher Befehl wird ausgeführt, welches Label gespeichert? Im erreichten Folgezustand x'=0.47: Darf einfach das alte Label behalten werden? Vergleiche mit nachträglichem State-Jitter.

Hinweis: Das neue Label gehört zum neuen Zustand; die Labelregel muss dort neu ausgewertet werden.

## 5 · Matrix und Stabilität

`A=[[-1,2],[1,−1]]`. Schreibe die zwei skalaren Fehlergleichungen. Berechne die Eigenwerte über `(-1−λ)²−2=0`. Entferne nur A_xy: Welche Matrix entsteht, und welche Eigenwerte hat sie?

Hinweis: A_xy ist Zeile x, Spalte y.

## 6 · Produkt und Soft-Loss

(a) Für `ẋ=−x+2xy`, `ẏ=−y`: Berechne den Jacobian am Ursprung und die x-Rate am Punkt (0.25,1). Widersprechen sich die zwei Aussagen?

(b) BC-Loss 0.2, Stabilitätsgewicht 3, Eigenwertrealteile −1 und +0.1. Berechne den Stable-BC-Lehrloss. Was ist bei Realteilen −1 und 0? Ist null Strafe dann gleich strikte Stabilität?

Hinweis: Ableitungen des Produkts sind `∂xy/∂x=y`, `∂xy/∂y=x`. ReLU nimmt nur positive Werte mit.

## 7 · ACT und Zeitindizes

Zwei Pläne sagen für denselben Zeitpunkt Aktionen 0.4 und 0.8 voraus; Gewichte 1 und 0.5. Welche Aktion ergibt sich? Was ist der Unterschied zwischen Chunklänge 16 und Ausführung von zwei Aktionen? Weshalb kann der ACT-Trainingsencoder beim Einsatz nicht einfach denselben demonstrierten Chunk erhalten?

Hinweis: Gewichte normieren; der Testchunk soll erst erzeugt werden.

## 8 · Diffusion und zwei Modi

(a) A⁰=0.5, ᾱ=0.36, ε=1. Berechne Aᵏ mit der Standard-DDPM-Hilfsformel.

(b) Warum wird ε und nicht A⁰ als Noise-Lernziel verwendet? Werden alle Denoisingzwischenwerte am Roboter ausgeführt?

(c) Bei gleich häufigen Aktionen −1/+1: Welcher deterministische Wert minimiert erwartete MSE? Kann er aufgabenuntauglich sein?

Hinweis: √0.36=0.6, √0.64=0.8.

## Vertiefung 9 · Kovarianzbudget

Σ̂=`[[0.04,0.01],[0.01,0.09]]`, T=20, α=2. Berechne Spur, Skalierungsfaktor, neue Matrix und T trΣ. Was passiert mit typischen linearen Ausschlägen, wenn α auf 4 steigt?

## Vertiefung 10 · Bounded Disturbance

`ė_x=−2e_x+0.5e_y`, `|e_y|≤0.1`, `e_x(0)=0`. Leite einen Bound für `|e_x(t)|` ab. Welcher langfristige Wert bleibt? Warum ist das kein Beweis einer richtigen Aufgabenlösung?

## Vertiefung 11 · Evaluation richtig lesen

Eine Taskrate steigt von 0.4 auf 0.6. Berechne Prozentpunkte und relative Verbesserung. Drei trainierte Modelle werden je 40-mal getestet: Wie viele Trainingsreplikate sind es? Warum sollten letztes Checkpoint und bestes Checkpoint nicht als identische Messwerte behandelt werden?

## Vertiefung 12 · Das Modell in eigenen Worten erklären

Erkläre jeder Methode mit genau vier Sätzen: Problem, Eingriff, zusätzlich benötigte Information, Grenze. Nutze ein Greiferbeispiel und möglichst wenige Fachwörter. Die richtige Erklärung ist wichtiger als ein auswendig gelernter Algorithmusname.

Bewerte dich ohne Note: „kann ich erklären“, „kann ich nur mit Hinweis“ oder „noch unklar“. Für „noch unklar“ ein neues eigenes Zahlenbeispiel bilden. [Lösungen](07_loesungen.md) erst danach öffnen.
