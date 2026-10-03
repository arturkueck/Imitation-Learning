# Lese- und Prüfprotokoll

Bearbeitung: 1. Oktober 2026. Dieses Protokoll beschreibt tatsächlich ausgeführte Quellensichtung. Es ersetzt nicht die Inhaltsdossiers.

## Vorabkontext

Gelesen: `next_research_direction.md`, `Projektarbeit Themenvorschlag -- Artur.md`, `README.md`, `latex/plan_a/OVERVIEW_AND_LITERATURE.md`, `latex/plan_b/OVERVIEW_AND_LITERATURE.md`, `latex/plan_a/COMPARATIVE_REVIEW.md`. Wegen des heutigen State-Stack-Fokus sind frühere Lift-Empfehlungen Kontext, keine neue Auswahlentscheidung.

Zusätzlich für C gelesen: Replikationsbericht, Protokoll, forensischer Diffusions-Zwischenbericht; Direct-Modell/Queue, Fensterbildung, Expertzustand sowie relevante Loss-/Shapeabschnitte der Lift-Kontraktion. Zusätzlich die Direct-/Diffusionskonfigurationen für Seed 2 und der Replikations-Evaluationscode: gespeicherter Diffusionshorizont 8, Laufzeitoverride auf 2 verifiziert. Die lokalen Success-Abschnitte der Umgebung wurden geprüft; ihr interner Stabilitätscheck und die zusätzliche 40-Frame-Evaluationsnachlaufzeit sind unterschiedliche Prüfungen. Hashes am finalen Audit: `project_manifest.json`. Berichtsangaben wurden nicht durch neue Trainings- oder Simulatorläufe reproduziert.

## Volltexte

| Paper | Tatsächlich geprüfte Abschnitte | Prüfart |
|---|---|---|
| DAgger | PDF S. 1–8: Einführung, Notation/BC, Forward/SMILe, DAgger, theoretische und finite-sample Analyse, sämtliche Experimente und Future Work | Volltext seitenweise; S. 4–6 gezielt erneut gelesen |
| DART | S. 1–8: Haupttext vollständig; S. 10–14: Beweise, MLE/Scaling, Hyperparameter, zusätzliche Shift-/Kovarianzexperimente, HSR-Erfolgstest; Referenzen S. 9–10 | Volltext seitenweise; S. 8 als Bild geprüft |
| Stable-BC | v1 S. 1–8 vollständig: Problem, Linearisierung, model-based/model-free Loss, drei Simulationen, reale Studie, Conclusion | Lokales PDF und arXiv-v1 bytegleich; S. 4–5 als Bilder, Formeln abgeglichen |
| ACT | S. 1–11 Haupttext vollständig; S. 15–19 Appendix A–F, Architektur, Hyperparameter und zusätzliche Fehlversuche; S. 7 ist Task-Abbildung | Volltext seitenweise; S. 6/8 als Bilder; Methoden/Tabellen/Limitationen erneut gelesen |
| Diffusion Policy | S. 1–11 Haupttext vollständig; S. 14–16 Appendix A–J, einschließlich Scaling, Horizonte, Effektaggregation und Hardwareevaluation | Volltext seitenweise; S. 6/15 als Bilder; Limitations S. 11 erneut gelesen |

Nicht vollständig gelesen: spätere IJRR-Diffusion-Policy-Erweiterung, nicht zugänglicher RA-L-Stable-BC-Journalvolltext und externe Nachfolgearbeiten. Keine Inhaltsclaims aus diesen ungelesenen Fassungen.

## Metadaten und Quellenzugang

PMLR-/RSS-Webeinträge mit Titelseiten abgeglichen. Stable-BC- und IJRR-DOI-Datensätze von Crossref abgerufen und gespeichert. IJRR-Druckdatum dort September 2025; zuerst online 11. Oktober 2024. Die unversionierte arXiv-Diffusion-Policy-Seite führt heute eine erweiterte v5 mit geändertem Autorensatz.

Stable-BC-IEEE-Artikelansicht bot lediglich JavaScript-/Botprüfung; direkter AAM-Abruf HTTP 418; Autorenprojekt-PDF HTTP 404. Danach frei zugängliches arXiv v1 geladen und mit lokalem PDF verglichen. Inhaltliche Gleichheit mit der Journalfassung bleibt ungeklärt. Keine Paywall- oder Zugriffssperre umgangen.

## Nachweisgrenzen

Textauszüge sind zum schnellen Finden archiviert; die Layout-Extraktion kann zwei Spalten zusammenführen. Gleichungen und kritische Tabellen wurden deshalb gegen das Seitenbild geprüft. Originalzitate sind insgesamt je Paper unter 25 Wörtern und werden auf ihrer angegebenen Seite nachgeschlagen; Auslassung eines Originalzitats bedeutet nicht, dass die Stelle ungelesen ist.

Die endgültigen Markdown-Dateien enthalten 14 Felder pro Dossier und zehn Belegstellen je Paper. Der strukturelle Audit prüft Anzahl, eindeutige IDs, gültige PDF-Seiten, Zitatfundstellen, lokale Linkziele, Dateihashes und Preprintmarkierung. Wissenschaftliche Paraphrasen, Einschränkungen und die A/B/C-Trennung wurden anhand der gelesenen Quellen redaktionell geprüft; dies ist keine unabhängige zweite Begutachtung.
