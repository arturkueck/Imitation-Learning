"""Build the concise, nine-page meeting handout; no model or simulator use."""
from pathlib import Path
from xml.sax.saxutils import escape
import json
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Image, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / 'output/pdf/Ruecksprache_Imitation_Learning_2026-10-12.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
for name, file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
INK = colors.HexColor('#182D3B')
TEAL = colors.HexColor('#0E8279')
MUTED = colors.HexColor('#596B77')
PALE = colors.HexColor('#E8F1EE')
PAPER = colors.HexColor('#FAFAF7')
LINE = colors.HexColor('#DCE4E6')
W,H=A4
M=43
CW=W-2*M
styles={
    'body':ParagraphStyle('body',fontName='Arial',fontSize=10.2,leading=14.5,textColor=INK,spaceAfter=8),
    'small':ParagraphStyle('small',fontName='Arial',fontSize=8.3,leading=11.4,textColor=MUTED,spaceAfter=6),
    'cell':ParagraphStyle('cell',fontName='Arial',fontSize=9.2,leading=12.5,textColor=INK,spaceAfter=0),
    'headcell':ParagraphStyle('headcell',fontName='Arial-Bold',fontSize=9.2,leading=12.5,textColor=colors.white),
    'h2':ParagraphStyle('h2',fontName='Arial-Bold',fontSize=13.5,leading=17,textColor=TEAL,spaceBefore=11,spaceAfter=7),
    'title':ParagraphStyle('title',fontName='Arial-Bold',fontSize=25,leading=29.5,textColor=INK,spaceAfter=14),
    'quote':ParagraphStyle('quote',fontName='Arial',fontSize=12.4,leading=18,textColor=INK,spaceAfter=0),
}
def clean(s):
    return s.replace('–','-').replace('—','-').replace('‑','-').replace('−','-')
def p(s,style='body'):
    return Paragraph(clean(s),styles[style])
def h(s):return p(s,'h2')
def table(head,rows,widths):
    data=[[p(v,'headcell') for v in head]]+[[p(v,'cell') for v in row] for row in rows]
    t=Table(data,colWidths=[CW*x for x in widths],hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
        ('LINEBELOW',(0,1),(-1,-1),0.35,LINE),
    ]))
    return t
def box(s):
    t=Table([[p(s,'quote')]],colWidths=[CW])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),0.5,LINE),
                          ('LEFTPADDING',(0,0),(-1,-1),15),('RIGHTPADDING',(0,0),(-1,-1),15),
                          ('TOPPADDING',(0,0),(-1,-1),13),('BOTTOMPADDING',(0,0),(-1,-1),13)]))
    return t
def picture(name,width=CW):
    from PIL import Image as PILImage
    file=HERE/'media'/name
    with PILImage.open(file) as im:a,b=im.size
    return Image(str(file),width=width,height=width*b/a)
def ref(label,url,desc):
    return p(f'<b>{label}</b> {escape(desc)}<br/><link href="{escape(url)}" color="#0E8279">Originalquelle öffnen</link>','small')

pages=[]
pages.append(('ENTSCHEIDUNGSVORLAGE', 'Wann hilft dynamikbasierte\nRegularisierung?',[
    p('Imitation Learning mit robomimic | Master-Projektarbeit | 3 Monate','small'),
    box('<b>Hypothese:</b> Eine nach lokaler Modellgültigkeit gewichtete BC-Regularisierung erhöht die Erfolgsrate nach echten Störungen gegenüber derselben ungewichteten Methode, ohne die nominale Leistung wesentlich zu senken.'),
    h('Das Problem'),
    p('Behavioral Cloning (BC) lernt, Expertenaktionen nachzuahmen. Bei der Ausführung führen kleine Abweichungen jedoch zu Zuständen, die in den Demonstrationen kaum vorkamen. Ein zusätzlicher Lernterm soll Korrektur fördern. Wenn sein Dynamikmodell falsch ist, kann er auch falsche Reaktionen belohnen.'),
    h('Der geplante Beitrag'),
    p('Eine begrenzte Erweiterung in robomimic implementieren, die zugrunde liegenden Modellannahmen prüfen und den Nutzen kontrolliert messen. Die Policyarchitektur bleibt gleich. Vorarbeiten sind Stable-BC und CCIL; die allgemeine Idee ist bereits bekannt [S3-S5].'),
    h('Passend zum verfügbaren Rahmen'),
    p('<b>Kern:</b> offizieller Lift-PH-Datensatz, Zustandsmerkmale, kleines BC-Netz, zunächst am eigenen PC. <b>Optional:</b> eine zweite Aufgabe, bevorzugt Can. Das Rechenzentrum ab etwa Woche 7 erweitert den Umfang; der Kern bleibt lokal abschließbar.'),
    h('Entscheidung nach Woche 3'),
    p('Erst prüfen, ob die Dynamiknäherung tragfähig ist. Falls nicht: Wechsel zur vorbereiteten Studie über zeitlich strukturierte Sensoraugmentation. Ein negativer Befund zur Modellgültigkeit bleibt wissenschaftlich auswertbar.'),
    p('<b>Für die Rücksprache vereinbaren:</b> erwarteter Methodenbeitrag, erlaubter Simulatorzugang, Mindestumfang und Umgang mit negativen Ergebnissen.','small'),
]))

pages.append(('FORSCHUNGSSTAND', 'Die Idee braucht eine\nklare Abgrenzung',[
    p('Gezielte Primärquellenrecherche bis 12.10.2026. Neue Preprints sind Hinweise; ihre Aussagen werden nicht als gesicherter Konsens behandelt.','small'),
    table(['Vorarbeit','Konsequenz für das Projekt'],[
        ['<b>robomimic</b><br/>CoRL 2021 / Dokumentation [S1-S2]','BC, zeitliche Modelle und Diffusion Policy sind verfügbar. Datenqualität, Beobachtungen und Evaluation mitkontrollieren.'],
        ['<b>Diffusion Policy</b><br/>RSS 2023 [S6]','Moderne Aktionsfolgen-Policy. Eine breite Architekturreplikation würde den kleinen Robustheitsversuch vergrößern.'],
        ['<b>Stable-BC</b><br/>RA-L 2025 [S3]','Regularisiert lokale Fehlerdynamik. Seine Garantien gelten unter Annahmen; sie übertragen sich nicht automatisch auf unseren Zusatzloss.'],
        ['<b>CCIL und Feinmanipulation</b><br/>ICLR / IROS 2024 [S4-S5]','Lokale Modelle, korrigierende Labels und Fehlerfilter existieren bereits. Unser Gegenstand ist ein gewichteter Lernterm und seine empirische Gültigkeit.'],
        ['<b>Kontraktive Policies</b><br/>ICLR 2025 / 2026 [S9-S10]','Kontraktion einer Policy oder des Diffusionssamplers ist von Kontraktion des physischen Roboterfehlers zu unterscheiden.'],
        ['<b>Action-Chunking-Analysen</b><br/>August / Oktober 2026 [S7-S8]<br/><i>Preprints</i>','Untersuchen Ensembling und Fehlerausbreitung. Der Messhorizont beeinflusst Stabilitätsdiagnosen; mehrere Horizonte als Zusatzdiagnose verwenden.'],
    ],[.35,.65]),
    h('Die abgeleitete Untersuchungslücke'),
    p('Wann bringt ein unabhängig geprüfter lokaler Dynamikterm in diesem robomimic-Aufbau einen Zusatznutzen gegenüber einfacher Sensoraugmentation und beliebiger Gewichtung? Das ist eine konkrete empirische Frage; ein weltweiter Neuheitsanspruch ist noch nicht belegt.'),
    p('<b>Lesereihenfolge:</b> robomimic-Studie → Stable-BC → CCIL / Feinmanipulation → aktuelle Abgrenzung. DAgger und DART sind Bezugspunkte für zusätzliche Expertenkorrekturen [S11-S12].','small'),
]))

pages.append(('MECHANISMUS', 'Zwei Störungen,\nzwei Lernziele',[
    picture('01_sensor_vs_state.png'),
    h('Was die neue Gewichtung leisten soll'),
    p('Der Zusatzloss schätzt, ob eine kleine Zustandsabweichung nach einer korrigierenden Aktion schrumpft. <b>A</b> beschreibt die offene Zustandsantwort, <b>B</b> die zusätzliche Aktionswirkung. Die Gewichtung <b>w</b> soll unzuverlässige Modellbereiche weniger stark berücksichtigen.'),
    box('BC-Loss + λ × gewichteter Korrektur-Loss<br/><font size="10">Konzeptionell: ê<sub>t+1</sub> = A δ + B Δa</font>'),
    h('Die entscheidende Grenze'),
    p('Kleine Fehler im Modell können eine falsche Korrektur begünstigen. Deshalb A/B durch getrennte Zustands- und Aktionsinterventionen prüfen. Erst danach trainieren. Gute Anpassung an Expertentrajektorien allein genügt nicht.'),
    p('Die Kalibrierung verwendet zusätzliche Simulatorinformation beim Training. Bei Ausführung erhält die Policy dieselben Beobachtungen wie BC. Dies ist simulationsgestütztes IL; keine allgemeine Stabilitätsgarantie.','small'),
]))

pages.append(('VORARBEITEN', 'Ein positiver Anlass -\nund ein offener Mechanismus',[
    picture('03_historical_lift_seeds.png'),
    h('Was diese Messung trägt'),
    p('Die frühere lokale Erweiterung erreicht nominal 56/60 statt 44/60 Erfolge. Es sind <b>drei Trainingsseeds mit je 20 Rollouts</b>. Das motiviert die Frage; die Grafik bestätigt weder die neue Methode noch deren Mechanismus [L2].'),
    h('Was die späteren Prüfungen ändern'),
    p('Die aus Expertendaten geschätzte Aktionsantwort war unter kontrollierten Eingriffen unzuverlässig. Der neue lokale Lossentwurf ist numerisch geprüft, aber untrainiert; eine vorgeschlagene Fehlerhülle bestand ihren unabhängigen Entwicklungstest nicht [L3].'),
    p('<b>Nächster kleiner Test:</b> lokales A gegen festes A bei identischem lokalem B. Keine erneute große Trainingsserie, bevor Modellgüte, Abdeckung und Kosten plausibel sind.','small'),
]))

pages.append(('EXPERIMENT', 'Fünf Arme,\neine Hauptfrage',[
    table(['Arm','Methode','Zweck'],[
        ['C0','Unverändertes BC','Referenzleistung'],
        ['C1','BC + konsistente Sensoraugmentation','Einfachere Alternative'],
        ['C2','BC + lokaler kalibrierter Loss; gleiches Gewicht','Ungewichtete Kontrolle'],
        ['C3','C2 + Gewichte nach Modellgültigkeit','Vorgeschlagene Änderung'],
        ['C4','C3 mit zufällig permutierten Gewichten','Gezielte Auswahl gegen Zufall'],
    ],[.08,.54,.38]),
    h('Was gleich bleibt'),
    p('Architektur, Demosplit, Updatebudget, Optimizer, Batchreihenfolge und Evaluator. C2-C4 nutzen dieselben A/B-Modelle, Perturbationen und harten Domainmasken. C4 erhält dieselbe Gewichtsverteilung. Gradientennormen und effektive Abdeckung werden protokolliert.'),
    h('Was gemessen wird'),
    p('<b>Fünf Bedingungen:</b> nominal, Sensorbias +5/-5 mm sowie echter Aktionsimpuls in +x/-x. Der Hauptimpuls erfolgt zu einem gleichen festen frühen Zeitpunkt. Erfolg wird erst im gemeinsamen Bewertungsfenster danach gezählt. Dosis und Zeitpunkt werden im Entwicklungspilot festgelegt.'),
    box('<b>Hauptvergleich:</b> C3 minus C2 bei gestörtem Taskerfolg.<br/><font size="10">Praktisches Ziel: +10 Prozentpunkte; nominal höchstens 5 Prozentpunkte schlechter. Schwellen vor Haupttest vereinbaren.</font>'),
    h('Umfang und Interpretation'),
    p('5 neue Trainingsseeds × 5 Arme = <b>25 finale Läufe</b>. Je 50 gemeinsame neue Starts in 5 Bedingungen = <b>6.250 Episoden</b>. Bis zu 15 Entwicklungsläufe kommen hinzu. C3 gegen C4 prüft, ob die Zuordnung nach Modellgüte hilft; C3 gegen C1 den Nutzen über Augmentation hinaus.'),
    p('Je Seed gepaarte Effekte und näherungsweise Unsicherheitsintervalle zeigen. Fünf Seeds bleiben wenig. Ein unklarer Effekt ist kein Gleichwertigkeitsnachweis.','small'),
]))

pages.append(('ZEITPLAN', 'Zwölf Wochen,\nohne Cluster-Abhängigkeit',[
    table(['Zeitraum','Arbeit','Vorzeigbares Ergebnis'],[
        ['Woche 1-2<br/>zuhause','Literatur, Baseline, feste Daten-/Versionsstände, Störungs- und Laufzeitpilot','Reproduzierbares Protokoll'],
        ['Woche 3<br/>zuhause','A/B-Gegenprüfung, Modellgüte, Abdeckung und Kosten','Entscheidung: A oder B'],
        ['Woche 4-5<br/>zuhause','Integration, Parität/Gradienten/Geometrie, kleiner Methodenpilot','Technisch geprüfte Methode'],
        ['Woche 6<br/>zuhause','Hyperparameter, Präzision und Testplan sperren; Text beginnen','Eingefrorenes Experimentpaket'],
        ['Woche 7-8','Finale Lift-Läufe, seriell lokal oder identisch parallel im Cluster','Rohdaten und Unsicherheit'],
        ['Woche 9','Eine Erweiterung bei abgeschlossenem Kern; sonst Fehleranalyse','Zweite Aufgabe oder vertiefte Diagnose'],
        ['Woche 10-11','Auswertung, Diskussion, Schreiben, Medien','Vollständige Rohfassung'],
        ['Woche 12','Reproduzierbarkeit, Korrektur, Vortrag, Puffer','Abgabefertige Arbeit'],
    ],[.18,.50,.32]),
    h('Rechenbudget transparent planen'),
    p('Lokal vorhanden: RTX 5070 mit etwa 12 GB VRAM und Lift-Umgebung. Kleine State-BC-Läufe sind eine plausible Basis. Tatsächliche Zeiten zuerst messen; die Kalibrierung kann teurer sein als das Training.'),
    p('<b>Kosten:</b> 25 × Trainingszeit + 6.250 × Episodenzeit + Kalibrierung + Entwicklung. Reines Planungsbeispiel: 4 s/Episode ergeben 6,9 h Evaluation; 10 s ergeben 17,4 h. Das sind keine neuen Messwerte.'),
    p('<b>Ohne Cluster:</b> abgeschlossene Lift-Studie. <b>Mit Cluster:</b> zusätzliche Replikation oder eine zweite Aufgabe. Keine breite Suche über Aufgaben, Netzwerke und Störungsraster gleichzeitig.','small'),
]))

pages.append(('GESPRÄCH', 'Zwei Alternativen\nund ein klarer Einstieg',[
    h('Alternative B: Zeitlich strukturierte Sensoraugmentation'),
    p('<b>Hypothese:</b> Ein über ein Zeitfenster konstanter Trainingsbias verbessert Robustheit gegen anhaltenden Sensorbias stärker als unabhängiges Frame-Rauschen bei gleicher Randverteilung. Kein entsprechender Recoverygewinn durch echte Impulse erwartet.'),
    p('Drei identische BC-RNN-Arme: ohne Rauschen, unabhängiges Rauschen, konstanter Fensterbias. Ein Gedächtnismodell ist hier wesentlich: Beim zustandslosen MLP kann dieselbe Randverteilung denselben erwarteten Loss erzeugen. Geringeres Modellrisiko, klarer Trainingsbeitrag.'),
    h('Alternative C: Feedback oder Mittelung?'),
    p('<b>Hypothese:</b> Häufigeres Replanning hilft nach Störungen stärker als bloßes temporales Ensembling. Dieselben vorhandenen Direct-Checkpoints mit zwei Aktionen, einer Aktion und einer gemittelten Aktion ausführen. Gripper gesondert behandeln. Wenig Training nötig; Schwerpunkt ist die Ausführung [S7-S8,S13].'),
    h('So kannst du beginnen'),
    box('„Ich möchte nicht nur ein Modell trainieren, sondern eine konkrete Annahme prüfen: Hilft ein dynamikbasierter Zusatzloss dann mehr, wenn ich ihn nur dort stark gewichte, wo das lokale Modell zuverlässig ist? Ich starte mit Lift, trenne Messfehler von echten Störungen und vergleiche mit einfachen Kontrollen.“'),
    h('Im Gespräch entscheiden'),
    p('1. Genügt Adaption plus saubere Ablation als Methodenbeitrag?<br/>2. Ist zusätzlicher Simulatorzugang im Training erlaubt?<br/>3. Reicht eine gründliche Aufgabe als Mindestumfang?<br/>4. Sind negative Ergebnisse und Alternative B akzeptabel?<br/>5. Welche Clusterressourcen sind ab etwa Woche 7 realistisch?'),
    p('15-Minuten-Ablauf: 2 min Frage · 3 min Literatur/Vorarbeiten · 4 min Experiment · 2 min Plan · 4 min Entscheidungen. Der ausführliche Leitfaden enthält einen 90-Sekunden-Sprechtext.','small'),
]))

pages.append(('METHODISCHER ANHANG', 'Vor dem Haupttest\ndiese Punkte festlegen',[
    h('1 / Datenzugang und Trennung'),
    p('Offizielles Lift-PH mit vorhandenem 180/20-Demosplit. Innerhalb der Trainingsdemos Modellfit, Kalibrierung und Gegenprüfung demoweise trennen. Bereits genutzte Demos als Entwicklung markieren. Neue finale Startzustände sperren; sie dürfen weder Gewichte noch Checkpointwahl beeinflussen.'),
    h('2 / Modellprüfung vor Training'),
    p('A/B durch getrennte physisch konsistente Eingriffe identifizieren und auf anderen Eingriffen prüfen. Orientierung, Geschwindigkeit, Gripper, Controllerzustände und Kontakte kontrollieren. Vektorfehler, falsche Kontraktionsfreigaben, Abdeckung und Simulatorabfragen ausweisen. Die gescheiterte Fehlermarge nicht aus Prüfdaten nachjustieren.'),
    p('Diskussionsvorschlag fürs Entwicklungsgate: mindestens 30% Abdeckung im beanspruchten Arbeitsbereich, höchstens 10% falsche Freigaben unter akzeptierten Prüffällen. Schwellen und Nenner vor Prüfung sperren. Dies sind praktische Vorschläge, keine bewiesenen Sicherheitsgrenzen.','small'),
    h('3 / Aktive Abdeckung während des Lernens'),
    p('Eingefrorene Gewichte bedeuten nicht konstante effektive Auswahl: Policyaktionen können den kalibrierten Bereich verlassen. Gleiche Maskierungsregel in C2-C4, Abdeckung je Phase und über die Zeit berichten. Kontaktfreie Aktivität allein belegt keinen Mechanismus in Kontaktphasen.'),
    h('4 / Erfolg, Unsicherheit und Zusatzkosten'),
    p('Hauptmetrik: voller Taskerfolg nach festem Impuls, beide Richtungen gleich gewichtet. Native Erfolgsbedingung im gemeinsamen Zeitfenster nach Eingriff auswerten; ein früherer Erfolg allein genügt nicht. Abbrüche nicht still aus dem Nenner entfernen.'),
    p('95%-Intervalle näherungsweise über gekreuztes Resampling von Trainingsseed und gemeinsamem Start; Paarungen erhalten. Positiver Befund: praktisches Ziel erreicht, Gewinnintervall über null und untere nominale Differenzgrenze über -5 Punkten. Präzision in Woche 6 anhand des Piloten planen. Sonst explizit explorativ/unklar.'),
    h('5 / Was ein negatives Ergebnis bedeutet'),
    p('Augmentation gleich gut und billiger: Zusatzmodell nicht gerechtfertigt. Zufallsgewichte gleich gut: Gültigkeitsauswahl als Erklärung nicht gestützt. Besserer Modellfehler ohne Taskgewinn: Diagnose und Aufgabenerfolg auseinanderhalten. Alle Kalibrier-, Trainings- und Evaluationskosten bilanzieren.'),
]))

pages.append(('QUELLEN & MATERIAL', 'Nachlesen und zeigen',[
    ref('[S1]','https://proceedings.mlr.press/v164/mandlekar22a.html','Mandlekar et al. What Matters in Learning from Offline Human Demonstrations. CoRL 2021, PMLR 2022.'),
    ref('[S2]','https://robomimic.github.io/docs/introduction/implemented_algorithms.html','robomimic: offizielle Algorithmen-Dokumentation; Datensatzlinks im ausführlichen Leitfaden.'),
    ref('[S3]','https://collab.me.vt.edu/Stable-BC/','Mehta et al. Stable-BC. IEEE RA-L 2025. Autorenprojekt mit Demo-Video.'),
    ref('[S4]','https://arxiv.org/abs/2310.12972','Ke et al. CCIL: Continuity-based Data Augmentation for Corrective Imitation Learning. ICLR 2024.'),
    ref('[S5]','https://arxiv.org/abs/2405.19307','Deshpande et al. Data Efficient Behavior Cloning for Fine Manipulation via Continuity-based Corrective Labels. IROS 2024 laut Autoren.'),
    ref('[S6]','https://diffusion-policy.cs.columbia.edu/','Chi et al. Diffusion Policy. RSS 2023. Autorenprojekt und Videos.'),
    ref('[S7]','https://arxiv.org/abs/2608.02547','Lazzati et al. Why Does Action Chunking Improve Behavioral Cloning Performance in Robotic Control? Preprint, 03.08.2026.'),
    ref('[S8]','https://arxiv.org/abs/2610.01626','Goyal. Measuring the Stability Assumption Behind Action Chunking. Preprint, 01.10.2026.'),
    ref('[S9]','https://arxiv.org/abs/2412.07544','Abyaneh et al. Contractive Dynamical Imitation Policies for Efficient Out-of-Sample Recovery. ICLR 2025.'),
    ref('[S10]','https://proceedings.iclr.cc/paper_files/paper/2026/hash/1dec73169509c223220744b2c9b2df37-Abstract-Conference.html','Abyaneh et al. Contractive Diffusion Policies. ICLR 2026.'),
    ref('[S11-S13]','https://proceedings.mlr.press/v15/ross11a.html','DAgger (AISTATS 2011); DART (CoRL 2017); ACT (RSS 2023). Einzelne Original-Links im Leitfaden.'),
    h('Lokale Quellen und Medien'),
    p('<b>[L1]</b> FORSCHUNGSPLAN.md (04.10.2026).<br/><b>[L2]</b> praxis/reports/lift_ph_full_100ep_summary.json.<br/><b>[L3]</b> SESSION_RESEARCH_REPORT.md der Lift-Session vom 04.10.2026.<br/><b>[L4]</b> Stack-Replikation und Replaymanifest vom 01.10.2026.','small'),
    p('Im Begleitordner: ausführlicher Gesprächsleitfaden, Quellen-/Medienregie, zwei Grafiken, 10-Sekunden-Schemaanimation und ausgewählte historische Stack-Replays. Die Replays illustrieren eine andere Aufgabe, keine neue Evidenz für die Hypothese.','small'),
]))

c=canvas.Canvas(str(OUT),pagesize=A4)
c.setTitle('Erste Rücksprache - Imitation Learning mit robomimic')
c.setAuthor('Vorbereitung für Artur')
c.setSubject('Master-Projektarbeit: Hypothese, Forschungsstand, Kontrollen, Zwölf-Wochen-Plan')
layout=[]
for number,(kicker,title,items) in enumerate(pages,1):
    c.setFillColor(PAPER);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(TEAL);c.rect(0,H-11,W,11,fill=1,stroke=0)
    c.setFont('Arial-Bold',9);c.drawString(M,H-39,'RÜCKSPRACHE / '+kicker)
    y=H-59
    allitems=[p(title.replace('\n','<br/>'),'title')]+items
    for f in allitems:
        y-=f.getSpaceBefore() if hasattr(f,'getSpaceBefore') else 0
        fw,fh=f.wrap(CW,y-54)
        if y-fh < 52:
            raise RuntimeError(f'Page {number} overflow at {type(f).__name__}: bottom {y-fh:.1f}')
        f.drawOn(c,M,y-fh)
        y-=fh+(f.getSpaceAfter() if hasattr(f,'getSpaceAfter') else 0)
    layout.append({'page':number,'content_bottom':round(y,1),'title':title})
    c.setStrokeColor(LINE);c.line(M,40,W-M,40)
    c.setFont('Arial',8);c.setFillColor(MUTED)
    c.drawString(M,26,'Artur · Master-Projektarbeit · Stand 12.10.2026')
    c.drawRightString(W-M,26,f'{number} / {len(pages)}')
    c.showPage()
c.save()
reader=PdfReader(OUT)
assert len(reader.pages)==len(pages)
assert all(len(page.extract_text())>150 for page in reader.pages)
check={'path':str(OUT),'pages':len(reader.pages),'layout':layout,'links':sum(len(pg.get('/Annots',[])) for pg in reader.pages)}
(HERE/'pdf_validation.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(check,ensure_ascii=False))
