# Simulationen: erst vorhersagen, dann rechnen lassen

Öffne [das Lernlabor](simulationen/index.html) im Browser. Es funktioniert ohne Internet. Diese Simulationen erklären Mechanismen in kleinen Modellen; sie führen keine neuen Experimente am Stack-Roboter durch. Die genauen Modelle stehen in [MODELLE.md](simulationen/MODELLE.md).

Nutze für jedes Labor diese vier Zeilen als Lernnotiz:

```text
Meine Vorhersage:
Ich ändere genau:
Ich beobachte:
Meine Erklärung / was daraus nicht folgt:
```

## Labor 1 · Fehlerakkumulation

**Ziel:** Unterschied zwischen zusätzlichem Fehler und Verstärkung verstehen. Formel: `e_{t+1}=q e_t+b`.

1. Setze b=0. Vermute für q=0.7,1,1.2 die Richtung der Entwicklung.
2. Prüfe die drei Werte. q<1 dämpft vorhandenen Fehler, q=1 erhält ihn, q>1 verstärkt ihn.
3. Setze q=0.7,b=0.03. Rechne den Grenzwert `b/(1−q)=0.1`. Mit Start e₀=0.1 bleibt die Kurve hier exakt konstant, obwohl die Eigenwirkung dämpfend ist.
4. Erkläre den Unterschied zwischen einem einzelnen Startfehler und dauerhafter fehlerhafter Aktion.

**Nicht ableiten:** Dass eure MSE automatisch einen T²-Taskfehler erzeugt. Atlas G1,D3; Übungen 1–2.

## Labor 2 · Datenabdeckung: BC, DAgger und vereinfachtes DART

**Ziel:** Herkunft der Zustände und Herkunft der Labels unterscheiden.

1. Lass Teststart=1.4 und DAgger-Runden=0. Betrachte die Aktionen nahe den nominalen Zuständen ±0.2 und weiter entfernt.
2. Vermute, ob viele gut imitierte kleine Abweichungen die Aktion bei x=1.4 festlegen. Beobachte den BC-Testrollout.
3. Füge eine DAgger-Runde hinzu. Der Learner besucht Zustände; der analytische Expert liefert dort neue Labels; alle Labels werden gemeinsam neu gefittet.
4. Setze DART-Noise auf null und dann auf 3. Die Daten stammen aus gestörter **Expert-Ausführung**, die Labels bleiben die ungestörten Expertaktionen an den dabei erreichten Zuständen.

**Warum ist BC hier absichtlich schlecht?** Bei kaum beobachteten großen x-Werten ist der Kubikterm schwach bestimmt. Ein gewählter Regularisierungsprior zieht ihn zur ungünstigen Zahl +1.2. Dadurch wird das Abdeckungsproblem sichtbar. Dieser Prior ist eine Lehrkonstruktion; BC muss außerhalb seiner Trainingsregion nicht grundsätzlich scheitern.

**Nicht ableiten:** Ein fairer DAgger-vs-DART-Erfolgsvergleich oder eine Umsetzung des vollständigen DART-Verfahrens. Die Datenzahlen und Abläufe unterscheiden sich; DARTs adaptive Noiseoptimierung fehlt. Atlas D1–D2,R1–R2; Übungen 3–4.

## Labor 3 · Mit und ohne xy-Term

**Ziel:** Drei Aussagen auseinanderhalten: Kopplung, nichtlineares Produkt und lokale Stabilität.

### A. Lineare Kopplung A_xy

`ė_x=−e_x+c e_y`, `ė_y=d e_x−e_y`. x/y bezeichnen hier Roboter-/Umgebungsfehler, keine Tischachsen.

1. c=2,d=1: Rechne `λ=−1±√2`. Ein positiver Eigenwert erklärt den wachsenden Modus.
2. c=0,d=1: Beide Eigenwerte sind −1. Vergleiche die Kurven. Es wurde nur y→x entfernt; x→y bleibt.
3. c=4,d=0: Eigenwerte weiterhin −1. Dennoch kann die Norm zunächst wachsen, weil die abklingende y-Komponente x antreibt. **Stabil ist nicht gleich monoton.**
4. c=0,d=0: Nun sind die zwei Fehler vollständig entkoppelt.

### B. Das Produkt x·y

Wechsle das Modell: `ẋ=−x+cxy`, `ẏ=−y`, Start x=0.25,y=1. d wird nicht verwendet.

1. c=2: Zu Beginn `ẋ=−0.25+2·0.25·1=0.25`: x wächst zunächst.
2. Später klingt y ab. Bei y<0.5 wird x wieder kleiner.
3. Am Ursprung x=y=0 ist der Jacobian −I mit und ohne cxy. Der Produktterm ist dort in erster Ordnung null. Das bedeutet nicht, dass er überall unwichtig ist.

**Nicht ableiten:** Dass jede Kopplung schadet, dass null ReLU-Strafe globale Stabilität beweist oder dass die Modelle euren kontaktreichen Stack darstellen. Atlas S1–S6; Übungen 5–6.

## Labor 4 · Chunks und Replanning

**Ziel:** Vorhersagelänge und Ausführungslänge unterscheiden.

1. Ensembling aus, T_a=1: Der Zielwechsel in Schritt 12 wird sofort in den neuen Befehl aufgenommen.
2. T_a=8: Ein alter Plan läuft nach dem Wechsel noch weiter. Rechne vorab: Pläne starten bei 0,8,16; der Wechsel bei 12 liegt im Plan ab 8.
3. Ensembling an: Jeder Schritt erzeugt einen neuen 10er-Plan. Nur Vorhersagen für *jetzt* werden kombiniert.
4. Vergleiche m=0 und m=1. Der älteste Plan erhält Index 0; großes m hält daher stärker an ihm fest.

**Nicht ableiten:** Chunking sei generell schlecht. Das Labor isoliert die Verzögerung einer von Hand festgelegten Planfunktion; es zeigt keine erlernte zeitliche Kohärenz oder CVAE-Ablation. Atlas A1,A3,P3; Übung 7.

## Labor 5 · Generative Aktionen

**Ziel:** Mittelwert und Verteilung unterscheiden; Rechenschritt und Roboterschritt trennen.

1. Vermute den MSE-Mittelwert bei gleich häufigen Expertaktionen −1 und +1.
2. Starte bei Recheniteration 0. Die 120 Sampleaktionen kommen aus einer breiten Gaußverteilung.
3. Gehe in Zehnerschritten bis 100. Der bekannte Score einer zunehmend weniger geglätteten Zweimodenverteilung zieht Samples in die zwei Regionen; Rauschen bleibt Teil des Samplers.
4. Wechsle den Seed. Vergleiche die Verteilung, nicht einzelne Kurven. Warum müssen nicht genau 60 Samples auf jeder Seite landen?

**Nicht ableiten:** Ein trainiertes Diffusionsnetz könne beliebige fehlende Demos ersetzen. Hier sind beide Modi schon explizit bekannt. Die Zwischenwerte sind keine ausgeführten Roboterbefehle. Atlas G3,P1–P4; Übung 8.

## Labor 6 · Noise-Kovarianz

**Ziel:** Standardabweichung, Varianz, Korrelation und kumulativen Abstand verstehen.

1. Bei α=1 ändere ρ von +0.7 auf −0.7. Die Punktwolke kippt; ihre erwartete Gesamtquadratsumme bleibt gleich.
2. Rechne `T trΣ=α`, bei T=20 also Spur 0.05.
3. Verdopple α. Die Varianzen verdoppeln sich, typische lineare Ausschläge wachsen um √2.
4. Stelle die Verbindung zu DART her: Die echte Methode schätzt eine geeignete Richtung aus Learnerabweichungen; hier stellst du sie selbst ein.

**Nicht ableiten:** Dass eine bestimmte Korrelation für euren Roboter optimal wäre. Die Rohkovarianz ist künstlich vorgegeben. Atlas R1–R2; Vertiefung 9.
