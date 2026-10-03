# Idee und Umsetzung der BC-Verfahren

Ein gemeinsames Lernbild: Ein Greifer steht neben einem Würfel. Der Expert kann ihn zum Würfel führen. Eine Policy soll aus der Beobachtung die passende Steuerung lernen. Die folgenden Greiferbeispiele sind didaktisch erfunden. Paperbelege stehen am Ende jeder Methode; die Beispiele ersetzen sie nicht.

## BC als Ausgangspunkt

**Frage:** Kann ich aus vorhandenen Demonstrationen direkt eine Aktionsregel lernen?

Ein Datensatz enthält Paare `(Beobachtung, Expertaktion)`. Das Netz sieht jeweils die Beobachtung und produziert eine Aktion. Ein Loss vergleicht sie mit dem Label; Gradienten verändern die Netzparameter. Anschließend handelt das Netz ohne Expertlabels.

```text
Für jeden Trainingsbatch:
    Modellaktionen = policy(Beobachtungen)
    Loss = mittlerer Aktionsfehler(Modellaktionen, Expertaktionen)
    Gradienten berechnen und Parameter aktualisieren
Bei der Ausführung:
    beobachten → Aktion vorhersagen → ausführen → erneut beobachten
```

Eine kleine Demo-MSE zeigt, dass das Modell die bereitgestellten Labels trifft. Sie zeigt noch nicht, was es nach einer unerwarteten Greiferabweichung tut. Der optimale deterministische MSE-Prädiktor ist, unter üblichen Integrabilitätsbedingungen, der **bedingte Aktionsmittelwert**. Das kann problematisch sein, wenn verschiedene gültige Aktionen nicht sinnvoll gemittelt werden können. Atlas G1–G3, Labor 1 und 5. Quellen: DAG-01–03.

### Welche Teile eines BC-Modells können variieren?

Ein MLP verarbeitet einen Merkmalsvektor; ein RNN führt ein internes Gedächtnis; ein Transformer verknüpft Eingabetokens über Attention. Diese Begriffe beschreiben Rechenarchitektur. Deterministische Regression, Gaussian/GMM, CVAE und Diffusion beschreiben dagegen Aspekte der **Ausgabeverteilung und des Lernziels**. Ein Chunk beschreibt die zeitliche Ausgabeform. Diese Achsen sind kombinierbar: „Transformer“ allein sagt noch nicht, ob die Policy ein CVAE oder ein deterministischer Chunk-Regressor ist.

Eine Gaussian Policy liefert beispielsweise Mittelwert und Varianz, eine GMM mehrere gewichtete Gaußkomponenten. Das sind Hintergrundbegriffe, keine zusätzlich untersuchten Primärarbeiten. Robomimic ist der Software-Rahmen für Daten, Training und Evaluation; es ist selbst kein einzelner BC-Algorithmus.

## 1. DAgger: Trainiere auch auf deinen eigenen Zuständen

**Problem:** Der Greifer gerät beim Handeln etwas zu weit nach links; solche Zustände fehlen in den nominalen Demos.

**Idee:** Lass die Lernpolicy handeln. Frage den Experten bei den tatsächlich erreichten Zuständen nach der richtigen Aktion. Füge diese Labels zu den bisherigen Daten hinzu. Das neue Netz bekommt damit Korrekturbeispiele aus seiner eigenen Erfahrung.

```text
D = anfängliche Expertendemos
policy = trainiere_supervised(D)
Für mehrere Erhebungsrunden:
    Zustände durch policy oder Expert/Learner-Mischung besuchen
    für jeden erfassten Zustand: Expertaktion anfragen
    neue Paare zu D hinzufügen
    policy auf dem gesamten D trainieren
Kandidaten nach Validation vergleichen
```

**Wichtig:** „Der Expert wird ausgeführt“ und „der Expert wird nach dem Label gefragt“ sind unterschiedliche Dinge. Eine Mischung wählt die ausführende Policy mit einer Wahrscheinlichkeit; sie bedeutet bei DAgger nicht einfach das arithmetische Mitteln zweier Greiferbefehle.

**Was es braucht:** Expertkompetenz auf den erreichten Zuständen, echte neue Labels und Rollouts. Die Originaltheorie verlangt weitere Lern-/Lossannahmen; ein beliebiges tiefes Netz bekommt die Garantie nicht automatisch. Beim zustandsbehafteten StackExpert muss eine korrekte Phase bekannt sein, bevor ein Korrekturlabel als Expertantwort gelten kann.

**Sag es selbst:** „DAgger verändert vor allem die ___, auf denen ich Expertlabels erhalte.“ Antwort: Zustände der Datenerhebung. Atlas D1–D4; Labor 2. Primärbelege: DAgger PDF S. 2–6, DAG-01–07.

## 2. DART: Lass den Experten korrigieren, während du Daten sammelst

**Problem:** Rein nominale Demonstrationen zeigen selten, wie man einen Fehler korrigiert.

**Idee:** Der Expert führt den Roboter, aber auf den ausgeführten Befehl kommt eine Störung. Beim nächsten Beobachten sieht der Expert deren Wirkung und gibt eine Korrektur. Aufgezeichnet wird seine **beabsichtigte, ungestörte** Aktion am tatsächlich erreichten Zustand.

```text
Noiseverteilung initialisieren
Für jede Erhebungsrunde:
    Zustand beobachten
    Expertlabel u_star bestimmen und speichern
    u_star + Noise ausführen
    erreichten Zustand wieder vom Experten beurteilen lassen
    temporäres BC-Modell auf aggregierten Demos trainieren
    seine Abweichungen vom Experten schätzen
    Noise-Kovarianz und Stärke für nächste Runde anpassen
Finales BC auf allen Demos trainieren
```

**Kleines Beispiel:** Bei `x=0.5` sagt der Expert `u*=−0.5`. Es wird mit Noise `+0.2` die Aktion `−0.3` ausgeführt. Das Trainingslabel zu diesem x bleibt `−0.5`. Am neuen x folgt eine neue Expertantwort. Das Modell soll nicht lernen, die absichtliche Störung als korrekte Aktion zu reproduzieren.

**Abgrenzung:** Ein vorhandenes x nachträglich verrauschen und sein altes Label behalten erzeugt keine neue Expertreaktion. Das ist Inputaugmentation und kein vollständiger DART-Ablauf. Sehr starke Störungen können die sinnvolle Aufgabe zerstören. Die Kovarianz beschreibt, welche Aktionskomponenten gemeinsam schwanken.

**Sag es selbst:** „Bei DART sind Ausführungsaktion und Trainingslabel verschieden, weil ___.“ Atlas R1–R3; Labore 2 und 6. Primärbelege: DART PDF S. 4–6/12–14, DART-02–05/09.

## 3. Stable-BC: Lerne, wie Abweichungen weiterlaufen

**Problem:** Zwei nahe beieinanderliegende Zustände können durch die Policy weiter auseinanderlaufen.

**Idee:** Die Demonstrationsaktion soll weiterhin getroffen werden. Zusätzlich untersucht der Loss, wie kleine Änderungen von Roboterzustand x und Umgebungszustand y die weitere Dynamik beeinflussen. Instabile lokale Modi werden bestraft. In einer Variante wird auch die Empfindlichkeit gegenüber Umgebungsabweichung reduziert.

```text
Für demonstrierte x, y und Aktion u:
    BC-Aktionsfehler berechnen
    Ableitungen von Roboterdynamik und Policy berechnen
    lokale Fehlerdynamik bilden
    modellbasiert: ganze Matrix A auf Eigenwerte prüfen
    bei unbekanntem g: Roboterblock A1 und Kopplung A2 verwenden
    BC + gewichtete Zusatzstrafen gemeinsam optimieren
```

**Warum x/y?** x ist zum Beispiel die Greiferposition, y die Objektposition. Wenn das Objekt versetzt wird, muss die Policy reagieren. Eine Kopplung ist also manchmal notwendig. „Möglichst unabhängig von y“ kann zwar Störungen abschirmen, aber auch das Zielverfolgen verhindern.

**Zwei verschiedene „xy-Terme“:** In der lokalen Matrix ist `A_xy` die Wirkung einer y-Abweichung auf die Änderungsrate des x-Fehlers: `ė_x=A_xx e_x+A_xy e_y`. Das ist **kein** Produkt x·y. Ein echtes Produkt `ẋ=−x+cxy` ist eine nichtlineare Wechselwirkung; sein Jacobian hängt vom Ort ab. Beide stehen in Labor 3 nebeneinander.

**Voraussetzungen und Grenzen:** Im sogenannten modellfreien Paperfall ist die Roboterdynamik f weiterhin bekannt; nur die Umgebungsdynamik g ist unbekannt. Die Analyse ist lokal. Eine ReLU-Strafe von null erzwingt noch keine strikt negativen Eigenwertrealteile. Und „stabil“ heißt nicht automatisch „richtiger Würfelstapel“.

**Sag es selbst:** „Eigenwerte beschreiben ___; der BC-Loss beschreibt ___.“ Antwort: lokale Fehlerentwicklung; Übereinstimmung der Aktionen mit Demos. Atlas S1–S6; Labor 3. Primärbelege: **Stable-BC Preprint v1**, PDF S. 2–5, SBC-02–06/10.

## 4. ACT: Eine kleine Bewegungsfolge statt einer isolierten Aktion

**Problem:** Ein Griff besteht aus zeitlich zusammenhängenden Teilbewegungen. Menschliche Demos enthalten außerdem Variation und Pausen.

**Idee:** Ein Transformer sagt einen Chunk voraus. Ein CVAE lernt Variation über eine latente Variable z. Temporales Ensembling kombiniert überlappende Vorhersagen für denselben Ausführungszeitpunkt.

```text
Training:
    Encoder: Gelenkzustand + demonstrierter Chunk → Latentverteilung q(z)
    z daraus ziehen
    Decoder: Bilder + Gelenkzustand + z → vorhergesagter Chunk
    Rekonstruktionsloss + beta * KL zum Normalprior optimieren
Ausführung im Original:
    Encoder entfällt; z = 0
    jeden Zeitschritt einen neuen Chunk vorhersagen
    Vorhersagen für den aktuellen Zeitpunkt gewichtet kombinieren
    eine kombinierte Aktion ausführen
```

**Ensembling-Beispiel:** Ein älterer Plan sagt für *jetzt* 0.8, ein neuer Plan 0.6. Mit Gewichten 1 und 0.5 wird `(0.8+0.5·0.6)/1.5≈0.733` ausgeführt. Es werden nicht eine Aktion von gestern und eine von morgen gemittelt. Beide sind Vorhersagen für denselben Zeitpunkt.

**CVAE einfach erklärt:** Der Encoder sieht beim Training die tatsächlich demonstrierte Folge und codiert ihre Variation. Im Einsatz ist diese Folge unbekannt; deshalb kann der Encoder nicht einfach weiter benutzt werden. Im beschriebenen ACT-Test ist z fest auf null gesetzt. Generatives Training bedeutet hier nicht automatisch stochastische Ausführung.

**Grenzen:** Langes offenes Chunk-Abarbeiten reagiert spät auf Veränderungen. Ensembling kann glätten und zugleich neue Reaktionen verzögern. Das Paper nennt den ältesten Plan zuerst bei `exp(−mi)`; für positives m bekommt er das größte Gewicht. L1-Implementationsbeschreibung und MSE-Pseudocode widersprechen sich im Original und werden hier nicht gleichgesetzt.

**Sag es selbst:** „Chunking, CVAE und Ensembling sind drei ___ Bestandteile.“ Antwort: getrennte. Atlas A1–A3; Labore 4–5. Primärbelege: ACT PDF S. 5–6/15–16, ACT-01–04.

## 5. Diffusion Policy: Aus Rauschen eine passende Aktionsfolge erzeugen

**Problem:** Für eine Beobachtung können mehrere gültige, zusammenhängende Bewegungen existieren. Ein einzelner Mittelwert bildet sie schlecht ab.

**Idee:** Beim Training wird eine echte Aktionsfolge kontrolliert verrauscht. Ein konditioniertes Netz lernt das injizierte Rauschen vorherzusagen. Beim Einsatz beginnt man mit Rauschen und verfeinert es iterativ zu einer Aktionsfolge. Die Beobachtungen bleiben die Bedingung des Generators.

```text
Training:
    Beobachtungshistorie O und echten Aktionschunk A0 wählen
    Rauschlevel k und Noise epsilon ziehen
    Ak = verrauschte Version von A0
    epsilon_hat = Netz(O, Ak, k)
    MSE(epsilon_hat, epsilon) optimieren
Ausführung:
    vollständigen Rauschchunk initialisieren
    mit Scheduler und Netz mehrfach denoisen
    nur Ta passende Aktionen der Tp Vorhersagen ausführen
    neue To Beobachtungen sammeln und erneut planen
```

**Zwei Zeiten:** Die Iterationen k beim Denoising sind Rechenschritte. Die Zeit t ist der tatsächliche Roboterablauf. Der Roboter führt nicht jedes Zwischenrauschen als Befehl aus.

**Warum nicht einfach den Mittelwert?** Wenn links und rechts am Hindernis gültig sind, soll eine Folge zu einer Seite passen. Eine gemittelte Folge kann unbrauchbar sein. Dafür muss die Verteilung tatsächlich aus den Demos gelernt werden; Diffusion erzeugt nicht automatisch richtige Recovery, die in den Daten fehlt.

**Grenzen:** Iterative Generierung braucht Zeit. Backbone, Aktionsraum und Replanning beeinflussen die Ergebnisse. Ein Noise-MSE-Wert ist nicht direkt derselbe Messwert wie eine Aktions-MSE. Labor 5 nutzt einen *bekannten analytischen Score*, um die Idee zu zeigen; es trainiert keine originale Diffusion Policy.

**Sag es selbst:** „Das Netz bekommt beim Training ___ als Ziel; nach dem Denoising führt der Roboter ___ aus.“ Antwort: Noise; fertige Aktionen. Atlas P1–P5; Labore 4–5. Primärbelege: Diffusion Policy RSS PDF S. 3–5/11/14–15, DP-01–04/10.

## Gemeinsam vergleichen

| Methode | Was wird hauptsächlich geändert? | Was sie zusätzlich braucht |
|---|---|---|
| BC | Supervised Policytraining auf festen Daten | passende Demos und Eingaben |
| DAgger | Herkunft der Zustände und neue Expertlabels | Expertfragen auf Learnerzuständen |
| DART | gestörte Expert-Datenerhebung | Korrekturexpert und sinnvolle Störungen |
| Stable-BC | Loss für lokale Fehlerdynamik | Dynamikannahmen und Ableitungen |
| ACT | Aktionsfolgen, Latentmodell, Ensembling | synchronisierte Chunks und passende Ausführung |
| Diffusion | generative Aktionsfolge und Denoising | Noise-Training und iterative Inferenz |

## Bezug zu eurem Projekt — ausdrücklich Projektkontext

Die vorhandene Direct-Policy hat schon einen Chunk mit 16×7 Ausgaben. Zwei Frames mit je 15 Merkmalen ergeben 30 Eingabewerte. Der Chunk am Anker t enthält Aktionen t−1 bis t+14; ausgeführt werden Index 1 und 2, also t und t+1. Ein 16er-Chunk heißt deshalb nicht 16 Schritte ohne Feedback. Direct ist durch Chunking allein weder originales ACT noch Diffusion.

Das Netz sieht nicht ausdrücklich den gesamten internen Zustand des programmierten Experts. Deshalb ist es eine offene Frage, welche Entscheidungen aus den zwei Frames eindeutig ablesbar sind. Die lokalen Erfolgszahlen werden in diesen Lernlaboren nicht simuliert. Projektbelege: [OUR-02–05/12](../literature/comparisons/relation_to_our_results.md).
