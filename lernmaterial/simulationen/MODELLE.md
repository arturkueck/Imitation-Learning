# Modellbeschreibung und Abgrenzung

Die Zahlen sind abstrakte didaktische Einheiten. Es wird kein Controller aus eurem Robotercode geladen. `engine.js` enthält reine Rechenfunktionen, `app.js` Darstellung und Bedienung. Es gibt keine Netzwerkaufrufe, externe Bibliotheken oder Trainingsjobs. Zufallszahlen kommen aus einem seedbaren linearen Kongruenzgenerator mit Box-Muller-Gaußtransformation; das ist keine kryptographische Zufallsquelle.

## 1. Fehler

Rekurrenz `e_{t+1}=q e_t+b`, e₀=0.1, 25 Schritte. Bei q≠1: `e_t=q^t e₀+b(1−q^t)/(1−q)`. Bei q=1: `e_t=e₀+tb`. Das Modell illustriert Eigenwirkung und dauerhafte Störung, nicht den DAgger-Taskkostenbound.

## 2. Daten

Expert `u*(x)=−x−0.6x³`, Dynamik `x_{t+1}=x_t+0.08u_t`. Nominal: 24 Labels auf gleichmäßig verteilten x zwischen −0.2 und 0.2. Modell `u=w₁x+w₃x³`. Optimiert wird exakt über ein 2×2-Normalgleichungssystem:

`mean_i[(w₁x_i+w₃x_i³−u_i*)²] + 0.002[w₁²+(w₃−1.2)²]`.

Der Kubikprior +1.2 ist **absichtlich ungünstig**. Er bleibt bei begrenzter Datenabdeckung schwach bestimmt und erzeugt einen sichtbaren Extrapolationsfehler. Dies ist keine allgemeine Eigenschaft von BC und keine Paperhyperparameterwahl.

DAgger: Für jede angeforderte Runde wird der aktuelle Learner ab gewähltem Teststart bis 50 Schritte bzw. |x|>4 ausgeführt. An allen zurückgegebenen Zuständen mit |x|≤4 wird der Expert neu ausgewertet; Daten werden aggregiert, anschließend wird neu gefittet. Keine Expertmischung. Wiederholte Zustandslabels bleiben als wiederholte Beispiele im Datensatz.

DART-Lehrvariante: 120 Schritte ab x=0.1 mit `u_exec=u*(x)+σξ`, ξ standardnormal, Seed 7. Gespeichert wird `(x,u*(x))`; Noise ist kein Label. Der anschließend gefittete Regressor nutzt diese plus nominale Daten. Original-DARTs iterative Anpassung von Kovarianz und Stärke ist nicht implementiert. Labor 6 erklärt die gesonderte Skalierungsrechnung. Labelzahlen sind ungleich; Rolloutkurven sind kein kontrollierter Leistungsvergleich.

## 3. Kopplung

Linear: `ė_x=−e_x+c e_y`, `ė_y=d e_x−e_y`, Start (0.2,0.8). Ohne c-Term wird nur c=0 gesetzt, d bleibt. Eigenwerte analytisch `−1±√(cd)`, bei cd<0 komplexe Paare. Der diagonale Wert −1 ist fest.

Produkt: `ẋ=−x+cxy`, `ẏ=−y`, Start (0.25,1). d ist irrelevant und das Bedienelement deaktiviert. Jacobian `J=[[-1+cy,cx],[0,−1]]`; UI-Eigenwertaussage am Ursprung. Exakte Vergleichslösung: `y=y₀e^{-t}`, `x=x₀exp(−t+c y₀(1−e^{-t}))`.

Integration: klassisches RK4, Δt=0.02, höchstens 500 Schritte=10 Zeiteinheiten. Abbruch bei nichtendlichen Werten oder |Komponente|>50. Bei abgeschnittener Kurve ist der Abbruch ausdrücklich angezeigt. Das Phasendiagramm verbindet Zustände in zeitlicher Reihenfolge; beide Achsen sind separat beschriftet, keine geometrische Roboterdarstellung.

## 4. Chunks

Skalare absolute Positionsziele. Handgeschriebener Prädiktor: `p_{j+1}=p_j+0.25(goal_t−p_j)`; Planlänge zehn. Die simulierte Pflanze erreicht das ausgeführte Positionsziel ohne Verzögerung. Ziel +1 bis t=11, −1 ab t=12, insgesamt 40 Befehle.

Ohne Ensembling wird alle T_a Befehle neu geplant; T_a∈1…10. Mit Ensembling wird jeden Schritt neu geplant und genau eine gewichtete Position ausgeführt. Es werden nur gültige Vorhersagen für denselben t gemittelt; `w_i=exp(−mi)` mit i=0 für den ältesten Plan. T_a ist dann deaktiviert. Kein gelernter Decoder, kein CVAE, keine Kameras. Das Modell zeigt Verzögerung und Glättung, nicht die gesamte ACT-Methode.

## 5. Generativ

Zieldichte: gleichgewichtete Gaußmischung mit Mittelwerten ±1 und Standardabweichung 0.18. 120 Initialsamples aus N(0,1.2²), Seed 11/21/31. Für Iteration j=0…99 wird σ_j=1−j/99 und v_j=0.18²+σ_j² benutzt. Der Score der geglätteten Mischung wird analytisch ausgewertet. Update `a←a+0.01 score(a)+√0.02 ξ`.

Dies ist endliches annealed Langevin, kein originaler DDPM/DDIM-Scheduler, keine trainierte Diffusion Policy. Dichtehistogramm: 48 Bins von −4 bis 4, Höhe count/(120·Binbreite); außerhalb liegende Samples werden nicht in diese Anzeige hineingeclippt. Gezeichnete Samplepfade: zwölf der 120 Samples. Mittlerer Bereich |a|<0.3 ist eine didaktische Regionszählung, kein Erfolgs- oder Kollisionskriterium.

## 6. Noise

Rohstandardabweichungen σ₁=0.2, σ₂=0.4; `Σ̂=[[σ₁²,ρσ₁σ₂],[ρσ₁σ₂,σ₂²]]`. UI |ρ|≤0.9 vermeidet singuläre Kovarianz. T=20; Skalierung `Σ^α=αΣ̂/(T trΣ̂)`. Gaußziehungen über zwei unabhängige Standardnormale: `η₁=sσ₁z₁`, `η₂=sσ₂(ρz₁+√(1−ρ²)z₂)`, s=√Skalierungsfaktor. 140 Samples, Seed 13.

Analytisch `T E||η||²=T trΣ^α=α`; der empirische Abstand endlicher Samples muss nicht exakt α sein. Die Richtung ist hier manuell, kein Ergebnis einer DART-Schätzung.

## Verantwortliche Interpretation

Die Modelle erklären Ideen und erlauben überprüfbare Rechenbeispiele. Sie isolieren jeweils wenige Größen und lassen reale Wahrnehmung, Kontaktphysik, Datenpipeline und Netzoptimierung aus. Die wissenschaftlichen Aussagen, Fassungen und Einschränkungen stehen weiterhin in `literature/`. Die Tests prüfen, ob das jeweilige Lehrmodell wie beschrieben rechnet; sie validieren keine Methode am Roboter.
