# Imitation-Learning-Vorschlag und Zeitplan

- [proposal.tex](proposal.tex): englisches Exposé, drei Seiten. Eine nur aus Zweier-Demonstrationen gelernte BC-Policy soll eine nicht demonstrierte Aufgabe lösen, den Dreierturm. Einziges Lernsignal dafür sind Erfolg und Misserfolg eigener Versuche. Geprüft wird, ob ein darauf vortrainierter Critic („IL-informed critic“) Actor-Critic gegenüber BC und gegenüber Actor-Critic mit neuem Critic verbessert. Enthält Vorarbeiten aus diesem Repository, Hypothese, Abgrenzung (fester Sequencer, privilegierter Zustand, keine Dreier-Expertendaten im Training) und Ausblick.
- [schedule.tex](schedule.tex): separater Gantt-Zeitplan. Der Drei-Seed-Pilot legt Aktor-Beschränkung, kleinsten relevanten Effekt und Seedzahl des Hauptvergleichs fest (vgl. [AGENTS.md](../../../AGENTS.md), Abschnitt 1).
- [LITERATUR.md](LITERATUR.md): Originalarbeiten und ihre Bedeutung für die Datenfrage.
- [Exportierte PDFs](../../../output/pdf): `Imitation_Learning_Proposal_v2.pdf` und `Imitation_Learning_Gantt_v2.pdf`. Die älteren Exporte mit dem Präfix `Self_Imitation_Learning_` dokumentieren den früheren, engeren Entwurf.

## Bauen

LuaLaTeX aus dem Vorlagenordner verwenden, da die TU-Klasse Schrift- und Grafikpfade relativ auflöst. Aus dem Repository-Stamm:

```powershell
Push-Location tubs-latex-cd-lite-main
lualatex ../latex/projektarbeit_proposal/v2/proposal.tex
lualatex ../latex/projektarbeit_proposal/v2/proposal.tex
lualatex ../latex/projektarbeit_proposal/v2/schedule.tex
lualatex ../latex/projektarbeit_proposal/v2/schedule.tex
Pop-Location
```

Die Befehle erzeugen PDFs im Arbeitsverzeichnis; die Exportkopien unter `output/pdf/` müssen bei einer Aktualisierung gesondert ersetzt werden. Hinweise für Overleaf stehen am Anfang der beiden TeX-Dateien.
