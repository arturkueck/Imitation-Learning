# Gleichungsatlas mit Variablen und Zahlenbeispielen

Dieser Atlas erklärt die zentralen Gleichungen der fünf Literaturdossiers und notwendige Hilfsformeln. „Alle möglichen Gleichungen“ wäre unbegrenzt; hier ist der Umfang konkret: BC-Ziele, DAgger-Bounds und No-Regret, DART-Kovarianz/KL, Stable-BC-Jacobian/Loss/Bound, ACT-CVAE/Ensembling und Diffusionsziel/-inferenz/Score plus Evaluationsrechnung. Keine neuen Paperergebnisse. **Jedes Zahlenbeispiel ist selbst konstruiert.**

Ein Eintrag hat vier Schritte: Frage → Formel → Symbole → Rechnung und Grenze. Lies zuerst nur G1–G3, D1–D2, R1, S1–S4, A1/A3 und P1–P3. Die restlichen Einträge sind Vertiefung.

## G1 · Wie misst BC einen Aktionsfehler?

\[
L_{BC}(\theta)=\frac1N\sum_{i=1}^N\|\pi_\theta(o_i)-a_i^*\|_2^2.
\]

| Variable | Bedeutung und Form |
|---|---|
| `D={(o_i,a_i*)}` | Demonstrationsdatensatz |
| `N` | Zahl betrachteter Beispiele, etwa Batchgröße |
| `o_i` | Beobachtungsvektor oder Bild des Beispiels i |
| `a_i*` | Expertaktionsvektor; Stern bezeichnet Referenz |
| `π_θ(o_i)` | vorhergesagter Aktionsvektor gleicher Form |
| `θ` | alle lernbaren Gewichte |
| `||·||²` | Summe quadrierter Fehlerkomponenten |

**Rechnung:** Zwei skalare Expertaktionen 1 und −1, Ausgaben 0.8 und −0.6. Loss=`((−0.2)²+(0.4)²)/2=0.10`. Bei Summe statt Mittel wäre er 0.20. Ein Framework kann zusätzlich über Komponenten mitteln; die Konvention muss genannt werden.

**L1-Alternative:** Durchschnitt der absoluten Differenzen=`(0.2+0.4)/2=0.30`. Größere Fehler werden bei Quadraten relativ stärker betont. Quelle für BC-Grundziel: SBC-02, Preprint S. 2; für ACT-L1/MSE-Widerspruch: ACT-03, RSS S. 6. Diese Mittelwertnotation vereinheitlicht die Erklärung; die Dossiers erhalten die jeweilige Papierschreibweise.

## G2 · Wie lernt ein Parameter?

\[
\theta_{new}=\theta_{old}-\eta\nabla_\theta L.
\]

`η` ist die Lernrate, `∇_θL` der Gradient, also alle partiellen Ableitungen des Losses nach den Parametern. Diese Formel beschreibt einfachen Gradientenabstieg, nicht den vollständigen AdamW-Optimizer eures Projekts.

**Rechnung:** `L=(θ−2)²`, `θ=0`, `η=0.1`. Gradient=`2(θ−2)=−4`; neuer θ=`0−0.1(−4)=0.4`. Der Loss sinkt von 4 auf 2.56. Das Netz „weiß“ dabei nicht, was ein Würfel ist; es verändert Parameter, um den definierten Loss zu reduzieren.

## G3 · Warum kann ein Mittelwert falsch sein?

\[
\hat a(o)=\mathbb E[a^*\mid o]
\]

ist der optimale unbeschränkte deterministische MSE-Prädiktor, wenn der zweite Moment existiert. `E[·|o]` bedeutet bedingter Durchschnitt. **Rechnung:** Expertaktion −1 oder +1 mit je 50 %: Mittelwert 0; Loss des Mittelpunkts ist 1. Ständig +1 ergibt erwarteten Loss 2. MSE bevorzugt trotzdem 0, auch wenn 0 bei der Aufgabe gegen ein Hindernis fährt. Das ist ein mathematisches Lernbeispiel; kein Nachweis von Multimodalität eurer Stackdaten. Labor 5.

## D1 · Auf welcher Zustandsverteilung lerne ich?

\[
d_\pi=\frac1T\sum_{t=1}^T d_\pi^t,
\qquad
\hat\pi_{BC}=\arg\min_{\pi\in\Pi}\mathbb E_{s\sim d_{\pi^*}}\ell(s,\pi).
\]
\[
\hat\pi_{IL}=\arg\min_{\pi\in\Pi}\mathbb E_{s\sim d_\pi}\ell(s,\pi).
\]

`T` = Rollouthorizont; `d_π^t` = Verteilung des Zustands zum Zeitpunkt t bei Policy π; `Π` = erlaubte Modellfamilie; `ℓ` = Imitationsloss; `π*` = Expert. BC verwendet Expertzustände; das eigentliche Rolloutziel verwendet eigene Zustände. In der zweiten Formel hängt die Verteilung selbst von der optimierten Policy ab.

**Rechnung:** Expertzustände sind zu 90 % „mittig“ und 10 % „seitlich“. Der Loss ist dort 0.01 bzw. 0.5. Expertgewichteter Loss=`0.9·0.01+0.1·0.5=0.059`. Die Lernpolicy besucht beide Zustände zu je 50 %: eigener Loss=`0.5·0.01+0.5·0.5=0.255`. **Gleicher punktweiser Prädiktor, andere Häufigkeiten.** Quelle: DAG-01–02, PDF S. 2.

## D2 · Wie mischt und aggregiert DAgger?

\[
\pi_i=\beta_i\pi^*+(1-\beta_i)\hat\pi_i,
\qquad D\leftarrow D\cup\{(s,\pi^*(s))\}.
\]

`i` = Erhebungsrunde; `β_i∈[0,1]` = Expert-Ausführungswahrscheinlichkeit; `π̂_i` = aktuelle Lernpolicy. Das Plus beschreibt die **Mischpolicy**, keine Pflicht zur Aktionsmittelung. D wächst um Expertlabels an den erreichten Zuständen.

**Rechnung:** Bei β=0.25 werden im Erwartungswert 25 von 100 Befehlen vom Experten ausgeführt. Trotzdem kann für alle 100 erfassten Zustände ein Expertlabel angefragt werden. Quelle: DAG-05–06, PDF S. 4.

## D3 · Was bedeuten die Fehlerbounds?

\[
J(\pi)\le J(\pi^*)+T^2\epsilon,
\qquad J(\pi)\le J(\pi^*)+uT\epsilon.
\]

`J` = erwartete kumulative Taskkosten, nicht Aktions-MSE; `ε` = erwarteter geeigneter Imitationsfehler; `u` = obere Schranke zusätzlicher zukünftiger Kosten einer Fehlaktion bei anschließender Expertfortsetzung. **u ist hier keine Roboteraktion.** Erste Formel misst ε unter Expertzuständen, zweite unter eigener Verteilung. Kosten müssen passend beschränkt sein; das Surrogat muss die im Satz geforderte Fehlerbeziehung besitzen.

**Rechnung nur zum Lesen der Skalierung:** T=10, ε=0.01: Zusatzbound der ersten Formel 1. Bei T=100: 100. Für die zweite Formel mit u=2: 0.2 bzw. 2. Das sind Obergrenzen, keine simulierten tatsächlichen Kosten. Wenn u selbst mit T wächst, ist auch die zweite Aussage nicht universell linear. Für eure kontinuierliche MSE sind diese Zahlen ohne zusätzliche Herleitung nicht einsetzbar. Quelle: DAG-03–04, PDF S. 2–3; der erste Satz wird dort Ross/Bagnell 2010 zugeschrieben.

## D4 · Was heißt No-Regret?

\[
\frac1N\sum_{i=1}^N\ell_i(\pi_i)
-\min_{\pi\in\Pi}\frac1N\sum_{i=1}^N\ell_i(\pi)
\le\gamma_N,\qquad\gamma_N\to0.
\]

`N` = Anzahl Erhebungs-/Online-Lernrunden, nicht der BC-Batch von G1; `ℓ_i` = Loss auf Zustandsverteilung der Runde i; `γ_N` = mittlerer Regretbound. Verglichen wird die Folge eingesetzter Policies mit **einer festen Policy**, die rückblickend auf allen Runden gut wäre.

**Rechnung:** Rundverluste der benutzten Policies 0.4 und 0.2 ergeben 0.3. Der beste feste Kandidat hätte 0.25. Mittlerer Regret 0.05. Ein sinkender Trainingsloss allein beweist nicht diese Bedingung.

DAggers idealisiertes Ergebnis enthält außerdem

\[
\exists\hat\pi:\quad \mathbb E_{d_{\hat\pi}}\ell\le\epsilon_N+O(1/T),
\qquad \epsilon_N=\min_{\pi\in\Pi}\frac1N\sum_i\mathbb E_{d_{\pi_i}}\ell(s,\pi).
\]

`∃` heißt „es existiert ein Kandidat“, nicht „der letzte Kandidat ist garantiert gut“. `O(1/T)` beschreibt eine asymptotische Größenordnung, keine exakt bekannte Zahl 1/T. Starke Konvexität, beschränkter Loss, Mischung und Stichprobenannahmen gehören dazu. Quelle: DAG-07/10, PDF S. 4–6.

## R1 · Wie sieht gestörte Expertenausführung aus?

\[
u_t^{exec}=u_t^*+\eta_t,\quad\eta_t\sim\mathcal N(0,\Sigma),
\quad\theta_R=\arg\min_\theta\mathbb E_{\xi\sim p(\cdot|\pi^*,\psi)}J(\theta,\theta^*|\xi).
\]

Die erste Gleichung ist eine erklärende Gauß-DART-Schreibweise. `u*` = beabsichtigte Expertaktion, `η_t` = Aktionsstörung, `Σ` = Kovarianz, `ξ` = vollständige Trajektorie, `ψ` = Noiseparameter. DARTs `J` ist die Summe der **Aktionssurrogatverluste**, nicht automatisch das Taskkosten-J aus DAgger. Das Label bleibt u*. Quelle: DART-02/04, PDF S. 4–6.

**Kovarianzrechnung:** Zwei Aktionsabweichungen `δ₁=(0.2,0.1)`, `δ₂=(−0.2,−0.1)` ergeben beide das äußere Produkt

\[
\delta\delta^\top=\begin{bmatrix}0.04&0.02\\0.02&0.01\end{bmatrix}.
\]

Das ist eine 2×2-Matrix, kein Skalar. Positive Nebendiagonalen sagen: beide Komponenten schwanken gemeinsam. Diese Beispielmatrix ist rangdefizient; Rauschen fehlt in einer Richtung. Labor 6 verwendet bewusst reguläre Kovarianzen mit |ρ|<1.

## R2 · Wie werden Richtung und Stärke des DART-Rauschens gewählt?

\[
\hat\Sigma=\frac1T\mathbb E\sum_t\delta_t\delta_t^\top,
\quad\delta_t=\pi_{\hat\theta}(x_t)-\pi_{\theta^*}(x_t),
\quad\Sigma^\alpha=\frac{\alpha}{T\operatorname{tr}(\hat\Sigma)}\hat\Sigma.
\]

`δ_t` = Learner/Expert-Differenz am selben Zustand; `tr` = Summe der Diagonaleinträge; `α` = angenommener kumulativer quadratischer Aktionsfehler. Es wird die Richtung der geschätzten Streuung behalten und die Gesamtstärke angepasst. `E` mittelt über Erhebungstrajektorien. Der zweite Moment enthält auch systematische Abweichung; es ist hier nicht einfach eine Mittelwert-abgezogene Statistik von δ.

**Rechnung:** Matrix aus R1 hat Spur 0.05. Bei T=10 und α=1: Skalierungsfaktor `1/(10·0.05)=2`, neue Spur 0.1, erwarteter Gesamtrauschfehler `T trΣ=1`. Ist die Spur null, ist die Skalierung nicht definiert.

Die Noiseoptimierung lautet im Paper außerdem

\[
\hat\psi_{k+1}=\arg\min_\psi\mathbb E_{\xi\sim p(\cdot|\pi^*,\psi_k)}
\left[-\sum_{t=0}^{T-1}\log\pi^*(\pi_{\hat\theta}(x_t)|x_t,\psi)\right].
\]

Hier ist `k` Erhebungsrunde. Die verrauschte Expertverteilung soll Learneraktionen plausibel machen. Negative Log-Wahrscheinlichkeit ist klein bei hoher Wahrscheinlichkeit: p=0.8 gibt `−ln p≈0.223`, p=0.2 gibt etwa 1.609. Bei kontinuierlichen Aktionen sind es Dichten statt diskreter Wahrscheinlichkeiten. Quelle: DART-04, PDF S. 5/12–13.

## R3 · Was sagt der KL-Bound über Verteilungsunterschiede?

\[
|\mathbb E_qJ-\mathbb E_pJ|\le T\sqrt{\tfrac12D_{KL}(p\Vert q)}.
\]

`p` = Trajektorienverteilung des Learners, `q` = gestörte Experttrajektorien; `J` = Summe von T punktweisen Losses in [0,1]. Die Formel begrenzt die Differenz zweier erwarteter Losses, nicht direkt Taskerfolg.

**Rechnung:** T=10, KL=0.02 → Grenze `10√0.01=1`. Bei null KL ist die Differenz null. Ein endlicher KL-Wert benötigt passenden Support; ein deterministischer Expert kann Trajektorien nicht abdecken, die der Learner besucht. Quelle: DART-03/05, PDF S. 5–6/10–11.

## S1 · Welche Dynamik wird bei Stable-BC betrachtet?

\[
\dot x=f(x,u),\quad\dot y=g(x,y,u),\quad u=\pi_\theta(x,y),
\quad e_x=x'-x,\quad e_y=y'-y.
\]

`x∈Rⁿ` = Roboterzustand, `y∈Rᵐ` = Umgebung, `u∈Rᵖ` = Aktion; `f∈Rⁿ`, `g∈Rᵐ` = Änderungsraten. Der Strich bezeichnet die gestörte Vergleichstrajektorie, **keine Ableitung**; die Punkte sind Ableitungen nach Zeit. Die Referenz kann selbst in Bewegung sein. x und y sind Vektoren und nicht notwendig räumliche X-/Y-Achsen.

**Rechnung:** Referenzgreifer 0.50 m, gestörter Greifer 0.52 m: `e_x=0.02 m`. Referenzobjekt 0.80 m, verschobenes Objekt 0.79 m: `e_y=−0.01 m`. Quelle: SBC-02–03, **Preprint v1**, S. 2–3.

## S2 · Woher kommt die x/y-Kopplungsmatrix?

\[
\dot z=Az,\quad z=\begin{bmatrix}e_x\\e_y\end{bmatrix},\quad
A=\begin{bmatrix}
f_x+f_u\pi_x&f_u\pi_y\\g_x+g_u\pi_x&g_y+g_u\pi_y
\end{bmatrix}.
\]

`f_x=∂f/∂x` hat Form n×n; `f_u` n×p; `π_x` p×n; `π_y` p×m. Deshalb ist `f_uπ_y` n×m: Umgebungsfehler wird in eine Roboterfehlerrate übersetzt. `g_x` m×n, `g_y` m×m, `g_u` m×p. A ist insgesamt (n+m)×(n+m). Die Kettenregel erklärt die Produkte.

**Rechnung:** `f=u`, `π=−x+2y`, `g=x−y` im skalaren Lernmodell:

\[
A=\begin{bmatrix}-1&2\\1&-1\end{bmatrix}.
\]

`f_x=0,f_u=1,π_x=−1,π_y=2,g_x=1,g_y=−1,g_u=0`. Jede Matrixzahl lässt sich damit einzeln rekonstruieren. In dieser linearen Simulation ist A exakt; im Paper entsteht sie durch lokale Linearisierung. Quelle: SBC-03, Preprint S. 3.

## S3 · Mit Kopplung und ohne Kopplung

Für `A=[[-1,c],[d,−1]]` gilt

\[
\det(A-\lambda I)=(-1-\lambda)^2-cd=0,
\quad \lambda_\pm=-1\pm\sqrt{cd}.
\]

`I` = Einheitsmatrix, `det` = Determinante; `λ±` = beide Eigenwerte. Bei negativem cd ist die Wurzel komplex, beide Realteile sind −1.

**Rechnung:** c=2,d=1 → `λ≈0.414,−2.414`, ein Modus wächst. **Ohne y→x-Kopplung:** c=0, d bleibt 1 → beide Eigenwerte −1. Es kann weiterhin x→y-Kopplung geben. **Ohne jede gegenseitige Kopplung:** zusätzlich d=0.

**Ein echtes Produkt:** `ẋ=−x+cxy`, `ẏ=−y` hat

\[
J(x,y)=\begin{bmatrix}-1+cy&cx\\0&-1\end{bmatrix}.
\]

Am Ursprung ist J für jedes c gleich −I, obwohl der Produktterm an anderen Orten wirkt. Bei c=2,y=1 ist die momentane x-Rate `ẋ=x` positiv; später sinkt y und x klingt ab. Für Startwerte x₀,y₀ gilt exakt `y(t)=y₀e^{-t}`, `x(t)=x₀ exp(−t+c y₀(1−e^{-t}))`. Diese Zusatzformeln sind eigene Lehrmodelle, keine Stable-BC-Papergleichungen. Labor 3.

## S4 · Was genau bestraft Stable-BC?

\[
L=L_{BC}+\lambda\sum_{\sigma\in eig(A)}\operatorname{ReLU}(\operatorname{Re}\sigma).
\]

`eig(A)` = Menge der Eigenwerte; `σ` = einzelner Eigenwert, um ihn von Lossgewicht λ zu unterscheiden; `Reσ` = Realteil; `ReLU(v)=max(0,v)`; λ = nichtnegatives Gewicht.

**Rechnung:** Eigenwerte 0.414 und −2.414, BC-Loss 0.10, λ=2 → Gesamtverlust `0.10+2·0.414≈0.928`. Bei Eigenwerten 0 und −2 ist die Strafe null, obwohl strikte Hurwitz-Stabilität nicht erfüllt ist. Ein stabiler Roboter, der am Start bleibt, kann zudem die Aufgabe verfehlen: deshalb bleibt BC im Loss. Quelle: SBC-04/10, Preprint S. 4.

## S5 · Unbekannte Umgebung: A₁, A₂ und ein Fehlerbound

\[
\dot e_x=A_1e_x+A_2e_y,\quad\|e_y\|\le\epsilon,
\quad A_1=f_x+f_u\pi_x,\quad A_2=f_u\pi_y.
\]

A₁ ist der n×n-Roboterblock, A₂ der n×m-Kopplungsblock. Die Roboterdynamik f bleibt bekannt. Unbekanntes g bedeutet, dass die gesamte Matrix nicht geprüft werden kann.

\[
\|e_x(t)\|\le\|e^{A_1t}e_x(0)\|
+\|A_2\|\epsilon\int_0^t\|e^{A_1(t-\tau)}\|d\tau.
\]

`τ` = Integrationszeit; `e^{A₁t}` = Übergangsoperator des linearen Systems. Der erste Term ist eigener Startfehler, der zweite der über die Zeit eingetragene Umgebungseinfluss. Matrixnorm und Vektornorm müssen kompatibel sein.

**Skalares Zahlenbeispiel:** A₁=−2,A₂=0.5, ε=0.1,e_x(0)=0.2. Dann

\[
|e_x(t)|\le0.2e^{-2t}+0.025(1-e^{-2t}).
\]

Bei t=1: etwa `0.0271+0.0216=0.0487`. Langfristig bleibt die obere Grenze 0.025. Stable Roboterdynamik plus begrenzte Störung bedeutet hier nicht fehlerfreie Übereinstimmung.

Der Preprint gibt zusätzlich eine gröbere Normschranke mit `exp(||A₁||t)−1` an (Gl. 10, S. 4). Aus `||e^{A₁t}||≤e^{||A₁||t}` folgt für `||A₁||>0` ein Integralbound `(e^{||A₁||t}−1)/||A₁||`; bei null Norm t. Diese Schranke wächst und ist nicht allein ein zeituniformer Stabilitätsbeweis. Im Beispiel mit ||A₁||=2 wächst sie trotz stabiler echter Dynamik. Der Preprint hat außerdem einen ungeklärten Ableitungsindex bei A₁; hier verwenden wir die mit seiner Blockmatrix konsistente Form. Quelle: SBC-05, Preprint S. 4–5; SBC-G2–G4.

## S6 · Der Loss bei unbekanntem g

\[
L=L_{BC}+\lambda_1\|A_2\|+
\lambda_2\sum_{\sigma\in eig(A_1)}\operatorname{ReLU}(\operatorname{Re}\sigma).
\]

λ₁ gewichtet Umgebungsempfindlichkeit, λ₂ instabile Roboter-Eigenwerte. **Rechnung:** BC=0.1, ||A₂||=0.5, λ₁=0.2, λ₂=2, einziger Eigenwert A₁=−2 → `L=0.1+0.1+0=0.2`. A₂ auf null zu drücken könnte die Reaktion auf ein bewegtes Ziel verhindern. Stabilität und Aufgabeninformation müssen zusammenpassen. Quelle: SBC-06, Preprint S. 5.

## A1 · Was ist ein Chunk?

\[
A_t=(a_t,a_{t+1},\ldots,a_{t+k-1}),\qquad \hat A_t=\pi_\theta(o_t,z).
\]

Hier wird die Länge k eindeutig mit letztem Index t+k−1 geschrieben; das Paper verwendet auch die Kurznotation t:t+k. `k` = Zahl vorhergesagter Aktionen; bei Aktionsdimension p hat A Form k×p. `z` = ACT-Latent, nicht Stable-BC-Fehlervektor.

**Rechnung:** k=4,p=2 → acht Ausgabewerte. Vorhersagelänge 4 und Ausführungshorizont 1 sind vereinbar: nach einer Aktion wird neu beobachtet. Quelle: ACT-01–02, RSS S. 5–6.

## A2 · CVAE: Rekonstruktion plus passender Latentraum

\[
z\sim q_\phi(z|A_t,\bar o_t),\quad
L=L_{reconst}+\beta D_{KL}(q_\phi\Vert\mathcal N(0,I)).
\]

`φ` = Encoderparameter; `θ` = Decoderparameter; `ō` = propriozeptive Encoderbeobachtung ohne Bilder; der Decoder erhält vollständige Beobachtung; `β` = KL-Gewicht. Das q ist die aus dem demonstrierten Chunk geschätzte Latentverteilung. Der Normalprior soll auch ohne bekannten Testchunk nutzbar sein.

Eine erklärende Hilfsformel für diagonales Gaussian-q ist

\[
D_{KL}(\mathcal N(\mu,diag(\sigma_j^2))\Vert\mathcal N(0,I))
=\tfrac12\sum_j(\mu_j^2+\sigma_j^2-1-\log\sigma_j^2),
\quad z=\mu+\sigma\odot\epsilon,\quad\epsilon\sim\mathcal N(0,I).
\]

`j` = Latentkomponente; `⊙` = komponentenweise Multiplikation. Diese Standard-Gaußrechnung und Reparametrisierung erläutern das Verfahren; sie sind keine neu nummerierten ACT-Gleichungen.

**Rechnung:** eine Dimension μ=1,σ²=1 → KL=0.5. Rekonstruktionsloss=0.2,β=0.1 → Gesamt=0.25. μ=0,σ²=1 → KL=0. Bei Test-z=0 wird nicht die Expertfolge nachträglich encodiert. Quelle: ACT-03–04, RSS S. 6/16; Original nennt L1 im Text und MSE im Pseudocode.

## A3 · Temporales Ensembling

\[
a_t=\frac{\sum_{i=0}^{r-1}e^{-mi}\hat a_t^{(i)}}{\sum_{i=0}^{r-1}e^{-mi}}.
\]

`r` = Zahl verfügbarer Pläne für denselben t; `i=0` = ältester Plan in der Originalbeschreibung; `m≥0` = Gewichtsabfall. Alle Vorhersagen müssen denselben Zeitpunkt und Aktionsraum betreffen.

**Rechnung:** Vorhersagen 0.8,0.6; `m=ln2` → Gewichte 1,0.5; Ergebnis 0.733. m=0 → Gleichgewichtung 0.7. Große m bevorzugen hier den ältesten Plan, nicht den neuesten. Quelle: ACT-02, RSS S. 5–6; Labor 4.

## P1 · Vorwärtsrauschen und Noise-Lernziel

\[
A^k=\sqrt{\bar\alpha_k}A^0+\sqrt{1-\bar\alpha_k}\epsilon,
\qquad L=\mathbb E\|\epsilon-\epsilon_\theta(O_t,A^k,k)\|^2.
\]

`A⁰` = echter Aktionschunk; `Aᵏ` = verrauschter Chunk derselben Form; `ε∼N(0,I)` = injiziertes Rauschen; `ε_θ` = Noisevorhersage des Netzes; `O_t` = Beobachtungshistorie; `k` = Rauschlevel; `ᾱ_k∈(0,1]` = Signalanteil des Schedules. **Diese Standard-DDPM-Notation erklärt die Skalierung.** RSS Gl. (5) schreibt das Vorwärtsrauschen schematisch als `A⁰+εᵏ`; beide Schreibweisen werden nicht als identische Implementationsdetails ausgegeben.

**Rechnung:** Skalar A⁰=0.8, ᾱ=0.64, ε=−0.5 → `Aᵏ=0.8·0.8+0.6(−0.5)=0.34`. Noisevorhersage −0.4 → Noisequadratfehler 0.01. Ziel ist −0.5, nicht die echte Aktion 0.8. Quelle: DP-01, RSS S. 3.

## P2 · Eine Aktion rekonstruieren und iterativ denoisen

Aus P1 folgt als Lehrrechnung

\[
\hat A^0=\frac{A^k-\sqrt{1-\bar\alpha_k}\hat\epsilon}{\sqrt{\bar\alpha_k}}.
\]

Mit Aᵏ=0.34, ᾱ=0.64 und perfektem ε̂=−0.5 ergibt sich Â⁰=0.8. Bei ε̂=−0.4 ergibt sich 0.725. Diese Rekonstruktionsformel allein ist noch kein vollständiger Scheduler.

Die Originaldarstellung des Rückwärtsschritts lautet schematisch

\[
A_t^{k-1}=\alpha\big(A_t^k-\gamma\epsilon_\theta(O_t,A_t^k,k)+\mathcal N(0,\sigma^2I)\big).
\]

`α,γ,σ` sind Schedulegrößen, keine beliebig austauschbaren Hyperparameter. **Nur Arithmetikbeispiel:** Aᵏ=0.5, ε̂=0.2, α=1, γ=0.1, konkrete Noiseziehung=0 → nächster Wert 0.48. Diese frei gewählten Werte implementieren keinen originalgetreuen DDPM/DDIM-Schritt. Quelle: DP-01, RSS S. 3, Gl. (4).

## P3 · Welche Horizonte gehören zur Ausführung?

`T_o` Beobachtungsframes → `T_p` vorhergesagte Aktionen → `T_a` ausgeführte Aktionen → neues Feedback. Der Denoisingindex k ist eine weitere, getrennte Rechenachse.

**Projektbeispiel, ausdrücklich C:** T_o=2, T_p=16, T_a=2. Bei 20 Hz sind zwei ausgeführte Befehlsintervalle 0.1 s bis zum nächsten Plan. Der Chunk hat 16 Zeitslots; zwischen erstem und letztem Zeitstempel liegen 15 Rasterintervalle, also 0.75 s. Wegen der lokalen Ausrichtung t−1 bis t+14 liegt ein Positionstermin in der Vergangenheit; nicht alle 16 Positionen sind zukünftige Befehle. Ausgeführt werden Index 1 und 2. Anzahl der Befehlsintervalle und Abstand zwischen Zeitstempeln sind verschiedene Zählweisen. Quelle: DP-02, RSS S. 3; lokale OUR-03–05.

## P4 · Score, Energie und die Zweimoden-Simulation

\[
p_\theta(a|o)=\frac{e^{-E_\theta(o,a)}}{Z(o,\theta)},\qquad
\nabla_a\log p_\theta(a|o)=-\nabla_aE_\theta(o,a).
\]

`E_θ` = Energiefunktion; `Z` = Normalisierer über alle Aktionen; `∇_a log p` = **Score**, Richtung steigender Logdichte. Z hängt nicht von a ab und verschwindet deshalb bei der Aktionsableitung. Die Nähe zu `−ε_θ` im RSS-Text ist schematisch; bei Rauschvorhersage gehören Noiselevel und Skalierung dazu. Quelle: DP-04, RSS S. 5.

**Labormodell mit bekanntem Score:**

\[
p(a)=\tfrac12\mathcal N(a;-1,v)+\tfrac12\mathcal N(a;+1,v),
\quad s(a)=\frac{w_-(a)(-1-a)+w_+(a)(1-a)}{v},
\]

w_± sind die auf Summe 1 normalisierten Gaußdichten am aktuellen a. v ist die mit dem Rauschlevel vergrößerte Varianz. Nahe +1 zieht der Score typischerweise zum rechten Modus, nahe −1 zum linken. Bei a=0 ist der symmetrische Score null.

Das Labor benutzt **annealed Langevin**:

\[
a_{j+1}=a_j+h\,s_j(a_j)+\sqrt{2h}\,\xi_j,\quad\xi_j\sim\mathcal N(0,1).
\]

`h` = Samplerschrittweite; `j` = Recheniteration. Die Glättungsvarianz nimmt ab. Der stochastische Anteil erlaubt Bewegung, auch wenn der Score null ist. Es ist weder originales DDIM noch ein trainiertes ε-Netz. Endliche Samples/Schritte approximieren die bekannte Verteilung; ihre Häufigkeiten müssen nicht exakt 50/50 sein.

## P5 · Aktionsnormalisierung und Prozentzahlen

\[
\tilde a=2\frac{a-a_{min}}{a_{max}-a_{min}}-1.
\]

`a_min,a_max` = jeweilige Trainingsbereichsgrenzen der Aktionskomponente, `ã` = normierter Wert. **Rechnung:** a_min=0,a_max=10,a=7 → ã=0.4. Bei gleicher Min-/Max-Grenze ist die Division nicht definiert und braucht eine Sonderbehandlung. Die RSS-Aktionsregel belegt keine beliebige Observation-Normalisierung. Quelle: DP-09, S. 14.

\[
r_i=\frac{bestDP_i-bestBaseline_i}{bestBaseline_i},\quad\bar r=\frac1M\sum_i r_i.
\]

`i` = Benchmarkspalte; `M` = Zahl berücksichtigter Spalten. Beispiel 0.6→0.9: **+30 Prozentpunkte**, aber **50 % relative Verbesserung**. RSS berichtet 46.9 % als mittlere relative Verbesserung mit Bestvariantenwahl, nicht als universellen Prozentpunktegewinn. Quelle: DP-06, S. 15.

## E1 · Evaluation: Was ist eine Erfolgsrate?

\[
\hat p=\frac{n_{success}}{n_{tests}},\quad
\bar p=\frac1S\sum_{s=1}^S p_s,\quad
SD=\sqrt{\frac{\sum_s(p_s-\bar p)^2}{S-1}}.
\]

`S` = Zahl unabhängiger Trainingsreplikate, `p_s` = Erfolgsrate des Replikats, SD = Stichprobenstreuung der Raten. Ein Testrollout ist keine neue Trainingsreplikation. **Rechnung:** 8/10,6/10,7/10 → Mittelwert 0.7, SD 0.1=10 Prozentpunkte. Geteilte Teststarts machen Vergleiche gepaart; sie vermehren nicht die Zahl trainierter Modelle.

Aktions-MSE, Endabstand, IoU und binärer Taskerfolg messen unterschiedliche Dinge. IoU=`Schnittfläche/Vereinigungsfläche`; Schnittfläche 3, Vereinigungsfläche 5 → 0.6. Ein tatsächliches Erfolgskriterium muss vor der Erfolgsrate definiert sein. DAgger, DART, ACT und DP verwenden verschiedene Tasks und Kriterien. Die sechs Lehrlabore liefern keine Roboter-Erfolgsraten.
