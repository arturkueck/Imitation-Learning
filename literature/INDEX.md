# Literatur-Wissensbasis: Behavioural Cloning und State-Stack

Stand: **1. Oktober 2026**. Diese Basis dokumentiert fünf Primärarbeiten für einen späteren wissenschaftlichen Bericht. Sie enthält keine Methodenempfehlung und keine neuen Experimente.

## Einstieg und Navigation

| Datei | Zweck |
|---|---|
| [CLAIMS.md](CLAIMS.md) | Thematisch geordnete, einzeln belegte Aussagen; stabile Claim-IDs |
| [BIBLIOGRAPHY.md](BIBLIOGRAPHY.md) | Verifizierte Publikationsdaten, Versionsunterscheidung, BibTeX |
| [GAPS_AND_QUESTIONS.md](GAPS_AND_QUESTIONS.md) | Ungeklärte Quellenpunkte und Grenzen der Projektaussagen |
| [DAgger](methods/dagger.md) | Interaktive Datenaggregation und bedingte theoretische Garantien |
| [DART](methods/dart.md) | Störungen während der Demonstration und Korrekturlabels |
| [Stable-BC](methods/stable_bc.md) | Lokale Fehlerdynamik und Stabilitätsregularisierung |
| [ACT](methods/act.md) | Chunking, CVAE, Transformer und temporales Ensembling |
| [Diffusion Policy](methods/diffusion_policy.md) | Konditionierte Aktionsdiffusion und Receding Horizon |
| [Methodenvergleich](comparisons/method_comparison.md) | Unterschiede in Mechanismus, Voraussetzungen und Evidenz |
| [Bezug zu unseren Ergebnissen](comparisons/relation_to_our_results.md) | Getrennte Literatur- und Projektevidenz |

## Verbindliche Leseregeln

**A = Quellenaussage.** Behauptung der Autoren, mit belegter Fassung und Seite. Ein theoretischer Satz gilt nur unter seinen Annahmen. Ein berichteter Erfolg gilt für die jeweilige Versuchskonfiguration.

**B = eigene Interpretation.** Analytische Einordnung, die nicht als Aussage der Autoren zitiert werden darf.

**C = Projektbezug.** Verknüpfung mit lokalen Daten, Code oder Berichten. C ist entweder ein belegter Projektbefund oder ausdrücklich eine ungetestete Übertragungsannahme. Literaturergebnisse sind keine lokalen Messungen.

Evidenzklassen: **T** = theoretischer Satz/Herleitung unter Annahmen; **M** = Methodenbeschreibung; **E** = quantitative experimentelle Autorenangabe; **Q** = qualitative Beobachtung; **L** = von Autoren explizit genannte Grenze; **H** = Motivation/Hypothese der Autoren. Ein **P-** vor diesen Klassen kennzeichnet eine ausschließlich im Preprint geprüfte Stelle. Das ist besonders für Stable-BC relevant.

Die Claim-IDs `DAG-01` bis `DAG-10`, `DART-01` bis `DART-10`, `SBC-01` bis `SBC-10`, `ACT-01` bis `ACT-10` und `DP-01` bis `DP-10` werden bei späteren Ergänzungen nicht umnummeriert. Jede ID hat genau einen kanonischen Eintrag in CLAIMS.md. Die zehn Fundstellen pro Paper verweisen auf diese Einträge. Kapitelpositionen und Verwendungsvorschläge sind B, keine zusätzliche Evidenz.

## Seiten- und Versionskonvention

Eine **PDF-Seite** zählt ab der ersten Seite der eingefrorenen Datei mit 1. Fundstellen geben eine konkrete PDF-Seite und einen Abschnitt bzw. eine Tabelle an. Ein Abschnitt kann auf einer anderen Seite beginnen. Keine Seitenzahl wurde aus einer Suchvorschau übernommen.

| Quelle | Gelesene Fassung und Umfang | Zitierkonvention |
|---|---|---|
| DAgger | AISTATS/PMLR-PDF, 9 Seiten; Text S. 1–8 einschließlich Theorie und Experimente, Literatur S. 9 | PDF S. n; bibliographische Proceedings-Paginierung 627–635. Das heruntergeladene PDF zeigt keine laufenden Proceedings-Seitenzahlen. |
| DART | CoRL/PMLR-PDF, 14 Seiten; Haupttext S. 1–8, Beweise/Zusatzexperimente/Roboterevaluation S. 10–14; Referenzen S. 9–10 | PDF S. n = im PDF gedruckte lokale Seite n; bibliographischer Umfang 143–156 |
| Stable-BC | Vorhandenes 8-seitiges PDF vollständig gelesen; SHA-256 identisch mit arXiv:2408.06246v1 | **Preprint v1, PDF S. n**. RA-L-Journalmetadaten verifiziert, finaler Journalvolltext nicht zugänglich; keine Umrechnung zu 1952 ff. |
| ACT | RSS-Original-PDF, 19 Seiten; Haupttext S. 1–11, Architektur/Details/Limitationen/Hyperparameter S. 15–19 | PDF S. n = gedruckte Seite n; Paper-ID 016 ist keine Seite |
| Diffusion Policy | RSS-Original-PDF, 16 Seiten; Haupttext S. 1–11, Appendix S. 14–16 | PDF S. n = gedruckte Seite n; Claims beziehen sich auf RSS 2023, nicht die erweiterte IJRR-Fassung |

Für vier Arbeiten beruhen die Inhaltsclaims auf der peer-reviewten Originalpublikation. **Stable-BC ist ein offener Versionsfall:** Das Paper ist peer-reviewed in RA-L 2025 publiziert; der hier tatsächlich geprüfte Inhalt stammt aus dem ausdrücklich gekennzeichneten Preprint. Eine inhaltliche Gleichheit mit der Journalfassung ist nicht nachgewiesen.

## Provenienz und Prüfung

Die eingefrorenen PDFs, seitenweise Textauszüge und SHA-256-Werte liegen in [_research](_research/manifest.json). Die Hashes binden Seitenbelege an konkrete Dateien. `acquire.py`, `read_pages.py` und `render_checks.py` dokumentieren die Extraktion. Kritische Tabellen und Gleichungen wurden zusätzlich als Seitenbilder geprüft: DART S. 8; Stable-BC S. 4–5; ACT S. 6 und 8; Diffusion Policy S. 6 und 15. Rohtext kann Formeln und Spalten fehlerhaft zusammenführen; er ist kein Ersatz für das PDF.

Vorab gelesen wurden [next_research_direction.md](../next_research_direction.md), die [Projektbeschreibung](../Projektarbeit%20Themenvorschlag%20--%20Artur.md), README sowie die vorhandenen Literaturdateien unter `latex/plan_a` und `latex/plan_b`. Diese älteren Literaturübersichten dienen nur als Recherchekontext. Empfehlungen aus ihnen werden hier nicht übernommen. Projektzahlen wurden mit dem Replikationsbericht und dessen eingefrorenem Protokoll abgeglichen; relevante Wrapper- und Expert-Eigenschaften zusätzlich im Code geprüft.

Zitate sind absichtlich sparsam: pro Paper höchstens ein kurzer Originalauszug; die übrigen Stellen enthalten präzise Paraphrasen. Bei Widersprüchen werden beide Stellen genannt und die Auflösung bleibt ungeklärt. Aus Diagrammen wurden keine scheinexakten Werte abgelesen. [Lese-/Prüfprotokoll](_research/READING_LOG.md) und [struktureller Audit](_research/validation.json) dokumentieren den Umfang; der Audit prüft keinen wissenschaftlichen Inhalt automatisch.

## Pflege für den wissenschaftlichen Bericht

Beim Schreiben zuerst Claim-ID und Fassung prüfen, dann die angegebene PDF-Seite öffnen. A und B/C sprachlich getrennt halten. Für jeden Zahlenvergleich Modalität, Datenquelle, Aktionsraum, Erfolgskriterium, Trainingsbudget und Checkpointauswahl mitführen. Bei neuen Experimenten nur C ergänzen; A bleibt an die unveränderte Primärquelle gebunden. Versionswechsel erfordern einen erneuten Seitenabgleich und einen dokumentierten Änderungsgrund.
