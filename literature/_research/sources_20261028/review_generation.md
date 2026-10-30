# Quellenprüfung: DemoGen und PSD Data Quality

Geprüfte Fassungen: DemoGen arXiv:2502.16932v1 (18 PDF-Seiten), PSD arXiv:2605.01544v2 (8 PDF-Seiten). Ein aktueller Konferenzannahmestatus wurde nicht zusätzlich recherchiert; `venue` beschreibt die tatsächlich geprüfte Preprintfassung. Die Titel-/Autorenangaben stammen aus den PDFs. Wichtig: Die PSD-v2-Titelseite nennt Noushad Sojib, **Sajay Arthanat** und Momotaz Begum; ältere Metadaten mit nur zwei Autoren sind für diese Fassung unvollständig.

Die 12 deutschen Keynotes in `review_generation.json` sind Paraphrasen. `projectRelevance` enthält ausdrücklich eigene Übertragungsüberlegungen. Alle Fundstellen wurden in den vorhandenen nummerierten Lesefassungen gelesen; Zahlen aus den ausgewählten Ergebnistabellen wurden visuell gegengeprüft.

## Visuelle Prüfung

- `demogen_p09_qa.png`: mit Poppler `pdftoppm` gerenderte PDF-Seite 9, visuell geprüft. Tabelle III: 530 Rollouts, acht Aufgaben, fünf Wiederholungen pro Konfiguration und Mittelwerte 11,0/74,6 bestätigt. Linke Spalte bestätigt einmalige Ausgangsbewegung plus zwei Wiederholungen für Punktwolken sowie gezielt zu den Evaluationspositionen erzeugte Daten.
- `psd_quality_p06_qa.png`: gerenderte PDF-Seite 6, visuell geprüft. Tabelle II: drei Seeds und 50-%-Filterung, Mittelwerte 0,58/0,74 sowie bildbasiertes RoboMimic-Square 0,87/0,85 bestätigt. Tabelle IV: Personenmittelwerte 0,15/0,38, Beibehalten von 60 % und 20 Rollouts im Text bestätigt.

## Extraktionsgrenzen

- Nichtleere Layoutzeilen verbinden bei zweispaltigem Satz oft Text beider Spalten. Die Locator-Beschreibung nennt deshalb die relevante Spalte und den Abschnitt. Zeilennummern sind ausschließlich lokale Suchhilfen.
- Tabellenzeilen stehen in der Extraktion teilweise hinter dem Fließtext, obwohl die Tabellen im PDF oben erscheinen. Die Keynotes kennzeichnen dies; Seitenzahl und Tabellennummer bleiben maßgeblich.
- DemoGen enthält gerasterte/rotierte Abbildungstexte, die pypdf nicht vollständig erfasst. Aussagen basieren nicht auf ausgelassenen Beschriftungen.
- Formeltypografie in PSD wird nicht vollständig erhalten (z. B. Summenzeichen/Indizes); die Notizen beschreiben den Algorithmus in Worten und erheben keinen Anspruch auf eine mathematische Validierung.
- PSDs pauschale positive Formulierung im Fließtext wird durch Tabelle II begrenzt: bildbasiertes RoboMimic-Square verbessert sich nicht. Das Gegenbeispiel ist ausdrücklich dokumentiert.
- Die lokalen Projektmetriken wurden nicht mit den Paperquoten gleichgesetzt. Insbesondere sind 74,6 % DemoGen keine Mehrwürfelturmquote und PSD-Glätte kein Turmerhaltmaß.
