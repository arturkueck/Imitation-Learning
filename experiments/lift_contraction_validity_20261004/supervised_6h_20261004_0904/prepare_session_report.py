"""Separate research synthesis; preserve the completed pilot report."""
import json,hashlib,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
S=Path(__file__).resolve().parent;ROOT=S.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (S/'SESSION_RESEARCH_REPORT.md').exists()
session=read(S/'session.json');pilot=read(S/'pilot_summary.json');ref=read(S/'method_reference_001/result.json')
assert pilot['training_updates_per_arm']==2000 and not pilot['robust_algorithmic_improvement_established']
assert ref['state']=='REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE'
names=['mechanism_AB_001','mechanism_AB_002','mechanism_action7_001','mechanism_correction_001','gradient_audit_001','mechanism_domain_001','recorded_domain_001','recorded_response_001','local_response_001','clearance_filter_001','external_proxy_001','error_margin_001','method_reference_001']
costs=[]
for name in names:
    p=S/name;r=read(p/'result.json');sup=read(p/'supervisor_result.json')
    costs.append(dict(name=name,raw_state=r['state'],worker_seconds=r.get('elapsed_seconds'),supervisor_seconds=sup['elapsed_seconds'],
                      counts=r.get('counts'),result_sha256=sha(p/'result.json')))
jobs=[]
for p in S.rglob('supervisor_result.json'):
    if 'attempts' in p.relative_to(S).parts:continue
    r=read(p);jobs.append(dict(path=str(p.relative_to(S)),returncode=r.get('returncode'),elapsed_seconds=r['elapsed_seconds'],worker_identity=r['worker'],job_closed=r['worker_job_closed']))
inventory=dict(primary_diagnoses=costs,recorded_diagnostic_supervisor_jobs=jobs,total_recorded_diagnostic_supervisor_seconds=sum(x['elapsed_seconds'] for x in jobs),
               includes_recorded_preflights_failures_and_independent_verifiers=True,excludes_pilot_and_uninstrumented_foreground_preparation_analysis=True,
               pilot_training_seconds={k:v['total_training_seconds'] for k,v in pilot['learning_and_costs'].items()},pilot_evaluation_seconds=pilot['evaluation_seconds'])
with (S/'research_cost_inventory.json').open('x',encoding='utf-8') as out:json.dump(inventory,out,indent=2)
costtable='\n'.join(f"| [{c['name']}]({c['name']}/RESULT.md) | {c['worker_seconds']:.3f} | {c['supervisor_seconds']:.3f} | {c['raw_state']} |" for c in costs if c['worker_seconds'] is not None and (S/c['name']/'RESULT.md').exists())
now=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2))).isoformat()
report=f'''# Ergebnis der beaufsichtigten BC-Forschung

Fachlicher Stand {now}. Sessionfenster **04.10.2026,09:11:19–15:11:19Berlin**, unverändert sechs Stunden. Forschungsarbeit ausgewertet; organisatorischer Abschluss mit tatsächlichem Prozess-/Wachhalteende wird nach Deadline separat unten ergänzt. [Sessionprotokoll](SESSION_PROTOCOL.md), [operative Endprüfung](SESSION_CLOSEOUT.md). Der alte [Pilotbericht](RESULT.md) bleibt erhalten.

**Hauptaussage:** Das Projekt besitzt begrenzte historische Lift-Taskgewinne einer Kontraktionsregularisierung. Die jetzige Arbeit identifiziert konkrete Fehler ihrer lokalen Dynamikapproximation und implementiert einen korrigierten Lossentwurf. **Eine robuste neue BC-Algorithmusverbesserung, schnellere Trainingskonvergenz und eine Erklärung des Direct-vs-Diffusion-Gaps sind weiterhin nicht etabliert.** Der neue Sensorvergleich ist genau ein Trainingsseed; alle nachfolgenden Simulatorzweige benutzen eingefrorene Checkpoints und sind keine zusätzlichen Trainingsreplikate.

## 1. Primärliteratur, getrennt von Projektbefunden

Die Originalarbeiten wurden vor Implementationsentscheidungen geprüft und für diese Synthese erneut am04.10.2026 gelesen. Externe Resultate übertragen sich nicht automatisch auf diesen Lift-/Stack-Aufbau.

| Originalarbeit | Allgemeiner Beitrag | Konsequenz für dieses Projekt |
|---|---|---|
| [Stable-BC, Mehta et al.2024, AbschnitteIII–IV](https://arxiv.org/html/2408.06246v1) | Modelliert gekoppelte lokale Fehlerdynamik und formuliert modellbasierte bzw. eingeschränkte modellfreie Stabilitätsbedingungen; nimmt bekannte Roboterdynamik voraus. | Unser diskreter finite-Differenz-Loss auf EEF-Position mit empirischem A/B prüft nicht sämtliche Eigenwert-/Kopplungsbedingungen des Papers. Keine Übernahme seiner Garantie. Die dortige Konvergenz der Zustandsfehler ist außerdem kein Nachweis weniger Optimizerupdates. |
| [CCIL, Ke et al., Abschnitte4.2–4.3 undAppendixB](https://arxiv.org/html/2310.12972v2) | Lernt lokal kontinuierliche Dynamik, erzeugt korrigierende Labels und begrenzt deren Fehler unter lokalen Annahmen; behandelt ungeeignete Bereiche gesondert. | Fehler-/Gültigkeitsgewichtung ist eine bestehende Idee. Expert-OLS-Gain und Kontaktfreiheit ersetzen die erforderliche lokale Genauigkeitsprüfung nicht. |
| [Deshpande et al.2024, AbschnitteIV-C/IV-D](https://arxiv.org/html/2405.19307v1) | Untersucht CCIL in feiner Manipulation; im dortigen Versuch können schlechte generierte Labels Leistung verschlechtern. Labelqualität und zusätzliche Datenabdeckung bilden einen Trade-off. | Begründet die Messung von Fehlannahmen **und** Abdeckung; belegt weder Schaden noch Nutzen unseres noch untrainierten Losskandidaten. Kontakt ist auch kein universeller Ausschluss aller möglichen lernbaren Dynamikmodelle. |
| [DART, Laskey et al.2017](https://proceedings.mlr.press/v78/laskey17a.html) | Stört Expert-Ausführung bei der Demonstrationsaufnahme und passt den Störungsumfang an Lernerfehler an. | Unsere bestehende Offline-Sensoraugmentation erhebt keine echten Experten-Recoveryaktionen; anderes Label-/Datenregime. |
| [DAgger, Ross et al.2011](https://proceedings.mlr.press/v15/ross11a.html) | Aggregiert Expertlabels auf von der lernenden Policy besuchten Zuständen. | Benötigt zusätzliche Expertabfragen; kein solcher Zugang in den jetzigen Offlineproben. |
| [ACT, Zhao et al.2023](https://www.roboticsproceedings.org/rss19/p016.html) | Verbindet Actionchunking mit temporalem Ensembling für feine Manipulation. | Bestehende Stack-Baselines nutzen bereits Chunks. ACT-Erfolg erklärt den lokalen Direct-/Diffusion-Vergleich nicht kausal. |

Mögliche Eigenleistung: überprüfbare, kostenbilanzierte volle und zustandsabhängige Dynamikregularisierung unter expliziten Gültigkeits-/Fehlerannahmen. Neuheit ist **nicht** durch einen B7-Fit oder die allgemeine Regularisierungs-/Recoveryidee nachgewiesen. Erst saubere Abgrenzung zu Literatur und replizierter Nutzen tragen einen wissenschaftlichen Verbesserungsanspruch.

## 2. Verifizierte historische Projektergebnisse

[Separater Rohdaten-/Hashaudit](../legacy_verification.json): drei alte Lift-Trainingsseeds. Bei10000Updates nominal BC44/60 versus bestehende Kontraktion56/60; unter+2cmOffset47/60 versus55/60, unter−2cm37/60 versus57/60; +Impuls41/60 versus59/60, −Impuls48/60 versus55/60. Bei2000Updates nominal23/60 versus36/60. Die älteren2000Update-Auswertungen haben180fehlende Initialzustands-Paarmetadaten; spätere Auswertungen prüfen gepaarte Starts. Das sind lokale Taskbefunde der bestehenden Methode, keine etablierte Erklärung ihres Mechanismus, keine ausaggregierten60unabhängigen Trainingsreplikate und kein Zeitkonvergenznachweis.

Expert-OLS-K sagt Demonstrationsübergänge vergleichsweise gut voraus, besteht aber die geprüfte partielle Aktionsantwort nicht. Die Schlussfolgerung „Zustands-/Aktionskorrelation ersetzt keine kontrollierte kausale Aktionsintervention“ ist durch Projektinterventionen gestützt. Welche verborgenen Zustands-/Controllergrößen die gesamte Abweichung erklären, bleibt offen. [Vorherige Forschungsetappe](../RESEARCH_STATUS.md).

Der frühere unveränderte StackTwo-C-Diffusionslauf wurde auf Nutzerwunsch bei **16800Updates** abgebrochen, Checkpoint/Logs/Hashes erhalten, keine finale Evaluation. [Abbruchnachweis](../../stack_overnight_C_diffusion_20261004/cancellation_verified.json). Er bleibt beendet. Lift-Nativerfolge sind keine stabilen Stacks; weder dieser Abbruch noch die folgenden Lift-Diagnosen beantworten den Direct-vs-Diffusion-Gap.

## 3. Ein neuer Trainingsseed: BC versus Sensoraugmentation

`attempt_002`, Seed41004,180/20Lift-PH-Demos, gleiche256×256Policy/Adam1e-4/Batch100; identische Anfangsgewichte und gesamte Trainingsbatchreihenfolge. Jeder Arm **genau2000Optimizerupdates**, alle104Evaluationsepisoden komplett. Keine anhand von Evaluation gewählte Zwischencheckpointauswahl. Verifiziert302Source-/Konfigurationsdateien und916Runtimeassets bei Pilotabschluss; [Nachweis](verification_1791098800.json), [effektive Konfigurationen/Checkpoints](attempts/attempt_002), [Rohzusammenfassung](pilot_summary.json).

Sensorarm:50%sauberer BC-Loss und50%gleicher Expertenaktion unter zufälliger5mmEEF-Messstörung, abgeleitetes Objekt-minus-EEF-Feature passend geändert; keine physisch verschobene Expertaufnahme. Separate Noise-RNG schützt Batchpaarung. Keine neue Policyarchitektur.

| Finale Bedingung, feste Starts | BC | Augmentation |
|---|---:|---:|
| Nominal |4/10|3/10|
| Sensorbias+5mm |3/10|4/10|
| Sensorbias−5mm |3/10|4/10|
| Tatsächlicher Aktionsimpuls |3/10|3/10|

Sensor6/20→8/20 bei nominalem Verlust; die20Fälle sind zwei Bedingungen auf denselben10Starts, nicht20unabhängige Trainingsreplikate. Kleine vorab fixierte Entwicklungsregel genau erfüllt, keine robuste Überlegenheit. Nominale Lernkurve der ersten6Starts für beide0/6bei500,0/6bei1000,1/6bei2000; nachhaltige4/6Schwelle von keinem erreicht, beide zensiert. **Kein schnellere-Konvergenz-Nachweis.** Trainingszeit8.859sBC/11.391sAugmentation, Evaluation182.095s. Letzter Loss0.04073427/0.04005975; unterschiedliche Ziele, deshalb kein eigenständiger Verbesserungsnachweis aus diesen Losswerten.

Dataset-SHA256 `2067777cb8b532e9263dd09fd6448c41cc31224bb27be4a3b734010ae13eb540`; B0-Endcheckpoint `27a38fc65415d419a060cd0fc529f8f30d82bc36cdf77d54cc79d7a3e52117fa`, B1 `0850c472342f79bada30dde6b7e2f9cbf0d106b0fd76144f41eb0177f404d6e9`. Losskurven, effektiveConfigs und vollständige Checkpointmanifeste in den Armen. Technischer attempt_001scheiterte vor Training an abgeleiteten Configschlüsseln; korrigiert mit frischem Preflight und Versuch, ursprüngliche Artefakte erhalten.

## 4. Mechanismusbefunde, keine weiteren Trainingseeds

| Frage | Verifizierter eigener Befund | Tragweite |
|---|---|---|
| Passt Expert-OLS als Aktionsgain? | [A/B-Diagnose](mechanism_AB_002/RESULT.md): OLS0/18, frühere partielleKalibrierung18/18, neuerFit18/18 auf getrennten Prüfdemos. | Partielle kausale Aktionsantwort, keine Policyverbesserung. Technisch reparierte Wiederholung mit bereits gesehenen Ankern kein neuer unberührter Bestätigungssatz. |
| Fehlt Rotation? | [Volle7D-Antwort](mechanism_action7_001/RESULT.md): bei gleichem A/Translationsfit91.9%weniger medianer Ratiofehler,6/6Prüfanker besser; Gripper früh degeneriert. | Unterstützt Einbeziehung der Rotation, keine91.9%Taskverbesserung. |
| Verbessert genauere Vorhersage die tatsächliche Korrektur? | [Korrekturtest](mechanism_correction_001/RESULT.md):88.9%weniger Ratiofehler, aber beide kalibrierten Korrektoren72/72Ein-Schritt-Schwellen; volleVariante braucht mehr Kommandonorm. | Kein besseres Recoveryverhalten gegenüber Translationskontrolle etabliert. |
| Ist gleicherlambda ein fairer Vergleich? | [Gradientenaudit](gradient_audit_001/RESULT.md): B7/OLSNormquotient spät4.07Train/2.77Valid, früh1.06/1.09. | Stärke/Richtung verändern sich abschnittsabhängig; zusätzlich kontrollieren. |
| Gilt Kalibrierung für alle Phasen? | [Live-Domain](mechanism_domain_001/RESULT.md): Herstellung12/12, Domain8/12; alle4späten Kontakte. [Statische Zuordnung](recorded_domain_001/RESULT.md):60/60geometrisch passend,49/60statisch frei. | Gültigkeit nur konditional; statische Annotation kein dynamischer Beweis. |
| Erklärt kontrollierte Controllergeschichte die Übertragungsfehler? | [Zwei Ersatzgeschichten](recorded_response_001/RESULT.md):672Zweige,24/24hergestellt,16/24frei; ähnliche Antworten, trotzdem sechs falsche B7-Freigaben je Geschichte. | Diese beiden Historien erklären den Fehler nicht hinreichend; Originalexpertgeschichte nicht rekonstruiert. |
| Hilft lokale statt feste B7? | [Neue lokaleIdentifikation](local_response_001/RESULT.md):56.12%weniger Fehler,8/8Anker besser, falscheFreigaben6→1. | Zustandslokalität gestützt, lokale Simulator-/Cachekosten nötig, Restfehler bleibt. |
| Liefert ein vorab verfügbarer Filter ausreichend Coverage? | [AlleNähepaare](clearance_filter_001/RESULT.md):0/12akzeptiert. [ExternerProxy](external_proxy_001/RESULT.md):7gültigakzeptiert,0falsch,1gültigverworfen; einfacherKontaktflag hier besser. Spätere [neueProbe](error_margin_001/RESULT.md) hat M0eineFehlannahme, M2keine bei gleicher7/12Abdeckung. | All-Paar-Regel verworfen, externerFilter begrenzter Trade-off statt universeller Garantie. TatsächlicheSelbstkontakte im Label unverändert. |
| Überträgt sich eine empirische Fehlerhülle? | [NeueDemos](error_margin_001/RESULT.md): alteepsilon0.0021163913,10/48gültigeAntworten überschreitenGrenze; falscheFreigaben2→0, richtigeFreigaben10→4. | Vorab fixiertes Entwicklungsgate **verfehlt**; kein Vergrößern/Retuning aus Prüfoutcomes. |
| Ist der konkrete Lossentwurf berechenbar? | [Referenz](method_reference_001/RESULT.md):7D/A/B_local/w/epsilon implementiert, NumPyprüfung und4/4Parameterableitungen bestanden; Policyfeatures12/12passend, privilegierterB_cache8/12, effektiveCoverageM0 48/72/M2 42/72. | Rechenbarkeit bestätigt; produktiver Algo unverändert, gescheiterteFehlerhülle und Trainingsgates bleiben offen. |

Echte körperliche5mmEEF-Perturbationen, festeOrientierung/Geschwindigkeit/Objekt/Gripper/Controller-/Auxiliarzustände und Kontakt/Wiederholungsgates geprüft. Fehler-/Kontaktfälle bleiben in geplantenNennern; keine wissenschaftlich negativenFrames ersetzt. Gegenprüfungsdemos jeweils vorab disjunkt von bis dahin verwendeten Daten; posthocExploration und reparierte technischeWiederholung gesondert markiert. Ein gefrorenerBC-Checkpoint, keine breit repliziertePolicyfamilie.

## 5. Geranktes Hypothesenledger und Forschungsentscheidung

| Rang | Hypothese | Status / nächstes diskriminierendes Ergebnis |
|---:|---|---|
|1|Die verbleibende feste offeneZustandsantwort A begrenzt die enge Fehlerentscheidung.|LokalesB verbessert; Restfehler/gescheiterteHülle bleiben. FrühesA≈I widerspricht großem grobemFehler, schließt entscheidungsrelevante kleine lokaleFehler nicht aus. Lokal identifiziertesA gegen gleichesfestesA bei gleichemB_local auf neuenDemos testen. **Noch Hypothese.**|
|2|Volle und zustandslokale Aktionsantwort verhindert falsche Lossbewertung.|Rotation und B-Lokalität in mehreren kleinenInterventionstests gestützt. Preiswerte breiteCacheversorgung/Aktionsdomain bei weitertrainierterPolicy ungeprüft.|
|3|VerfügbaresDomaingewicht und übertragbareFehlergrenze erlauben nützlicheRegularisierung.|All-PaarFilter verworfen, extern begrenzteCoverage/Trade-off. Endliche globaleFehlerhülle scheitert; keineTrainingsfreigabe.|
|4|Ein Nutzen des Losswechsels kann bloß geänderteGradientenstärke sein.|Stärkeunterschiede gemessen; passendeKontrollbedingung erforderlich. Noch kein neuerTrainingseffekt zurErklärung.|
|5|Sensoraugmentation liefert robusteRecovery oder schnellereKonvergenz.|EinSensorpilot zeigt kleinenBiasvorteil/nominalenVerlust, echterImpuls gleich, Kurven zensiert. Keine Unterstützung für diese stärkerenAussagen.|
|6|Mehr unverändertesDiffusionstraining erklärt/verbessertBC.|KeinAlgorithmenvergleich, aufNutzerwunsch abgebrochen. Wird nicht verfolgt.|

Minimaler **nächster Versuch außerhalb dieser Session**, noch nicht gestartet: vier neueTrain-Demos vorab aus dem180/20Split fixieren, je10/50/85%Frame, eingefrorenesB0; gleiche336Zweige. B_local aus14nominalenAktionsinterventionen, A_local aussechsnominalenphysischenZustandsinterventionen, getrenntePfull-Zweige prüfen. Primär einzig A_frozen/B_local gegen A_local/B_local, gleiche alteFehlerhülle/Schwelle, vollständigeCoverage/Kontakt-/Klassifikations-/Vektorfehler-/Kostenangaben. Gegenprüfung ist von A/B-Identifikationszweigen getrennt. Kein nachträgliches Erhöhenepsilon; Rang-/Gatefehler erhalten. Das isoliert die Zustandsapproximation, statt ein unverändertesModell erneut zu trainieren. Vor Launch konkretesProtokoll/Seed/Quelle/Entscheidungsregel einfrieren; dieser Bericht ist eine Empfehlung, keine automatisch eingeplante neueSession.

Erst bei tragfähigenDomain-/Fehler-/Kosten-/Cache-/Aktionsregiongates: vorab budgetierter gepaarterMethodenvergleich mit mehrerenTrainingsseeds, gleichemDemosplit/Initialgewichten/Batches/Starts/Updatebudget. NeueRegularisierung gegenBC und bestehendeKontraktion sowie eineKontrolle der effektivenGradientenstärke. Sensorbias und tatsächlicheAktionsstörung separat, Taskerfolg/Teilphasen sowieUpdate-/Gesamtzeitkurven getrennt; gesamteSimulatoridentifikation mitzählen. KeinBestCheckpoint nachEvaluation. AufStack separat stabileStackmetriken/feste40Starts prüfen, LiftErfolg nicht alsStackerfolg ausgeben.

## 6. Zusatzkosten, Fehler und Nachvollziehbarkeit

| Diagnose | Primärworker s | Primärsupervisor s | Unveränderter Rohstatus |
|---|---:|---:|---|
{costtable}

Diese Tabelle zählt Primärworker/aufsicht; nicht addieren, weilSupervisorzeitWorkerzeit einschließt. Alle **{len(jobs)}** gespeicherten Diagnose-Supervisorjobs einschließlich Vorprüfungen, technischerFehlversuche und unabhängigerVerifikation zusammen **{inventory['total_recorded_diagnostic_supervisor_seconds']:.3f}s**; [vollständigesKosteninventar](research_cost_inventory.json). Nicht vollständig instrumentierte ForegroundVorbereitung/Analyse und alleSetupforwards sind darin nicht erschöpfend enthalten; daher kein vollständigerEnd-to-End-Laufzeitbenchmark. Pilottraining/Evaluation separat. VielhöhererKalibrieraufwand als20.25sPilottraining verhindert schon jetzt eine Behauptung allgemeinerBeschleunigung aus Trainingssekunden allein.

TechnischeNegativeerhalten: attempt_001Configvorstart; mechanism_AB_001verändertesSolverwarmstart undfrischeReparatur; mechanism_correction_001Aggregation erst nach312Zweigen, reineAnalyse-ReparaturenohnePhysikwiederholung; recorded_responseVorprüfungsmetadaten; clearanceVorprüfungen mit nichtberechneten nativenInsel-/DualArbeitsarrays und dokumentierterkonditionalerHashkorrektur; error_marginPhaseNenner72→24 ausschließlichMetadaten in frischemOrdner. KeinefachlicheGate-/Marginlockerung. [Agentchecks](agent_checks.jsonl) protokollieren nur tatsächliche Agentaufrufe; [lokaleChecks](monitor_checks.jsonl) sind getrennt. Immediate09:26Prüfung ist scheduled:false. KeinebehauptetenAgentchecks aus lokalenWatchdogticks.

Aktuell alleForschungsworker/-jobs beendet, organisatorischeSessionaufsicht bleibt bis15:11:19Berlin ACTIVE. Der tatsächlicheoperativeSchlussnachweis wird nachDeadline ergänzt. Quellen/Configs/Dataset/Seeds/Updatecounts/Losses/Startpaarungen/Checkpointhashes sind in denverlinktenImmutableArtefakten dokumentiert. Ein späterer final_verification_-Nachweis prüft Ende und Provenienz, ohne alteBerichte oder Checkpoints zu überschreiben.
'''
with (S/'SESSION_RESEARCH_REPORT.md').open('x',encoding='utf-8') as out:out.write(report)
with (S/'report_preparation.json').open('x',encoding='utf-8') as out:json.dump(dict(created_berlin=now,report_sha256=sha(S/'SESSION_RESEARCH_REPORT.md'),cost_inventory_sha256=sha(S/'research_cost_inventory.json'),status='RESEARCH_SYNTHESIS_PREPARED_MONITORING_ACTIVE_UNTIL_DEADLINE'),out,indent=2)
print(json.dumps(dict(report=str(S/'SESSION_RESEARCH_REPORT.md'),recorded_diagnostic_jobs=len(jobs),recorded_diagnostic_supervisor_seconds=inventory['total_recorded_diagnostic_supervisor_seconds']),indent=2))
