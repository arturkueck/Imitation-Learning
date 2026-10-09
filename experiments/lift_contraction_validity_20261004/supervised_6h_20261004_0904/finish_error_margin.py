import json, hashlib, time, tomllib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import psutil
S=Path(__file__).resolve().parent; O=S/'error_margin_001'; ROOT=S.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json'); status=read(S/'status.json'); pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
assert tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())['status']=='ACTIVE'
assert all(status['progress'][a]['optimizer_updates']==2000 for a in ['B0','B1']) and status['progress']['evaluation']['episodes_completed']==104
processes={}
for p in [O,O/'preflight_001',O/'query_verification_001']:
    sup=read(p/'supervisor_result.json'); launch=read(p/'launch.json'); identity=dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])
    assert not alive(sup['worker']) and not alive(identity) and sup['worker_job_closed'] and sup['returncode']==0
    assert launch['deadline_unix']<=session['deadline_unix']
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_identity=identity,both_exited=True,worker_job_closed=True,elapsed_seconds=sup['elapsed_seconds'])
r=read(O/'result.json'); a=read(O/'analysis_verification.json'); f=read(O/'filter_analysis.json'); l=read(O/'local_identification.json')
m=read(O/'analysis_repair_001/margin_analysis.json'); v=read(O/'analysis_repair_001/margin_verification.json'); q=read(O/'query_verification_001/result.json'); pref=read(O/'preflight_001/result.json')
original=read(O/'margin_analysis.json')
assert original['primary']==m['primary'] and original['cases']==m['cases'] and original['secondary_masks']==m['secondary_masks'] and original['state']==m['state']
for phase in m['strata']:
    oldphase=dict(original['strata'][phase]);oldphase['planned_cases']=24
    assert oldphase==m['strata'][phase]
assert m['raw_sha256']==a['raw_sha256']==v['raw_sha256']==q['raw_sha256']==sha(O/'result.json')
assert v['margin_analysis_sha256']==sha(O/'analysis_repair_001/margin_analysis.json') and q['filter_analysis_sha256']==sha(O/'filter_analysis.json')
assert v['state']=='DIRECT_SOLVE_AND_MARGIN_DECISIONS_INDEPENDENTLY_VERIFIED' and q['state']=='NATIVE_FILTER_QUERIES_INDEPENDENTLY_REPRODUCED'
assert a['source_hashes_verified'] and a['executed_branches']==336 and r['policy_training_updates']==r['fit_updates']==0
now=time.time(); d=datetime.fromtimestamp(now,timezone.utc); p=m['primary']; sel=read(O/'selection.json')
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           trigger_utc='2026-10-04T12:09:46.504Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,deadline_unix=session['deadline_unix'],heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           processes=processes,worker_state=r['state'],audit_state=a['state'],margin_state=m['state'],primary=p,
           planned_anchors=12,eligible_anchors=a['eligible_anchors'],planned_branches=336,executed_branches=336,
           new_policy_updates=0,local_identification_fits=m['local_identification_fits'],epsilon_train=m['epsilon_train'],masks=f['masks'],
           hashes={n:sha(O/n) for n in ['result.json','analysis_verification.json','local_identification.json','filter_analysis.json','margin_analysis.json','margin_verification.json','analysis_repair_001/margin_analysis.json','analysis_repair_001/margin_verification.json','analysis_repair_001/REPAIR.json','query_verification_001/result.json','source_hashes.json']},
           metadata_repair='Per-phase planned denominator24 instead of mistakenly repeated global72; primary decisions and all data exactly unchanged, originals retained.',
           decision='Frozen empirical envelope evaluated without retuning. Distinguish bound violations, decision errors, domain mask and coverage; no policy improvement or universal guarantee. Preserve scientific outcome; no training/sweep. Next reference loss and cache/action-region audit, original monitoring deadline unchanged.')
table='\n'.join(f"| {'Ungesicherte lokale Vorhersage' if name=='raw' else 'Vorhersage + feste Fehlermarge'} | {p[name]['true_safe']} | {p[name]['false_safe']} | {p[name]['false_reject']} | {p[name]['true_reject']} |" for name in ['raw','upper'])
strata='\n'.join(f"| {fr} | {s['conditional_cases']}/24 | {s['bound_violations']} | {s['raw']['false_safe']} | {s['upper']['false_safe']} | {s['upper']['true_safe']} | {s['upper']['false_reject']} |" for fr,s in m['strata'].items())
violations=[c for c in m['cases'] if c['bound_violated']]
examples='\n'.join(f"- {c['demo']}, Frame {c['t']}, Achse {c['axis']} {c['sign']}: normierter Vektorfehler {c['normalized_vector_error']:.10g}, beobachtete Ratio {c['observed_ratio']:.10g}, Vorhersage {c['raw_ratio']:.10g}, Vorhersage+Marge {c['upper_ratio']:.10g}." for c in sorted(violations,key=lambda c:c['normalized_vector_error'],reverse=True)[:3])
outcome='Die kleine vorab fixierte Entwicklungsregel ist erfüllt; das bleibt ein endlicher lokaler Befund ohne Trainingsfreigabe oder allgemeine Grenze.' if m['state'].endswith('_PASSED') else 'Die vorab fixierte Entwicklungsregel ist **nicht erfüllt**. Fehlergrenzenverletzungen, falsche Freigaben und Abdeckung bleiben getrennte Kriterien. Die Marge wird nicht aus diesen Gegenprüfungsdaten vergrößert; kein Retry oder Seed-/Schwellensweep.'
report=f'''# Feste empirische Fehlermarge: frische Gegenprüfung

Stand {event['berlin']}. Seed4100412, vier neue Train-Demos {', '.join(sel['selected_demos'])}, unveränderter180/20-Split; zwölf H_reset-Anker bei10/50/85%, **336/336** geplante Zweige. Eingefrorener B0-Endcheckpoint/A, null Policyupdates. [Vorabprotokoll](PROTOCOL.md), [effektive Auswahl](selection.json), [fixierte Marge und Herkunft](margin_spec.json).

## Primärer Befund

Lokales B7 je gültigem Anker aus14 nominalen ±0,1-Aktionszweigen bestimmt; tatsächlich geklippte Differenzen und Rang geprüft. **{m['local_identification_fits']} lokale Fits** mit je21 Koeffizienten, kein Policytraining. Sechs getrennte physische ±5-mm-Pfull-Prüfzweige je Anker, keine lokale Identifikation aus diesen Policyantworten. Primär gleiches A/B_local und gleiche Rohantworten; geändert wird nur die Entscheidungsfehlermarge.

epsilon_train=**{m['epsilon_train']:.17g}**, vor neuen Daten als maximales normiertes Vektorresiduum aus48 alten gültigen Trainprüfungen festgelegt. Die neue Regel verlangt r_hat+epsilon_train<0,99 statt r_hat<0,99. Tatsächliche Gegenprüfung r_observed<0,99. Technische Herstellung **{sum(x['technical_passed'] for x in a['physical_audits'])}/12**, dynamische kontaktfreie Domain **{a['eligible_anchors']}/12**. **{m['conditional_policy_cases']}/72** geplante Policyprüfungen numerisch gültig bewertet, {m['unscored_due_domain']} wegen Domain nicht numerisch bewertet; keine ersetzten Frames. Alle tatsächlichen Selbstkontakte bleiben im Label.

| Regel auf gültigen Prüffällen | Richtig freigegeben | Falsch freigegeben | Unnötig verworfen | Richtig verworfen |
|---|---:|---:|---:|---:|
{table}

**{p['bound_violations']}** Fälle überschreiten die alte empirische Vektorfehlergrenze; Maximum neuer normierter Vektorfehler **{p['maximum_normalized_vector_error']}**. Wissenschaftlicher Margenstatus **{m['state']}**, physischer Rohstatus **{r['state']}**. {outcome}

| Phase | Gültige / geplante Prüfungen | Grenze verletzt | Falsche Freigaben roh | Falsche Freigaben mit Marge | Richtig frei mit Marge | Unnötig verworfen mit Marge |
|---|---:|---:|---:|---:|---:|---:|
{strata}

Die Dreiecksungleichung liefert eine obere Ratio nur unter einer tatsächlich geltenden Vektorfehlergrenze. Ein Maximum auf endlichen älteren Trainfällen ist keine solche allgemeine Grenze. Insbesondere kann die Entscheidung zufällig korrekt bleiben, obwohl die Fehlergrenze nicht übertragen wird; umgekehrt ist Nullfehler bei Nullabdeckung keine nützliche Regel. Das ist ein Mechanismustest einer eingefrorenen Policy, kein neuer Trainingseed oder Taskgewinn.

{examples if examples else 'Keine empirische Fehlergrenzenverletzung an den gültigen neuen Prüffällen beobachtet; keine Universalitätsaussage.'}

## Sekundäre Masken und praktische Grenzen

Unveränderte vor Antwortaktionen berechnete M0/M2 separat, ohne Auswahl eines günstigeren Primärsubsets: M0 {f['masks']['M0']['accepted']}/12 akzeptiert, {f['masks']['M0']['false_accept']} dynamische Fehlannahmen, {f['masks']['M0']['false_reject']} unnötige Verwerfungen; M2 {f['masks']['M2']['accepted']}/12 akzeptiert, {f['masks']['M2']['false_accept']} dynamische Fehlannahmen, {f['masks']['M2']['false_reject']} unnötige Verwerfungen. [Vollständige phasengetrennte Zahlen](analysis_repair_001/margin_analysis.json). Keine daraus gewählte neue Maske/Schwelle.

Simulatoridentifikation und feste Controllerersatzgeschichte sind privilegierte Zusatzinformationen. Ein Cache muss korrekt mit Datasetframes/Policyfeatures verbunden werden; eine weiter trainierte Policy kann die um B0 identifizierte Aktionsregion verlassen. Gewichtung, Fehlermarge und volle Aktionsantwort dürfen außerdem den Vergleich nicht durch unkontrollierte Gradientenskalenänderung entscheiden. Diese praktischen Gates und der replizierte Task-/Robustheitsvergleich bleiben offen. Historische Taskgewinne/Literatur/Sensorpilot bleiben getrennte Evidenz; Hauptaussage unverändert, noch keine robuste neue BC-Algorithmusverbesserung.

## Quellen, Verifikation und Kosten

Vor Primärlaunch Auswahl/Marge/Code eingefroren, [source_hashes.json](source_hashes.json), Dataset-/Checkpoint-/Kalibrierhashes in Auswahl und margin_spec. [Physischer Audit](analysis_verification.json) prüft alle gespeicherten Zustände/History/Geometrie/Gates und Quellhashes. [Lokale Identifikation](local_identification.json), [Marginanalyse](analysis_repair_001/margin_analysis.json); unabhängige direkte lineare Lösung statt lstsq und Rohzustands-/Norm-/Fehlerrechnung reproduziert **{v['local_fits_verified']} Fits/{v['policy_cases_verified']} Entscheidungen**, maximaler Matrixunterschied {v['maximum_B_difference']:.3g}, Ratiounterschied {v['maximum_ratio_difference']:.3g}, Fehlerunterschied {v['maximum_error_difference']:.3g}, [Nachweis](analysis_repair_001/margin_verification.json). Gelenkgrenzen kommen aus eingefrorenen Workerassertionen; andere ausgewiesene Gates werden aus Rohzuständen nachgerechnet. Ein reiner Metadatenfehler wiederholte zunächst den globalen geplanten Nenner72 in jeder Phase; [frische Reparatur](analysis_repair_001/REPAIR.json) korrigiert nur diese drei Angaben auf24. Primäre/sekundäre Zählungen, sämtliche Fallentscheidungen, Formel, Marge und Quellen vor Primärlaunch bleiben exakt gleich, Originalanalysen bleiben erhalten. Kein erneut ausgeführter Simulatorzweig oder Training.

Primärworker **{r['elapsed_seconds']:.3f} s**, Supervisor **{processes['error_margin_001']['elapsed_seconds']:.3f} s**. Zähler {json.dumps(r['counts'])}, zwölf explizite Queryforwards zusätzlich, weitere Setupforwards nicht vollständig instrumentiert. Vorprüfung {pref['elapsed_seconds']:.3f} s Worker/{processes['preflight_001']['elapsed_seconds']:.3f} s Supervisor: sechs bekannte Boxcases und alter Frame, sieben Query-/sechs originale synthetische Forwards, eine Rekonstruktion, keine Antwortaktionen/Integration. Unabhängige Queryneuherstellung {q['elapsed_seconds']:.3f} s Worker/{processes['query_verification_001']['elapsed_seconds']:.3f} s Supervisor, zwölf Rekonstruktionen/Queryforwards, exakt gleiche Masken/Kontaktlisten und nominale Zustände, [Nachweis](query_verification_001/result.json); keine Policyantworten/Integration. Analysen erzeugen keine weiteren Physiksteps.

Alle drei Worker und Supervisoren anhand PID/Erzeugungszeit beendet, Jobs geschlossen. Sessioncoordinator/Heartbeat ACTIVE bis unverändert15:11:19 Berlin. [Nächster konkreter Schritt](../NEXT_METHOD_REFERENCE.md): isolierte Lossreferenz und Cache-/Aktionsregion-/Gradientenaudit ohne Policyupdates; keine Integration als angeblich validierter Trainingsalgorithmus.

SHA-256 Rohdaten `{sha(O/'result.json')}`; physischer Audit `{sha(O/'analysis_verification.json')}`; korrigierte Marginanalyse `{sha(O/'analysis_repair_001/margin_analysis.json')}`; unabhängige korrigierte Rechnung `{sha(O/'analysis_repair_001/margin_verification.json')}`. Endcheckpoint/Dataset unverändert.
'''
with (O/'RESULT.md').open('x',encoding='utf-8') as out:out.write(report)
nextreport='''# Lossreferenz und praktische Cachegates, ohne Training

Nach dem fixierten Fehlermargenvergleich, vor neuen Berechnungen. Keine neue Simulator-/Seed-/Schwellensuche und kein weiterer Policytrainingslauf. Der nächste Check setzt den konkreten Methodenkandidaten als isolierte, ausdrücklich experimentelle reine Tensorfunktion um und prüft seine Rechenbarkeit. Die Haupthypothese zu robuster BC-Verbesserung bleibt offen.

1. Tatsächlichen Agentcheck/Session-/Prozessstatus mit Originaldeadline15:11:19 Berlin protokollieren. Frischer method_reference_001, maximal20Minuten einschließlich Gesamtlaufzeitlimit, Safe-stop und selbst endender Supervisor. Keine Änderung bestehender Checkpoints, Datasetlabels oder produktiver Algo-Registrierung.
2. Referenzfunktion erhält delta[N,3], vollständige Aktionsdifferenz[N,7], eingefrorene A[N,3,3]/B[N,7,3], feste nichtnegative Fehlerhülle[N], vorab verfügbare Gewichte[N] und rho. Berechnet geplanten vollen Batchmittelwert von w*relu((norm(deltaA+daB)/norm(delta)+epsilon)^2-rho^2). Kein Renormalisieren durch Zahl gültiger Beispiele; nullgewichtete ungültige Cacheeinträge müssen vor Rechenoperationen sicher ausgeschlossen werden, nicht NaN*0. Geometrie/Dynamik/Masken/epsilon sind konstante Annotationen, nur Policyaktionen erhalten Gradienten. Nullperturbation und nichtfinite aktive Inputs explizit ablehnen. Diese Implementierung ist keine garantierte Stabilitätsmethode, die alte empirische Fehlerhülle bleibt unverändert und wird nicht als allgemeine Grenze behandelt.
3. Auf bereits gespeicherten error_margin_001-Daten, ausdrücklich exploratives Implementationsaudit: vollständige Policyfeaturezuordnung zum HDF5 und Cacheframe/dataset/checkpoint/Sourcehash prüfen (nur tatsächlich konfigurierte Policykeys, nicht sämtliche Simulatorobservables). Baseline/perturbierte Aktionen gegen nominale Identifikationsregion prüfen: komponentenweise zwischen tatsächlich geklipptem ±0,1-Probeendpunkt. Coverage, fehlende/nicht identifizierte Einträge und beide festen DomainmaskenM0/M2 getrennt, nicht dynamische Outcomeeligibility als angeblich vorher verfügbare Maske ausgeben. Wenn ein B nur nach erfolgreicher vollständiger Physikprüfung gecacht wurde, dies als privilegiertes Validitätslabel/Zusatzkosten ausweisen. Keine Auswahl anhand neuer Taskperformance.
4. Erst reine Formel-/Gradientenprüfung, dann wenn technisch möglich eingefrorener B0 ohne Optimizerkonstruktion/-step: Losswerte/Gradientennormen und Anteil aktiver Samples mit/ohne festem epsilon, M0/M2 sowie Aktionsregion separat melden; unbekannte/ungültige Cacheframes im geplanten Nenner. Float64-Richtungsableitung auf vorab erstem gültigen Frame, keine Kinkpunkte als Derivativfehler oder Erfolg ausgeben. Semantik von Sensorperturbation versus physischer Perturbation der tatsächlich verwendeten Policyfeatures prüfen. Alle Parameter-/Checkpoint-/Datasethashes unverändert verifizieren. Kein aus diesem Audit gewähltes Trainingslambda.
5. Referenzcode, wirksame Inputs, Quelle/Hashes/Zeiten und RESULT speichern. Die fachliche Entscheidung muss auch negative Fehlerhüllen-/Maskenbefunde aus error_margin_001 enthalten. Am folgenden letzten Check Gesamtbericht mit Forschungsevidenz und separat Pilotresultat fertigstellen, Kosten/negatives/Limitierungen und minimalen nächsten Methodenvergleich darlegen. Keine Trainingsfreigabe aus bloßer Formelkorrektheit.

Das ist die konkrete Implementierung eines Forschungsentwurfs. Wissenschaftlicher Beitrag kann erst ein kostenkontrolliert replizierter Verbesserungsnachweis mit separat geprüfter Domain/Fehlermarge sein. Bestehende Stable-BC/CCIL-Ideen zu Fehlerdynamik und Gültigkeit sind keine hier erstmals erfundenen Konzepte.
'''
with (S/'NEXT_METHOD_REFERENCE.md').open('x',encoding='utf-8') as out:out.write(nextreport)
event['next_protocol_sha256']=sha(S/'NEXT_METHOD_REFERENCE.md')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
paragraph=f"**Zehnter Check, Trigger14:09 Berlin:** [Fixierte Fehlermarge](error_margin_001/RESULT.md), 336 Zweige, Herstellung{sum(x['technical_passed'] for x in a['physical_audits'])}/12, Domain{a['eligible_anchors']}/12, {m['local_identification_fits']} lokale Fits und null Policyupdates. Marge{m['epsilon_train']:.8g} aus alten48Trainfällen unverändert; auf {m['conditional_policy_cases']}/72 geplanten Gegenprüfungen {p['bound_violations']} Fehlerhüllenverletzungen, falsche Freigaben roh{p['raw']['false_safe']} / mit Marge{p['upper']['false_safe']}, richtig frei mit Marge{p['upper']['true_safe']}, unnötig verworfen{p['upper']['false_reject']}. Wissenschaftlicher Status{m['state']}; kein Vergrößern der Marge, kein weiterer Seed-/Schwellensweep oder Training. Lokale Fits/Entscheidungen direkt nachgerechnet, native Queries12/12 reproduziert, Worker/-Jobs beendet. [NEXT_METHOD_REFERENCE.md](NEXT_METHOD_REFERENCE.md) implementiert als nächste begrenzte Arbeit eine isolierte Lossreferenz plus Cache-/Aktionsregion-/Gradientenaudit ohne Updates, kein validierter produktiver Algorithmus. Monitoring/Originaldeadline15:11:19 unverändert; ältere Aufträge unten erledigte Historie."
p=S/'PILOT_INTERPRETATION.md'; txt=p.read_text(encoding='utf-8'); marker='Diese Fortsetzung ist ein Arbeitsauftrag an den aktiven Agent-Trigger.'; assert txt.count(marker)==1
p.write_text(txt.replace(marker,marker+'\n\n'+paragraph),encoding='utf-8')
p=ROOT/'FORSCHUNGSPLAN.md';txt=p.read_text(encoding='utf-8');marker='## 8. Aktueller Status und nächste fachliche Arbeit';assert txt.count(marker)==1
prefix='experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/'
rootpara=paragraph.replace('(error_margin_001/RESULT.md)','('+prefix+'error_margin_001/RESULT.md)').replace('(NEXT_METHOD_REFERENCE.md)','('+prefix+'NEXT_METHOD_REFERENCE.md)')
p.write_text(txt.replace(marker,marker+'\n\n'+rootpara),encoding='utf-8')
with (S.parent/'RESEARCH_STATUS.md').open('a',encoding='utf-8') as out:out.write('\n\n## Zehnter Check: Fehlerhülle und Entscheidungsabdeckung\n\n'+paragraph.replace('(error_margin_001/RESULT.md)','(supervised_6h_20261004_0904/error_margin_001/RESULT.md)').replace('(NEXT_METHOD_REFERENCE.md)','(supervised_6h_20261004_0904/NEXT_METHOD_REFERENCE.md)')+'\n')
print(json.dumps({k:v for k,v in event.items() if k!='hashes'},indent=2))
