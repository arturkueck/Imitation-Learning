# Nächster kontrollierter Schritt nach der Phasendiagnose

Status: Untersuchungsprotokoll vorbereitet, nicht ausgeführt. Kein neuer
Trainingslauf gestartet. Grundlage: run_001, 220 Entwicklungsversuche.

## Entscheidung

Zunächst prüfen, ob der zweite Greifprozess die späteren Ausfälle verursacht.
Danach erst das BC-Curriculum festlegen. Ein pauschales Lift→Travel→Descend→Open
wird durch die Diagnose nicht gestützt: Travel und Open funktionieren in den
getesteten Expertenkontexten, während in 15/48 zweiten Lift-Starts kein Griff
erkannt wird und alle diese Gesamtversuche scheitern.

## Kontrollierter Eingriff ohne Training

- Referenz: unveränderte B-Modelle s1/s2/s3, 30.000 Updates, bestehende Clock-Korrektur.
- Vergleich: gleiche Anfangszustände und identische B-Ausführung bis zum
  zweiten Greifprozess. Nur Approach/Descend-to-grasp/Close der zweiten
  Platzierung durch den vorhandenen Experten ausführen, dann bei Lift wieder
  an denselben B-Controller übergeben. Kein Teleportieren, kein Griff erzwingen.
- Vergleichspanel: ausschließlich die 20 bereits geöffneten Entwicklungsszenen.
  Drei Modellseeds, keine neue Bestätigungsprüfung und keine Optimizer-Updates.
- Primär: erkannter Griff am zweiten Lift-Start und vollständige
  Drei-Würfel-Stabilität für 50 Frames. Sekundär: neue Fehler nach Übernahme.
- Paarweise auswerten: Gewinn/Verlust pro identischem Modell und Startzustand.
  Ein Eingriff ist eine Ursachenprüfung, kein nachgewiesener BC-Lernfortschritt.
- Budget: höchstens 20 Minuten, keine automatischen Neustarts,
  unveränderliche Checkpoints und vollständige Eingriffsprotokolle.

## Konsequenz für ein anschließendes BC-Curriculum

Wenn der Eingriff die fehlenden Griffe und einen relevanten Teil der
Gesamtausfälle behebt, liegt der Fokus auf dem zweiten Greifen und seinen
Eingangszuständen. Zuerst den bestehenden Datensatz auf tatsächliche Abdeckung
dieser Zustände prüfen. Zweier-Demonstrationen ersetzen keine Demonstrationen
nach dem ersten Platzieren und Rückzug. Bei fehlender Abdeckung sind neue
Expertenkorrekturen aus diesen Zuständen nötig; bloßes Oversampling genügt nicht.

Für das spätere Lernexperiment sind drei getrennte Vergleiche vorgesehen:

1. B mit gleichem zusätzlichem Updatebudget weitertrainieren.
2. Phasen-/Übergangsbeispiele häufiger zeigen, zeitlich gemischt.
3. Exakt dieselben Minibatches wie 2, innerhalb der relevanten Fertigkeit von
   einfachen zu schwierigeren Eingangszuständen geordnet.

Damit werden zusätzliches Training, veränderte Datenexposition und Reihenfolge
getrennt. Architektur, Loss, Optimizer, Seeds, Updatebudget und Evaluator bleiben
gepaart. Neue Beispiele werden nach vollständigen Ausgangsepisoden geteilt;
keine Frames derselben Korrektur in Training und Validierung. Diagnose- und
Bestätigungsszenen werden getrennt gehalten. Neue Bestätigungsstarts erst nach
Festlegung des endgültigen Protokolls öffnen.

Kein Critic-Pretraining: Optimiert wird weiterhin die BC-Aktion samt gelerntem
Phasenabschluss. Retreat und langes stabiles Halten benötigen eigene
Datenabdeckung, falls sie künftig ebenfalls gelernt werden sollen.
