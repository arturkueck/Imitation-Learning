> **Aktueller Stand:** [Abgeschlossene Startprüfung](EXECUTION_READINESS.md), [Datensatzbericht](DATASET_REPORT.md), verbindlicher READY_PLAN_v2.json. Ältere Zwischenstände sind überholt.

# Neuer Trainingslauf: kontrollierter B0/B-Pilot

24.10.2026. Konzeption und technische Vorbereitung, **kein gestarteter Dauerlauf**. Maschinenlesbare Parameter: [training_plan.json](training_plan.json). Das frühere 12h-Training ist abgeschlossen; dessen Freigabe wird nicht als Aktivierung dieses neuen Plans interpretiert.

## Entscheidung nach zwei Agentprüfungen

Der erste Agent hat [Schwachstellen und Abnahmekriterien](AUDIT_FINDINGS.md) unabhängig aufgelistet. Der zweite Agent behebt die Daten-/Sampler-/Loss-/Collectorfehler in neuen Modulen und protokolliert die tatsächliche Prüfung in [IMPLEMENTATION_VALIDATION.md](IMPLEMENTATION_VALIDATION.md).

**Erster Vergleich nur B0/B.** Beide beginnen je Trainingsseed mit exakt demselben der drei früheren C-Parentmodelle. Beide erhalten denselben eingefrorenen Datensatz, dieselben Frames in derselben Reihenfolge und dieselbe Optimierung. Nur das Gewicht des neuen Übergangsdatenanteils unterscheidet sich:

| Faktor | B0 | B |
|---|---|---|
| Übergangsabschnitte | dieselben gültigen Abschnitte | dieselben gültigen Abschnitte |
| Qualitätsgewicht | immer1 | 0,5+1,5×Q |
| Original/Replay/Neu | 50/25/25% | 50/25/25% |
| Actor und Controller | identisch | identisch |
| Elternmodell und Samples | pro Seed identisch | pro Seed identisch |

Damit wird tatsächlich Gewichtung isoliert. Zusätzliche Turmfeatures(C), geänderte Rückzugsphasen, Sicherheitscontroller und RL bleiben ausgeschlossen und würden eigene Vergleiche erfordern. Der unveränderte Parent ist als Nullupdate-Modell auswählbar.

## Wichtige Messkorrektur vor jeder neuen Sammlung

Die Prüfung hat einen realen Fehler entdeckt: Der Greifer ist ein Robosuite-Dictionary. Die alte `check_contact(gripper_dict,cube)`-Abfrage erfasst dessen Geometrien nicht und kann trotz tatsächlichem Griff `False` melden. Der native Graspcheck unterstützt Dictionaries dagegen. Der neue Collector iteriert die konkreten Greifergeometrien, speichert nativen Griff und prüft das untere Präfix mit korrekten Fingerkontakten.

[Historische Messkorrektur](../stack_five_curriculum_20261023/MEASUREMENT_CORRECTION.md). Die bisherigen Prozentwerte werden nicht nachträglich als Quoten einer korrigierten kontaktfreien Metrik ausgegeben. Beide neuen Arme verwenden identisch die neue Metrikversion.

Ein weiterer Rekonstruktionsversuch zeigte: `sim.forward()` auf dem historischen gespeicherten Zustand reproduziert die damals geloggten abgeleiteten Positionen nicht exakt; im untersuchten Beispiel beträgt die Abweichung bis ungefähr0,56mm. Deshalb werden daraus keine nachträglichen exakten Grasp-/Kontaktlabels konstruiert. Das fehlgeschlagene Preflight und seine Fehlermeldung bleiben erhalten. Statt toleranzbasiert vermeintlich korrekte Labels zu erzeugen, wird für den echten Vergleich neu mit synchronisierten Zuständen gesammelt.

## Geplante Ausführung in vier Stufen

### 1. Native Datenerfassung und Integrität

200 feste Vollrollouts:100 mit drei und100 mit vier Würfeln. Pro Höhe Indizes0–59 Training und160–199 Validierung (Laufzeitrevision v2); Teacher zyklisch aus den drei vorab eingefrorenen Parents zuweisen. Keine Wiederholung bis zum gewünschten Erfolg und keine neuen Skriptexpertenaktionen. Die Sammlung enthält auch Fehlschläge, aus denen vollständig sichere lokale Übergänge extrahiert werden können.

Neue Namensräume:3er510000–510199,4er511000–511199. Ein Scan historischer JSON-Seedfelder ergab keine Kollisionen mit den geplanten Bereichen. Vor Aktivierung nochmals prüfen. Die technischen Seeds498001/498002 bleiben von Training, Auswahl und Erfolgsstatistik ausgeschlossen.

Collector muss exakt vor/nach Aktion synchronisierte Beobachtungen und Simzustände, native Griffe, alle Fingerkontakte, Controllerzustand und Teacheraktionen speichern. Kontakt mit der neu aufgenommenen Quelle ist erlaubt; geschützt wird ausschließlich das bereits gestapelte Präfix.

### 2. Übergangsdaten und Informationsgate

Ein gültiger Übergang beginnt nach zehn gültigen fingerfreien Präfixframes. Das nächste Quellobjekt muss binnen200 Steuerschritten mindestens30mm angehoben und dabei mindestens fünf aufeinanderfolgende Frames nativ gegriffen werden. Der untere Turm bleibt während des Abschnitts und50 weiteren Nachlaufframes streng gültig. Die Aktionsziele enden am bestätigten Pickup; der Nachlauf dient nur dessen Bewertung und wird nicht zusätzlich als Transporttraining eingeschleust. Unvollständige Episodenenden werden zensiert/abgelehnt.

Diese strenge Akzeptanz ist bewusst konservativ. Dadurch sind Erhalt- und Kontaktfreiheitsanteile des Scores unter akzeptierten Abschnitten weitgehend konstant; die tatsächlich verfügbare Qualitätsvariation muss aus den gemessenen Ruhe-/Zentrierungsreserven stammen. Kein künstlicher Qualitätsgewinn wird behauptet.

Scoreversion `strict_contact_lift_v1_no_clearance`:0,50 konstanter Erhaltterm,0,25 Ruhe und0,25 Zentrierung. Kontaktfreiheit wird ausschließlich als hartes Kriterium geprüft; Freiraum ist ausgeschlossen. Das ist eine ausdrücklich vereinfachte erste Ablation gegenüber dem fünfteiligen Vorschlag. Es gibt keine verlässlich gemessenen Freiraumabstände im alten Bestand. Die ursprüngliche fünfteilige Grafik im README bleibt als weitergehender Vorschlag gekennzeichnet; sie ist nicht der v1-Produktionsscore.

Geplante Pilotgates: mindestens30 gültige Trainingsabschnitte aus20 Familien sowie10 Validierungsabschnitte aus10 Familien, mindestens zwei verschiedene Teacherquellen, keine Familie in mehreren Splits. Rohscore-Standardabweichung mindestens0,02 und ein messbarer neuer Actorgradient über1e-10 dienen als vorab festgelegte technische Informativitätsprüfungen, nicht als universelle Lernschwellen. MSE und Gradient je Parent/Phase/Teacher, Scorekomponenten, Gewichtungsverteilung und effektive Stichprobengröße protokollieren. Bei fehlender Vielfalt oder fast null Gradient nicht automatisch mehr Updates starten.

Quellhashes, Teacheraktionen, zeitliche Zuordnung und bewusst korrumpierte Negativbeispiele müssen geprüft sein. Historische Fingerflags werden nie als verifizierte Native-Messung akzeptiert. Der vorhandene historische Datensatz ist nur Inventur-/Proxyquelle; seine derzeit streng nachweisbaren Abschnitte reichen nicht zur Produktionsfreigabe.

### 3. Gepaarte Optimierung und Entwicklung

Je drei Parents × zwei Arme = sechs Modelle, zunächst je10.000 Updates, Batch64, AdamW3e-5, WeightDecay1e-6, Gradientenclip10. Checks bei0/3000/10000 Updates. Das sind insgesamt60.000 geplante Updates; höchstens23,43 Originalpass-Äquivalente pro Modell bei Normierung aller Mischbeispiele auf27.322 Originalframes. Historische Vortrainingskosten und neue Simulation werden zusätzlich bezahlt.

Die neuen16 Frames werden im Loss gewichtet und innerhalb dieses Viertels normalisiert. Qualitätsgewichtung verändert weder die Original-/Replaymasse noch die Samplinghäufigkeit. Phasen → Episode → Abschnitt → Frame werden nur aus tatsächlich vorhandenen Gruppen gezogen; es wird keine künstliche Vollständigkeit aller sieben Phasen verlangt. Identische Samplehashes beider Arme nachweisen.

Completion-BCE nur auf Originalexpertframes. **Das friert die Completionvorhersage nicht ein:** Action- und Completionoutput teilen Hiddenlayer. Deshalb die originale Completionvalidierung und simulierte Phasen-/Rückzugsdauern separat verfolgen.

Primäre Entwicklung: vorbereitete Präfixe mit zwei bzw.drei Würfeln, je20 neue Startfamilien520000/521000. Gleicher vollständiger Simulations- **und** Controllerzustand pro Modellvergleich; erste Aktion und nächster Zustand müssen im technischen Replay identisch rekonstruierbar sein. Vollständige Controller- und Sequencerzustände sind nun gespeichert; der Replay in frischer Umgebung wurde für Drei- und Viererzustände mit exakt identischer erster Aktion und Folgezustand bestätigt. Gescheiterte Benchmarkvorbereitung wird als Coveragefehler sichtbar, nicht aus dem Nenner entfernt.

Metrik: Anteil erfolgreicher nächster Aufnahmen mit **durchgehend gültigem unterem Präfix**. Native Aufnahme alleine genügt nicht. Ergänzend je10 neue vollständige2er/3er/4er-Rollouts in getrennten Bereichen522000/523000/524000. Auswahl ausschließlich auf Entwicklung: zuerst schlechteres der beiden Übergangsstrata verbessern, dann vollständiger Vierererfolg, dann geringere Regression, bei exaktem Gleichstand früherer Checkpoint. Die konkrete Tupelberechnung muss im Evaluator implementiert und getestet sein, bevor `--train` freigeschaltet wird.

### 4. Freeze, unabhängige Bestätigung und Schlussauswertung

Die Entwicklungsentscheidung auf je20 getrennten Übergangsfamilien525000/526000 bestätigen. Praktisches Fortsetzungskriterium: mindestens fünf Prozentpunkte Verbesserung in beiden Präfixstrata, bestätigt bei mindestens zwei der drei Lernseeds, ohne mehr als fünf Prozentpunkte Regression niedrigerer Stapelhöhen. Das ist eine operative Pilotentscheidung mit kleiner Stichprobe, kein Signifikanzbeweis. Gepaarte Unsicherheit und jeden Seed offen berichten.

Alle sechs ausgewählten Modelle vor reservierten Endtests einfrieren. Je Modell50 Übergangsstarts pro Präfixgröße(530000/531000),50 vollständige Zweier(532000),100 vollständige Dreier(533000) und100 vollständige Vierer(534000). Die Startbereiche sind in JSON exakt begrenzt. Keine weitere Optimierung oder Modellauswahl aus Endtests. Vorbereitete Türme zählen niemals als vollständige Stapelerfolge. Ein Fünfertraining ist nicht Bestandteil dieses ersten Piloten.

## Budget und technische Aufsicht

Obergrenze acht Stunden AB GO: bis5h für gepaarte Optimierung und Entwicklung, mindestens3h für Endtests/Bericht. Die abgeschlossene Datenerfassung/Prüfung wird separat bilanziert. Das ist noch keine aktivierte Deadline. Erst beim Start feste UTC-Zeit und unabhängigen Supervisor setzen; Deadline niemals nachträglich verlängern. Die Evaluation kann das Budget dominieren; vor Aktivierung anhand technischer Laufzeiten prüfen und gegebenenfalls den gesamten Plan vorab verkleinern, nicht unbemerkt nur einen Arm kürzen.

Kein automatischer Retry, keine blinde Fortsetzung in bestehende Ausgabeordner, keine zweite Instanz. Gültige Teilergebnisse und Fehlerursache behalten. Keine neuen Hintergrundprozesse oder Automationen in der Konzeptionsphase.

## Was der Code jetzt belegt – und was nicht

Ausgeführte technische Prüfungen stehen ausschließlich in IMPLEMENTATION_VALIDATION.md und den zugehörigen JSON-Artefakten. Kurze Optimizer-Smokes prüfen Loss, Paarung und Serialisierung; sie belegen keine Verbesserung von Turmerhalt oder Erfolgsrate. Ein positiver Kontakt-/Grasp-Smoke belegt die Messleitung, keinen repräsentativen Trainingserfolg.

Datensatzgates, Onlineevaluation, Checkpointauswahl und vollständiger vorbereiteter Replay sind inzwischen bestanden beziehungsweise implementiert und geprüft. Der Langlauf wartet ausschließlich auf das ausdrückliche Go für READY_PLAN_v2.json. Diese offenen Punkte werden nicht durch einen erfolgreichen Unit-Test ersetzt. Das Trainingskonzept ist damit klar spezifiziert und der Daten-/Lernkern überprüfbar; eine vollständige empirische Bestätigung seiner Güte erfolgt erst im eigentlichen kontrollierten Versuch.
