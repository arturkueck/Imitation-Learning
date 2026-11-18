# Literaturgrundlage zum Proposal

Das Exposé verbindet die Knappheit und Abdeckung von Demonstrationen
mit der Frage, wie gut eine Policy auf neue Stapelszenen überträgt.
Die Arbeiten zur Self-Imitation erklären, wie eigene Versuche weitere
Lernsignale liefern können. Actor-Critic-Arbeiten begründen anschließend
die konkrete Frage, ob die Vorinitialisierung des Critic einen Vorteil
für die resultierende Policy hat. Die Tabelle enthält auch Arbeiten für
die breitere Recherche, die im Exposé aus Platzgründen entfallen.

| Originalarbeit | Beitrag zum Datenproblem | Grenze für unsere Fragestellung |
|---|---|---|
| [Ross, Gordon und Bagnell, DAgger (2011)](https://proceedings.mlr.press/v15/ross11a.html) | Erfasst die Verschiebung zu Zuständen, die die gelernte Policy selbst erzeugt. Der Experte beschriftet solche Zustände. | Setzt Expertenzugang voraus. Die Theorie bestimmt keine optimale Abfragestrategie für unsere einzelnen Greifphasen. |
| [Laskey et al., DART (2017)](https://proceedings.mlr.press/v78/laskey17a.html) | Injiziert Störungen bei Demonstrationen und erfasst so Korrekturen. | Störungen in Expertenabläufen und echte Lernerabläufe sind unterschiedliche Erhebungsverfahren. |
| [Mandlekar et al., RoboMimic-Studie (PMLR 2022)](https://proceedings.mlr.press/v164/mandlekar22a.html) | Vergleicht sechs Offline-Verfahren für Manipulation. Demonstrationsqualität und Wahl des Checkpoints beeinflussen die Ergebnisse. | Begründet die getrennte Messung von Trainings- und Aufgabenerfolg. Die Studie belegt kein Curriculum für unsere Stapelaufgabe. |
| [Mandlekar et al., MimicGen (2023)](https://proceedings.mlr.press/v229/mandlekar23a.html) | Passt vorhandene Demonstrationen an neue Simulatorkontexte an und erzeugt dadurch größere, vielfältigere Datensätze. | Umfang, Abdeckung und Generierungsaufwand können sich zugleich ändern. Ein isolierter Reihenfolgeeffekt braucht eigene Kontrollen. |
| [Hejna et al., ReMix (PMLR 2025)](https://proceedings.mlr.press/v270/hejna25a.html) | Untersucht datengesteuerte Gewichte für Teilbestände großer Robotikdatensätze. | Eine bessere Mischung beantwortet eine andere Frage als die zeitliche Reihenfolge der gleichen Beispiele. |
| [Bengio et al., Curriculum Learning (2009)](https://icml.cc/2009/papers/119.pdf) | Untersucht veränderte Trainingsverteilungen, etwa von einfacheren zu komplexeren Beispielen. | Die relevante Schwierigkeit muss für die konkrete Aufgabe definiert und überprüft werden. |
| [Hou et al., Active Robot Curriculum Learning (2025)](https://arxiv.org/abs/2503.02277) | Verbindet adaptive Aufgabenauswahl, neue menschliche Demonstrationen und Actor-Critic-Training. | Die gemeinsame Intervention verändert Erhebung und Training. Aus ihren Ergebnissen folgt kein isolierter Effekt der Präsentationsreihenfolge. |
| [Oh et al., Self-Imitation Learning (2018)](https://proceedings.mlr.press/v80/oh18b.html) | Nutzt frühere Aktionen des Agenten, wenn deren beobachteter Return die geschätzte Zustandsbewertung übertrifft. | Der Ansatz stammt aus Reinforcement Learning. Ein Return überträgt sich nicht automatisch auf sinnvolle lokale Labels für Kontaktübergänge. |
| [Zhu et al., Self-Adaptive Imitation Learning (2022)](https://doi.org/10.1609/aaai.v36i8.20914) | Verwendet wenige, möglicherweise suboptimale Demonstrationen und ersetzt einen Teil der Anleitung durch besser bewertete eigene Trajektorien. | Untersucht Aufgaben mit verzögertem Feedback und Rangfolgen von Trajektorien. Es prüft keinen isolierten Critic-Warmstart für das Stapeln. |
| [Wang et al., Critic Regularized Regression (2020)](https://proceedings.neurips.cc/paper/2020/hash/588cb956d6bbe67078f29f8de420a13d-Abstract.html) | Verwendet gelernten Wert als Auswahl- bzw. Gewichtungssignal in einem Offline-Lernverfahren. | Ein Critic muss bei Verwendung auf den eigenen Zuständen und Daten überprüft werden. Ein lokaler Score allein zeigt noch keinen Nutzen für die ausgeführte Policy. |
| [Nair et al., AWAC (2020)](https://arxiv.org/abs/2006.09359) | Verbindet vorhandene Daten und weitere Interaktion. Die geschätzten Vorteile von Aktionen gewichten das Lernen der Policy. | Der gesamte Algorithmus verbindet mehrere Schritte. Sein Erfolg belegt den Effekt eines vortrainierten Critic allein nicht. |
| [Kernbach et al., Actor-Critic Pretraining for PPO (2026, Preprint)](https://arxiv.org/abs/2602.23804) | Trainiert den Actor zunächst mit BC und den Critic mit Returns aus den Rollouts dieser Policy. Berichtet auf mehreren simulierten Aufgaben geringeren Interaktionsbedarf, einschließlich Aufwand der Vorphase. | Der Nutzen hängt von der Aufgabe ab. Die Arbeit liefert einen direkten Vergleichspunkt für die Stapelstudie, keinen Nachweis der Übertragbarkeit. |

Im vorgeschlagenen Versuch verwenden beide Actor-Critic-Arme denselben
BC-Actor als Ausgangspunkt. Der direkte Vergleich mit einem neu
initialisierten Critic misst den Zusatzbeitrag des Vortrainings. Der
unveränderte BC-Actor dient als Referenz für den Nutzen der
anschließenden Actor-Updates insgesamt. Das Exposé verwendet
„IL-informed critic“ als Bezeichnung für diesen Einsatz von Returns aus
Rollouts einer durch Imitation gelernten Policy.
