from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent / 'keynote_sources'

# Each locator: PDF page, first/last nonempty layout row, column/section.
PAPERS = [
('dagger', 'DAgger — Ross, Gordon und Bagnell (2011)', 'AISTATS/PMLR-Original, 9 PDF-Seiten.', [
('Problem', 'Eigene Aktionen verändern die späteren Beobachtungen. Dadurch ist die i.i.d.-Annahme klassischen überwachten Lernens im Rollout verletzt.', [(1,14,30,'rechte Spalte, Einleitung')]),
('BC-Lernziel', 'Klassisches BC minimiert den Imitationsverlust auf Expertenzuständen; das eigentliche Imitationsziel bewertet dagegen die durch die Policy selbst erzeugte Zustandsverteilung.', [(2,13,25,'rechts, §2, Gl. (1)'),(2,28,36,'rechts, §2.1, Gl. (2)')]),
('Fehlerakkumulation', 'Theorem 2.1 liefert unter den genannten 0–1-Surrogatloss- und Kostenannahmen den Worst-Case-Term T²ε. Das ist keine allgemeine Vorhersage empirischer Fehlerkurven.', [(2,38,49,'rechts, Theorem 2.1')]),
('Algorithmus', 'DAgger sammelt Rollouts, lässt die besuchten Zustände vom Experten labeln und trainiert auf dem aggregierten Datensatz. Die Policy wird anhand von Validierung ausgewählt.', [(4,2,13,'links, Algorithmus 3.1')]),
('Expertmischung', 'Die Erhebung kann Expert- und Learneraktionen mischen; der mittlere Expertanteil soll gegen null gehen. Expertlabels bleiben Teil der Datenerhebung.', [(4,26,44,'links, §3'),(4,7,10,'links, Algorithmus 3.1')]),
('Empirischer Umfang', 'Die Originalarbeit untersucht SuperTuxKart, Super Mario und OCR. Ihre Experimente sind kein direkter Nachweis für robotisches Stack- oder Multitask-Lernen.', [(2,27,39,'links, Einleitung')]),
]),
('dart', 'DART — Laskey et al. (2017)', 'CoRL/PMLR-Original, 14 PDF-Seiten.', [
('Mechanismus', 'Rauschen wird während der Expertenausführung injiziert. Der Expert demonstriert dadurch echte Korrekturen; anschließend wird auf diesen Demonstrationen überwacht gelernt.', [(4,23,35,'§4, links neben Abb. 1'),(4,43,47,'§4, Gl. (2)')]),
('Rauschwahl', 'Richtung und Größe des Rauschens sollen die Fehler der späteren Policy annähern. DART optimiert ein parametrisiertes Rauschmodell statt beliebiges Rauschen zu verwenden.', [(2,14,21,'§1')]),
('Daten', 'Die reale HSR-Studie verwendet vier Demonstratoren. Pro untersuchter Bedingung wird die finale Policy mit 40 Demonstrationen trainiert: zehn anfänglichen und 30 zusätzlichen.', [(8,18,28,'§5.2')]),
('Ergebnis mit Erfolgskriterium', 'Berichtet werden 79 % für DART α=3 gegenüber 49 % für BC. Erfolg betrifft Zielidentifikation und freien Greifpfad; danach folgt ein Open-loop-Greifplan.', [(8,29,37,'§5.2')]),
('Rauschstärke als Grenze', 'DART α=6 erreicht 72 %. Die Autoren vermuten zu starkes Rauschen für den menschlichen Demonstrator; mehr Rauschen ist hier nicht automatisch besser.', [(8,33,37,'§5.2')]),
('Offener Kamerawiderspruch', 'Abb. 3 beschreibt eine kopfmontierte RGB-D-Kamera, der Fließtext eine Eye-in-hand-Perspektive. Die Kameramontage deshalb nicht ohne Klärung eindeutig zitieren.', [(8,1,4,'Bildunterschrift Abb. 3'),(8,10,16,'§5.2')]),
]),
('stable_bc', 'Stable-BC — Mehta et al. (Preprint 2024)', 'arXiv:2408.06246v1, 8 PDF-Seiten. RA-L 2025 ist bibliographisch bekannt; diese Fundstellen belegen ausschließlich v1, nicht die Journalfassung.', [
('Intervention', 'Stable-BC verändert das Lernverfahren über Stabilitätsbedingungen; der Trainingsdatensatz muss dafür nicht verändert werden.', [(2,7,12,'links, Beitragsübersicht')]),
('Voraussetzungen', 'Roboterzustand x und Umgebungszustand y werden getrennt. Ein genaues Modell der Roboterdynamik f wird vorausgesetzt; die Umgebungsdynamik g darf unbekannt sein.', [(2,25,44,'rechts, §III')]),
('Lokale Analyse', 'Die Arbeit linearisiert gekoppelte Fehlerdynamiken und untersucht die Eigenwerte der Matrix A. Der Bezug ist lokale Stabilität nahe demonstriertem Verhalten.', [(3,17,31,'rechts, §IV-A')]),
('Loss und Parameter', 'Im modellbasierten Fall ergänzt eine Strafe auf positive Realteile der Eigenwerte den BC-Loss. λ steuert das relative Gewicht.', [(4,2,21,'links, Gl. (7) und Erläuterung')]),
('Stabilität ≠ Aufgabenerfolg', 'Die Autoren erklären ausdrücklich, dass Stabilität allein keine korrekte Aufgabenausführung sicherstellt; eine Policy könnte lokal stehen bleiben.', [(3,45,58,'rechts, Stability vs. Performance')]),
('Grenze von model-free', 'Ohne g wird eine Schranke für die Abweichung des Umgebungszustands angenommen. Die Methode bleibt von f abhängig und liefert keine uneingeschränkte globale Taskgarantie.', [(4,22,45,'links, §IV-C'),(2,29,31,'rechts, Robot')]),
]),
('act', 'ACT — Zhao et al. (2023)', 'Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware, RSS-Original, 19 PDF-Seiten.', [
('Action Chunking', 'ACT sagt Sequenzen von k Aktionen voraus. Die Autoren motivieren dies mit einem kürzeren effektiven Entscheidungshorizont und zeitlichen Abhängigkeiten menschlicher Demonstrationen.', [(5,35,45,'links, §IV-A'),(5,5,15,'rechts, Fortsetzung §IV-A')]),
('Temporal Ensembling', 'Bei jedem Zeitschritt neu vorhergesagte Chunks überlappen. Gemittelt werden Vorhersagen für denselben Ausführungszeitpunkt; dadurch entstehen zusätzliche Inferenzkosten.', [(5,16,37,'rechts, §IV-A')]),
('Generatives Training', 'ACT wird als CVAE trainiert. Zur Ausführung wird der Encoder verworfen und z auf null gesetzt; die beschriebene Decodierung ist damit deterministisch.', [(6,27,43,'links, §IV-B')]),
('Eingaben und Aktionen', 'Die beschriebene Policy nutzt vier RGB-Bilder mit 480×640 Pixeln und Gelenkpositionen. Ausgaben sind absolute Zielgelenkpositionen beider Arme, insgesamt 14 Dimensionen pro Schritt.', [(6,13,24,'rechts, §IV-C')]),
('Trainingsbedingungen', 'Die Autoren nennen ungefähr 80 Millionen Parameter, Training von Grund auf pro Aufgabe und etwa fünf Stunden auf einer RTX 2080 Ti. Diese Zahlen sind setupspezifisch.', [(6,46,50,'rechts, §IV-C')]),
('Offene Loss-Diskrepanz', 'Algorithmus 1 nennt MSE als Rekonstruktionsloss; der Implementierungsabschnitt nennt L1 statt L2. Die konkrete Losswahl nur mit dieser Versionsdiskrepanz wiedergeben.', [(6,11,13,'links, Algorithmus 1'),(6,39,44,'rechts, §IV-C')]),
]),
('diffusion_policy', 'Diffusion Policy — Chi et al. (2023)', 'RSS-Original, 16 PDF-Seiten; keine Übertragung der Belege auf die spätere IJRR-Erweiterung.', [
('Grundidee', 'Das Diffusionsmodell erzeugt Roboteraktionen durch einen auf Beobachtungen konditionierten Denoising-Prozess.', [(3,7,14,'links, §II-C')]),
('Ausführungshorizonte', 'Aus To Beobachtungsschritten werden Tp Aktionen vorhergesagt; nur Ta davon werden vor erneuter Planung ausgeführt. Beobachtungs-, Vorhersage- und Ausführungshorizont sind verschiedene Parameter.', [(3,15,28,'links, §II-C')]),
('Backbone-Abwägung', 'Die Autoren berichten für Transformer gute Ergebnisse bei komplexen oder schnell wechselnden Aktionen, aber höhere Hyperparametersensitivität. Sie schlagen CNN als ersten Versuch vor.', [(4,8,21,'links, §III-A')]),
('Kameraverarbeitung', 'Unterschiedliche Ansichten erhalten separate Encoder. ResNet-18 wird ohne Vortraining gemeinsam mit der Policy trainiert; Spatial Softmax und GroupNorm ersetzen Standardkomponenten.', [(4,23,35,'links, §III-B')]),
('Multimodalität', 'Stochastische Initialisierung und Sampling erlauben mehrere Aktionsmodi. Abb. 4 illustriert alternative Wege um ein Objekt; das ist ein konkretes Beispiel, keine universelle Generalisierungsgarantie.', [(4,6,25,'rechts, §IV-A'),(4,33,39,'rechts, Abb. 4')]),
('Inferenzkosten', 'DDIM erlaubt weniger Denoising-Schritte bei der Inferenz. Berichtet werden 100 Trainings- gegenüber zehn Inferenzschritten und etwa 0,1 s Latenz auf einer RTX 3080.', [(4,46,56,'links, §III-D')]),
]),
('umi', 'UMI — Chi et al. (2024)', 'RSS-Original p045, 14 PDF-Seiten; eigens aus den Proceedings geladen, nicht mit der vorhandenen unversionierten latex-Datei gleichgesetzt.', [
('Erhebung', 'UMI verwendet einen handgeführten Parallelgreifer mit GoPro als Sensor und Aufnahmegerät; für bimanuale Demonstrationen kommt ein zweiter Greifer hinzu.', [(4,1,9,'links, §III-A')]),
('Kameramontage', 'UMI nutzt ausschließlich Wrist-Kameras. Bei Demonstration und Roboterausführung bleibt ihre Montage relativ zu den Greiferfingern gleich, um Beobachtungsunterschiede zu reduzieren.', [(4,18,29,'links, HD1')]),
('Bildinformation', 'Ein 155°-Fisheye erweitert den Kontext; Seitenspiegel liefern zusätzliche Perspektiven für implizite Tiefeninformation.', [(2,1,3,'Abb. 2'),(4,34,46,'rechts, HD3')]),
('Zeit und Aktionen', 'Beobachtungen werden zeitlich abgeglichen; veraltete Aktionen verworfen. Vorhergesagte Posen beziehen sich auf dieselbe aktuelle Endeffektorpose.', [(6,1,11,'links, PD1.1'),(6,22,42,'links, PD1.2/PD2')]),
('Kameraablation', 'Beim Cup Arrangement: 305 Demonstrationen, 20 Testfälle; UMI erreicht 20/20, die auf 69° entzerrte/beschnittene Bildvariante 11/20. Dies isoliert nicht allein die Kameraposition.', [(7,24,28,'links, Performance'),(7,14,25,'rechts, No Fisheye lens')]),
('Generalisierungsziel', 'Die Generalisierungsfrage betrifft unbekannte Umgebungen und Objekte. Die Capability-Tests verwenden vier Aufgaben mit randomisierten Starts in der Erhebungsumgebung.', [(6,33,40,'rechts, §IV'),(6,52,56,'rechts, §V')]),
]),
('libero', 'LIBERO — Liu et al. (2023)', 'NeurIPS Datasets and Benchmarks, offizielles Proceedings-PDF, 16 Seiten.', [
('Problemdefinition', 'Eine aufgabenkonditionierte Policy lernt Aufgaben nacheinander. Frühere Aufgabendaten sind beim Lernen neuer Aufgaben nicht vollständig verfügbar.', [(3,13,24,'§2.2'),(3,25,40,'Lifelong Imitation Learning')]),
('Benchmarkstruktur', 'Spatial, Object und Goal enthalten jeweils zehn Aufgaben und variieren unterschiedliche Wissensaspekte. LIBERO-100 ergänzt 100 Aufgaben mit gemischten Anforderungen.', [(5,13,29,'§4.2')]),
('Einfach → komplex', 'LIBERO-100 wird in 90 kurze Vortrainingsaufgaben und zehn lange Aufgaben für nachfolgendes Lifelong Learning aufgeteilt. Das Protokoll ist kein reiner Zero-shot-Test.', [(5,30,33,'§4.2'),(3,25,40,'§2.2')]),
('Datenherkunft', 'Je Aufgabe werden 50 hochwertige Demonstrationen bereitgestellt, erhoben durch menschliche Teleoperation mit einer 3Dconnexion SpaceMouse.', [(6,11,15,'Ende §4.4')]),
('Vergleichsmethoden', 'Verglichen werden Experience Replay, EWC und PackNet sowie sequenzielles Fine-Tuning und Multitask-Lernen als Referenzen.', [(5,34,42,'§4.3')]),
('Metriken', 'Forward Transfer, negativer Backward Transfer und AUC beruhen auf Erfolgsraten. Sie erfassen Lernen neuer Aufgaben, Vergessen und Gesamtleistung; die Checkpointregel gehört zur Definition.', [(6,28,42,'§5.1'),(6,54,57,'Fußnote 5')]),
]),
('open_x', 'Open X-Embodiment / RT-X — Collaboration (2024er Preprint)', 'arXiv:2310.08864v5 vom 21.03.2024, 12 PDF-Seiten. ICRA 2024 ist der Publikationsort; diese Belege gelten für v5. Der finale Verlagsvolltext wurde nicht abgeglichen.', [
('Datenumfang', 'Die Fassung beschreibt über eine Million reale Trajektorien aus 60 Datensätzen und 22 Verkörperungen, vereinheitlicht im RLDS-Format.', [(3,13,27,'rechts, §III-A')]),
('Trainingsmenge unterscheiden', 'Die experimentelle Trainingsmischung umfasst neun Verkörperungen. Die 22 Verkörperungen des Gesamtbestands dürfen nicht als Trainingsumfang dieser Experimente angegeben werden.', [(5,19,28,'links, Fortsetzung §IV-C')]),
('Modalitäten und Koordinaten', 'Pro Datensatz wird eine Kameraansicht gewählt; Aktionen werden normalisiert und grob vereinheitlicht. Koordinatenrahmen sowie absolute/relative Positions- oder Geschwindigkeitssteuerung bleiben heterogen.', [(4,20,44,'links, §IV-A')]),
('Transferbefund', 'In der Emergent-Skills-Evaluation erreicht RT-2-X 75,8 % gegenüber 27,3 % für RT-2. Die Fertigkeiten fehlen in den Google-Robot-Daten, sind aber in Bridge vorhanden.', [(6,1,10,'Tabelle II'),(6,19,33,'links, §V-B')]),
('Datenablation', 'Ohne Bridge sinkt der entsprechende RT-2-X-Wert auf 42,8 %. Die Autoren deuten dies als Evidenz für Fertigkeitstransfer aus WidowX-Daten.', [(6,1,10,'Tabelle II'),(6,34,40,'links, §V-B')]),
('Übertragungsgrenze', 'Die Experimente untersuchen keine Generalisierung auf neue Roboter und keine stark abweichenden Sensor-/Aktuatormodalitäten.', [(6,50,59,'rechts, §VI')]),
]),
]

manifest = json.loads((B/'manifest.json').read_text(encoding='utf-8'))
doc = ['# Paper-Keynotes mit Seiten- und Zeilenbelegen', '', 'Stand: 21.10.2026. 48 paraphrasierte Stichpunkte zu den acht Papern der Forschungsnotiz.', '',
'## So verwendest du die Fundstellen', '',
'**S.** ist die PDF-Seite, ab der ersten PDF-Seite mit 1 gezählt. **Z.** bezeichnet die selbst erzeugte, seitenlokale Nummer einer nichtleeren Textzeile in der verlinkten Lesefassung. Es sind **keine offiziellen Zeilennummern der Publikation**. Bei zweispaltigen PDFs kann eine Layoutzeile Text beider Spalten enthalten; deshalb steht die Spalte zusätzlich am Beleg. Absätze nicht spaltenübergreifend lesen. Die Nummerierung ist eingefroren und nicht mit Editorzeilen identisch.', '',
'Alle Stichpunkte sind Paraphrasen, keine wörtlichen Zitate. Einordnungen und Einschränkungen sind als solche formuliert. Für den wissenschaftlichen Text Autor/Jahr plus Seite und ggf. Abschnitt verwenden; die eigenen Zeilenangaben dienen als Suchhilfe. Beispiel: „… (Zhao et al., 2023, PDF-S. 5, Abschn. IV-A).“ Die Literaturfassung im Literaturverzeichnis muss zur verwendeten PDF passen.', '',
'Die PDF-Hashes, Quellen-URLs und Zeilenzahlen stehen im [Manifest](_research/keynote_sources/manifest.json). Die Extraktion erfolgte mit pypdf 6.10.0 im Layoutmodus, ohne Leerzeilen; Formeln können Extraktionsartefakte enthalten. Die zitierten Textbereiche wurden gelesen; acht kritische Seiten zusätzlich als Seitenbilder geprüft. Dies ist keine vollständige Replikation oder mathematische Prüfung aller Paper.', '',
'**Versionshinweise:** Stable-BC wird ausschließlich aus arXiv v1 belegt; Open X-Embodiment aus arXiv v5. Für UMI wird das RSS-PDF verwendet. Zahlen und Fundstellen nicht ungeprüft auf andere Fassungen übertragen.', '',
'**Korrektur zur älteren Literaturübersicht:** Das DAgger-PDF zeigt gedruckte Proceedings-Paginierung (z. B. PDF-S. 4 = gedruckte S. 630), die der Textextraktor teilweise auslässt. Hier wird durchgehend die eindeutige PDF-Seitenzählung verwendet.', '']
records=[]
for key,title,version,notes in PAPERS:
    m=manifest['papers'][key]
    pdf=(B/m['pdf']).resolve()
    numbered=B/f'{key}.numbered.txt'
    filelines=numbered.read_text(encoding='utf-8').splitlines()
    pages=json.loads((B/f'{key}.pages.json').read_text(encoding='utf-8'))
    doc += [f'## {title}', '', version, '', f'[Originalquelle]({m["source"]}) · [Lokales PDF](<{pdf.as_posix()}>) · [Nummerierte Lesefassung](<{numbered.as_posix()}>)', '']
    for index,(label,note,locators) in enumerate(notes,1):
        refs=[]
        for page,start,end,section in locators:
            assert 1 <= start <= end <= len(pages[page-1])
            marker=f'S{page:02d}:Z{start:03d} | '
            global_line=next(i for i,line in enumerate(filelines,1) if line.startswith(marker))
            refs.append(f'[PDF-S. {page}, Z. {start}–{end}](<{numbered.as_posix()}:{global_line}>), {section}')
        doc += [f'- **{key.upper()}-K{index:02d} — {label}:** {note} **Fundstelle:** '+ '; '.join(refs)+'.', '']
        records.append({'id':f'{key.upper()}-K{index:02d}','paper':key,'note':note,'locators':locators})
    doc += ['']
doc += ['## Hinweise fürs Schreiben', '',
'Die Ergebnisse verschiedener Paper sind keine gemeinsame Rangliste. Bei Zahlen jeweils Aufgabe, Datenmenge, Metrik und Versuchsbedingungen nennen. DAgger/DART behandeln vor allem Zustandsverteilungen; Stable-BC lokale Stabilität; ACT/Diffusion Policy die Policyrepräsentation; UMI die Erhebungs- und Ausführungsschnittstelle; LIBERO und Open X-Embodiment liefern unterschiedliche Transferprotokolle. Diese Zuordnung ist eine redaktionelle Synthese der obigen Belege.', '',
'Bei ACT bleibt die Diskrepanz L1/MSE und bei DART die Kamerabeschreibung offen. Nicht stillschweigend eine Variante auswählen. Die neuen IDs mit „-K“ sind unabhängig vom älteren [Claim-Register](CLAIMS.md); dessen IDs bleiben unverändert.', '']
(ROOT/'literature/PAPER_KEYNOTES.md').write_text('\n'.join(doc),encoding='utf-8')
(B/'keynotes.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Wrote {len(records)} keynotes; all page/line ranges and link destinations validated.')
