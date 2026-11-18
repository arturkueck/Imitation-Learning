# Imitation-Learning-Vorschlag und Zeitplan

- [proposal.tex](proposal.tex): englisches Exposé zu begrenzten Demonstrationsdaten und Generalisierung beim simulierten Würfelstapeln. Die Literatur führt von Imitation Learning über Self-Imitation zur Frage, ob ein vortrainierter Critic Actor-Critic gegenüber BC und Actor-Critic mit neuem Critic verbessert.
- [schedule.tex](schedule.tex): separater Gantt-Zeitplan mit den Meilensteinen für diesen Vergleich.
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
