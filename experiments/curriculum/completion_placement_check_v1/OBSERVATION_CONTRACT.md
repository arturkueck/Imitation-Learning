# Welche Ablagebedingungen kann der gelernte Abschluss beobachten?

Codepruefung am 18.11.2026, waehrend der unveraenderten Diagnose.
Keine Aenderung von Eingaben, Modellen, Auswahl oder Endpunkten.

Der tatsaechliche zehn-dimensionale Eingabevektor in
`experiments/self_imitation/stack_phased_8h_20261023/method.py::vector`
enthaelt:

- Greiferposition relativ zum zu Phasenbeginn gespeicherten Anker, drei Werte;
- Greiferquaternion, vier Werte;
- zwei Greifer-Gelenkpositionen;
- Phasenuhr `min(steps,100)/20`, ein Wert.

In Phase 5 ist der Anker die Position des Zielwuerfels beim Eintritt. Der
Phasenindex waehlt einen separaten Feedforward-Kopf. Es gibt hier keinen
rekurrenten Zustand. Die Clock-Korrektur betrifft ausschliesslich die finale
Phase 6; sie fuegt keine Objektmessungen hinzu.

**Direkt nicht enthalten** sind aktuelle Pose des gehaltenen Wuerfels,
Quell-/Zielwuerfel-Versatz, Wuerfelkontakt und Wuerfelgeschwindigkeiten.
Greiferzustand und Zeit koennen mit diesen Groessen korrelieren; das ist
keine direkte Messung ihres tatsaechlichen Werts. Der explizite geometrische
Guard verwendet zusaetzliche Simulatorinformationen und besitzt deshalb
einen anderen Beobachtungsvertrag als das vorhandene Modell.

Folgerung als Hypothese: Bei abweichender Lage des Wuerfels im Griff koennen
aehnliche vorhandene Policy-Eingaben unterschiedliche korrekte
Abschlussentscheidungen verlangen. Eine bessere Konvergenz auf denselben
Eingaben beseitigt diese moegliche Mehrdeutigkeit nicht automatisch. Die
vorliegende Diagnose beweist noch nicht, wie viel eines Leistungsdefizits
allein auf diese Beobachtungsgrenze entfaellt.

Ein spaeterer Methodenvergleich muesste deshalb Daten-/Abschlussregel und
Beobachtungsvertrag getrennt kontrollieren. Ein Guard mit privilegiertem
Simulatorzustand waere nicht als reine Verbesserung des vorhandenen
Abschlussklassifikators bei gleichen Informationen auszugeben. Fuer einen
realen Transfer waeren messbare Pose-/Kontaktsignale und deren Fehler zu
beruecksichtigen. Dieser Hinweis startet kein neues Training.
