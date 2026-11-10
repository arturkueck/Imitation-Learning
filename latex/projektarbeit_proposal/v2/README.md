# Self-Imitation-Vorschlag und Zeitplan

- [proposal.tex](proposal.tex): englischer Projektvorschlag; BC- und Critic-Terme sind farblich getrennt.
- [schedule.tex](schedule.tex): separater Gantt-Zeitplan.
- [Exportierte PDFs](../../../output/pdf): `Self_Imitation_Learning_Proposal_v2.pdf` und `Self_Imitation_Learning_Gantt_v2.pdf`.

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
