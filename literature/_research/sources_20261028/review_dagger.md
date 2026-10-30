# Quellenprüfung: Policy-Calibrated DAgger und Reward-DAgger

Prüfung am 28.–29.10.2026 anhand der von `acquire_20261028.py` eingefrorenen PDFs und `.numbered.txt`-Lesefassungen. Keine Trainingsläufe und keine neuen Experimente.

- **Policy-Calibrated DAgger:** arXiv:2609.30462v1, 8 Seiten. Methodik und Voraussetzungen auf PDF-Seiten 3–5, Ergebnisprotokoll auf S. 6–7 gelesen. Seite 6 mit Poppler gerendert und visuell geprüft: Tabelle I/II, Szenarienzahl, Wiederholungen, DAgger-Linien und Standardfehler stimmen mit den Keynotes überein. Insbesondere 3D bleibt Simulation trotz realem Scan; RRT-Orakel ist Teil des Experiments. Behauptungen einer orakelfreien vollständigen Versuchspipeline wären falsch. Review-Status ICRA 2027 stammt aus den zuvor geprüften arXiv-Metadaten, nicht aus einer Annahmebestätigung.
- **Reward-DAgger:** arXiv:2610.04054v1, 11 Seiten. Methode S. 3, Setup S. 4, Transfer S. 5–6, Realrobotergrenzen S. 7 und Limitationen S. 8 gelesen. Seite 6 mit Poppler gerendert und visuell geprüft: Die Extraktion verschiebt Tabelle II ans Seitenende und lässt Tabellenzellen zusammenlaufen. Die Originalansicht bestätigt Tabelle III und Stack-Erfolg 65/75/80 %. Quellaufgaben-Kalibrierung nicht als vollständig kalibrierungsfreies Verfahren darstellen; nur spätere Zielaufgaben und Updates nutzen das feste Gate.

Die Layout-Extraktion verbindet teilweise linke und rechte Spalten in derselben Zeile. Deshalb enthalten alle Vermerke Spalten-/Abschnittsangaben. Formeln werden im Text teilweise beschädigt; Keynotes paraphrasieren die methodischen Aussagen und leiten keine neuen Formelergebnisse aus der Extraktion ab. Eigene Projektbezüge stehen ausschließlich im Feld `projectRelevance` und sind als Einordnung markiert.

Visuelle Prüfbilder: `policy_calibrated_dagger_p6.png`, `reward_dagger_p6.png` (interne Prüfartefakte).

Ergebnis: 12 deutsche Keynotes. Jede Fundstelle wurde gegen den nummerierten Text gelesen; wichtige Ergebnistabellen zusätzlich im PDF-Bild kontrolliert. Keine vollständige mathematische Replikation oder umfassende Peer-Review-Prüfung behauptet.
