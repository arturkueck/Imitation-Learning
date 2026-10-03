# Ungeklärte Punkte und Aussagegrenzen

Stand: 1. Oktober 2026. Diese Liste dokumentiert offene Verifikation und Interpretationsgrenzen. Sie ist **keine Methodenempfehlung und kein neuer Experimentplan**. „Ungeklärt“ bedeutet, dass die Wissensbasis die fragliche Aussage nicht als gesichert verwendet.

## Quellenstatus und Fassungen

| Gap-ID | Offener Punkt | Verifizierter Stand / Fundstelle | Konsequenz für Zitation |
|---|---|---|---|
| SBC-G1 | Journalvolltext und Änderungen gegenüber Preprint | RA-L 10(2):1952–1959, DOI verifiziert; gelesene Datei byteidentisch mit arXiv v1. IEEE-AAM HTTP 418, Autoren-PDF HTTP 404 | Inhaltsclaims nur mit **Preprint v1**, PDF-Seiten 1–8; keine Journal-Seiten oder finale Garantie ausgeben |
| DP-V1 | Vermischung RSS, arXiv v5 und IJRR | RSS-Original hat sieben Autoren und 12 Tasks; Journal hat acht Autoren, andere Reihenfolge, zusätzliche bimanuale Tasks | Hier durchgängig RSS-Claims; Journal nur Metadaten/Versionsabgrenzung |
| META-G1 | DOI für DAgger/DART | Offizielle PMLR-Einträge liefern keinen DOI | Offizielle URL verwenden; DOI nicht erfinden. „Nicht angegeben“ ist keine Behauptung, ein DOI könne nirgends existieren. |

## Widersprüche oder begrenzte Angaben im Originaltext — A mit B-Prüfung

| Gap-ID | Konkrete Fundstellen | Offener Punkt / Behandlung |
|---|---|---|
| ACT-G1 | RSS PDF S. 6, Algorithmus 1 versus §IV-C | Pseudocode schreibt MSE, Implementationstext L1. Beide gespeichert; tatsächlicher versionsgebundener Code-/Versuchsabgleich ungeklärt. |
| ACT-G2 | PDF S. 8, Tabelle III; S. 10, §V-C | „remaining 3“ in Caption/Text, tatsächlich vier zusätzliche reale Taskspalten. Inhalte/Ergebnisse nach den tatsächlichen Spalten, keine siebente/fehlende Aufgabe erfunden. |
| DART-G1 | CoRL PDF S. 8, §5.2; Abb. 3 | Zwei ausgeschriebene α-Formeln verwenden beide Faktor 3, die Bedingungsnamen sind DART-3 und DART-6. Keine stillschweigende Korrektur zum Faktor 6 als exakt zitierte Formel. |
| DART-G2 | PDF S. 8, Abb. 3 und §5.2; S. 2 | Caption spricht von head-mounted RGBD/Primesense, Text von eye-in-hand. Exakte in der Studie verwendete Policyperspektive aus diesen Angaben allein uneindeutig. |
| DART-G3 | PDF S. 8, Ergebnisabsatz | Testanzahlformulierung ungeschickt; S. 14 nennt explizit 20 Tests je Policy. Gerundete 49/79/72 % werden nicht zu vermeintlich exakten Erfolgscounts rückgerechnet. |
| DART-G4 | PDF S. 6/11, Proposition 4.1 | Support-/KL-Argument setzt geeignete Gaußverteilung und Supervisorannahme voraus. Singularität und measure-theoretische Details bei deterministischen kontinuierlichen Policies nicht neu bewiesen; keine universelle monotone Success-Verbesserung behauptet. |
| SBC-G2 | Preprint S. 3, Gl. (6) versus S. 4, Definition A₁ | Einmal ∇_uπ statt ∇_xπ. Dossier verwendet ausdrücklich den Roboterblock aus Gl. (6); finale Journal-Korrektur ungeklärt. |
| SBC-G3 | Preprint S. 4, Gl. (9)–(10) | Als B festgehalten: die gedruckte Exponential-Normschranke in (10) wächst mit Zeit. Sie belegt für sich keine zeituniforme Schranke. Keine stille stärkere Garantie ergänzt. |
| SBC-G4 | Preprint S. 4–5, Gl. (7)/(11) | ReLU(Re(σ)) bestraft positive Werte, nicht den Rand null. Ein minimierter Soft-Loss ist kein automatischer Beweis strikter Hurwitz-Stabilität in einer ganzen Nachbarschaft. Das ist B, nicht ein zusätzliches Autorentheorem. |
| DP-G1 | RSS PDF S. 4, §III-D versus S. 14, Appendix D / S. 15, Tabellen VI–VII | Haupttext nennt 100 Train-/10 Inferenz-Diffusionsschritte und 0,1 s auf RTX 3080; Appendix nennt 16 reale Inferenzschritte. Bezug zur gleichen gemessenen Konfiguration ungeklärt; lokale 10 DDIM-Schritte separat C. |
| DP-G2 | PDF S. 6, Tabelle III versus S. 7, §V-A4 | Kitchen 656 Demos in Tabelle, 566 im Text. Exakter verwendeter Umfang ungeklärt; beide Werte erhalten. |
| DP-G3 | PDF S. 6, Tabelle III versus S. 15, Appendix I | Sauce Pour/Spread jeweils 90 PH in Tabelle, 50 Demos und 90 % Training in Appendix. Kein eindeutiger Datasetcount ohne weiterführenden Versions-/Codeabgleich. |
| DP-G4 | PDF S. 9, §VI-B | LSTM-GMM Mug Flip wird mit einer Teilmenge derselben Daten trainiert. Exakter Teilmengenfaktor hier nicht angegeben; kein datengleicher Vergleich behauptet. |
| DP-G5 | PDF S. 10, Abb. 11 und Begleittext | Pour-Success 0,79, zugleich an anderer Stelle zwanzig Versuche beschrieben. Ohne Rohdaten kein exakter ganzzahliger Successcount rekonstruiert. |
| DP-G6 | PDF S. 2–3, Gl. (3)/(5) | Vorwärtsrausch-Formel ist schematisch additiv. Konkrete DDPM/DDIM-Skalierung und Schedulerimplementierung nicht aus dieser Gleichung allein reproduzierbar. |

Widersprüche wurden anhand der Originalseiten geprüft, nicht automatisch aus kaputter Textextraktion übernommen. ACT S. 6/8, DART S. 8, Stable-BC S. 4/5 und DP S. 6/15 wurden zusätzlich visuell geprüft.

## B/C: Projektbezogene Wissensgrenzen

| Gap-ID | Was offen ist | Was bereits belegt ist | Zulässige Verwendung |
|---|---|---|---|
| OUR-G1 | Wie groß der lokale Train-/Rollout-State-Shift quantitativ ist und ob er Hauptursache des Scheiterns ist | Andere Erfolgsraten und Phasenprofile | Covariate Shift als Literaturmotiv, lokale Ursache als ungeklärt |
| OUR-G2 | Ob zwei Frames die Expertphase hinreichend bestimmen | Expert hält Phase/Ziel/Verweildauer; Policy erhält nicht diese internen Variablen | Partial Observability als mögliche Erklärung B, kein gemessener Mechanismus |
| OUR-G3 | Ob mehrere korrekte Aktionen/Chunks für dieselbe Policyeingabe empirisch relevant sind | Deterministischer Expertcode mit Gedächtnis | Keine automatische Gleichsetzung „programmierter Expert = beobachtungsbedingt unimodal“ |
| OUR-G4 | Korrekte Oraclelabels an Fehlzuständen und für folgende Chunkpositionen | Nur nominal erfolgreiche Expert-Demos geprüft | DAgger-/DART-Übertragung nur konzeptionell einordnen |
| OUR-G5 | Lokale Jacobians/Robot-/Kontaktdynamik und ursprüngliche Stable-BC-Annahmen | Liftfinite-difference-Modul ist eine andere Approximation; Stack hat Queue/Kontakte | Keine Original-Stable-BC-Garantie auf Projektcode übertragen |
| OUR-G6 | Welche Veränderung zwischen Direct/Diffusion kausal wirkt | Vergleich repliziert beide kompletten Modellkonfigurationen | Ergebnis auf Konfigurationsebene, keine reine Objective-Ablation |
| OUR-G7 | Allgemeine Prognosekraft der Offline-Transportmerkmale | Gepoolte Korrelationen und drei Direct-Seedwerte | Deskriptive Diagnose, keine validierte Vorhersagemetrik |
| OUR-G8 | Umfassende Störungsrobustheit von State-Stack über definierte Störungsverteilungen | Vierzig identische nominale Starts und stabile Success-Tails in der Replikation | Nominale Startvariation nicht als allgemeiner Robustheitsbenchmark bezeichnen |
| OUR-G9 | Abgeschlossene kausale Diffusionsfehleranalyse | Zusatzbericht war beim Lesen noch Zwischenstand | Nur finalen Replikationsvergleich als abgeschlossenen Hauptbefund verwenden |

## Fehlende Details, die nicht rekonstruiert wurden

Nicht tabellierte Diagrammwerte von DAgger, DART und Stable-BC werden qualitativ oder über ausdrücklich genannte Textzahlen beschrieben. Die Wissensbasis behauptet keine exakten Rohmittelwerte aus Pixelpositionen. Nicht genannte Standardabweichungen, statistische Tests, Trainingsseeds oder Samplecounts werden nicht ergänzt.

Es wurde keine vollständige Code-Reproduktion der fünf Originalmethoden durchgeführt. Aussagen über Originalmethoden beziehen sich auf die gelesenen Paperfassungen. Laufzeiten aus anderer Hardware sind keine lokalen Budgetschätzungen. Ein Seitenbeleg für eine theoretische Behauptung ersetzt nicht die Prüfung ihrer Voraussetzungen im Projekt.

## Regeln für eine spätere Auflösung

Bei neuer Quellenfassung: Dateihash und Fassung speichern, vorhandene Stelle direkt vergleichen und Seiten-/Gleichungsänderung dokumentieren. Ein Gap wird erst als gelöst markiert, wenn der widersprüchliche Punkt eindeutig belegt ist. Bei neuen Projektergebnissen C mit lokalem Protokoll ergänzen; Literaturclaims A werden dadurch weder bestätigt noch widerlegt. Diese Datei hält Wissenslücken sichtbar und priorisiert keine neue Methode.
