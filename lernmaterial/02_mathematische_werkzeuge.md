# Die Werkzeuge, bevor du Paper-Gleichungen liest

Du musst zunächst weder Matrixanalyse noch Wahrscheinlichkeitstheorie beherrschen. Ziel ist: Du kannst sagen, was eine Formel hineinbekommt, was sie ausgibt und was sich verändert. Alle Zahlenbeispiele hier sind eigene Lernbeispiele.

## 1. Eine Formel wie einen Satz lesen

\[
L(\theta)=\frac1N\sum_{i=1}^{N}\|\pi_\theta(o_i)-a_i^*\|^2.
\]

Lies: „Für jedes der N Beispiele berechne ich die Differenz zwischen Modellaktion und Expertaktion, quadriere ihre Größe und bilde den Durchschnitt.“

| Zeichen | Übersetzung |
|---|---|
| `=` | linke und rechte Seite sind gleich definiert |
| `≈` | Näherung, keine exakte Gleichheit |
| `≤` | obere Schranke; der tatsächliche Wert darf kleiner sein |
| `Σ` als Summenzeichen | addiere die folgenden Terme |
| Index `i` | welches Trainingsbeispiel? |
| Index `t` | welcher Zeitpunkt im Ablauf? |
| `*` | hier Expert bzw. Referenz; nicht Multiplikation |
| `θ` | alle trainierbaren Modellparameter zusammen |
| `π_θ` | Policy mit diesen Parametern |
| `arg min_θ L` | der Parameterwert, bei dem L möglichst klein wird |
| `min_θ L` | der kleinste Losswert selbst |

Beispiel `L(θ)=(θ−2)²`: `arg min L=2`, aber `min L=0`. Parameter und Loss sind unterschiedliche Dinge.

## 2. Vektoren, Normen und Formen

Eine Aktion kann mehrere Komponenten haben: `a=(0.2,−0.1)` bedeutet hier zwei abstrakte Steuergrößen. Die euklidische Norm ist

\[
\|a\|_2=\sqrt{0.2^2+(-0.1)^2}=\sqrt{0.05}\approx0.224.
\]

Für die Expertaktion `(0.1,0.1)` ist die Differenz `(0.1,−0.2)` und die **quadrierte** Norm `0.05`. Das ist nicht `0.224`. L1 addiert Beträge: `|0.1|+|−0.2|=0.3`. L1 und L2-MSE bestrafen große Fehler unterschiedlich.

Eine Aktionsfolge mit vier Zeitpunkten und zwei Komponenten hat Form `4×2`. Ein Batch aus acht solcher Folgen hat Form `8×4×2`. Ob ein Loss über Zeit und Komponenten summiert oder mittelt, verändert seinen Zahlenwert und die passende Regularisierungsstärke.

Beim Addieren müssen Größen dieselbe Bedeutung und Skala besitzen. Meter, Quaternionkomponenten und Greiferwerte einfach gleich zu gewichten ist eine Modellentscheidung. Bei Stable-BC beeinflusst eine Zustandsskalierung auch die Ableitungen und Matrixnormen.

## 3. Ableitungen: Wie empfindlich reagiert etwas?

Für `u(x)=−2x` sagt die Ableitung `du/dx=−2`: Ein kleines zusätzliches `Δx=0.01` ändert u um ungefähr `−0.02`. Der Wert der Aktion und die Empfindlichkeit sind verschieden.

Für zwei Eingaben `u(x,y)=−2x+0.5y` gilt

\[
\frac{\partial u}{\partial x}=-2,\qquad
\frac{\partial u}{\partial y}=0.5.
\]

Bei der ersten Ableitung wird y festgehalten, bei der zweiten x. „Partiell“ heißt: nur eine Eingaberichtung verändern. Ein **Jacobian** sammelt alle diese Empfindlichkeiten in einer Matrix. Zeile = Ausgabekomponente, Spalte = Eingabekomponente.

Die Kettenregel ist ein Weg durch zwei Funktionen. Wenn `ẋ=f(x,u)` und `u=π(x,y)`, führt eine Änderung in x sowohl direkt durch f als auch indirekt durch die Policy:

\[
\frac{\partial\dot x}{\partial x}=f_x+f_u\pi_x.
\]

Beispiel `f(x,u)=0.5x+2u`, `π(x,y)=−x+0.3y`: `f_x=0.5`, `f_u=2`, `π_x=−1`. Insgesamt `0.5+2(−1)=−1.5`. Der indirekte Weg kann die offene Dynamik stabilisieren. Genau dafür brauchst du diese Schreibweise bei Stable-BC.

## 4. Zeitentwicklung und Linearisierung

`ẋ` ist die zeitliche Änderungsrate von x, beispielsweise Meter pro Sekunde. `x_{t+1}` ist dagegen der Wert beim nächsten diskreten Schritt. Für ein kleines Zeitintervall Δt approximiert Euler:

\[
x_{t+1}\approx x_t+\Delta t\,\dot x_t.
\]

Bei `ẋ=−2x`, `x_0=1`, `Δt=0.1` folgt `x_1=0.8`; exakt wäre `e^{-0.2}≈0.819`. Eine zu große numerische Schrittweite kann sogar eine kontinuierlich stabile Gleichung numerisch instabil machen. Die Kopplungssimulation benutzt daher Runge-Kutta vierter Ordnung mit kleiner Schrittweite.

**Linearisierung** bedeutet: Eine nichtlineare Funktion wird nahe einer Referenz durch ihren Wert plus ihre lokalen Ableitungen ersetzt. Für `h(x)=x²` nahe x=2: `h(2+e)≈4+4e`. Der vernachlässigte Term ist `e²`. Bei e=0.01 ist er klein; bei e=3 nicht. Deshalb ist „lokal stabil“ keine Aussage über beliebig weit entfernte Zustände.

## 5. Matrizen und Eigenwerte

\[
\dot z=Az,\quad z=\begin{bmatrix}e_x\\e_y\end{bmatrix},\quad
A=\begin{bmatrix}-1&c\\d&-1\end{bmatrix}.
\]

Ausmultiplizieren ergibt `ė_x=−e_x+c e_y`, `ė_y=d e_x−e_y`. Die Diagonale beschreibt Eigenreaktion; die Nebendiagonale beschreibt Kopplung. Bei `c=d=0` klingen beide Fehler unabhängig ab. Bei `c=2,d=1` kann die gegenseitige Rückwirkung einen Fehler verstärken.

Ein **Eigenvektor** ist eine Richtung, die A nur skaliert: `Av=λv`. λ ist der zugehörige **Eigenwert**. Entlang dieses Modus entwickelt sich das kontinuierliche lineare System wie `e^{λt}`. Negative Realteile: Abklingen; positive: Wachstum; null: aus dieser Prüfung keine strikte asymptotische Stabilität. Für ein diskretes System `z_{t+1}=Bz_t` gilt stattdessen `|λ(B)|<1`.

`e^{At}` ist die **Matrixexponentialfunktion**, nicht das elementweise Exponenzieren aller Einträge. Stabile Eigenwerte garantieren bei allgemeinen Matrizen keine in jedem Moment sinkende euklidische Fehlernorm. Eine Kopplung kann zunächst Energie in eine andere Komponente verlagern. Labor 3 hat dafür das Beispiel c=4,d=0.

## 6. Wahrscheinlichkeit, Erwartungswert und KL

`p(a|o)` bedeutet: Verteilung der Aktionen, **gegeben** eine Beobachtung. Eine Verteilung kann zwei Gipfel haben: links oder rechts an einem Hindernis vorbei. Der Mittelwert null kann genau gegen das Hindernis zeigen.

`E[X]` ist ein gewichteter Durchschnitt. Wenn X mit Wahrscheinlichkeit 0.25 gleich 0 und mit 0.75 gleich 2 ist, dann `E[X]=1.5`. `s∼d_π` heißt: s wird gemäß der durch π erzeugten Zustandsverteilung betrachtet. Das ist beim BC/DAgger-Vergleich entscheidend.

`N(μ,Σ)` ist eine Gaußverteilung: μ beschreibt die Lage, Σ Varianzen und gemeinsame Schwankungen. In einer Dimension gilt Varianz `σ²`; Standardabweichung ist `σ`. Eine Standardnormalverteilung hat Mittelwert 0 und Varianz 1. Ein zufälliger Wert ist nicht immer null, nur weil der Mittelwert null ist.

\[
D_{KL}(p\Vert q)=\mathbb E_{a\sim p}\log\frac{p(a)}{q(a)}.
\]

KL misst einen gerichteten Unterschied von Verteilungen. Beispiel p=(0.5,0.5), q=(0.75,0.25): KL=`0.5 ln(2/3)+0.5 ln 2≈0.144` mit natürlichem Logarithmus. Umgekehrt ergibt sich ein anderer Wert. KL ist keine symmetrische geometrische Distanz. Wenn q Ereignissen mit positiver p-Wahrscheinlichkeit Wahrscheinlichkeit null gibt, kann KL unendlich sein.

## 7. Gleiche Buchstaben, verschiedene Bedeutungen

| Symbol | Wo? | Bedeutung |
|---|---|---|
| `u` | Roboter-/Stable-BC-Gleichung | Aktion |
| `u` | DAgger-Theorem | Konstante für zusätzlichen zukünftigen Aufwand |
| `β` | DAgger | Wahrscheinlichkeit, Expertaktion auszuführen |
| `β` | ACT | Gewicht des KL-Losses |
| `λ` | Eigenwertrechnung | Eigenwert, eventuell komplex |
| `λ,λ₁,λ₂` | Stable-BC-Loss | nichtnegative Gewichte der Strafterme |
| `k` | ACT | Chunklänge |
| `k` | Diffusion | Rausch-/Denoisingindex |
| `Σ` | DART | Kovarianzmatrix; nicht das Summenzeichen `∑` |
| `ε` | DAgger | erwarteter Imitationsfehler unter bestimmter Verteilung |
| `ε` | Stable-BC | obere Schranke der Umgebungsabweichung |
| `ε,ε_θ` | Diffusion | Rauschen bzw. vorhergesagtes Rauschen |
| `z` | Stable-BC | zusammengefasster Fehlervektor |
| `z` | ACT | latente Variable für Demonstrationsvariation |

Vor jeder Rechnung: Bedeutung, Form und gegebenenfalls Einheit der Symbole festlegen. [Gleichungsatlas](04_gleichungsatlas.md) setzt diese Werkzeuge ein.
