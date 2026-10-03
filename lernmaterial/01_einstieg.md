# Ein kurzer Einstieg in Imitation Learning

Stell dir vor, du zeigst einem Roboter, wie er einen Würfel greift und auf einen zweiten stellt. Währenddessen zeichnest du auf, was der Roboter beobachtet und welche Befehle du gibst. Solche Abläufe heißen **Demonstrationen**. Imitation Learning nutzt sie, um ein Verhalten zu lernen. Der Demonstrator heißt **Expert**; das gelernte Entscheidungsmodell heißt **Policy**.

Beim **Behavioural Cloning**, kurz BC, wird daraus eine überwachte Lernaufgabe: Eingabe ist eine Beobachtung, Ziel ist die Expertaktion. Beispielsweise lautet die Eingabe „Greifer fünf Zentimeter links vom Würfel“, die gewünschte Ausgabe „etwas nach rechts bewegen“. Ein neuronales Netz passt seine Parameter so an, dass seine Ausgaben möglichst gut zu den Demonstrationen passen. BC braucht dafür zunächst keinen selbst entworfenen Reward. Reinforcement Learning lernt dagegen typischerweise aus bewerteten Interaktionen mit der Umgebung. Diese Unterscheidung beschreibt die Grundformen; kombinierte Verfahren existieren.

Die Schwierigkeit beginnt bei der Ausführung. Gibt das Netz einen etwas falschen Befehl, steht der Greifer beim nächsten Schritt anders als in der Demo. Nun muss es mit einer Eingabe umgehen, die es vielleicht kaum gesehen hat. Weitere Fehler können folgen. Der Unterschied zwischen den Zuständen beim Lernen und beim eigenen Handeln heißt hier **Covariate Shift**. **Fehlerakkumulation** ist die mögliche zeitliche Folge. Beides ist verwandt, aber nicht identisch: Eine Verteilungsänderung muss nicht automatisch zum Scheitern führen.

Die fünf Methoden greifen an verschiedenen Stellen ein. **DAgger** lässt die Lernpolicy handeln und fragt den Experten, was an den dabei besuchten Zuständen richtig gewesen wäre. **DART** stört die Expertenausführung schon während der Demonstration, damit der Expert Korrekturen zeigt. **Stable-BC** ergänzt den Lernverlust um Bedingungen an die lokale Fehlerdynamik. **ACT** sagt zusammenhängende Aktionsfolgen voraus, modelliert Demonstrationsvariation und kombiniert überlappende Pläne. **Diffusion Policy** lernt, aus Rauschen eine zu den Beobachtungen passende Aktionsfolge zu erzeugen.

Alle benötigen aussagekräftige Daten und eine sinnvolle Eingabe. Wenn die Eingabe eine wichtige Information verschweigt, kann auch ein großes Netz sie nicht eindeutig rekonstruieren. Schließlich entscheidet die tatsächlich ausgeführte Aufgabe über Erfolg: Eine kleine Aktionsabweichung im Datensatz ist hilfreich, beweist aber noch keinen stabilen Würfelstapel.

## Vier Wörter mit einem Beispiel

| Wort | Bedeutung | Beispiel |
|---|---|---|
| Zustand `s` | Beschreibung des Systems; im Modell oft vollständig | Positionen, Geschwindigkeiten, Kontaktzustand |
| Beobachtung `o` | Information, die die Policy wirklich erhält | Kamerabild oder ausgewählte State-Merkmale |
| Aktion `a` bzw. `u` | Befehl an den Roboter | Zielposition, Geschwindigkeit oder Greiferbefehl, abhängig vom Controller |
| Policy `π` | Regel von Eingabe zu Aktion oder Aktionsverteilung | `π(o)=a` bzw. `p(a|o)` |

„State-Input“ heißt nicht automatisch, dass die Beobachtung den gesamten Zustand enthält. Zwei Frames sind eine kurze Historie; sie garantieren keine vollständige Information über eine intern gespeicherte Expertphase.

## Selbstcheck ohne Nachlesen

1. Was ist beim BC das Trainingslabel?
2. Weshalb beeinflusst eine Aktion die nächste Eingabe?
3. Welche zwei Methoden erzeugen neue Korrektursupervision?

Antworten: Expertaktion; durch die Systemdynamik; DAgger und DART. Wenn du dazu ein Greiferbeispiel geben kannst, bist du bereit für den nächsten Text.

Vertiefung: [Algorithmen](03_algorithmen.md). Primärbezüge: DAG-01–06, DART-02, SBC-03–06, ACT-01–04, DP-01–02 in [CLAIMS.md](../literature/CLAIMS.md).
