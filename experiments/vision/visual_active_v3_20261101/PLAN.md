# Vision V3: Kameraposen, Aufnahmebedarf und gespeicherte Wunschpositionen

Stand 02.11.2026 (Entwurfsbeginn 01.11.). **Konzept und Prototypen, kein Training gestartet.** `PROPOSED_CONFIG.json` setzt `training_enabled=false` und `hardware_execution_enabled=false`. Es gibt hier keinen ausführbaren Trainingsstarter. Bestehende V2-Gewichte, Daten und Ergebnisse bleiben unverändert.

## Ziel

Das System soll aus kalibrierten RGB-Bildern unbekannte Würfel und Quader lokalisieren und entscheiden können, ob zusätzliche Bildevidenz voraussichtlich nützt. Wenn ja, soll es einen Aufnahmeauftrag mit gewünschter Kameraposition **und Orientierung** erzeugen. Der Auftrag wird vor der Bewegung dauerhaft gespeichert. Der Ganzarmplaner prüft unabhängig, ob und wie die Kamerapose erreichbar ist. Gewünschte, geplante und tatsächlich erreichte Pose bleiben getrennt.

Eine angeforderte Pose ist kein Fahrbefehl. Eine gute Klassifikationswahrscheinlichkeit beweist keinen freien Raum. Bewegung und Kamerakalibrierung werden nicht durch eine Poseausgabe des Netzes ersetzt. Ein gewünscht besserer Blick kann nach der Aufnahme schlechtere Daten liefern; dieser Fall wird erhalten und bewertet.

## Ausgangsbefund und Konsequenz

Der V2-Nachtlauf lieferte sechs Modelle mit je 904.112 Parametern und drei Seeds pro Kameravariante. Der anschließende geschlossene Kameratest erzeugte sieben neue Aufnahmen. Bei vier echten Zielpaaren stieg der mittlere Positionsfehler von 14,90 auf 37,81 mm, bei drei weiteren Auslösern handelte es sich um Zusatzdetektionen. Die Übernahmeregel verwarf alle neuen Schätzungen.

Auch feste Kameramodelle verschlechterten sich nach der Bewegung. Der Befund trennt daher Blickwinkel-, Verdeckungs- und Roboterbildänderungen nicht kausal. Die neuen Daten müssen diese Faktoren abdecken. Eine Entscheidung über hilfreiche neue Ansichten wird auf dem **verbesserten, danach eingefrorenen Wahrnehmungsmodell** aufgebaut. Die bisherigen sieben negativen Fälle dienen der Diagnose, nicht als alleiniger Trainingsdatensatz.

## Stufe A: Wahrnehmung aus unterschiedlichen Kameraposen

### Vergleichsmodelle

| Modell | Rolle | Eingaben | Parameter |
| --- | --- | --- | ---: |
| M0 | eingefrorene V2-Referenz | zwei feste Ansichten + eine Handansicht | 904.112 |
| M1 | kontrolliertes Finetuning | dieselbe Architektur, breitere Pose-/Verdeckungsdaten | 904.112 |
| M2 | gesonderter Historienvergleich | zwei aktuelle feste Ansichten + null bis drei Handansichten derselben unveränderten Szene | voraussichtlich 904.112 |

M1 zeigt zunächst den Nutzen der Daten. M2 untersucht separat, ob das Beibehalten vorheriger Handbilder hilft. M2 darf nicht gleichzeitig als Nachweis eines reinen Datenvorteils ausgegeben werden. Beide Varianten werden aus den passenden V2-Checkpoints für Seeds 1/2/3 initialisiert und mit denselben Familien, Trainingsbudgets und Auswahlregeln verglichen. Keine Auswahl des besten Einzel-Seeds für einen Methodenvergleich.

### Architektur

Der vorhandene CNN hat sechs Conv2D-Schichten mit 32/64/128 Kanälen und ReLU. Pro RGB-Bild 160×160 entstehen 400 Tokens mit Breite 128. Kalibrierte Strahlen enthalten Weltstrahlrichtung und Kamerazentrum. Drei Transformer-Decoder mit jeweils vier Attention-Köpfen, Feedforward-Breite 256, GELU und Dropout 0,1 erzeugen fünf Objektslots. Ein MLP 128→128→16 liefert Detektion, Position, Größe, 6D-Rotation und drei Sichtbarkeitslogits.

Für M2 wird die feste Zahl von drei Eingabebildern variabel (maximal fünf). Die drei Kamera-Embeddings werden als **Rollen** verwendet: fest links, fest rechts, Handkamera. Mehrere Handbilder teilen dasselbe Rollen-Embedding und unterscheiden sich über ihre jeweiligen kalibrierten Strahlen. Die Sichtbarkeit wird für die drei Rollen trainiert; für die Handrolle bedeutet sie sichtbar in mindestens einer tatsächlich verfügbaren Handansicht. Sie ist dann ausdrücklich keine einzelne Sichtbarkeitsausgabe pro gespeichertem Foto. Das erhält zunächst die Parameterform des alten Checkpoints; die Historienanpassung ist noch nicht implementiert oder benchmarkiert.

M1 hat 1.200 Bildtokens, M2 höchstens 2.000. Es wird kein Zeit-/Bildindex als Ersatz für die wirkliche Kamerapose verwendet. Historienmasken verhindern den Zugriff auf fehlende Bilder. Bei einer bewegten Szene dürfen alte Bilder nicht ungeprüft mit neuen fusioniert werden; der erste Versuch beschränkt sich auf statische Szenen und identische `scene_revision`.

Für den kontrollierten M1-Vergleich bleiben Strahlen- und Ausgabekoordinaten sowie Ursprung/Skalierung des V2-Kerns unverändert. Die Anforderungsköpfe und das Journal verwenden dagegen konsequent `robot_base`. Die bekannten Transformationsartefakte müssen diese Umrechnung explizit auflösen; Welt- und Basiswerte werden nicht direkt gemischt.

### Daten

0–5 Objekte, etwa je zur Hälfte Würfel und Quader. Unter den nichtleeren Szenen: 25 % verstreut, 25 % gemischt, 35 % Türme, 15 % Wand/Brücke. Leere Szenen und falsche Zusatzdetektionen bleiben enthalten. Verdeckte, gleichfarbige, graue, helle und überstrahlte Objekte werden gezielt abgedeckt. Gleiche Farben sind keine Objektidentitäten.

Ziel für die Objektzahl: 5 % leer, je 19 % für ein bis fünf Objekte. Objektzahl und Anordnung werden gemeinsam unter ihren physikalischen Bedingungen zugeteilt (kein Turm mit einem Objekt, keine Brücke mit zwei). Tatsächlich realisierte Histogramme und Abweisungsgründe werden vor Freigabe der Daten geprüft; die Zielquoten dürfen nicht mit durch einfache Fallbacks verzerrten Istquoten verwechselt werden.

Je Familie zunächst sechs zulässige Roboter-/Kameraposen: eine ursprüngliche, zwei nahe, zwei mittlere, eine schräge. Vorgeschlagene Kameraverschiebungen: 10–40, 40–120 und 120–220 mm; tatsächliche Erreichbarkeit geht vor jeder Quote. Für jede Pose werden beide festen Kameras und die Handkamera aufgenommen, damit veränderte Roboterverdeckungen sichtbar bleiben. Es werden gültige Roboterkonfigurationen erzeugt, keine frei schwebende Kamera ohne passenden Arm.

Die Posen werden aus vorab festgelegten Arbeitsraum-/Roboterbereichen und aus beobachtungsbasierten Kandidaten erzeugt. Nicht alle Kameras dürfen stets auf die exakte Sollobjektmitte zeigen: Das würde die Position über die Kalibrierung indirekt verraten. Objektgeometrie darf in der Simulation zur Kollisionsprüfung und als Trainingslabel dienen, aber nicht als Eingabe der Wahrnehmung oder als zur Laufzeit verfügbarer Fokus.

Bekannte Robotermasken, Gelenkstände, Kamerakalibrierung, Aufnahmezeiten und Referenzbilder werden gespeichert. Leere Referenzbilder sind ein optionales Diagnosesignal. Sie können real bei einer neuen Handkamerapose nicht beliebig aus einer objektfreien Simulation erzeugt werden. Deshalb bleibt der Wahrnehmungskern RGB+Kalibrierung; ein fehlender Referenzscore wird als fehlend (`-1`) behandelt und nicht als perfekte Übereinstimmung. Das spätere Anforderungsmodell bekommt im Training auch Beispiele ohne Referenzscore.

Sichtbarkeit für den Loss wird ausschließlich aus den **verfügbaren Eingabebildern des jeweiligen Beispiels** berechnet. Vollständig verdeckte Objekte bekommen keine erzwungene genaue Pose. Spätere, noch nicht aufgenommene Kandidatenbilder dürfen nicht die anfänglichen Wahrnehmungs-Labels oder Eingaben verändern.

### Familienaufteilung

| Split | Familien | Verwendung |
| --- | ---: | --- |
| Perception train | 12.000 | M1/M2-Finetuning |
| Model validation | 2.000 | Checkpoint- und Variantenwahl |
| Request train | 4.000 | neue Familien für Bedarfs-/Kandidatenköpfe nach Einfrieren der Wahrnehmung |
| Request validation | 500 | frühes Stoppen der Anforderungsköpfe |
| Request threshold calibration | 500 | einmalige Auswahl der Auslöse-/Übernahmeschwellen |
| Final IID | 2.000 | eingefrorener Gesamtvergleich |
| Final Kamera-OOD | 1.000 | zurückgehaltene Bereiche des zulässigen Posegitters, neue Familien |
| Final Geometrie-OOD | 1.000 | neue Familien und getrennte Quadergrößen/Seitenverhältnisse |

Alle Aufnahmen, Historien, Kandidaten, Duplikate und Augmentationen derselben Familie bleiben im selben Split. Posebereiche für Kamera-OOD werden vorab reserviert. Die bisherigen, bereits untersuchten Validierungs-/Diagnoseszenen sind keine neue unabhängige Schlussprüfung. Die vorhandenen reservierten V2-Schlussdaten werden nicht für die neue Wahl benutzt.

Zuerst wird ein Erfassungs-/Durchsatzpilot mit 1.000 Familien vorgesehen, um Renderqualität, erreichbare Poseverteilung, Speicherbedarf und Trainingsdurchsatz zu messen. Er startet hier nicht. Der vollständige Entwurf umfasst 23.000 Familien; sechs Posen mit je drei RGB-Bildern ergeben bis zu 414.000 RGB-Bilder, ungefähr 31,8 GB allein als unkomprimierte RGB-Arrays. Referenzen und Labels kommen hinzu. PNG-/Shard-Kompression, optionale Referenzaufnahme und Streaming werden vor der Vollerzeugung gemessen; keine ungeprüfte RAM-Vollbeladung.

### Lernverfahren und Loss

AdamW, anfänglich Lernrate 1e-4, Weight Decay 1e-4, effektive Batchgröße 32, zunächst Microbatch 4 und acht Akkumulationsschritte. Gradient Clipping 1,0; drei Warmup-Epochen, danach Cosine-Absenkung. Maximal 60 Epochen pro Modell, frühes Stoppen nach zehn Epochen ohne vorab definierten Validierungsfortschritt. FP32 als erste Vergleichsbasis; alternative Präzision erst nach numerischem Preflight.

Eine Epoche umfasst zunächst 12.000 zufällig aus den Familien gebildete Beobachtungskontexte, nicht alle sechs Posen sechsmal zusätzlich. Das sind bei Batch 32 etwa 375 Optimizer-Schritte pro Epoche, höchstens 22.500 pro Modell. M1 und M2 mit jeweils drei Seeds bedeuten maximal 135.000 neue Wahrnehmungs-Updates. Ein Stundenbudget wird erst nach dem Durchsatzpilot festgelegt; 60 Epochen sind eine Obergrenze, keine garantierte Laufzeit.

Objektzuordnung über Hungarian-Matching. Kombinierter Loss wie bisher: Detektion 1, Position 5, Größe 1, symmetriebewusste Rotation 0,5, rollenbezogene Sichtbarkeit 0,25. Positions-/Größenanteile SmoothL1, Detektion/Sichtbarkeit BCE mit Logits. Boxsymmetrien dürfen nur größenverträgliche Achsentausche als äquivalent behandeln. Das aktuelle Matching und die physische Dekodierung bleiben die Referenz. Zusätzliche probabilistische Poseköpfe werden nicht gleichzeitig eingeführt; sonst wäre die Ursache eines Fortschritts schwerer zuzuordnen.

## Stufe B: Bedarf und nützliche Wunschpose lernen

Diese Stufe beginnt erst nach Auswahl und Einfrieren der Wahrnehmungsvariante auf Model validation. Die getrennten Request-train-Familien waren nicht Teil ihres Finetunings. So stammen die Gewinnlabels nicht nur aus bereits auswendig bekannten Wahrnehmungsbeispielen.

### Ziele und Ausgaben

Es werden zwei Fragen getrennt:

1. **Fehlt nützliche Bildevidenz?** Ein Bedarfskopf liefert ein Logit für `needs_reobserve`.
2. **Welche der geometrisch geprüften Kandidaten hilft voraussichtlich?** Ein gemeinsamer Kandidatenkopf liefert erwarteten Nettogewinn und ein Logit für hilfreiche Aufnahme.

Die Wunschpose wird aus Kandidaten ausgewählt, nicht als uneingeschränkte XYZ-Ausgabe direkt an den Arm geschickt. Maximal zwölf Kandidaten je Entscheidung. Ein unabhängiger Planer prüft die vollständige Gelenkkonfiguration einschließlich Greifer, Kamera und Halterung. Die erwartete Verdeckung der festen Ansichten wird berücksichtigt. Ein Kandidatenscore ersetzt weder diese Prüfung noch die Kartenfrische.

`needs_reobserve=true` kann mit `request_image=false` auftreten, etwa wenn kein gültiger Kandidat oder kein Aufnahmebudget vorhanden ist. Diese Entscheidung wird protokolliert. Bei `request_image=true` wird zuerst ein konkreter CaptureRequest mit Wunschpose gespeichert. Wenn die anschließende Bahnprüfung scheitert, bleibt der Auftrag mit `blocked` erhalten. Beide Fälle sind kein abgeschlossener erfolgreicher Blickwechsel.

### Kopfarchitektur: untrainierter Prototyp

| Kopf | Dimensionen / Aktivierung | Verifizierte Parameter |
| --- | --- | ---: |
| Bedarf | 23 → 64 → 32 → 1; GELU zwischen linearen Schichten | 3.649 |
| Kandidat | 23 Beobachtungs- + 19 Kandidatenmerkmale = 42 → 128 → 64 → 2; GELU | 13.890 |
| Zusammen | drei Ausgabenarten: Bedarf, Gewinn, hilfreich | 17.539 |

Mit einem Wahrnehmungskern wären das rechnerisch 921.651 Parameter. Der Historienkern selbst ist noch nicht umgesetzt. Die Kopfparameter und Forward-Dimensionen sind durch `request_heads.py` und Tests geprüft, nicht durch Training validiert.

Die 23 Beobachtungsmerkmale umfassen vorhergesagtes Fokuszentrum, Größe, 6D-Rotation, Detektionsscore, Seed-Unterstützung, Positionsstreuung je Achse, Sichtbarkeit je Kamerarolle, Historienlänge, optionalen Bildwiderspruch und ein Fokus-vorhanden-Flag. Die 19 Kandidatenmerkmale beschreiben Kamerapose, Blickrichtung/-abstand, Gelenkbewegung, erwartete Roboterverdeckung beider festen Ansichten, gültige Kalibrierung, Aufnahmekosten und Kandidatengültigkeit. Alle Merkmale stammen aus bisherigen Beobachtungen, bekannter Kalibrierung/Robotik und Kandidatenplanung. Kein tatsächlicher zukünftiger Fehler, keine zukünftigen RGB-Features und keine unbekannte Sollgeometrie als Eingang.

Insbesondere bekommt der Kandidatenkopf keine aus den unbekannten Sollobjekten berechnete exakte Hindernisdistanz. Die unabhängige Kollisionsprüfung darf diese in der Simulation als Referenz verwenden; das ist noch keine kamerabasierte Freiraumlösung. Der Planungsbackend (`sim_reference` oder tatsächlich visuell geprüft) wird im Auftragsverlauf gespeichert. Reale Bewegungen bleiben bei unbekanntem Raum blockiert; das Netz kann diese Sperre nicht durch einen hohen Gewinnscore überstimmen.

Wenn ein Objekt nicht einmal detektiert ist, darf das Modell keine erfundene Objektidentität voraussetzen: `target_scope=scene`, Fokusflag 0 und fehlende Fokusmerkmale maskieren. Ungeklärter Vordergrund kann einen Szenenblick motivieren; ohne solchen Hinweis können gemeinsam übersehene Objekte weiter unentdeckt bleiben. Dies wird gesondert geprüft.

### Gewinnlabels

Für jeden gespeicherten Anfangskontext werden zulässige Kandidaten tatsächlich in der Simulation gerendert. Das eingefrorene Wahrnehmungsmodell wertet den Anfangskontext und den durch ein Kandidatenbild erweiterten Kontext aus. Die getrennte Sollgeometrie liefert ausschließlich das Trainingslabel des resultierenden Fehlers. Das ist Offline-überwachtes Lernen aus gemessenen Gegenbeispielen, kein blindes Übernehmen eigener Vorhersagen als Wahrheit.

Vorgeschlagener Satzfehler in äquivalenten Millimetern: pro Sollobjekt gedeckelter Positionsfehler (50 mm), zusätzlich 0,25-mal gedeckelter physischer Ecken-RMSE (50 mm); fehlende beobachtbare Objekte erhalten diese Fehlerobergrenzen. Falsche Zusatzdetektionen kosten 50 mm je Objekt, normiert auf max(1, Sollobjektzahl). Die Objektreferenz für ein Vorher-/Kandidatenpaar ist die gleiche, im Paar beobachtbare Sollmenge. Vollständig in allen zugehörigen Bildern unsichtbare Objekte werden nicht als angeblich exakt schätzbar behandelt. Leere Szenen werden separat mit Zusatzdetektionskosten bewertet.

Nettogewinn = Satzfehler vorher − Satzfehler nachher − Aufnahmekosten. Vorläufige Kosten: 0,2 äquivalente mm pro Sekunde geplanter Bewegung plus 1 mm pro zusätzlicher Aufnahme. Hilfreich bedeutet mindestens 2 mm Nettogewinn. Bedarfslabel positiv, wenn der anfängliche Satzfehler über 5 mm liegt und mindestens ein gültiger Kandidat diesen Mindestgewinn erreicht. Diese Schwellen sind Entwurfswerte und werden vor dem ersten gelabelten Pilot festgeschrieben; sie sind keine reale Sicherheits- oder Montagegrenze.

Negative Kandidaten, Kamera-Fahrfehler, fehlende Zuordnungen, Zusatzdetektionen und erfolglose Blickwechsel bleiben im Datensatz. Scheitert eine Aufnahme, erhält sie kein erfundenes Geometrie-Gewinnlabel; sie wird als fehlgeschlagene Aktion mit eigener Maske protokolliert. Ohne ausreichend positive Kandidatengewinne wird Stufe B nicht als funktionsfähige Blickauswahl bewertet. Ein Netz, das immer keine Aufnahme verlangt, ist kein Erfolg.

Training der Köpfe: AdamW 3e-4, Weight Decay 1e-4, Batch 256, maximal 30 Epochen, Early Stopping fünf Epochen. Loss = BCE(Bedarf) + SmoothL1(Gewinn/20 mm, beta 0,1) + 0,5 BCE(hilfreich). Maskierung ungültiger/fehlgeschlagener Kandidaten; nach Familien auswerten. Merkmalsnormalisierung nur auf Request train. Auslösewahrscheinlichkeiten und Gewinnschwellen erst auf dem getrennten 500-Familien-Kalibrierungssplit wählen, nicht auf dem Schlussvergleich.

## Aufnahmeauftrag und Speicherung der Wunschposition

`praxis/src/active_view/capture_requests.py` ist eine implementierte, getestete Schnittstelle für den späteren Lauf. Sie enthält weder einen trainierten Anforderungskopf noch einen Roboter-Treiber.

Ein Auftrag speichert:

- eindeutige `request_id`, Episode und unveränderte `scene_revision`;
- IDs der bisherigen Bilder und vorhergesagten Objekttracks oder Szenenbezug;
- Anlass, Modellrevision und Kalibrierungsrevision;
- **gewünschte optische Kamerapose**: Position in Metern und Einheitsquaternion in Reihenfolge w,x,y,z;
- Bezugssystem `robot_base`, optische Achsen OpenCV (+X rechts, +Y unten, +Z nach vorn), UTC-/Zeitzonenzeit;
- später geplante Kamerapose, Planreferenz und sieben Armwinkel;
- später tatsächliche Kamerapose, tatsächlichen Aufnahmezeitpunkt, neue Bild-ID und relativen Bildpfad;
- Abweichung Wunsch–Ist in Metern und Radiant sowie spätere Annahme-/Zurückstellungsentscheidung.

Weltkoordinaten der Simulation sind nicht stillschweigend Roboterbasiskoordinaten. `pose_from_mujoco` verlangt explizit `T_world_base` und rechnet außerdem die MuJoCo-Kameraachsen (Blick −Z) in OpenCV-Achsen um. Die gewünschte Kamera- und die benötigte EE-Pose sind nicht identisch: Für den späteren Planer gilt `T_base_EE = T_base_camera * inverse(T_EE_camera)` mit der bekannten Handkameramontage. Auch diese Montagekalibrierung muss versioniert sein.

Zustandsfolge: `requested → planned → captured → evaluated`. Alternativ `blocked`, `failed` oder `cancelled`. Eine Kameraaufnahme kann nicht ohne vorherigen Plan als erfüllt angehängt werden. Eine geänderte Szene oder Kalibrierungsrevision erfordert einen neuen beziehungsweise neu validierten Auftrag. Die API speichert eine reale Abweichung, statt die Wunschpose nachträglich durch die Istpose zu überschreiben.

Ein angeforderter Blick ist noch kein erfüllter Blick. Vorgeschlagene Erfüllungstoleranz: 3 mm und 0,035 rad; vor realem Einsatz müssen Kalibrierungs- und Nachführfehler gemessen werden. Ein Bild außerhalb dieser Toleranz kann mit seiner **wirklichen** Pose für Wahrnehmung nützlich sein, darf aber nicht als Belohnung der nie erreichten Wunschpose fehlbeschriftet werden. Die aktuelle Journal-API protokolliert Fehlerwerte; die Toleranzentscheidung muss der spätere Aufnahmetreiber treffen.

JSONL ist append-only, mit Sequenz, vorherigem Hash und SHA-256 je Datensatz, exklusiver Schreibsperre und fsync. Auch Entscheidungen gegen eine Aufnahme werden geloggt. Unterbrochene/defekte Protokolle und vorhandene Schreibsperren führen zum Fehler, nicht zu stiller Reparatur. Die Hashkette erkennt versehentliche Änderungen; sie ist kein Schutz vor vollständiger böswilliger Neuschreibung.

`capture-request.schema.json` beschreibt den konkreten Auftrag. Das Verzeichnis `example` enthält vier ausdrücklich synthetische Protokollereignisse: keine Aufnahme nötig, konkreter Wunschauftrag, verknüpfte positive Entscheidung, blockierter Auftrag. Es wurden dafür keine Bilder erzeugt und keine Bewegungen ausgeführt. Dieses Beispiel ist kein echter erfolgreicher Blickwechsel.

## Auswertung, Plots und Auswahlregeln

Zu allen trainierten Varianten: Training-/Validation-Loss, Train-Probe im Evalmodus, Einzel-Loss-Komponenten, Lernrate und getrennte Pose-/Anordnungsgruppen. Alle fünf Epochen plus Epoche 0, Best und Final die bisher verlangten 3D-Überlagerungen: Cyan Soll, Orange Vorhersage, halbtransparent, ohne nachträgliche räumliche Ausrichtung. Position, Größe, physische Ecken, symmetriebewusste Orientierung, 3D-IoU, fehlende und zusätzliche Objekte berichten.

Für die Anforderungsköpfe zusätzlich:

- Bedarfs-Precision/Recall und Zuverlässigkeitsdiagramme auf echten Fehler-/Gewinnlabels;
- vorhergesagter gegen tatsächlichen Nettogewinn, auch negative Gewinne;
- Fehler vor/nach Aufnahme und Anteil der verschlechterten übernommenen Ergebnisse;
- übersehene gemeinsame Fehler und fälschlich als Objekte gewählte Ziele;
- Zahl gewünschter, geplanter, blockierter, fehlgeschlagener, erfüllter und zurückgestellter Aufträge;
- Wunsch-/Ist-Posefehler und feste Kamera-Verdeckung pro Auftrag;
- durchschnittliche und maximale Zusatzaufnahmen, Zeit und Bewegungsweg;
- reine feste Kameras als Kontrolle für veränderte Roboterbilder;
- gepaarte Szenen-/Familien-Bootstrap-Intervalle und die drei Modellseeds getrennt.

Vorgeschlagene Entwicklungsgates vor Aktivierung: kein deutlicher Rückschritt auf ursprünglichen Ansichten (vorläufig mehr als 0,5 mm Positionsfehler oder mehr als 1 Prozentpunkt weniger 10-mm-Recall), messbarer Nutzen auf neuen Posen, ausreichende positive Anfragefälle und geringe Quote schädlicher Übernahmen. Als Ziel für Letztere zunächst höchstens 5 %, mit Konfidenzintervall statt nur Punktwert; keine garantierte Fehlerquote. Die endgültigen Gates werden vor einer ersten großen Auswertung festgeschrieben, nicht nach Ansehen der Schlusswerte.

Maximal zwei zusätzliche Aufnahmen, danach Ergebnis zurückstellen, wenn die Evidenz nicht reicht. Kein endloses Nachfragen. Ein untrainierter Kopf, fehlende Freiraumkarte, abgelaufene Kalibrierung oder veränderte Szene löst keine Armbewegung aus.

## Grenzen und Status der Umsetzung

Fertig sind Konzept, maschinenlesbare Konfiguration, untrainierte Kopfprototypen, Auftrags-/Entscheidungsjournal, Koordinatenkonvertierung, Schema und synthetisches Speicherbeispiel. Die Parameterzahlen und Journalfunktionen wurden ohne Optimizer getestet.

Noch nicht implementiert sind V3-Datenerzeugung, Historienanpassung, Trainingsschleifen, Lern-/Kalibrierung der Anforderungsköpfe, Verbindung zum echten Aufnahmetreiber sowie ein realer kollisionsfreier Blickwechsel. Die bestehenden bisherigen Simulationsversuche werden nicht rückwirkend als mit diesem Journal ausgeführte Aufträge dargestellt. Der konkrete neue Trainer muss diese Schnittstelle ab der Erzeugung seiner ersten Kandidaten benutzen.

Unbekannte Objektgeometrie ist zur Laufzeit keine Eingabe. Die Simulation darf sie als Lern-/Auswertungslabel liefern. Zuverlässiger Realtransfer, unbekannte Nicht-Quader und präzise Lego-Verbindungen sind weiterhin eigene Aufgaben. Montage/IL/RL und ein Placement-Quality-Modell werden durch diesen Vision-Plan nicht bereits trainiert.

## Quellen und Reproduktion

Mehrblick-Repräsentationen mit randomisierten Blickwinkeln werden in [Seo et al., ICML 2023](https://proceedings.mlr.press/v202/seo23a.html) untersucht. Koordinierte aktive Kamera-/Handsteuerung unter Verdeckung wird in [Cheng et al., CoRL 2018](https://proceedings.mlr.press/v87/cheng18a.html) untersucht. Beide Arbeiten motivieren die Richtung; die hier vorgeschlagenen MLPs, Schwellen und Datengrößen sind ein eigener, noch ungetesteter Entwurf und keine nachgewiesene Replikation dieser Methoden.

```powershell
& .\praxis\.venv\Scripts\python.exe experiments/vision/visual_active_v3_20261101/request_heads.py
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_capture_requests.py -q -p no:cacheprovider --basetemp=praxis/.cache/capture_request_tests_new
```

Der Kopf-Forward prüft nur zufällig initialisierte Netze. Er führt kein Training aus. Das synthetische Journalbeispiel kann einmalig mit `make_request_example.py` in einen noch nicht vorhandenen Ordner erzeugt werden. Aktuell sind elf Tests bestanden; der normale externe pytest-Tempordner war in der Sandbox nicht schreibbar, weshalb der Testlauf einen neuen Workspace-Tempordner verwendet hat.
